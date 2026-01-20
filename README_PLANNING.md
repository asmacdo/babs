# BABS Enhancement Initiative: Executive Summary

## Overview

This repository contains planning documentation for enhancing BABS (BIDS App Bootstrap) to support large-scale neuroimaging workflows processing thousands of datasets. These documents outline the goals, technical specifications, and implementation roadmap for making BABS a more scalable and flexible tool for reproducible neuroimaging research.

## Document Structure

### 1. SCALING_PLAN.md
**The comprehensive planning document**

This document provides:
- Current state analysis of BABS architecture
- Detailed goals and objectives for scaling
- Complete technical requirements for all proposed changes
- Phased implementation roadmap
- Testing strategy and success metrics
- Risk assessment and mitigation strategies

**Key Topics:**
- Flexible container management
- BIDS-study layout implementation
- Multi-dataset support
- Backwards compatibility considerations

**Audience:** Project stakeholders, development team, contributors

### 2. CONTAINER_PATH_SPEC.md
**Technical specification for container path flexibility**

This document focuses on the immediate priority: removing hardcoded container paths and enabling flexible container management.

**Key Topics:**
- Detailed problem statement
- Technical design for container path discovery
- Complete code implementation specifications
- Unit and integration testing plans
- Documentation requirements

**Audience:** Developers implementing the changes

### 3. This File (README_PLANNING.md)
**Navigation and quick reference**

Provides overview and guidance for using these planning documents.

## Priority Items

### High Priority (Implement First)

1. **Container Path Flexibility** (CONTAINER_PATH_SPEC.md)
   - Remove hardcoded paths
   - Enable DataLad config reading
   - Support repronim/containers
   - **Estimated Effort:** 2-3 weeks
   - **Impact:** High - Enables container sharing

2. **BIDS-Study Layout** (SCALING_PLAN.md, Phase 2)
   - Implement sourcedata/raw organization
   - Implement derivatives/<app> structure
   - Make output zipping optional
   - **Estimated Effort:** 3-4 weeks
   - **Impact:** High - Improves standards compliance

### Medium Priority

3. **Multi-Dataset Management** (SCALING_PLAN.md, Phase 3)
   - Dataset registry system
   - Batch processing capabilities
   - Shared resource management
   - **Estimated Effort:** 4-5 weeks
   - **Impact:** Medium - Enables large-scale workflows

### Lower Priority

4. **Migration Tools** (SCALING_PLAN.md, Phase 4)
   - Migration scripts
   - Documentation updates
   - Tutorial content
   - **Estimated Effort:** 2-3 weeks
   - **Impact:** Medium - Eases transition

## Key Problems Being Solved

### 1. Container Path Hardcoding
**Current Issue:**
```python
# babs/babs.py, lines 2210-2211
self.container_path_relToAnalysis = op.join(
    "containers", ".datalad", "environments",
    self.container_name, "image"
)
```

**Solution:** Flexible discovery reading from DataLad config and supporting multiple sources (local, shared, repronim).

**Benefit:** Enables container sharing across multiple datasets, reducing storage requirements and enabling use of repronim/containers infrastructure.

### 2. Output Organization
**Current Issue:**
- Outputs don't follow BIDS-study layout
- Limited customization options
- Not optimized for thousands of datasets

**Solution:** Implement BIDS-study layout with:
```
sourcedata/raw/          # Input BIDS datasets
derivatives/mriqc/       # MRIQC outputs (non-zipped)
derivatives/fmriprep/    # fMRIPrep outputs (non-zipped)
```

**Benefit:** Standards-compliant output organization, better for large-scale workflows, easier integration with other tools.

### 3. Scalability
**Current Issue:**
- Each project duplicates containers
- Limited support for processing multiple datasets
- No batch processing capabilities

**Solution:** 
- Shared container pools
- Dataset registry and management
- Batch processing infrastructure

**Benefit:** Can efficiently process thousands of datasets with shared resources.

## How to Use These Documents

### For Project Managers
1. Start with **SCALING_PLAN.md** for overview and roadmap
2. Review priority items and timeline
3. Use for resource planning and stakeholder communication

### For Developers
1. Read **SCALING_PLAN.md** for context and goals
2. Use **CONTAINER_PATH_SPEC.md** for implementation details
3. Follow the implementation checklist
4. Reference code examples and test specifications

### For Contributors
1. Review **SCALING_PLAN.md** to understand the vision
2. Pick tasks from the implementation roadmap
3. Use specifications for guidance
4. Follow the testing and documentation requirements

### For Users
1. These documents explain upcoming features
2. Prepare for new workflows and migration
3. Provide feedback on proposed changes

## Quick Start: Implementing Container Path Flexibility

The highest priority item can be started immediately. Here's the quickstart guide:

### Step 1: Review Specification
Read **CONTAINER_PATH_SPEC.md** sections:
- Problem Statement
- Proposed Solution
- Technical Design (Container Path Discovery Algorithm)
- Code Changes (sections 2.1, 2.2, 2.3)

### Step 2: Set Up Development Environment
```bash
# Clone repository
git clone https://github.com/asmacdo/babs.git
cd babs

# Create development branch
git checkout -b feature/flexible-container-paths

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run existing tests to ensure baseline
pytest tests/
```

### Step 3: Implement Core Functionality
1. Create `discover_container_path()` in `babs/utils.py`
2. Add helper functions and exceptions
3. Write unit tests for new functions
4. Run tests: `pytest tests/test_container_discovery.py`

### Step 4: Integrate with BABS
1. Modify `Container.__init__()` in `babs/babs.py`
2. Update CLI in `babs/cli.py`
3. Run integration tests
4. Test with real containers

### Step 5: Documentation
1. Create `docs/source/container_sources.rst`
2. Update existing documentation
3. Add examples

### Step 6: Review and Merge
1. Run full test suite
2. Create pull request
3. Address review feedback
4. Merge when approved

## Implementation Timeline

### Month 1: Container Path Flexibility
- **Weeks 1-2:** Core implementation
- **Weeks 3-4:** Testing and documentation

### Month 2: BIDS-Study Layout
- **Weeks 1-2:** Directory structure and path generation
- **Weeks 3-4:** Output organization and testing

### Month 3: Multi-Dataset Support
- **Weeks 1-2:** Design and core functionality
- **Weeks 3-4:** Testing and integration

### Month 4: Polish and Migration
- **Weeks 1-2:** Migration tools and documentation
- **Weeks 3-4:** User testing and refinement

## Success Metrics

Track progress using these metrics:

### Technical Metrics
- [ ] All existing tests pass (backwards compatibility)
- [ ] New tests achieve >90% code coverage
- [ ] Performance overhead <100ms for container discovery
- [ ] Zero breaking changes for existing users

### Functional Metrics
- [ ] Containers can be read from DataLad configuration
- [ ] repronim/containers integration works
- [ ] BIDS-study layout produces valid output
- [ ] Multiple datasets can share containers
- [ ] Can process 1000+ datasets efficiently

### Adoption Metrics
- [ ] Documentation covers all new features
- [ ] Migration tools successfully tested
- [ ] Positive user feedback
- [ ] Community contributions

## Getting Help

### Questions About These Plans?
- **For clarification:** Open an issue with label `question:planning`
- **For technical details:** Reference the specific document section
- **For implementation help:** Open an issue with label `implementation`

### Want to Contribute?
1. Review the implementation roadmap
2. Pick a task that interests you
3. Comment on the related issue (or create one)
4. Follow the implementation guidelines
5. Submit a pull request

### Found Issues in Planning?
- Open an issue with label `planning:issue`
- Describe the problem or inconsistency
- Suggest improvements if possible

## Related Resources

### BABS Resources
- **Documentation:** https://pennlinc-babs.readthedocs.io
- **Repository:** https://github.com/PennLINC/babs
- **Paper:** https://doi.org/10.1101/2023.08.16.552472

### External Resources
- **BIDS Specification:** https://bids-specification.readthedocs.io/
- **DataLad:** https://docs.datalad.org/
- **DataLad Containers:** http://docs.datalad.org/projects/container/
- **repronim/containers:** https://github.com/ReproNim/containers
- **FAIRly Big Framework:** https://doi.org/10.1038/s41597-022-01163-2

## Feedback and Updates

These planning documents are living documents that will evolve based on:
- Implementation findings
- User feedback
- Technical constraints
- Community input

**Last Updated:** 2026-01-20

**Status:** Planning Phase - Ready for Implementation

## Next Actions

1. **Team Review:** Schedule meeting to review these documents
2. **Prioritization:** Confirm priority order and timeline
3. **Resource Allocation:** Assign developers to phases
4. **Kickoff:** Begin Phase 1 implementation
5. **Community Engagement:** Share plans with user community

---

## Appendix: File Locations and Sizes

| File | Purpose | Size | Target Audience |
|------|---------|------|-----------------|
| SCALING_PLAN.md | Comprehensive plan | ~21KB | All stakeholders |
| CONTAINER_PATH_SPEC.md | Technical spec | ~29KB | Developers |
| README_PLANNING.md | This file | ~10KB | Everyone |

**Total Documentation:** ~60KB of planning documentation

## Document Maintenance

These documents should be updated:
- After each implementation phase
- When requirements change
- Based on user feedback
- When technical constraints are discovered

**Maintainer:** Development team lead
**Review Schedule:** Monthly during implementation, quarterly after completion
