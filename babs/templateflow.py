"""This module is for the optional `templateflow` section of the container config."""

import re
from dataclasses import dataclass

# Where templateflow is registered as a subdataset, relative to `analysis`.
TEMPLATEFLOW_PATH_IN_BABS = 'sourcedata/templateflow'

_ALLOWED_KEYS = {'source', 'version', 'required'}
_TEMPLATE_DIR = re.compile(r'^tpl-[A-Za-z0-9]+$')


@dataclass(frozen=True)
class TemplateflowConfig:
    """The `templateflow` section of the container config, validated.

    Attributes
    ----------
    source: str
        Anything `datalad clone` accepts: the templateflow superdataset to register.
    version: str or None
        A commit-ish to check out after cloning; None keeps whatever `source` is at.
    required: list of str
        Patterns, relative to the templateflow root, of the files every job fetches.
        Each starts with a literal `tpl-<name>/` directory.
    """

    source: str
    version: str | None
    required: list[str]

    @property
    def templates(self):
        """The `tpl-*` subdatasets the `required` patterns reach, sorted."""
        return sorted({pattern.split('/', 1)[0] for pattern in self.required})


def templateflow_from_config(config):
    """Read and validate the optional `templateflow` section of a container config.

    Parameters
    ----------
    config: dict
        The whole container config.

    Returns
    -------
    TemplateflowConfig or None
        None when the section is absent.

    Raises
    ------
    TypeError
        If the section is not a mapping.
    ValueError
        If the section is present but malformed.
    """
    section = config.get('templateflow')
    if section is None:
        return None
    if not isinstance(section, dict):
        raise TypeError('`templateflow` must be a mapping with `source` and `required`.')

    unknown = set(section) - _ALLOWED_KEYS
    if unknown:
        raise ValueError(
            f'Unknown key(s) in `templateflow`: {sorted(unknown)}. '
            f'Allowed: {sorted(_ALLOWED_KEYS)}.'
        )

    source = section.get('source')
    if not isinstance(source, str) or not source:
        raise ValueError('`templateflow.source` must be a non-empty string.')

    version = section.get('version')
    if version is not None and (not isinstance(version, str) or not version):
        raise ValueError('`templateflow.version`, when given, must be a non-empty string.')

    required = section.get('required')
    if not isinstance(required, list) or not required:
        raise ValueError('`templateflow.required` must be a non-empty list of patterns.')
    for pattern in required:
        _validate_required_pattern(pattern)

    return TemplateflowConfig(source=source, version=version, required=list(required))


def _validate_required_pattern(pattern):
    """Refuse a `required` pattern babs cannot map onto one template subdataset."""
    if not isinstance(pattern, str) or not pattern:
        raise ValueError(f'`templateflow.required` entries must be non-empty strings: {pattern!r}')
    if pattern.startswith('/'):
        raise ValueError(f'`templateflow.required` patterns must be relative: {pattern!r}')
    parts = pattern.split('/')
    if '..' in parts:
        raise ValueError(f"`templateflow.required` patterns must not contain '..': {pattern!r}")
    if not _TEMPLATE_DIR.match(parts[0]):
        raise ValueError(
            '`templateflow.required` patterns must start with a literal template '
            f'directory such as `tpl-MNI152NLin2009cAsym/`: {pattern!r}'
        )
