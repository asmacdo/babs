import subprocess
from pathlib import Path

import datalad.api as dlapi
import pytest

from babs.bootstrap import BABSBootstrap
from babs.templateflow import (
    TEMPLATEFLOW_PATH_IN_BABS,
    TemplateflowConfig,
    templateflow_from_config,
)

SOURCE = 'https://github.com/templateflow/templateflow.git'


def _config(**section):
    return {'templateflow': section}


def test_absent_section_is_none():
    assert templateflow_from_config({'input_datasets': {}}) is None


def test_minimal_section():
    tf = templateflow_from_config(
        _config(source=SOURCE, required=['tpl-OASIS30ANTs/tpl-OASIS30ANTs_res-01_T1w.nii.gz'])
    )
    assert tf == TemplateflowConfig(
        source=SOURCE,
        version=None,
        required=['tpl-OASIS30ANTs/tpl-OASIS30ANTs_res-01_T1w.nii.gz'],
    )


def test_templates_are_the_distinct_first_components():
    tf = templateflow_from_config(
        _config(
            source=SOURCE,
            version='abc123',
            required=[
                'tpl-MNI152NLin2009cAsym/*_res-02_T1w.nii.gz',
                'tpl-MNI152NLin2009cAsym/*_res-02_desc-brain_mask.nii.gz',
                'tpl-OASIS30ANTs',
            ],
        )
    )
    assert tf.version == 'abc123'
    assert tf.templates == ['tpl-MNI152NLin2009cAsym', 'tpl-OASIS30ANTs']


@pytest.mark.parametrize(
    ('section', 'message'),
    [
        ({'source': SOURCE, 'required': ['tpl-X/a'], 'versoin': 'x'}, 'Unknown key'),
        ({'required': ['tpl-X/a']}, 'source'),
        ({'source': '', 'required': ['tpl-X/a']}, 'source'),
        ({'source': SOURCE, 'version': '', 'required': ['tpl-X/a']}, 'version'),
        ({'source': SOURCE}, 'required'),
        ({'source': SOURCE, 'required': []}, 'required'),
        ({'source': SOURCE, 'required': 'tpl-X/a'}, 'required'),
        ({'source': SOURCE, 'required': ['/abs/tpl-X/a']}, 'relative'),
        ({'source': SOURCE, 'required': ['tpl-X/../tpl-Y/a']}, r"'\.\.'"),
        ({'source': SOURCE, 'required': ['tpl-*/a']}, 'literal template'),
        ({'source': SOURCE, 'required': ['sub-01/a']}, 'literal template'),
        ({'source': SOURCE, 'required': ['']}, 'non-empty'),
    ],
)
def test_malformed_section_is_refused(section, message):
    with pytest.raises(ValueError, match=message):
        templateflow_from_config(_config(**section))


def test_section_must_be_a_mapping():
    with pytest.raises(TypeError, match='mapping'):
        templateflow_from_config({'templateflow': ['tpl-X/a']})


# --- registration at `babs init` -------------------------------------------------


def _git(cwd, *args):
    return subprocess.run(
        ['git', *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def fake_templateflow(tmp_path):
    """A templateflow-shaped superdataset with one `tpl-Foo` subdataset, two commits.

    Returns the path and the first commit, so a pinned `version` has somewhere to go.
    """
    tf = dlapi.create(tmp_path / 'templateflow')
    dlapi.create(dataset=tf.path, path=tmp_path / 'templateflow' / 'tpl-Foo')
    first = _git(tf.path, 'rev-parse', 'HEAD')
    (tmp_path / 'templateflow' / 'README').write_text('later\n')
    tf.save(message='a later commit')
    return tmp_path / 'templateflow', first


def _bootstrap(tmp_path, **section):
    bs = BABSBootstrap(tmp_path / 'project')
    dlapi.create(bs.analysis_path)
    bs.templateflow = templateflow_from_config({'templateflow': section})
    return bs


def _registered_commit(bs):
    return _git(bs.analysis_path, 'rev-parse', f'HEAD:{TEMPLATEFLOW_PATH_IN_BABS}')


def test_register_keeps_source_version_when_unpinned(tmp_path, fake_templateflow):
    tf_path, _ = fake_templateflow
    bs = _bootstrap(tmp_path, source=str(tf_path), required=['tpl-Foo/*'])
    bs._register_templateflow()
    assert _registered_commit(bs) == _git(tf_path, 'rev-parse', 'HEAD')
    # only templateflow itself is installed; the template subdataset waits for the job
    assert not (Path(bs.analysis_path) / TEMPLATEFLOW_PATH_IN_BABS / 'tpl-Foo' / '.git').exists()
    assert _git(bs.analysis_path, 'status', '--porcelain') == ''


def test_register_pins_version(tmp_path, fake_templateflow):
    tf_path, first = fake_templateflow
    bs = _bootstrap(tmp_path, source=str(tf_path), version=first, required=['tpl-Foo/*'])
    bs._register_templateflow()
    assert _registered_commit(bs) == first
    assert _git(bs.analysis_path, 'status', '--porcelain') == ''


def test_register_refuses_unknown_version(tmp_path, fake_templateflow):
    tf_path, _ = fake_templateflow
    bs = _bootstrap(tmp_path, source=str(tf_path), version='no-such-ref', required=['tpl-Foo/*'])
    with pytest.raises(ValueError, match='could not be checked out'):
        bs._register_templateflow()


def test_register_refuses_unknown_template(tmp_path, fake_templateflow):
    tf_path, _ = fake_templateflow
    bs = _bootstrap(tmp_path, source=str(tf_path), required=['tpl-Bar/*'])
    with pytest.raises(ValueError, match='tpl-Bar, which is not a template subdataset'):
        bs._register_templateflow()
