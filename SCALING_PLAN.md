# BABS Scaling Plan: Large-Scale Workflow Enhancement

## Executive Summary

This document outlines the goals and necessary changes to make BABS (BIDS App Bootstrap) suitable for large-scale automation workflows that can handle thousands of datasets. The primary focus is on improving output dataset customization, enabling container sharing across multiple datasets, and adopting a standardized BIDS-study layout.

## Current State Analysis

### Container Handling

**Current Implementation:**
- Containers are managed as DataLad datasets
- Container paths are **hardcoded** in `babs/babs.py` (lines 2210-2211):
  ```python
  self.container_path_relToAnalysis = op.join("containers", ".datalad", "environments",
                                              self.container_name, "image")
  ```
- Path follows pattern: `analysis/containers/.datalad/environments/<container_name>/image`
- Containers are cloned into each project's `analysis/` folder during initialization

**Limitations:**
1. Container path is hardcoded to `datalad containers-add` results
2. Cannot leverage existing `repronim/containers` infrastructure
3. Each project duplicates container storage
4. Difficult to share containers across multiple datasets
5. Does not read from DataLad configuration files

### Output Dataset Structure

**Current Implementation:**
- Outputs are stored in project-specific structure
- Limited customization options
- Does not follow BIDS-study layout conventions

**Limitations:**
1. Not aligned with BIDS-study layout standards
2. No clear separation of source data and derivatives
3. Limited support for multiple apps per dataset
4. Output organization not scalable for thousands of datasets

## Goals

### Primary Goal
Enable BABS to support large-scale automation workflows that can process thousands of datasets, with each subject/session going through multiple BIDS Apps (MRIQC, FMRIPREP, etc.).

### Specific Objectives

1. **Flexible Container Management**
   - Read container paths from DataLad configuration
   - Support `repronim/containers` infrastructure
   - Enable container sharing across multiple datasets
   - Eliminate hardcoded container path assumptions

2. **BIDS-Study Layout Compliance**
   - Adopt standardized directory structure:
     - `sourcedata/raw/` - Input BIDS datasets
     - `derivatives/<app>/` - Application outputs (e.g., `derivatives/mriqc/`, `derivatives/fmriprep/`)
   - Ensure outputs are not zipped by default (configurable)
   - Support multiple derivatives from different apps in single dataset

3. **Scalability**
   - Efficient resource sharing across datasets
   - Minimize storage duplication
   - Support parallel processing of multiple datasets
   - Enable automation workflows at scale

## Required Changes

### 1. Container Configuration System

#### 1.1 Remove Hardcoded Container Paths

**Current Code (babs/babs.py:2210-2211):**
```python
self.container_path_relToAnalysis = op.join("containers", ".datalad", "environments",
                                            self.container_name, "image")
```

**Proposed Change:**
- Read container path from DataLad configuration
- Support both local and shared container locations
- Use `datalad.containers.<container_name>.image` config key

**Implementation:**
```python
# Read from DataLad config
def _get_container_path_from_config(self, container_name):
    """
    Read container image path from DataLad configuration.
    
    Checks for:
    1. Local config: datalad.containers.<container_name>.image
    2. Shared config: repronim/containers location
    3. Fallback to current hardcoded path for backwards compatibility
    """
    # Query datalad config
    # Return path from config
    # If not found, fallback to current behavior with warning
```

#### 1.2 Support repronim/containers

**Goal:** Enable using containers from the `repronim/containers` collection without duplicating them into each project.

**Implementation Steps:**
1. Add CLI option `--shared-container-path` to specify shared container location
2. Modify container validation to check:
   - Local project containers
   - Shared container paths
   - repronim/containers standard locations
3. Update documentation with examples using repronim/containers

#### 1.3 Configuration File Enhancement

**Add to container config YAML:**
```yaml
container:
  # Option 1: Use local container (current behavior)
  source: "local"
  path: "/path/to/local/container-dataset"
  
  # Option 2: Use shared container
  source: "shared"
  path: "/path/to/shared/containers"
  
  # Option 3: Use repronim/containers
  source: "repronim"
  container_id: "bids/fmriprep:23.1.3"
```

### 2. BIDS-Study Layout Implementation

#### 2.1 Directory Structure Changes

**Current Structure:**
```
project_root/
├── analysis/
├── containers/
├── input_ria/
└── output_ria/
```

**Proposed Structure:**
```
project_root/
├── sourcedata/
│   └── raw/          # Input BIDS datasets
├── derivatives/
│   ├── mriqc/        # MRIQC outputs (non-zipped)
│   ├── fmriprep/     # fMRIPrep outputs (non-zipped)
│   └── <app>/        # Other BIDS App outputs
├── analysis/         # Working directory (DataLad)
├── containers/       # Local containers (optional)
├── input_ria/        # Input RIA store
└── output_ria/       # Output RIA store
```

#### 2.2 Code Changes

**Files to Modify:**
1. `babs/babs.py` - Update project initialization
2. `babs/cli.py` - Add new CLI options for layout configuration
3. `babs/utils.py` - Add utility functions for BIDS-study layout

**New CLI Options:**
```bash
babs-init \
  --output-layout bids-study \
  --sourcedata-dir sourcedata/raw \
  --derivatives-dir derivatives \
  --no-zip-outputs \
  ...
```

#### 2.3 Output Organization

**Changes to zip_foldernames handling:**
- Make zipping optional (default: no zip for BIDS-study layout)
- Organize outputs by app name in `derivatives/` directory
- Maintain BIDS-compliant naming within each app's derivative folder

**Configuration Example:**
```yaml
output:
  layout: "bids-study"  # or "legacy" for backwards compatibility
  derivatives_dir: "derivatives"
  sourcedata_dir: "sourcedata/raw"
  zip_outputs: false
  apps:
    mriqc:
      version: "23.0.1"
    fmriprep:
      version: "23.1.3"
```

### 3. Multi-Dataset Support

#### 3.1 Shared Resources

**Goal:** Enable multiple datasets to share containers and other resources.

**Implementation:**
- Central container repository
- Shared configuration templates
- Reference-based container access (not copy)

#### 3.2 Dataset Management

**New Features:**
1. Dataset registry for tracking multiple datasets
2. Shared container pool across datasets
3. Centralized logging and monitoring
4. Batch processing capabilities

**Configuration:**
```yaml
datasets:
  - name: "dataset-001"
    input: "/data/raw/dataset-001"
    output: "/data/derivatives/dataset-001"
  - name: "dataset-002"
    input: "/data/raw/dataset-002"
    output: "/data/derivatives/dataset-002"

shared:
  containers: "/shared/containers"
  templates: "/shared/templates"
```

### 4. Backwards Compatibility

**Maintain Support For:**
1. Legacy output structure (via `--output-layout legacy`)
2. Current container path conventions
3. Existing configuration files
4. Current CLI interface

**Migration Path:**
1. Add deprecation warnings for old patterns
2. Provide migration tools/scripts
3. Document migration process
4. Support both layouts for transition period

## Implementation Roadmap

### Phase 1: Container Configuration (Priority: HIGH)

**Tasks:**
1. [ ] Add DataLad config reading functionality
2. [ ] Implement container path discovery from config
3. [ ] Add support for repronim/containers paths
4. [ ] Add CLI options for shared container locations
5. [ ] Update container validation logic
6. [ ] Write tests for new container discovery
7. [ ] Update documentation

**Estimated Effort:** 2-3 weeks

**Files to Modify:**
- `babs/babs.py` (~200 lines)
- `babs/cli.py` (~50 lines)
- `babs/utils.py` (new functions, ~100 lines)
- `tests/test_container_config.py` (new file, ~150 lines)
- `docs/source/preparation_container.rst` (~100 lines)

### Phase 2: BIDS-Study Layout (Priority: HIGH)

**Tasks:**
1. [ ] Design new directory structure
2. [ ] Implement sourcedata/raw organization
3. [ ] Implement derivatives/<app> organization
4. [ ] Add layout selection CLI options
5. [ ] Modify output path generation
6. [ ] Update zipping logic for new layout
7. [ ] Write tests for layout functionality
8. [ ] Update documentation with examples

**Estimated Effort:** 3-4 weeks

**Files to Modify:**
- `babs/babs.py` (~300 lines)
- `babs/cli.py` (~100 lines)
- `babs/utils.py` (~150 lines)
- `babs/constants.py` (new constants)
- `tests/test_bids_layout.py` (new file, ~200 lines)
- `docs/source/output_organization.rst` (new file, ~200 lines)

### Phase 3: Multi-Dataset Management (Priority: MEDIUM)

**Tasks:**
1. [ ] Design dataset registry system
2. [ ] Implement shared resource management
3. [ ] Add batch processing capabilities
4. [ ] Create dataset management CLI commands
5. [ ] Implement central logging
6. [ ] Write tests for multi-dataset features
7. [ ] Create comprehensive documentation

**Estimated Effort:** 4-5 weeks

**Files to Create:**
- `babs/dataset_manager.py` (~400 lines)
- `babs/shared_resources.py` (~200 lines)
- `tests/test_multi_dataset.py` (~250 lines)
- `docs/source/multi_dataset_workflows.rst` (~300 lines)

### Phase 4: Migration and Documentation (Priority: MEDIUM)

**Tasks:**
1. [ ] Create migration guide
2. [ ] Write migration scripts
3. [ ] Add backwards compatibility tests
4. [ ] Create workflow examples
5. [ ] Update all existing documentation
6. [ ] Create video tutorials

**Estimated Effort:** 2-3 weeks

**Deliverables:**
- Migration guide document
- Migration scripts
- Updated documentation
- Example workflows
- Tutorial videos

## Technical Considerations

### DataLad Configuration Reading

**Reference Implementation:**
```python
import datalad.api as dlapi
from datalad.support.exceptions import NoDatasetFound

def get_container_config(dataset_path, container_name):
    """
    Read container configuration from DataLad.
    
    Looks for: datalad.containers.<container_name>.image
    """
    try:
        ds = dlapi.Dataset(dataset_path)
        config_key = f"datalad.containers.{container_name}.image"
        value = ds.config.get(config_key, None)
        return value
    except NoDatasetFound:
        return None
```

### Container Path Discovery

**Priority Order:**
1. Explicit CLI argument `--container-path`
2. DataLad config: `datalad.containers.<name>.image`
3. Shared container location: `<shared-path>/<name>/image`
4. repronim/containers: Check standard locations
5. Legacy path: `containers/.datalad/environments/<name>/image`

### Output Path Generation

**BIDS-Study Layout:**
```python
def generate_output_path(project_root, layout, app_name, subject_id, session_id=None):
    """
    Generate output path based on layout type.
    
    For 'bids-study':
        {project_root}/derivatives/{app_name}/sub-{subject_id}/[ses-{session_id}/]
    
    For 'legacy':
        {project_root}/output_ria/{hash}/sub-{subject_id}_[ses-{session_id}_]{app_name}-{version}.zip
    """
    if layout == "bids-study":
        path = op.join(project_root, "derivatives", app_name, f"sub-{subject_id}")
        if session_id:
            path = op.join(path, f"ses-{session_id}")
        return path
    else:
        # Legacy behavior
        return generate_legacy_output_path(...)
```

## Testing Strategy

### Unit Tests

1. **Container Discovery Tests**
   - Test DataLad config reading
   - Test shared container detection
   - Test repronim/containers integration
   - Test fallback mechanisms

2. **Layout Tests**
   - Test BIDS-study structure creation
   - Test path generation for various scenarios
   - Test output organization

3. **Multi-Dataset Tests**
   - Test shared resource access
   - Test concurrent dataset processing
   - Test container sharing

### Integration Tests

1. **End-to-End Workflows**
   - Single dataset with MRIQC and fMRIPrep
   - Multiple datasets with shared containers
   - Migration from legacy to BIDS-study layout

2. **Compatibility Tests**
   - Backwards compatibility with existing projects
   - Cross-version compatibility

### Performance Tests

1. **Scalability Tests**
   - Processing 100+ datasets
   - Container sharing efficiency
   - Resource utilization

## Documentation Updates

### New Documentation Sections

1. **Container Management Guide**
   - Using repronim/containers
   - Setting up shared container pools
   - Container configuration options

2. **BIDS-Study Layout Guide**
   - Directory structure explanation
   - Benefits and use cases
   - Migration from legacy layout

3. **Multi-Dataset Workflows**
   - Setting up batch processing
   - Managing multiple datasets
   - Resource optimization

4. **Migration Guide**
   - Step-by-step migration process
   - Troubleshooting common issues
   - Example migrations

### Updated Documentation

1. **Installation Guide** - Add shared container setup
2. **Configuration Guide** - Add new YAML options
3. **CLI Reference** - Document new options
4. **Walkthrough** - Add BIDS-study layout example

## Risk Assessment

### Technical Risks

1. **Breaking Changes**
   - **Risk:** New changes break existing workflows
   - **Mitigation:** Maintain backwards compatibility, extensive testing

2. **DataLad Integration**
   - **Risk:** Complex interactions with DataLad configuration
   - **Mitigation:** Thorough testing, fallback mechanisms

3. **Performance**
   - **Risk:** Overhead from new features affects performance
   - **Mitigation:** Performance testing, optimization

### Operational Risks

1. **User Adoption**
   - **Risk:** Users continue using legacy patterns
   - **Mitigation:** Clear documentation, migration tools, examples

2. **Migration Complexity**
   - **Risk:** Difficult for users to migrate existing projects
   - **Mitigation:** Automated migration scripts, detailed guide

## Success Metrics

1. **Functionality**
   - [ ] Containers can be read from DataLad config
   - [ ] repronim/containers integration works
   - [ ] BIDS-study layout produces valid output
   - [ ] Multiple datasets can share containers

2. **Performance**
   - [ ] No significant performance degradation
   - [ ] Container sharing reduces storage usage by >50%
   - [ ] Can process 1000+ datasets efficiently

3. **Usability**
   - [ ] Migration tools work for existing projects
   - [ ] Documentation covers all new features
   - [ ] Examples demonstrate all workflows

4. **Compatibility**
   - [ ] All existing tests pass
   - [ ] Legacy workflows continue to work
   - [ ] New features don't break old projects

## References

1. **BIDS Specification**: https://bids-specification.readthedocs.io/
2. **DataLad Documentation**: https://docs.datalad.org/
3. **DataLad Containers**: http://docs.datalad.org/projects/container/
4. **repronim/containers**: https://github.com/ReproNim/containers
5. **FAIRly Big Framework**: https://doi.org/10.1038/s41597-022-01163-2
6. **BIDS Apps**: https://bids-apps.neuroimaging.io/

## Appendix A: Code Examples

### Example 1: Container Configuration YAML

```yaml
# New format with flexible container sources
container:
  source: "repronim"  # Options: local, shared, repronim
  name: "bids/fmriprep"
  version: "23.1.3"
  
  # For shared containers
  shared_path: "/opt/shared/containers"
  
  # For repronim/containers
  repronim_branch: "master"
  
singularity_run:
  -w: "$BABS_TMPDIR"
  --n_cpus: '1'
  --fs-license-file: "/path/to/FreeSurfer/license.txt"
  --output-spaces: "MNI152NLin6Asym:res-2"

output:
  layout: "bids-study"
  derivatives_dir: "derivatives"
  sourcedata_dir: "sourcedata/raw"
  zip_outputs: false

cluster_resources:
  interpreting_shell: "/bin/bash"
  hard_memory_limit: 25G
  temporary_disk_space: 200G
  hard_runtime_limit: "96:00:00"
```

### Example 2: CLI Usage

```bash
# Initialize with BIDS-study layout and shared containers
babs-init \
  --project-root /path/to/project \
  --input /path/to/input/dataset \
  --output-layout bids-study \
  --derivatives-dir derivatives \
  --sourcedata-dir sourcedata/raw \
  --container-source repronim \
  --container-name bids/fmriprep \
  --container-version 23.1.3 \
  --shared-container-path /opt/shared/containers \
  --no-zip-outputs \
  --config /path/to/config.yaml

# Batch processing multiple datasets
babs-batch-submit \
  --datasets-config datasets.yaml \
  --shared-containers /opt/shared/containers \
  --parallel 10
```

### Example 3: Multi-Dataset Configuration

```yaml
# datasets.yaml
global:
  shared_containers: "/opt/shared/containers"
  output_layout: "bids-study"
  
datasets:
  - name: "HCP-YA"
    input: "/data/raw/HCP-YA"
    output: "/data/derivatives/HCP-YA"
    apps:
      - mriqc
      - fmriprep
    
  - name: "UKB"
    input: "/data/raw/UKB"
    output: "/data/derivatives/UKB"
    apps:
      - mriqc
      - fmriprep
      - xcpd
    
  - name: "ABCD"
    input: "/data/raw/ABCD"
    output: "/data/derivatives/ABCD"
    apps:
      - mriqc
      - fmriprep

containers:
  mriqc:
    source: "repronim"
    name: "bids/mriqc"
    version: "23.0.1"
  
  fmriprep:
    source: "repronim"
    name: "bids/fmriprep"
    version: "23.1.3"
  
  xcpd:
    source: "repronim"
    name: "bids/xcpd"
    version: "0.4.0"
```

## Appendix B: File Structure Comparison

### Current Structure (Legacy)

```
my_babs_project/
├── analysis/
│   ├── code/
│   ├── containers/
│   │   └── .datalad/
│   │       └── environments/
│   │           └── fmriprep-23-1-3/
│   │               └── image -> /path/to/fmriprep.sif
│   └── logs/
├── input_ria/
│   └── <dataset_hash>/
└── output_ria/
    └── <dataset_hash>/
        └── sub-01_ses-01_fmriprep-23-1-3.zip
```

### Proposed Structure (BIDS-Study Layout)

```
my_babs_project/
├── sourcedata/
│   └── raw/
│       ├── sub-01/
│       │   └── ses-01/
│       │       ├── anat/
│       │       └── func/
│       └── dataset_description.json
├── derivatives/
│   ├── mriqc/
│   │   ├── sub-01/
│   │   │   └── ses-01/
│   │   │       ├── anat/
│   │   │       └── func/
│   │   └── dataset_description.json
│   └── fmriprep/
│       ├── sub-01/
│       │   └── ses-01/
│       │       ├── anat/
│       │       ├── func/
│       │       └── figures/
│       ├── dataset_description.json
│       └── logs/
├── analysis/
│   ├── code/
│   └── logs/
├── input_ria/
│   └── <dataset_hash>/
└── output_ria/
    └── <dataset_hash>/

# Shared containers (outside project)
/opt/shared/containers/
├── bids/
│   ├── mriqc-23-0-1/
│   │   └── image
│   └── fmriprep-23-1-3/
│       └── image
```

## Appendix C: Migration Example

### Step 1: Assessment

```bash
# Check current project structure
babs-migrate assess --project-root /path/to/project

# Output:
# Current layout: legacy
# Container location: local (analysis/containers)
# Output format: zipped
# Suggested actions:
#   1. Migrate to BIDS-study layout
#   2. Move containers to shared location
#   3. Unzip existing outputs
```

### Step 2: Backup

```bash
# Create backup before migration
babs-migrate backup --project-root /path/to/project --backup-dir /path/to/backup
```

### Step 3: Migrate

```bash
# Perform migration
babs-migrate execute \
  --project-root /path/to/project \
  --target-layout bids-study \
  --shared-containers /opt/shared/containers \
  --unzip-outputs \
  --dry-run  # Remove after verifying plan

# Verify migration
babs-migrate verify --project-root /path/to/project
```

### Step 4: Update Configuration

```bash
# Update config for new layout
babs-config update \
  --project-root /path/to/project \
  --layout bids-study \
  --derivatives-dir derivatives \
  --no-zip-outputs
```

## Next Steps

1. **Review this document** with the team and stakeholders
2. **Prioritize features** based on user needs and resources
3. **Create detailed technical specifications** for Phase 1
4. **Set up development environment** with test datasets
5. **Begin implementation** starting with Phase 1
6. **Establish testing infrastructure** for new features
7. **Create user feedback mechanism** for beta testing

## Conclusion

This scaling plan provides a comprehensive roadmap for enhancing BABS to support large-scale workflows processing thousands of datasets. By implementing flexible container management, BIDS-study layout compliance, and multi-dataset support, BABS will become a more powerful and efficient tool for reproducible neuroimaging research at scale.

The phased approach ensures that critical features (container flexibility and BIDS-study layout) are implemented first, while maintaining backwards compatibility throughout the transition. The detailed technical specifications and code examples provide clear guidance for implementation.

Success will be measured not only by technical achievements but also by user adoption and the ability to process large-scale datasets efficiently and reproducibly.
