import pytest

from babs.templateflow import TemplateflowConfig, templateflow_from_config

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
