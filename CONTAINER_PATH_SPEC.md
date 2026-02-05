# Technical Specification: Container Path Flexibility

## Problem Statement

Currently, BABS hardcodes the container path to the result of `datalad containers-add`, specifically:
- Location: `babs/babs.py`, lines 2210-2211
- Hardcoded path: `containers/.datalad/environments/<container_name>/image`

This prevents:
1. Using `repronim/containers` for shared container management
2. Reading container paths from DataLad configuration
3. Sharing containers across multiple BABS projects
4. Flexible container deployment strategies

## Proposed Solution

### Overview

Implement a flexible container path discovery system that:
1. Reads container paths from DataLad configuration
2. Supports multiple container sources (local, shared, repronim)
3. Maintains backwards compatibility with existing projects
4. Provides clear error messages for troubleshooting

### Technical Design

#### 1. Container Path Discovery Algorithm

**Priority Order:**
```
1. Explicit CLI argument: --container-path
2. DataLad config: datalad.containers.<name>.image
3. DataLad config: datalad.containers.<name>.cmdexec
4. Shared container location: <shared-path>/.datalad/environments/<name>/image
5. repronim/containers: <repronim-path>/<name>/image
6. Legacy fallback: containers/.datalad/environments/<name>/image
```

#### 2. Code Changes

##### 2.1 New Function: `discover_container_path()`

**Location:** `babs/utils.py`

```python
def discover_container_path(
    dataset_path,
    container_name,
    explicit_path=None,
    shared_container_paths=None,
    repronim_path=None,
    allow_legacy=True
):
    """
    Discover container image path using multiple strategies.
    
    Parameters
    ----------
    dataset_path : str
        Path to the DataLad dataset (typically analysis folder)
    container_name : str
        Name of the container (e.g., 'fmriprep-23-1-3')
    explicit_path : str, optional
        Explicit container path provided via CLI
    shared_container_paths : list of str, optional
        List of shared container locations to check
    repronim_path : str, optional
        Path to repronim/containers clone
    allow_legacy : bool, optional
        Whether to fall back to legacy hardcoded path (default: True)
    
    Returns
    -------
    container_path : str
        Absolute path to the container image
    source : str
        Source of the container ('explicit', 'datalad-config', 'shared',
        'repronim', 'legacy')
    
    Raises
    ------
    ContainerNotFoundError
        If container cannot be found in any location
    
    Examples
    --------
    >>> path, source = discover_container_path(
    ...     '/project/analysis',
    ...     'fmriprep-23-1-3',
    ...     shared_container_paths=['/opt/containers']
    ... )
    >>> print(f"Found at {path} (source: {source})")
    Found at /opt/containers/.datalad/environments/fmriprep-23-1-3/image (source: shared)
    """
    
    # 1. Check explicit path
    if explicit_path is not None:
        if os.path.exists(explicit_path):
            return os.path.abspath(explicit_path), 'explicit'
        else:
            warnings.warn(f"Explicit path {explicit_path} does not exist")
    
    # 2. Check DataLad config
    try:
        ds = dlapi.Dataset(dataset_path)
        
        # Try datalad.containers.<name>.image
        config_key_image = f"datalad.containers.{container_name}.image"
        config_path = ds.config.get(config_key_image, None)
        if config_path and os.path.exists(config_path):
            return os.path.abspath(config_path), 'datalad-config'
        
        # Try datalad.containers.<name>.cmdexec (alternative config key)
        config_key_cmdexec = f"datalad.containers.{container_name}.cmdexec"
        cmdexec = ds.config.get(config_key_cmdexec, None)
        if cmdexec:
            # Parse cmdexec to extract image path
            # Format is typically: singularity exec {image} ...
            image_path = _extract_image_from_cmdexec(cmdexec)
            if image_path and os.path.exists(image_path):
                return os.path.abspath(image_path), 'datalad-config'
    
    except NoDatasetFound:
        warnings.warn(f"No DataLad dataset found at {dataset_path}")
    
    # 3. Check shared container locations
    if shared_container_paths:
        for shared_path in shared_container_paths:
            candidate = os.path.join(
                shared_path,
                '.datalad', 'environments',
                container_name, 'image'
            )
            if os.path.exists(candidate):
                return os.path.abspath(candidate), 'shared'
            
            # Also check direct path without .datalad/environments
            candidate_direct = os.path.join(shared_path, container_name, 'image')
            if os.path.exists(candidate_direct):
                return os.path.abspath(candidate_direct), 'shared'
    
    # 4. Check repronim/containers
    if repronim_path:
        # repronim/containers structure: <path>/<app>/<version>/image
        # Parse container_name to extract app and version
        app, version = _parse_container_name(container_name)
        if app and version:
            candidate = os.path.join(repronim_path, app, version, 'image')
            if os.path.exists(candidate):
                return os.path.abspath(candidate), 'repronim'
    
    # 5. Legacy fallback
    if allow_legacy:
        legacy_path = os.path.join(
            dataset_path,
            'containers', '.datalad', 'environments',
            container_name, 'image'
        )
        if os.path.exists(legacy_path):
            warnings.warn(
                f"Using legacy container path. Consider configuring "
                f"container path in DataLad config for better flexibility."
            )
            return os.path.abspath(legacy_path), 'legacy'
    
    # Not found anywhere
    raise ContainerNotFoundError(
        f"Container '{container_name}' not found in any configured location. "
        f"Checked: DataLad config, shared paths, repronim, legacy path."
    )


def _extract_image_from_cmdexec(cmdexec):
    """
    Extract image path from datalad.containers.*.cmdexec config value.
    
    Parameters
    ----------
    cmdexec : str
        The cmdexec configuration value (e.g., "singularity exec {img} {cmd}")
    
    Returns
    -------
    image_path : str or None
        Extracted image path, or None if not found
    """
    # Parse cmdexec format
    # Common formats:
    #   singularity exec {img} {cmd}
    #   singularity exec /path/to/image.sif {cmd}
    
    # Look for path after 'exec' and before '{cmd}'
    import re
    pattern = r'singularity\s+exec\s+([^\s]+)\s+'
    match = re.search(pattern, cmdexec)
    if match:
        path = match.group(1)
        # Remove {img} placeholder if present
        if path != '{img}':
            return path
    return None


def _parse_container_name(container_name):
    """
    Parse container name to extract app name and version.
    
    Parameters
    ----------
    container_name : str
        Container name (e.g., 'fmriprep-23-1-3' or 'bids-fmriprep-23.1.3')
    
    Returns
    -------
    app : str or None
        Application name (e.g., 'fmriprep')
    version : str or None
        Version string (e.g., '23.1.3')
    """
    # Try multiple patterns
    patterns = [
        r'^([a-zA-Z]+)-(\d+[-\.]\d+[-\.]\d+)$',  # fmriprep-23-1-3
        r'^bids-([a-zA-Z]+)-(\d+[-\.]\d+[-\.]\d+)$',  # bids-fmriprep-23.1.3
        r'^([a-zA-Z]+)[-_](\d+[-\.]\d+[-\.]\d+)$',  # fmriprep_23.1.3
    ]
    
    for pattern in patterns:
        match = re.match(pattern, container_name)
        if match:
            app = match.group(1)
            version = match.group(2).replace('-', '.')
            return app, version
    
    return None, None


class ContainerNotFoundError(Exception):
    """Raised when container cannot be found in any configured location."""
    pass
```

##### 2.2 Modify `Container.__init__()` in `babs/babs.py`

**Current code (lines ~2165-2240):**
```python
def __init__(self, container_ds, container_name, config_yaml_file):
    # ... existing code ...
    
    # HARDCODED PATH:
    self.container_path_relToAnalysis = op.join(
        "containers", ".datalad", "environments",
        self.container_name, "image"
    )
```

**New code:**
```python
def __init__(
    self,
    container_ds,
    container_name,
    config_yaml_file,
    explicit_container_path=None,
    shared_container_paths=None,
    repronim_path=None
):
    """
    Initialize Container object.
    
    Parameters
    ----------
    container_ds : str
        Path to container DataLad dataset
    container_name : str
        Name of the container
    config_yaml_file : str
        Path to configuration YAML file
    explicit_container_path : str, optional
        Explicit path to container image (from CLI)
    shared_container_paths : list of str, optional
        List of shared container locations to check
    repronim_path : str, optional
        Path to repronim/containers clone
    """
    
    # ... existing validation code ...
    
    # NEW: Discover container path using flexible strategy
    try:
        self.container_path_abs, self.container_source = discover_container_path(
            dataset_path=container_ds,
            container_name=container_name,
            explicit_path=explicit_container_path,
            shared_container_paths=shared_container_paths,
            repronim_path=repronim_path,
            allow_legacy=True
        )
        
        # Calculate relative path if possible
        try:
            self.container_path_relToAnalysis = os.path.relpath(
                self.container_path_abs,
                container_ds
            )
        except ValueError:
            # Can't calculate relative path (e.g., different drives)
            # Use absolute path
            self.container_path_relToAnalysis = self.container_path_abs
        
        print(f"Container found via '{self.container_source}' source:")
        print(f"  {self.container_path_abs}")
        
    except ContainerNotFoundError as e:
        raise ValueError(
            f"Could not locate container '{container_name}'. "
            f"Error: {str(e)}\n\n"
            f"Troubleshooting:\n"
            f"1. Check container name matches datalad containers-add name\n"
            f"2. Verify container dataset contains the container\n"
            f"3. Consider using --container-path to specify explicit path\n"
            f"4. Check DataLad configuration: datalad.containers.{container_name}.image"
        )
    
    # Verify container image exists and is accessible
    if not os.path.exists(self.container_path_abs):
        raise ValueError(
            f"Container image not found at discovered path: {self.container_path_abs}"
        )
    
    # ... rest of existing code ...
```

##### 2.3 Update CLI in `babs/cli.py`

**Add new arguments to `babs-init`:**

```python
# Around line 80-120, add to ArgumentParser:

parser.add_argument(
    "--container-path",
    type=str,
    required=False,
    help=(
        "Explicit path to container image. If provided, bypasses automatic "
        "container discovery. Useful for testing or non-standard setups."
    )
)

parser.add_argument(
    "--shared-container-path",
    type=str,
    action='append',
    required=False,
    help=(
        "Path to shared container location. Can be specified multiple times. "
        "BABS will search these locations for the container if not found locally. "
        "Example: /opt/shared/containers"
    )
)

parser.add_argument(
    "--repronim-containers-path",
    type=str,
    required=False,
    help=(
        "Path to repronim/containers clone. If provided, BABS will search "
        "for containers following repronim/containers structure: "
        "<path>/<app>/<version>/. Example: /opt/repronim-containers"
    )
)

parser.add_argument(
    "--read-container-from-config",
    action='store_true',
    default=True,
    help=(
        "Read container path from DataLad configuration "
        "(datalad.containers.<name>.image). This is the default behavior. "
        "Use --no-read-container-from-config to disable."
    )
)

parser.add_argument(
    "--no-read-container-from-config",
    action='store_false',
    dest='read_container_from_config',
    help="Do not read container path from DataLad configuration."
)
```

**Pass arguments to Container class:**

```python
# In the init_project function, around where Container is instantiated:

container = Container(
    container_ds=args.container_ds,
    container_name=args.container_name,
    config_yaml_file=args.container_config_yaml_file,
    explicit_container_path=args.container_path,
    shared_container_paths=args.shared_container_path,
    repronim_path=args.repronim_containers_path
)
```

#### 3. Configuration File Support

##### 3.1 Extended YAML Configuration

**Add container source configuration to YAML:**

```yaml
# New section in config YAML
container:
  # Source type: local, shared, repronim, explicit
  source: "shared"
  
  # For shared source
  shared_paths:
    - "/opt/shared/containers"
    - "/scratch/containers"
  
  # For repronim source
  repronim_path: "/opt/repronim-containers"
  
  # For explicit source
  explicit_path: "/path/to/specific/container.sif"
  
  # Read from DataLad config (default: true)
  read_from_config: true

# Existing sections remain unchanged
singularity_run:
  # ...

zip_foldernames:
  # ...
```

##### 3.2 Parse Container Config in `read_container_config_yaml()`

**Update in `babs/babs.py` (Container class):**

```python
def read_container_config_yaml(self):
    """Read and parse container configuration YAML file."""
    
    with open(self.config_yaml_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    # NEW: Check for container source configuration
    if 'container' in config:
        container_config = config['container']
        
        # Store for later use in path discovery
        self.config_container_source = container_config.get('source', None)
        self.config_shared_paths = container_config.get('shared_paths', [])
        self.config_repronim_path = container_config.get('repronim_path', None)
        self.config_explicit_path = container_config.get('explicit_path', None)
        self.config_read_from_config = container_config.get('read_from_config', True)
    
    # ... existing code for other config sections ...
```

#### 4. Error Messages and Logging

**Improve error messages to help users troubleshoot:**

```python
def _generate_container_troubleshooting_message(
    container_name,
    checked_locations
):
    """Generate helpful troubleshooting message for container not found errors."""
    
    msg = [
        f"\nContainer '{container_name}' could not be found.",
        "\nChecked locations:"
    ]
    
    for location, status in checked_locations.items():
        msg.append(f"  - {location}: {status}")
    
    msg.extend([
        "\nPossible solutions:",
        "1. Verify container name matches what was used in 'datalad containers-add'",
        "2. Check that container dataset has been properly cloned",
        "3. Specify container path explicitly with --container-path",
        "4. Add shared container location with --shared-container-path",
        "5. Check DataLad configuration:",
        f"   git config -f .datalad/config datalad.containers.{container_name}.image",
        "\nFor more help, see: https://pennlinc-babs.readthedocs.io/container-setup"
    ])
    
    return "\n".join(msg)
```

#### 5. Testing Strategy

##### 5.1 Unit Tests

**New test file: `tests/test_container_discovery.py`**

```python
import pytest
import os
import tempfile
from babs.utils import (
    discover_container_path,
    ContainerNotFoundError,
    _parse_container_name
)

class TestContainerDiscovery:
    """Test container path discovery functionality."""
    
    def test_explicit_path_takes_priority(self, tmp_path):
        """Test that explicit path is used when provided."""
        # Create a dummy container file
        container_path = tmp_path / "my_container.sif"
        container_path.touch()
        
        result_path, source = discover_container_path(
            dataset_path=str(tmp_path),
            container_name="test",
            explicit_path=str(container_path)
        )
        
        assert result_path == str(container_path.absolute())
        assert source == 'explicit'
    
    def test_datalad_config_detection(self, tmp_path):
        """Test reading container path from DataLad config."""
        # Setup mock DataLad dataset with config
        # ... implementation ...
        pass
    
    def test_shared_container_location(self, tmp_path):
        """Test finding container in shared location."""
        # Create shared container structure
        shared_path = tmp_path / "shared"
        container_path = shared_path / ".datalad" / "environments" / "test-1-0-0" / "image"
        container_path.parent.mkdir(parents=True)
        container_path.touch()
        
        result_path, source = discover_container_path(
            dataset_path=str(tmp_path / "analysis"),
            container_name="test-1-0-0",
            shared_container_paths=[str(shared_path)]
        )
        
        assert result_path == str(container_path.absolute())
        assert source == 'shared'
    
    def test_repronim_structure(self, tmp_path):
        """Test finding container in repronim/containers structure."""
        # Create repronim structure: <path>/fmriprep/23.1.3/image
        repronim_path = tmp_path / "repronim"
        container_path = repronim_path / "fmriprep" / "23.1.3" / "image"
        container_path.parent.mkdir(parents=True)
        container_path.touch()
        
        result_path, source = discover_container_path(
            dataset_path=str(tmp_path / "analysis"),
            container_name="fmriprep-23-1-3",
            repronim_path=str(repronim_path)
        )
        
        assert result_path == str(container_path.absolute())
        assert source == 'repronim'
    
    def test_legacy_fallback(self, tmp_path):
        """Test fallback to legacy hardcoded path."""
        # Create legacy structure
        dataset_path = tmp_path / "analysis"
        legacy_path = dataset_path / "containers" / ".datalad" / "environments" / "test" / "image"
        legacy_path.parent.mkdir(parents=True)
        legacy_path.touch()
        
        result_path, source = discover_container_path(
            dataset_path=str(dataset_path),
            container_name="test",
            allow_legacy=True
        )
        
        assert result_path == str(legacy_path.absolute())
        assert source == 'legacy'
    
    def test_not_found_raises_error(self, tmp_path):
        """Test that appropriate error is raised when container not found."""
        with pytest.raises(ContainerNotFoundError):
            discover_container_path(
                dataset_path=str(tmp_path),
                container_name="nonexistent",
                allow_legacy=False
            )
    
    def test_parse_container_name(self):
        """Test parsing container names to extract app and version."""
        # Test various formats
        assert _parse_container_name("fmriprep-23-1-3") == ("fmriprep", "23.1.3")
        assert _parse_container_name("bids-fmriprep-23.1.3") == ("fmriprep", "23.1.3")
        assert _parse_container_name("mriqc_23-0-1") == ("mriqc", "23.0.1")
        assert _parse_container_name("invalid") == (None, None)
```

##### 5.2 Integration Tests

**Test end-to-end workflows:**

```python
class TestContainerIntegration:
    """Test container discovery in full BABS workflows."""
    
    def test_init_with_shared_container(self):
        """Test babs-init with shared container location."""
        # Setup test environment with shared containers
        # Run babs-init with --shared-container-path
        # Verify container is found and used correctly
        pass
    
    def test_init_with_repronim_containers(self):
        """Test babs-init with repronim/containers."""
        # Setup test environment mimicking repronim/containers
        # Run babs-init with --repronim-containers-path
        # Verify container is found correctly
        pass
    
    def test_backwards_compatibility(self):
        """Test that existing projects continue to work."""
        # Create project using legacy setup
        # Verify it still works without any changes
        pass
```

#### 6. Documentation Updates

##### 6.1 New Documentation Section

**File:** `docs/source/container_sources.rst`

```rst
************************************************************
Flexible Container Management
************************************************************

Overview
========

BABS supports multiple ways to manage and locate BIDS App containers,
from local containers to shared infrastructure like repronim/containers.

Container Sources
=================

BABS can discover containers from several sources, in priority order:

1. **Explicit Path** (``--container-path``)
2. **DataLad Configuration** (read from dataset config)
3. **Shared Container Locations** (``--shared-container-path``)
4. **repronim/containers** (``--repronim-containers-path``)
5. **Legacy Location** (backwards compatibility)

Local Containers (Traditional Method)
======================================

This is the traditional BABS approach using ``datalad containers-add``:

.. code-block:: bash

    # Create container dataset
    datalad create -D "fMRIPrep container" fmriprep-container
    cd fmriprep-container
    
    # Add container
    datalad containers-add \
        --url /path/to/fmriprep-23.1.3.sif \
        fmriprep-23-1-3
    
    # Use in BABS
    babs-init \
        --container_ds /path/to/fmriprep-container \
        --container_name fmriprep-23-1-3 \
        # ... other options ...

Shared Containers
=================

Share containers across multiple BABS projects to save storage:

.. code-block:: bash

    # Setup shared container location (one time)
    export SHARED_CONTAINERS=/opt/shared/containers
    
    # Create container dataset in shared location
    cd $SHARED_CONTAINERS
    datalad create -D "Shared fMRIPrep" fmriprep-23-1-3
    cd fmriprep-23-1-3
    datalad containers-add \
        --url /path/to/fmriprep-23.1.3.sif \
        fmriprep-23-1-3
    
    # Use in BABS (all projects can reference this)
    babs-init \
        --shared-container-path $SHARED_CONTAINERS \
        --container_name fmriprep-23-1-3 \
        # ... other options ...

Benefits:
- Single container copy shared across all projects
- Centralized container management
- Reduced storage requirements

Using repronim/containers
=========================

`repronim/containers <https://github.com/ReproNim/containers>`_ provides
a curated collection of neuroimaging containers:

.. code-block:: bash

    # Clone repronim/containers (one time)
    git clone https://github.com/ReproNim/containers.git /opt/repronim-containers
    cd /opt/repronim-containers
    datalad get -n images/bids  # Get BIDS Apps
    
    # Get specific container
    datalad get images/bids/fmriprep--23.1.3.sing
    
    # Use in BABS
    babs-init \
        --repronim-containers-path /opt/repronim-containers \
        --container_name fmriprep-23-1-3 \
        # ... other options ...

DataLad Configuration
=====================

BABS can read container paths from DataLad configuration:

.. code-block:: bash

    # Set in DataLad dataset config
    cd /path/to/analysis
    git config -f .datalad/config \
        datalad.containers.fmriprep-23-1-3.image \
        /opt/containers/fmriprep-23.1.3.sif
    
    # BABS will automatically discover this
    babs-init \
        --container_name fmriprep-23-1-3 \
        # ... other options ...

This is useful for:
- Custom container locations
- HPC-specific paths
- Shared configurations

Explicit Container Path
=======================

For testing or special cases, specify the exact container path:

.. code-block:: bash

    babs-init \
        --container-path /custom/path/to/container.sif \
        --container_name my-custom-container \
        # ... other options ...

Troubleshooting
===============

Container Not Found
-------------------

If BABS cannot find your container, check:

1. **Container name matches**: Verify the name matches what was used in
   ``datalad containers-add``

2. **Container dataset cloned**: Ensure the container dataset was properly
   cloned into your project

3. **Check DataLad config**:

   .. code-block:: bash

       cd /path/to/analysis
       git config -f .datalad/config -l | grep containers

4. **Try explicit path**: Use ``--container-path`` to verify the container
   file exists and is accessible

Verifying Container Discovery
------------------------------

BABS will print which source was used to find the container:

.. code-block:: text

    Container found via 'shared' source:
      /opt/shared/containers/.datalad/environments/fmriprep-23-1-3/image

Best Practices
==============

1. **Use shared containers** for production environments processing
   multiple datasets

2. **Use repronim/containers** when available for standardization

3. **Configure DataLad** for HPC-specific paths that vary by user

4. **Document container sources** in your project README

5. **Test container accessibility** before submitting large job batches
```

##### 6.2 Update Existing Documentation

**Update:** `docs/source/preparation_container.rst`

Add section explaining new options:

```rst
Alternative Container Setup Methods
====================================

In addition to the traditional method of creating a local container dataset,
BABS now supports several alternative approaches for container management.

See :doc:`container_sources` for comprehensive documentation on:

- Shared container locations
- Using repronim/containers
- Reading container paths from DataLad configuration
- Explicit container paths

These methods are particularly useful for large-scale workflows processing
multiple datasets, as they enable container sharing and reduce storage
requirements.
```

#### 7. Backwards Compatibility

**Ensure existing projects continue to work:**

1. **Default behavior unchanged**: If no new options are provided, BABS
   behaves exactly as before (legacy path)

2. **Warning for legacy usage**: Print friendly warning suggesting
   configuration options when using legacy path

3. **Migration guide**: Provide clear documentation for migrating existing
   projects to use new features

4. **Testing**: Extensive tests ensure existing workflows are not broken

#### 8. Performance Considerations

**Optimization strategies:**

1. **Cache container path**: Once discovered, cache the path to avoid
   repeated lookups

2. **Lazy evaluation**: Only search for container when actually needed

3. **Parallel-safe**: Ensure container discovery is safe for parallel
   job execution

4. **Minimal overhead**: Discovery adds <100ms to initialization time

## Implementation Checklist

### Code Changes
- [ ] Implement `discover_container_path()` in `babs/utils.py`
- [ ] Add helper functions (`_extract_image_from_cmdexec`, `_parse_container_name`)
- [ ] Create `ContainerNotFoundError` exception class
- [ ] Modify `Container.__init__()` in `babs/babs.py`
- [ ] Update CLI arguments in `babs/cli.py`
- [ ] Add container config parsing in `read_container_config_yaml()`
- [ ] Implement caching mechanism for discovered paths
- [ ] Add comprehensive logging

### Testing
- [ ] Unit tests for `discover_container_path()`
- [ ] Unit tests for helper functions
- [ ] Integration tests for each container source type
- [ ] Backwards compatibility tests
- [ ] Performance tests
- [ ] Error handling tests

### Documentation
- [ ] Create `docs/source/container_sources.rst`
- [ ] Update `docs/source/preparation_container.rst`
- [ ] Add CLI reference documentation
- [ ] Create migration guide
- [ ] Add troubleshooting section
- [ ] Update README with new features

### Examples
- [ ] Example using shared containers
- [ ] Example using repronim/containers
- [ ] Example using DataLad config
- [ ] Example config YAML files
- [ ] Migration script

### Review
- [ ] Code review
- [ ] Documentation review
- [ ] User acceptance testing
- [ ] Performance validation

## Timeline

- **Week 1**: Core implementation (`discover_container_path()` and modifications to `Container` class)
- **Week 2**: CLI updates and configuration parsing
- **Week 3**: Testing (unit and integration)
- **Week 4**: Documentation and examples
- **Week 5**: Review, refinement, and user testing

## Success Criteria

1. [ ] Containers can be read from DataLad configuration
2. [ ] Shared container locations work correctly
3. [ ] repronim/containers integration functional
4. [ ] All existing tests pass (backwards compatibility)
5. [ ] New tests achieve >90% code coverage
6. [ ] Documentation complete and accurate
7. [ ] Performance overhead <100ms
8. [ ] Zero breaking changes for existing users

## Next Steps

1. Review this specification with the team
2. Get approval for implementation approach
3. Create GitHub issues for each major task
4. Begin implementation of core functionality
5. Set up test environment with sample containers
6. Create PR for review
