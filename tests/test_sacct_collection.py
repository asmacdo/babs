"""Tests for collecting the resources Slurm recorded for a batch of jobs.

`babs submit` submits one `afterany` job per batch, which runs
`analysis/code/sacct_job.py` once the whole job array has finished. That script
calls `sacct`, rolls the per-step accounting rows up into one row per array task,
and appends them to `analysis/code/job_resources.csv`.
"""

import csv
import os
import os.path as op
import subprocess
import sys
from unittest import mock

import pytest
import yaml

from babs import template_sacct_job as sacct_job
from babs.container import Container
from babs.generate_submit_script import generate_sacct_submit_script
from babs.scheduler import submit_sacct_job
from babs.system import System

CLUSTER_RESOURCES = {
    'interpreting_shell': '/bin/bash -l',
    'hard_memory_limit': '100G',
    'hard_runtime_limit': '48:00:00',
    'number_of_cpus': '16',
    'customized_text': '#SBATCH -A myaccount\n#SBATCH -p normal',
}


def _sacct_row(**fields):
    """Build one '|'-delimited sacct row with all of SACCT_FIELDS."""
    return '|'.join(str(fields.get(field, '')) for field in sacct_job.SACCT_FIELDS)


#: One finished task with a `.batch` and an `.extern` step, in the shape
#: `sacct --parsable2 --noheader` returns them.
ALLOCATION_FIELDS = {
    'State': 'COMPLETED',
    'ExitCode': '0:0',
    'Submit': '2026-08-26T10:00:00',
    'Start': '2026-08-26T10:02:30',
    'End': '2026-08-26T12:34:56',
    'Elapsed': '02:32:26',
    'ElapsedRaw': '9146',
    'Timelimit': '1-00:00:00',
    'Partition': 'normal',
    'ReqCPUS': '4',
    'NCPUS': '4',
    'ReqNodes': '1',
    'NNodes': '1',
    'ReqMem': '32G',
    'ReqTRES': 'billing=4,cpu=4,mem=32G,node=1',
    'AllocTRES': 'billing=4,cpu=4,mem=32G,node=1',
    'TotalCPU': '36:34:00',
    'UserCPU': '36:00:00',
    'SystemCPU': '00:34:00',
    'CPUTimeRAW': '131688',
    'NodeList': 'node042',
    'Cluster': 'mycluster',
    'Account': 'myaccount',
}


@pytest.fixture
def sacct_output():
    """A realistic `sacct` output for a 3-task array, one task of which failed."""
    step_fields = {
        key: value
        for key, value in ALLOCATION_FIELDS.items()
        if key not in ('Timelimit', 'Partition', 'ReqMem', 'ReqTRES')
    }
    lines = [
        _sacct_row(JobID='9911_1', JobName='fmr', **ALLOCATION_FIELDS),
        # the batch step is where the memory that was actually used is reported:
        _sacct_row(
            JobID='9911_1.batch',
            JobName='batch',
            MaxRSS='18234156K',
            AveRSS='12000000K',
            MaxVMSize='19500000K',
            MaxDiskRead='1024.50M',
            MaxDiskWrite='512.25M',
            **step_fields,
        ),
        # the extern step uses much less; it must not win the roll-up:
        _sacct_row(
            JobID='9911_1.extern',
            JobName='extern',
            MaxRSS='1024K',
            AveRSS='900K',
            MaxVMSize='5000K',
            **step_fields,
        ),
        # a task that ran out of time; its step is reported as CANCELLED:
        _sacct_row(
            JobID='9911_2',
            JobName='fmr',
            **{**ALLOCATION_FIELDS, 'State': 'TIMEOUT', 'NodeList': 'node043'},
        ),
        _sacct_row(
            JobID='9911_2.batch',
            JobName='batch',
            MaxRSS='30500000K',
            **{**step_fields, 'State': 'CANCELLED by 501', 'ExitCode': '0:15'},
        ),
        # a task that failed before any step was recorded, on an older Slurm that
        # reports the requested memory per cpu:
        _sacct_row(
            JobID='9911_3',
            JobName='fmr',
            **{
                **ALLOCATION_FIELDS,
                'State': 'FAILED',
                'ExitCode': '1:0',
                'ReqMem': '8Gc',
                'Elapsed': '00:02:28',
                'ElapsedRaw': '148',
                'TotalCPU': '00:04:10.500',
            },
        ),
        # a pending range of array tasks, which has nothing to account for:
        _sacct_row(JobID='9911_[4-6]', JobName='fmr', State='PENDING'),
    ]
    return '\n'.join(lines) + '\n'


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('1024K', 1024 * 1024),
        ('5.5G', 5.5 * 1024**3),
        ('32G', 32 * 1024**3),
        ('16Gn', 16 * 1024**3),  # older Slurm: per node
        ('8Gc', 8 * 1024**3),  # older Slurm: per cpu
        ('0', 0),
        ('', None),
        ('N/A', None),
        (None, None),
    ],
)
def test_parse_bytes(value, expected):
    assert sacct_job.parse_bytes(value) == expected


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('02:32:26', 9146),
        ('1-00:00:00', 86400),
        ('2-03:04:05', 2 * 86400 + 3 * 3600 + 4 * 60 + 5),
        ('04:05.500', 4 * 60 + 5.5),
        ('00:00:00', 0),
        ('UNLIMITED', None),
        ('Partition_Limit', None),
        ('', None),
        (None, None),
    ],
)
def test_parse_duration(value, expected):
    assert sacct_job.parse_duration(value) == expected


@pytest.mark.parametrize(
    ('sacct_job_id', 'expected'),
    [
        ('9911_1', ('9911_1', 1, '')),
        ('9911_1.batch', ('9911_1', 1, 'batch')),
        ('9911_12.extern', ('9911_12', 12, 'extern')),
        ('9911_[4-6]', ('9911_[4-6]', None, '')),  # a pending array range
        ('9911', ('9911', None, '')),  # not an array job
    ],
)
def test_split_job_id(sacct_job_id, expected):
    assert sacct_job.split_job_id(sacct_job_id) == expected


def test_parse_req_mem():
    assert sacct_job.parse_req_mem('32G') == (32 * 1024**3, '')
    assert sacct_job.parse_req_mem('8Gc') == (8 * 1024**3, 'cpu')
    assert sacct_job.parse_req_mem('16Gn') == (16 * 1024**3, 'node')


def test_rollup_takes_the_max_over_the_job_steps(sacct_output):
    rows = [
        dict(zip(sacct_job.SACCT_FIELDS, line.split('|'), strict=True))
        for line in sacct_output.splitlines()
    ]
    tasks = sacct_job.rollup_task_rows(rows)

    # the pending array range is not a task, so it is not collected:
    assert sorted(tasks) == ['9911_1', '9911_2', '9911_3']

    # the `.batch` step used more than the `.extern` step, so it wins:
    assert tasks['9911_1']['MaxRSS_bytes'] == 18234156 * 1024
    # the state comes from the allocation row, not from the steps:
    assert tasks['9911_1']['State'] == 'COMPLETED'
    assert tasks['9911_2']['State'] == 'TIMEOUT'
    # a task with no step rows has no used-memory to report:
    assert 'MaxRSS_bytes' not in tasks['9911_3']


def test_collect_and_write(tmp_path, sacct_output):
    """The collected CSV has one labeled row per task and is only appended to."""
    job_submit_csv = tmp_path / 'job_submit_9911.csv'
    job_submit_csv.write_text(
        'sub_id,ses_id,job_id,task_id\n'
        'sub-0001,ses-01,9911,1\n'
        'sub-0002,ses-01,9911,2\n'
        'sub-0003,ses-02,9911,3\n'
    )
    output_csv = tmp_path / 'job_resources.csv'

    def fake_run(commandlist, **kwargs):
        if commandlist[1] == '--helpformat':
            return subprocess.CompletedProcess(
                commandlist, 0, stdout=' '.join(sacct_job.SACCT_FIELDS), stderr=''
            )
        assert '-j' in commandlist
        assert '9911' in commandlist
        return subprocess.CompletedProcess(commandlist, 0, stdout=sacct_output, stderr='')

    argv = [
        'sacct_job.py',
        '--job-id',
        '9911',
        '--output',
        str(output_csv),
        '--job-submit-csv',
        str(job_submit_csv),
        '--n-retries',
        '0',
    ]
    with mock.patch.object(subprocess, 'run', side_effect=fake_run):
        with mock.patch.object(sys, 'argv', argv):
            assert sacct_job.main() == 0

    rows = list(csv.DictReader(output_csv.open()))
    assert [row['task_id'] for row in rows] == ['1', '2', '3']
    assert [row['sub_id'] for row in rows] == ['sub-0001', 'sub-0002', 'sub-0003']
    assert [row['ses_id'] for row in rows] == ['ses-01', 'ses-01', 'ses-02']

    # what the regression needs: requested vs. actually used walltime and memory
    assert rows[0]['state'] == 'COMPLETED'
    assert float(rows[0]['elapsed_sec']) == 9146
    assert float(rows[0]['timelimit_sec']) == 86400
    assert float(rows[0]['max_rss_bytes']) == 18234156 * 1024
    assert float(rows[0]['req_mem_bytes']) == 32 * 1024**3
    assert float(rows[0]['queue_wait_sec']) == 150

    # a per-cpu memory request is scaled to the total, so the column is comparable:
    assert float(rows[2]['req_mem_bytes']) == 8 * 1024**3 * 4
    assert rows[2]['req_mem_per'] == 'cpu'
    assert rows[2]['max_rss_bytes'] == ''

    # collecting the same job again does not duplicate its rows:
    with mock.patch.object(subprocess, 'run', side_effect=fake_run):
        with mock.patch.object(sys, 'argv', argv):
            assert sacct_job.main() == 0
    assert len(list(csv.DictReader(output_csv.open()))) == 3


def test_a_stale_mapping_is_not_used(tmp_path, sacct_output):
    """A `job_submit.csv` from another batch must not mislabel the tasks."""
    stale_csv = tmp_path / 'job_submit.csv'
    stale_csv.write_text('sub_id,ses_id,job_id,task_id\nsub-9999,ses-99,10000,1\n')

    task_id_map = sacct_job.read_task_id_map(str(stale_csv), '9911')
    assert task_id_map == {}


def test_unsupported_sacct_fields_are_dropped():
    """`sacct` errors out on a field the local Slurm does not know about."""

    def fake_run(commandlist, **kwargs):
        return subprocess.CompletedProcess(
            commandlist, 0, stdout='JobID JobName State Elapsed', stderr=''
        )

    with mock.patch.object(subprocess, 'run', side_effect=fake_run):
        fields = sacct_job.supported_fields(sacct_job.SACCT_FIELDS)
    assert fields == ['JobID', 'JobName', 'State', 'Elapsed']


def test_sacct_script_requests_its_own_resources():
    """The accounting job must not request the BIDS App's resources."""
    script = generate_sacct_submit_script(
        queue_system='slurm',
        cluster_resources_config=CLUSTER_RESOURCES,
        script_preamble='source activate babs',
        job_scratch_directory='/tmp',
        sacct_python_script='/proj/analysis/code/sacct_job.py',
        job_resources_path='/proj/analysis/code/job_resources.csv',
    )
    assert script.startswith('#!/bin/bash -l')
    # the cluster-specific directives the user set are kept:
    assert '#SBATCH -A myaccount' in script
    assert '#SBATCH -p normal' in script
    # but the BIDS App's resources are not:
    assert '100G' not in script
    assert '48:00:00' not in script
    assert '#SBATCH --mem=2G' in script
    assert '#SBATCH --cpus-per-task=1' in script
    assert '#SBATCH --time=00:20:00' in script
    assert '/proj/analysis/code/sacct_job.py' in script
    assert '--output "/proj/analysis/code/job_resources.csv"' in script

    subprocess.run(['bash', '-n', '-'], input=script, text=True, check=True)


def test_sacct_submit_template(tmp_path):
    """The submitted command depends on the array job with `afterany`."""

    class FakeBABS:
        analysis_path = '/proj/analysis'

    container = Container.__new__(Container)
    container.container_name = 'fmriprep-24-1-1'

    yaml_path = tmp_path / 'submit_sacct_job_template.yaml'
    container.generate_sacct_job_submit_template(str(yaml_path), FakeBABS(), System('slurm'))

    templates = yaml.safe_load(yaml_path.read_text())
    cmd = templates['cmd_template']
    assert '${array_job_id}' in cmd
    assert '${job_submit_csv}' in cmd

    cmd = cmd.replace('${array_job_id}', '9911')
    cmd = cmd.replace('${job_submit_csv}', '/proj/analysis/logs/job_submit_9911.csv')
    assert cmd.split() == [
        'sbatch',
        '--dependency=afterany:9911',
        '--kill-on-invalid-dep=yes',
        '--job-name',
        'fmr_sacct',
        '-e',
        '/proj/analysis/logs/fmr_sacct.e%A',
        '-o',
        '/proj/analysis/logs/fmr_sacct.o%A',
        '/proj/analysis/code/sacct_job.sh',
        '9911',
        '/proj/analysis/logs/job_submit_9911.csv',
    ]


def test_submit_sacct_job_without_a_template(tmp_path):
    """A project created before this feature existed must still be submittable."""
    os.makedirs(op.join(tmp_path, 'code'))
    assert submit_sacct_job(str(tmp_path), 'slurm', 9911, 'job_submit.csv') is None
