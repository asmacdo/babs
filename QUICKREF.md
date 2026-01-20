# Quick Reference: BABS Scaling Initiative

## 📋 What Was Done

Created comprehensive planning documentation for scaling BABS to handle thousands of datasets with:
- Flexible container management (supporting repronim/containers)
- BIDS-study layout compliance
- Multi-dataset processing capabilities

## 📁 Documents Created

| Document | Purpose | Lines | Size |
|----------|---------|-------|------|
| **SCALING_PLAN.md** | Comprehensive roadmap for all enhancements | 750 | 22KB |
| **CONTAINER_PATH_SPEC.md** | Detailed technical spec for container flexibility | 943 | 29KB |
| **README_PLANNING.md** | Executive summary and navigation guide | 318 | 10KB |
| **QUICKREF.md** | This quick reference | - | - |

## 🎯 Key Problems Addressed

### 1. Container Path Hardcoding
**Problem:** Container paths are hardcoded at `babs/babs.py:2210-2211`
```python
self.container_path_relToAnalysis = op.join(
    "containers", ".datalad", "environments",
    self.container_name, "image"
)
```

**Solution:** Flexible container discovery supporting:
- DataLad configuration reading
- Shared container locations
- repronim/containers infrastructure
- Explicit paths for testing

### 2. Output Organization
**Problem:** Outputs don't follow BIDS-study layout standards

**Solution:** Implement structure:
```
project/
├── sourcedata/raw/           # Input BIDS datasets
├── derivatives/
│   ├── mriqc/               # MRIQC outputs (non-zipped)
│   └── fmriprep/            # fMRIPrep outputs (non-zipped)
```

### 3. Scalability
**Problem:** Limited support for processing thousands of datasets

**Solution:** 
- Shared container pools across datasets
- Dataset registry and management
- Batch processing infrastructure

## 🚀 Implementation Priority

### Phase 1: Container Path Flexibility (HIGH PRIORITY)
**Estimated:** 2-3 weeks
- Remove hardcoded paths
- Implement flexible discovery
- Support repronim/containers
- **Start Here!**

### Phase 2: BIDS-Study Layout (HIGH PRIORITY)
**Estimated:** 3-4 weeks
- Implement sourcedata/raw structure
- Implement derivatives/<app> structure
- Make zipping optional

### Phase 3: Multi-Dataset Management (MEDIUM PRIORITY)
**Estimated:** 4-5 weeks
- Dataset registry
- Shared resource management
- Batch processing

### Phase 4: Migration Tools (MEDIUM PRIORITY)
**Estimated:** 2-3 weeks
- Migration scripts
- Documentation updates
- Tutorials

## 📖 Where to Start

### For Developers
1. Read **SCALING_PLAN.md** (Sections: Current State, Goals, Phase 1)
2. Read **CONTAINER_PATH_SPEC.md** (Complete - it's your implementation guide)
3. Set up dev environment:
   ```bash
   git checkout -b feature/flexible-container-paths
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```
4. Implement `discover_container_path()` in `babs/utils.py`
5. Follow the Implementation Checklist in CONTAINER_PATH_SPEC.md

### For Project Managers
1. Read **README_PLANNING.md** (complete overview)
2. Review **SCALING_PLAN.md** (Sections: Goals, Implementation Roadmap, Timeline)
3. Use for resource planning and stakeholder communication

### For Reviewers
1. Start with **README_PLANNING.md**
2. Check each document for:
   - Clarity and completeness
   - Technical accuracy
   - Feasibility of timeline
   - Missing considerations

## 💡 Key Insights

### From Code Analysis
- Container path is hardcoded in **one location**: `babs/babs.py:2210-2211`
- Uses `datalad_container.find_container import find_container_` (line 20)
- Configuration is read via `read_container_config_yaml()` method
- Current structure: `containers/.datalad/environments/<name>/image`

### From Documentation Analysis
- Current docs explain `datalad containers-add` workflow
- No documentation for shared containers
- No documentation for repronim/containers usage
- Migration documentation will be needed

### From Requirements Analysis
- Must maintain backwards compatibility
- Performance overhead must be minimal (<100ms)
- Clear error messages are critical
- Testing is extensive (unit + integration + e2e)

## ✅ Success Criteria

### Technical
- [ ] All existing tests pass
- [ ] New tests achieve >90% coverage
- [ ] Performance overhead <100ms
- [ ] Zero breaking changes

### Functional
- [ ] Read from DataLad config works
- [ ] repronim/containers integration works
- [ ] BIDS-study layout produces valid output
- [ ] Multiple datasets can share containers

### Adoption
- [ ] Documentation complete
- [ ] Migration tools tested
- [ ] Positive user feedback

## 📞 Getting Help

### Questions?
- **About planning:** Open issue with `question:planning` label
- **About implementation:** Open issue with `implementation` label

### Want to Contribute?
1. Review implementation roadmap
2. Pick a task
3. Comment on related issue
4. Submit PR

### Found Issues?
- Open issue with `planning:issue` label
- Describe problem
- Suggest improvements

## 🔗 Links

### BABS
- Docs: https://pennlinc-babs.readthedocs.io
- Repo: https://github.com/PennLINC/babs
- Paper: https://doi.org/10.1101/2023.08.16.552472

### Related
- BIDS Spec: https://bids-specification.readthedocs.io/
- DataLad: https://docs.datalad.org/
- repronim/containers: https://github.com/ReproNim/containers

## 📊 Statistics

- **Total Planning Documentation:** ~60KB
- **Total Lines:** 2,011
- **Estimated Implementation Time:** 3-4 months
- **Team Size Suggested:** 2-3 developers
- **Priority Features:** Container flexibility + BIDS-study layout
- **Expected Impact:** Enable processing of 1000+ datasets efficiently

## 🗓️ Timeline Summary

| Month | Phase | Focus | Deliverable |
|-------|-------|-------|-------------|
| 1 | Phase 1 | Container Paths | Flexible discovery working |
| 2 | Phase 2 | BIDS Layout | Standards-compliant output |
| 3 | Phase 3 | Multi-Dataset | Batch processing |
| 4 | Phase 4 | Migration | Tools and docs |

## 🎬 Next Steps

1. **Immediate:**
   - Team review of planning documents
   - Confirm priorities and timeline
   - Allocate resources

2. **Week 1:**
   - Start Phase 1 implementation
   - Set up test environment
   - Create GitHub issues for tasks

3. **Week 2-3:**
   - Implement core functionality
   - Write unit tests
   - Initial testing

4. **Week 4:**
   - Integration testing
   - Documentation
   - PR and review

## 📝 Notes

- No code changes were made in this planning phase
- These are planning documents only
- Implementation can start immediately
- All changes maintain backwards compatibility
- Documents are living - update as needed

---

**Created:** 2026-01-20  
**Status:** Planning Complete - Ready for Implementation  
**Last Updated:** 2026-01-20
