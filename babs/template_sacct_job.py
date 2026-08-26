"""Collect Slurm accounting data for a finished job array.

This python script is copied to ``analysis/code`` by ``babs init`` and is run by
``analysis/code/sacct_job.sh``, which ``babs submit`` submits as an ``afterany``
dependency of every job array it submits.

It calls ``sacct`` for the array job, rolls the per-step accounting rows up into
one row per array task, and appends the result to a CSV file. The point of the
CSV is to accumulate, across batches, the (requested vs. actually used) walltime
and memory of every task, so that the resources a future job needs can be
predicted (e.g. with a linear regression) instead of guessed.

This script only uses the python standard library so that it can run in whatever
environment ``script_preamble`` sets up on the compute node.
"""

import argparse
import csv
import os
import os.path as op
import subprocess
import sys
import time

#: The ``sacct`` fields to request. Fields that the local version of Slurm does
#: not know about are dropped before calling ``sacct`` (see ``supported_fields``).
SACCT_FIELDS = [
    'JobID',
    'JobName',
    'State',
    'ExitCode',
    'Submit',
    'Start',
    'End',
    'Elapsed',
    'ElapsedRaw',
    'Timelimit',
    'Partition',
    'ReqCPUS',
    'NCPUS',
    'ReqNodes',
    'NNodes',
    'ReqMem',
    'ReqTRES',
    'AllocTRES',
    'MaxRSS',
    'AveRSS',
    'MaxVMSize',
    'MaxDiskRead',
    'MaxDiskWrite',
    'TotalCPU',
    'UserCPU',
    'SystemCPU',
    'CPUTimeRAW',
    'NodeList',
    'Cluster',
    'Account',
    'WorkDir',
]

#: Fields that are only reported on the job step rows (``<job_id>.batch`` etc.),
#: not on the allocation row. They are rolled up by taking the maximum.
STEP_MAX_FIELDS = ['MaxRSS', 'AveRSS', 'MaxVMSize', 'MaxDiskRead', 'MaxDiskWrite']

#: Columns of the CSV file this script writes, in order.
OUTPUT_COLUMNS = [
    # identifiers:
    'job_id',
    'task_id',
    'sub_id',
    'ses_id',
    'job_name',
    # outcome:
    'state',
    'exit_code',
    'exit_signal',
    # timing (seconds; the raw strings are kept alongside):
    'submit_time',
    'start_time',
    'end_time',
    'queue_wait_sec',
    'elapsed_sec',
    'timelimit_sec',
    'total_cpu_sec',
    'user_cpu_sec',
    'system_cpu_sec',
    'cpu_time_sec',
    # memory (bytes):
    'req_mem_bytes',
    'req_mem_per',
    'max_rss_bytes',
    'ave_rss_bytes',
    'max_vmsize_bytes',
    # cpus/nodes:
    'req_cpus',
    'alloc_cpus',
    'req_nodes',
    'alloc_nodes',
    # disk (bytes):
    'max_disk_read_bytes',
    'max_disk_write_bytes',
    # raw strings, kept for reference:
    'elapsed',
    'timelimit',
    'req_mem',
    'req_tres',
    'alloc_tres',
    'partition',
    'node_list',
    'cluster',
    'account',
]

_MEMORY_MULTIPLIERS = {
    'K': 1024,
    'M': 1024**2,
    'G': 1024**3,
    'T': 1024**4,
    'P': 1024**5,
}

#: ``ReqMem`` used to carry a trailing 'n' (per node) or 'c' (per cpu) in Slurm
#: versions before 21.08. Newer versions always report the total.
_REQ_MEM_PER = {'n': 'node', 'c': 'cpu'}


def parse_bytes(value):
    """Convert a Slurm memory/disk value into bytes.

    Parameters
    ----------
    value : str or None
        A value such as ``'1234K'``, ``'5.5G'``, ``'0'`` or ``''``.

    Returns
    -------
    float or None
        The value in bytes, or None if it could not be parsed.
    """
    if value is None:
        return None
    value = value.strip()
    if not value or value in ('N/A', 'Unknown'):
        return None
    # drop a trailing per-node/per-cpu marker, e.g. '16Gn':
    if value[-1] in _REQ_MEM_PER:
        value = value[:-1]
    if not value:
        return None
    multiplier = 1
    if value[-1].upper() in _MEMORY_MULTIPLIERS:
        multiplier = _MEMORY_MULTIPLIERS[value[-1].upper()]
        value = value[:-1]
    try:
        return float(value) * multiplier
    except ValueError:
        return None


def parse_req_mem(value):
    """Split ``ReqMem`` into a value in bytes and what it is requested per.

    Parameters
    ----------
    value : str or None
        A value such as ``'16G'`` (Slurm >= 21.08) or ``'4Gc'``/``'16Gn'``
        (older Slurm, meaning per cpu / per node).

    Returns
    -------
    tuple of (float or None, str)
        The memory in bytes and one of ``'node'``, ``'cpu'`` or ``''``.
    """
    if value is None:
        return None, ''
    value = value.strip()
    per = _REQ_MEM_PER.get(value[-1], '') if value else ''
    return parse_bytes(value), per


def parse_duration(value):
    """Convert a Slurm duration into seconds.

    Parameters
    ----------
    value : str or None
        A duration such as ``'2-03:04:05'``, ``'03:04:05'``, ``'04:05.123'``
        or ``'UNLIMITED'``.

    Returns
    -------
    float or None
        The duration in seconds, or None if it is not a finite duration.
    """
    if value is None:
        return None
    value = value.strip()
    if not value or value in ('UNLIMITED', 'Partition_Limit', 'INVALID', 'N/A'):
        return None

    days = 0
    if '-' in value:
        days_str, _, value = value.partition('-')
        try:
            days = int(days_str)
        except ValueError:
            return None

    parts = value.split(':')
    if len(parts) > 3:
        return None
    try:
        # pad to hours:minutes:seconds; 'MM:SS' and 'SS' are both valid
        parts = [0.0] * (3 - len(parts)) + [float(part) for part in parts]
    except ValueError:
        return None
    hours, minutes, seconds = parts
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_int(value):
    """Convert a Slurm integer field into an int, or None if it is not one."""
    if value is None:
        return None
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        return None


def parse_exit_code(value):
    """Split Slurm's ``<exit code>:<signal>`` into two ints."""
    if not value or ':' not in value:
        return None, None
    code, _, signal = value.partition(':')
    return parse_int(code), parse_int(signal)


def split_job_id(sacct_job_id):
    """Split a ``sacct`` JobID into its array job id, task id and step.

    Parameters
    ----------
    sacct_job_id : str
        A JobID as reported by ``sacct``, e.g. ``'123_4'``, ``'123_4.batch'``,
        ``'123_4.extern'``, ``'123.batch'`` or ``'123_[5-8]'``.

    Returns
    -------
    tuple of (str, int or None, str)
        The ``<array job id>_<task id>`` base, the task id (None if this row is
        not a single array task) and the step name ('' for the allocation row).
    """
    base, _, step = sacct_job_id.partition('.')
    task_id = None
    if '_' in base:
        task_id = parse_int(base.split('_', 1)[1])
    return base, task_id, step


def supported_fields(requested_fields):
    """Drop the fields that the local ``sacct`` does not know about.

    ``sacct`` errors out on an unknown field, and the available fields differ
    between Slurm versions, so ask ``sacct`` what it supports first.

    Parameters
    ----------
    requested_fields : list of str
        The fields we would like to request.

    Returns
    -------
    list of str
        The subset of ``requested_fields`` that this ``sacct`` supports. If the
        supported fields cannot be determined, ``requested_fields`` is returned
        unchanged.
    """
    try:
        proc = subprocess.run(
            ['sacct', '--helpformat'],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return list(requested_fields)

    available = {field.strip().lower() for field in proc.stdout.split()}
    if not available:
        return list(requested_fields)

    keep = [field for field in requested_fields if field.lower() in available]
    dropped = [field for field in requested_fields if field.lower() not in available]
    if dropped:
        print(f'This version of sacct does not report: {", ".join(dropped)}')
    # JobID is what every row is keyed on, so it is not optional:
    if 'JobID' not in keep:
        keep.insert(0, 'JobID')
    return keep


def run_sacct(job_id, fields):
    """Call ``sacct`` for one job and return the parsed rows.

    Parameters
    ----------
    job_id : str
        The id of the (array) job to request accounting data for.
    fields : list of str
        The ``sacct`` fields to request.

    Returns
    -------
    list of dict
        One dict per ``sacct`` row, mapping field name to the raw string value.

    Raises
    ------
    RuntimeError
        If the ``sacct`` call fails.
    """
    commandlist = [
        'sacct',
        '-j',
        str(job_id),
        '--parsable2',  # '|'-delimited, no trailing delimiter
        '--noheader',
        '--format=' + ','.join(fields),
    ]
    proc = subprocess.run(commandlist, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f'sacct failed with return code {proc.returncode}\nstderr: {proc.stderr}'
        )

    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        values = line.split('|')
        if len(values) != len(fields):
            print(f'Skipping unparsable sacct row: {line}')
            continue
        rows.append(dict(zip(fields, values, strict=False)))
    return rows


def collect_sacct_rows(job_id, fields, n_retries=5, retry_delay=30):
    """Get the ``sacct`` rows for a job, waiting for the accounting db to catch up.

    Slurm writes accounting data asynchronously, so a job that has just finished
    may not be in the database yet when this dependency job starts.

    Parameters
    ----------
    job_id : str
        The id of the (array) job to request accounting data for.
    fields : list of str
        The ``sacct`` fields to request.
    n_retries : int
        How many extra attempts to make if ``sacct`` returns nothing.
    retry_delay : int
        Seconds to wait between attempts.

    Returns
    -------
    list of dict
        One dict per ``sacct`` row.
    """
    for attempt in range(n_retries + 1):
        rows = run_sacct(job_id, fields)
        if rows:
            return rows
        if attempt < n_retries:
            print(f'sacct returned no rows for job {job_id}; retrying in {retry_delay}s')
            time.sleep(retry_delay)
    return []


def rollup_task_rows(rows):
    """Roll ``sacct`` rows up into one record per array task.

    ``sacct`` reports an allocation row per task plus one row per job step (e.g.
    ``.batch``, ``.extern``). The requested resources are on the allocation row
    while the used memory/disk are on the step rows, so both are needed.

    Parameters
    ----------
    rows : list of dict
        The rows returned by :func:`run_sacct`.

    Returns
    -------
    dict
        Maps ``<array job id>_<task id>`` to a dict with the merged fields.
    """
    tasks = {}
    for row in rows:
        base, task_id, step = split_job_id(row.get('JobID', ''))
        if task_id is None:
            # not a single array task: either a non-array job or a pending
            # array range such as '123_[5-8]'. Nothing to account for.
            continue
        task = tasks.setdefault(base, {'task_id': task_id})
        if not step:
            # the allocation row carries the requested resources:
            task.update(row)
            task['task_id'] = task_id
        else:
            for field in STEP_MAX_FIELDS:
                value = parse_bytes(row.get(field))
                if value is None:
                    continue
                previous = task.get(field + '_bytes')
                if previous is None or value > previous:
                    task[field + '_bytes'] = value
    return tasks


def build_output_row(job_id, base, task):
    """Turn one rolled-up task into a row of the output CSV.

    Parameters
    ----------
    job_id : str
        The id of the array job being collected.
    base : str
        The ``<array job id>_<task id>`` key of this task.
    task : dict
        The merged ``sacct`` fields for this task.

    Returns
    -------
    dict
        A dict keyed by :data:`OUTPUT_COLUMNS`.
    """
    exit_code, exit_signal = parse_exit_code(task.get('ExitCode'))
    req_mem_bytes, req_mem_per = parse_req_mem(task.get('ReqMem'))
    req_cpus = parse_int(task.get('ReqCPUS'))
    alloc_cpus = parse_int(task.get('NCPUS'))
    # older Slurm reports memory per cpu; scale it so the column is comparable:
    if req_mem_bytes is not None and req_mem_per == 'cpu':
        n_cpus = alloc_cpus or req_cpus
        if n_cpus:
            req_mem_bytes = req_mem_bytes * n_cpus

    # `State` can be e.g. 'CANCELLED by 1234':
    state = (task.get('State') or '').split(' ')[0]

    elapsed_sec = parse_int(task.get('ElapsedRaw'))
    if elapsed_sec is None:
        elapsed_sec = parse_duration(task.get('Elapsed'))

    submit_time = (task.get('Submit') or '').strip()
    start_time = (task.get('Start') or '').strip()
    queue_wait_sec = None
    if submit_time and start_time:
        # both are ISO-ish local times, e.g. '2026-08-26T10:11:12'
        try:
            from datetime import datetime

            queue_wait_sec = (
                datetime.fromisoformat(start_time) - datetime.fromisoformat(submit_time)
            ).total_seconds()
        except ValueError:
            queue_wait_sec = None

    return {
        'job_id': parse_int(base.split('_', 1)[0]) or job_id,
        'task_id': task.get('task_id'),
        'sub_id': '',
        'ses_id': '',
        'job_name': task.get('JobName', ''),
        'state': state,
        'exit_code': exit_code,
        'exit_signal': exit_signal,
        'submit_time': submit_time,
        'start_time': start_time,
        'end_time': (task.get('End') or '').strip(),
        'queue_wait_sec': queue_wait_sec,
        'elapsed_sec': elapsed_sec,
        'timelimit_sec': parse_duration(task.get('Timelimit')),
        'total_cpu_sec': parse_duration(task.get('TotalCPU')),
        'user_cpu_sec': parse_duration(task.get('UserCPU')),
        'system_cpu_sec': parse_duration(task.get('SystemCPU')),
        'cpu_time_sec': parse_int(task.get('CPUTimeRAW')),
        'req_mem_bytes': req_mem_bytes,
        'req_mem_per': req_mem_per,
        'max_rss_bytes': task.get('MaxRSS_bytes'),
        'ave_rss_bytes': task.get('AveRSS_bytes'),
        'max_vmsize_bytes': task.get('MaxVMSize_bytes'),
        'req_cpus': req_cpus,
        'alloc_cpus': alloc_cpus,
        'req_nodes': parse_int(task.get('ReqNodes')),
        'alloc_nodes': parse_int(task.get('NNodes')),
        'max_disk_read_bytes': task.get('MaxDiskRead_bytes'),
        'max_disk_write_bytes': task.get('MaxDiskWrite_bytes'),
        'elapsed': (task.get('Elapsed') or '').strip(),
        'timelimit': (task.get('Timelimit') or '').strip(),
        'req_mem': (task.get('ReqMem') or '').strip(),
        'req_tres': (task.get('ReqTRES') or '').strip(),
        'alloc_tres': (task.get('AllocTRES') or '').strip(),
        'partition': (task.get('Partition') or '').strip(),
        'node_list': (task.get('NodeList') or '').strip(),
        'cluster': (task.get('Cluster') or '').strip(),
        'account': (task.get('Account') or '').strip(),
    }


def read_task_id_map(job_submit_csv, job_id):
    """Read the ``task_id`` -> subject/session mapping of the submitted batch.

    Parameters
    ----------
    job_submit_csv : str or None
        Path to the CSV that ``babs submit`` wrote for this batch. It has the
        columns ``sub_id``, ``job_id``, ``task_id`` and, for session-level
        processing, ``ses_id``.
    job_id : str
        The id of the array job being collected. Rows belonging to a different
        job id are ignored, so a stale file cannot mislabel the results.

    Returns
    -------
    dict
        Maps task id to a dict with ``sub_id`` and ``ses_id``.
    """
    if not job_submit_csv or not op.exists(job_submit_csv):
        return {}

    task_id_map = {}
    with open(job_submit_csv, newline='') as f:
        for row in csv.DictReader(f):
            row_job_id = parse_int(row.get('job_id', ''))
            if row_job_id is not None and str(row_job_id) != str(job_id):
                continue
            task_id = parse_int(row.get('task_id', ''))
            if task_id is None:
                continue
            task_id_map[task_id] = {
                'sub_id': (row.get('sub_id') or '').strip(),
                'ses_id': (row.get('ses_id') or '').strip(),
            }
    if not task_id_map:
        print(f'No rows for job {job_id} in {job_submit_csv}; not adding subject/session ids')
    return task_id_map


def append_rows(output_csv, output_rows):
    """Append rows to the resources CSV, skipping tasks that are already in it.

    The file accumulates across batches, so it is only ever appended to. The
    header is written when the file is created.

    Parameters
    ----------
    output_csv : str
        Path to the CSV file to append to.
    output_rows : list of dict
        Rows keyed by :data:`OUTPUT_COLUMNS`.

    Returns
    -------
    int
        How many rows were written.
    """
    import fcntl

    output_dir = op.dirname(op.abspath(output_csv))
    if output_dir and not op.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 'a+' so the file is created if needed, and locked before it is read:
    with open(output_csv, 'a+', newline='') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            existing = f.read()
            already_recorded = set()
            if existing.strip():
                for row in csv.DictReader(existing.splitlines()):
                    already_recorded.add((row.get('job_id'), row.get('task_id')))

            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction='ignore')
            if not existing.strip():
                writer.writeheader()

            n_written = 0
            for row in output_rows:
                if (str(row['job_id']), str(row['task_id'])) in already_recorded:
                    continue
                writer.writerow(row)
                n_written += 1
            return n_written
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def cli():
    parser = argparse.ArgumentParser(
        description=(
            'Collect the resources Slurm recorded for a finished job array and '
            'append them to a CSV file.'
        )
    )
    parser.add_argument(
        '--job-id',
        '--job_id',
        help='The id of the job array to collect accounting data for.',
        required=True,
    )
    parser.add_argument(
        '--output',
        help='Path of the CSV file to append the collected resources to.',
        required=True,
    )
    parser.add_argument(
        '--job-submit-csv',
        '--job_submit_csv',
        help=(
            'Path of the CSV that `babs submit` wrote for this batch, used to '
            'label each task with its subject (and session) id.'
        ),
        default=None,
    )
    parser.add_argument(
        '--n-retries',
        '--n_retries',
        help='How many times to retry if sacct has no data for the job yet.',
        type=int,
        default=5,
    )
    parser.add_argument(
        '--retry-delay',
        '--retry_delay',
        help='Seconds to wait between sacct attempts.',
        type=int,
        default=30,
    )
    return parser


def main():
    args = cli().parse_args()

    fields = supported_fields(SACCT_FIELDS)
    rows = collect_sacct_rows(
        args.job_id,
        fields,
        n_retries=args.n_retries,
        retry_delay=args.retry_delay,
    )
    if not rows:
        print(f'sacct has no accounting data for job {args.job_id}; nothing collected.')
        return 1

    tasks = rollup_task_rows(rows)
    if not tasks:
        print(f'No array tasks found in the sacct output for job {args.job_id}.')
        return 1

    task_id_map = read_task_id_map(args.job_submit_csv, args.job_id)

    output_rows = []
    for base in sorted(tasks, key=lambda key: tasks[key]['task_id']):
        output_row = build_output_row(args.job_id, base, tasks[base])
        output_row.update(task_id_map.get(output_row['task_id'], {}))
        output_rows.append(output_row)

    n_written = append_rows(args.output, output_rows)
    print(
        f'Collected resources for {len(output_rows)} tasks of job {args.job_id}; '
        f'wrote {n_written} new rows to {args.output}'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
