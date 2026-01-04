# Tasks: PyPI Pre-Release Documentation Audit

**Feature**: 005-complete-a-top
**Input**: Design documents from `/Users/tdyar/ws/iris-devtester/specs/005-complete-a-top/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✅ Loaded: Documentation audit, 70 requirements, 3-phase approach
2. Load optional design documents:
   → ✅ research.md: Gap analysis, priorities identified
   → ✅ data-model.md: Documentation entities defined
   → ✅ contracts/: Audit criteria and validation rules
   → ✅ quickstart.md: Step-by-step implementation guide
3. Generate tasks by category:
   → Phase 0: Prerequisites and tooling
   → Phase 1: Critical files (P0 - blocks release)
   → Phase 2: Link fixes and validation (P0 - blocks release)
   → Phase 3: Quality improvements (P1 - enhances UX)
   → Phase 4: Polish and final validation (P2 - optional)
4. Apply task rules:
   → File creation tasks: [P] parallel (independent files)
   → README/pyproject edits: Sequential (same files)
   → Validation tasks: Sequential (depends on completion)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → ✅ All critical files covered
   → ✅ All validation steps included
   → ✅ Dependency order correct
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All paths are absolute from repository root

## Path Conventions
This is a documentation-only feature. Paths:
- **Root docs**: `/Users/tdyar/ws/iris-devtester/{file}`
- **GitHub templates**: `/Users/tdyar/ws/iris-devtester/.github/{path}`
- **Examples**: `/Users/tdyar/ws/iris-devtester/examples/{file}`
- **Docs**: `/Users/tdyar/ws/iris-devtester/docs/{file}`
- **Source** (for docstring audit): `/Users/tdyar/ws/iris-devtester/iris_devtester/{module}`

---

## Phase 0: Prerequisites and Environment Setup

**Goal**: Install validation tools and verify development environment

- [ ] **T001** [P] Install markdown-link-check for link validation
  - **Command**: `npm install -g markdown-link-check` (or check if already installed)
  - **Validation**: Run `markdown-link-check --version`
  - **Time**: 2 minutes

- [ ] **T002** [P] Install readme_renderer for PyPI preview
  - **Command**: `pip install readme_renderer`
  - **Validation**: Run `python -m readme_renderer --version`
  - **Time**: 2 minutes

- [ ] **T003** [P] Install twine for package validation
  - **Command**: `pip install twine`
  - **Validation**: Run `twine --version`
  - **Time**: 2 minutes

- [ ] **T004** Verify development environment
  - **Check**: Python 3.9+, git, Docker running
  - **Validation**: `python --version`, `git --version`, `docker ps`
  - **Time**: 2 minutes

**Phase 0 Exit Criteria**:
- [x] All validation tools installed
- [x] Development environment verified
- [x] Ready to create documentation files

**Estimated Time**: 10 minutes

---

## Phase 1: Critical Files Creation (P0 - Blocks Release)

**Goal**: Create all missing community health files required for professional PyPI package

### Community Health Files

- [ ] **T005** [P] Create CONTRIBUTING.md
  - **File**: `/Users/tdyar/ws/iris-devtester/CONTRIBUTING.md`
  - **Source**: Template in `specs/005-complete-a-top/quickstart.md` (lines 15-154)
  - **Content**: Development setup, testing guidelines, code style, governance
  - **Validation**: File exists, contains all required sections (Development Setup, Testing Guidelines, etc.)
  - **Time**: 20 minutes

- [ ] **T006** [P] Create CODE_OF_CONDUCT.md
  - **File**: `/Users/tdyar/ws/iris-devtester/CODE_OF_CONDUCT.md`
  - **Source**: Contributor Covenant 2.1 (`curl https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md`)
  - **Customization**: Replace `[INSERT CONTACT METHOD]` with `community@intersystems.com`
  - **Validation**: File exists, contains Contributor Covenant 2.1 text
  - **Time**: 10 minutes

- [ ] **T007** [P] Create SECURITY.md
  - **File**: `/Users/tdyar/ws/iris-devtester/SECURITY.md`
  - **Source**: Template in `specs/005-complete-a-top/quickstart.md` (lines 165-235)
  - **Content**: Supported versions, reporting process, security best practices
  - **Validation**: File exists, contains disclosure policy and contact info
  - **Time**: 15 minutes

### GitHub Issue Templates

- [ ] **T008** [P] Create bug report template
  - **File**: `/Users/tdyar/ws/iris-devtester/.github/ISSUE_TEMPLATE/bug_report.yml`
  - **Source**: Template in `specs/005-complete-a-top/quickstart.md` (lines 242-298)
  - **Content**: YAML form with required fields (version, Python version, IRIS edition, etc.)
  - **Validation**: Valid YAML, file renders in GitHub UI
  - **Time**: 15 minutes

- [ ] **T009** [P] Create feature request template
  - **File**: `/Users/tdyar/ws/iris-devtester/.github/ISSUE_TEMPLATE/feature_request.yml`
  - **Source**: Template in `specs/005-complete-a-top/quickstart.md` (lines 300-332)
  - **Content**: YAML form for feature suggestions
  - **Validation**: Valid YAML, file renders in GitHub UI
  - **Time**: 10 minutes

- [ ] **T010** [P] Create pull request template
  - **File**: `/Users/tdyar/ws/iris-devtester/.github/PULL_REQUEST_TEMPLATE.md`
  - **Source**: Template in `specs/005-complete-a-top/quickstart.md` (lines 335-375)
  - **Content**: Checklist for PRs, constitutional compliance section
  - **Validation**: File exists, contains all required sections
  - **Time**: 10 minutes

**Phase 1 Exit Criteria**:
- [x] All 6 critical files exist
- [x] Files follow templates from quickstart.md
- [x] No syntax errors in YAML templates
- [x] GitHub renders templates correctly (manual check)

**Estimated Time**: 1.5 hours

---

## Phase 2: README and Metadata Fixes (P0 - Blocks Release)

**Goal**: Fix all PyPI compatibility issues and broken references

### README.md Fixes

- [ ] **T011** Fix README.md relative links to absolute URLs
  - **File**: `/Users/tdyar/ws/iris-devtester/README.md`
  - **Action**: Convert all relative links to absolute format
  - **Pattern**: `[text](file)` → `[text](https://github.com/intersystems-community/iris-devtester/blob/main/file)`
  - **Affected Links**:
    - `[CONTRIBUTING.md](CONTRIBUTING.md)` → absolute
    - `[Quickstart Guide](docs/quickstart.md)` → remove or create file
    - `[Best Practices](docs/best-practices.md)` → remove or create file
    - `[Troubleshooting](docs/troubleshooting.md)` → update to `docs/TROUBLESHOOTING.md` (to be created)
    - All other relative references
  - **Validation**: All links use `https://` format, no relative paths
  - **Time**: 30 minutes

- [ ] **T012** Remove broken documentation references from README.md
  - **File**: `/Users/tdyar/ws/iris-devtester/README.md`
  - **Action**: Remove or update references to non-existent files
  - **Files to check**:
    - `docs/quickstart.md` (doesn't exist) - remove link
    - `docs/best-practices.md` (doesn't exist) - remove link
    - `docs/troubleshooting.md` (will be created as `docs/TROUBLESHOOTING.md`) - update reference
  - **Validation**: All referenced files exist or links removed
  - **Time**: 15 minutes

- [ ] **T013** Define acronyms on first use in README.md
  - **File**: `/Users/tdyar/ws/iris-devtester/README.md`
  - **Action**: Add definitions for: DBAPI, JDBC, RAG, CI/CD
  - **Pattern**: First use → "DBAPI (Database API)"
  - **Validation**: All acronyms defined on first occurrence
  - **Time**: 15 minutes

### pyproject.toml Fixes

- [ ] **T014** Update pyproject.toml development status classifier
  - **File**: `/Users/tdyar/ws/iris-devtester/pyproject.toml`
  - **Change**: `"Development Status :: 4 - Beta"` → `"Development Status :: 5 - Production/Stable"`
  - **Rationale**: Package is v1.0.0, should reflect production readiness
  - **Validation**: Classifier matches version maturity
  - **Time**: 5 minutes

- [ ] **T015** Add changelog URL to pyproject.toml
  - **File**: `/Users/tdyar/ws/iris-devtester/pyproject.toml`
  - **Action**: Add to `[project.urls]` section: `Changelog = "https://github.com/intersystems-community/iris-devtester/blob/main/CHANGELOG.md"`
  - **Validation**: URL resolves, points to CHANGELOG.md
  - **Time**: 5 minutes

- [ ] **T016** Verify pyproject.toml description matches README tagline
  - **Files**: `/Users/tdyar/ws/iris-devtester/pyproject.toml` and `README.md`
  - **Check**: `description = "..."` in pyproject.toml equals README first paragraph
  - **Action**: If mismatch, update to match
  - **Validation**: Character-for-character match
  - **Time**: 10 minutes

### LICENSE Verification

- [ ] **T017** Verify LICENSE year is current
  - **File**: `/Users/tdyar/ws/iris-devtester/LICENSE`
  - **Check**: Copyright year is 2024 or 2025
  - **Action**: Update if outdated
  - **Validation**: Year is 2024 or 2025
  - **Time**: 5 minutes

**Phase 2 Exit Criteria**:
- [x] README uses only absolute URLs
- [x] All referenced files exist or removed
- [x] pyproject.toml classifier updated to Production/Stable
- [x] pyproject.toml has changelog URL
- [x] Acronyms defined in README
- [x] LICENSE year current

**Estimated Time**: 1.5 hours

---

## Phase 3: Quality Improvements (P1 - Enhances UX)

**Goal**: Create missing examples and documentation to improve first-time user experience

### Troubleshooting Guide

- [ ] **T018** Create docs/TROUBLESHOOTING.md
  - **File**: `/Users/tdyar/ws/iris-devtester/docs/TROUBLESHOOTING.md`
  - **Source**: Template structure in `specs/005-complete-a-top/data-model.md` (lines 435-482)
  - **Content**: Top 5 issues with symptom → diagnosis → solution → prevention format
  - **Issues to cover**:
    1. Docker daemon not running
    2. Password change required
    3. Port conflicts
    4. Connection failures
    5. Permission issues
  - **Validation**: All 5 issues documented, follows format template
  - **Time**: 1.5 hours

### Example Enhancements

- [ ] **T019** Enhance examples/README.md with learning path
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/README.md`
  - **Action**: Add learning path section showing recommended order (01→02→04→05→08→09)
  - **Source**: Template in `specs/005-complete-a-top/data-model.md` (lines 348-382)
  - **Content**: Prerequisites, learning path, "what each example demonstrates"
  - **Validation**: README includes learning path, prerequisites, expected outputs
  - **Time**: 30 minutes

- [ ] **T020** [P] Create examples/02_pytest_basic.py (if missing)
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/02_pytest_basic.py`
  - **Check**: If file doesn't exist, create it
  - **Source**: Template pattern in `specs/005-complete-a-top/data-model.md` (lines 384-420)
  - **Content**: Basic pytest fixture demo, module-scoped container
  - **Validation**: Example runs without errors, includes expected output comments
  - **Time**: 1 hour

- [ ] **T021** [P] Create examples/05_ci_cd.py
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/05_ci_cd.py`
  - **Content**: GitHub Actions integration example
  - **Demonstrates**: CI/CD setup, testcontainers in GitHub Actions, caching strategies
  - **Validation**: Example includes docstring, imports, expected output, runs successfully
  - **Time**: 1.5 hours

- [ ] **T022** [P] Create examples/09_enterprise.py
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/09_enterprise.py`
  - **Content**: Enterprise edition features demo
  - **Demonstrates**: License key usage, enterprise-specific features, advanced configuration
  - **Validation**: Example includes docstring, imports, expected output, conditional execution (skips if no license)
  - **Time**: 1.5 hours

- [ ] **T023** Add expected output to examples/01_quickstart.py
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/01_quickstart.py`
  - **Action**: Add `# Expected output: ...` comments showing what users should see
  - **Validation**: All print statements have corresponding expected output comments
  - **Time**: 15 minutes

- [ ] **T024** Add expected output to examples/04_pytest_fixtures.py
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/04_pytest_fixtures.py`
  - **Action**: Add `# Expected output: ...` comments
  - **Validation**: All print/assert statements have expected output comments
  - **Time**: 15 minutes

- [ ] **T025** Add expected output to examples/08_auto_discovery.py
  - **File**: `/Users/tdyar/ws/iris-devtester/examples/08_auto_discovery.py`
  - **Action**: Add `# Expected output: ...` comments
  - **Validation**: All print statements have expected output comments
  - **Time**: 15 minutes

### Example Testing

- [ ] **T026** Test all examples run without errors
  - **Files**: All `/Users/tdyar/ws/iris-devtester/examples/*.py`
  - **Action**: Run each example: `python examples/{file}.py`
  - **Validation**: All examples complete successfully, no errors
  - **Dependencies**: Requires Docker running, iris-devtester installed
  - **Time**: 30 minutes

**Phase 3 Exit Criteria**:
- [x] docs/TROUBLESHOOTING.md exists with top 5 issues
- [x] examples/README.md has learning path
- [x] All planned examples exist (02, 05, 09)
- [x] All examples include expected output
- [x] All examples run successfully

**Estimated Time**: 7 hours

---

## Phase 4: Polish and Final Validation (P2 - Optional Improvements)

**Goal**: Docstring audit, consistency checks, and comprehensive validation

### Docstring Audits

- [ ] **T027** [P] Audit iris_devtester/containers/ docstrings
  - **Files**: All Python files in `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/`
  - **Check**: All public classes/functions have Google-style docstrings with examples
  - **Requirements** (from FR-021, FR-022):
    - One-line summary
    - Extended description
    - All parameters documented
    - Return value documented
    - Minimal working example
  - **Action**: Add/enhance docstrings where missing or incomplete
  - **Validation**: All public APIs have complete docstrings
  - **Time**: 2 hours

- [ ] **T028** [P] Audit iris_devtester/connections/ docstrings
  - **Files**: All Python files in `/Users/tdyar/ws/iris-devtester/iris_devtester/connections/`
  - **Check**: Same requirements as T027
  - **Action**: Add/enhance docstrings
  - **Validation**: All public APIs have complete docstrings
  - **Time**: 2 hours

- [ ] **T029** [P] Audit iris_devtester/testing/ docstrings
  - **Files**: All Python files in `/Users/tdyar/ws/iris-devtester/iris_devtester/testing/`
  - **Check**: Same requirements as T027
  - **Action**: Add/enhance docstrings
  - **Validation**: All public APIs have complete docstrings
  - **Time**: 2 hours

### Consistency Checks

- [ ] **T030** Verify version consistency across files
  - **Files**:
    - `/Users/tdyar/ws/iris-devtester/README.md` (badge)
    - `/Users/tdyar/ws/iris-devtester/pyproject.toml` (version field)
    - `/Users/tdyar/ws/iris-devtester/iris_devtester/__init__.py` (__version__)
    - `/Users/tdyar/ws/iris-devtester/CHANGELOG.md` (latest version)
  - **Action**: Extract version from each file, ensure all match
  - **Validation**: All 4 locations show same version (1.0.0)
  - **Time**: 15 minutes

- [ ] **T031** Verify contact email validity
  - **Files**: README.md, SECURITY.md, CODE_OF_CONDUCT.md, pyproject.toml
  - **Check**: All email addresses are valid and monitored (or marked as examples)
  - **Action**: Update if invalid or add note if placeholder
  - **Validation**: No invalid/unmonitored emails
  - **Time**: 10 minutes

### Final Validations

- [ ] **T032** Validate PyPI README rendering
  - **File**: `/Users/tdyar/ws/iris-devtester/README.md`
  - **Command**: `python -m readme_renderer README.md -o /tmp/readme.html`
  - **Check**: No rendering errors, HTML looks correct
  - **Validation**: README renders without errors, formatting preserved
  - **Time**: 10 minutes

- [ ] **T033** Check all markdown links resolve
  - **Files**: All `*.md` files in repository
  - **Command**: `find . -name "*.md" -not -path "./node_modules/*" -not -path "./.venv/*" | xargs markdown-link-check`
  - **Validation**: No broken links (HTTP 200 for all URLs)
  - **Time**: 15 minutes

- [ ] **T034** Build package and run twine check
  - **Commands**:
    ```bash
    python -m build
    twine check dist/*
    ```
  - **Validation**: Package builds successfully, passes twine validation
  - **Time**: 10 minutes

- [ ] **T035** Run final compliance check against 70 requirements
  - **Source**: `specs/005-complete-a-top/spec.md` (FR-001 to FR-070)
  - **Action**: Manual review of each requirement against deliverables
  - **Validation**: All 70 requirements marked as "met" or "partial" with justification
  - **Time**: 1.5 hours

**Phase 4 Exit Criteria**:
- [x] All module docstrings audited and complete
- [x] Version consistent across all 4 files
- [x] Contact emails valid
- [x] README renders correctly on PyPI
- [x] All links resolve (no 404s)
- [x] Package builds and validates
- [x] 70-requirement compliance validated

**Estimated Time**: 8.5 hours

---

## Dependencies

### Critical Path
```
Phase 0 (T001-T004)
  ↓
Phase 1 (T005-T010) [All parallel]
  ↓
Phase 2 (T011-T017) [Sequential due to file dependencies]
  ↓
Phase 3 (T018-T026) [T020-T022 parallel, others sequential]
  ↓
Phase 4 (T027-T035) [T027-T029 parallel, T030-T035 sequential]
```

### Specific Dependencies

**Phase 0**:
- T001, T002, T003 → Can run in parallel
- T004 → Depends on T001-T003 complete

**Phase 1** (All parallel - different files):
- T005, T006, T007, T008, T009, T010 → Independent

**Phase 2** (Sequential - same files):
- T011 → T012 → T013 (all edit README.md)
- T014 → T015 → T016 (all edit pyproject.toml)
- T017 → Independent

**Phase 3**:
- T018 → Independent
- T019 → Blocks T026 (examples README needed for context)
- T020, T021, T022 → Can run in parallel (different files)
- T023, T024, T025 → Can run after T020-T022, but sequential per file
- T026 → Depends on T020-T025 (all examples must exist)

**Phase 4**:
- T027, T028, T029 → Can run in parallel (different modules)
- T030 → Independent
- T031 → Depends on T005-T007 (files must exist)
- T032 → Depends on T011-T013 (README must be fixed)
- T033 → Depends on T011-T012 (links must be absolute)
- T034 → Depends on T014-T016 (pyproject.toml must be fixed)
- T035 → Depends on all previous tasks

---

## Parallel Execution Examples

### Launch Phase 0 Prerequisites in Parallel
```bash
# Terminal 1
npm install -g markdown-link-check

# Terminal 2
pip install readme_renderer

# Terminal 3
pip install twine
```

### Launch Phase 1 File Creation in Parallel
```bash
# Using Task agents (example - adjust paths as needed)
Task: "Create CONTRIBUTING.md from template in specs/005-complete-a-top/quickstart.md at /Users/tdyar/ws/iris-devtester/CONTRIBUTING.md"
Task: "Create CODE_OF_CONDUCT.md using Contributor Covenant 2.1 at /Users/tdyar/ws/iris-devtester/CODE_OF_CONDUCT.md"
Task: "Create SECURITY.md from template at /Users/tdyar/ws/iris-devtester/SECURITY.md"
Task: "Create bug_report.yml template at /Users/tdyar/ws/iris-devtester/.github/ISSUE_TEMPLATE/bug_report.yml"
Task: "Create feature_request.yml template at /Users/tdyar/ws/iris-devtester/.github/ISSUE_TEMPLATE/feature_request.yml"
Task: "Create PR template at /Users/tdyar/ws/iris-devtester/.github/PULL_REQUEST_TEMPLATE.md"
```

### Launch Phase 3 Example Creation in Parallel
```bash
# Parallel tasks (different files)
Task: "Create examples/02_pytest_basic.py with basic pytest fixture demo"
Task: "Create examples/05_ci_cd.py with GitHub Actions integration example"
Task: "Create examples/09_enterprise.py with enterprise edition demo"
```

### Launch Phase 4 Docstring Audits in Parallel
```bash
# Parallel tasks (different modules)
Task: "Audit and enhance docstrings in iris_devtester/containers/ module"
Task: "Audit and enhance docstrings in iris_devtester/connections/ module"
Task: "Audit and enhance docstrings in iris_devtester/testing/ module"
```

---

## Time Estimates by Phase

| Phase | Tasks | Parallel Time | Sequential Time | Recommended |
|-------|-------|---------------|-----------------|-------------|
| Phase 0 | T001-T004 | 10 min | 10 min | Parallel |
| Phase 1 | T005-T010 | 1.5 hours | 1.5 hours | Parallel |
| Phase 2 | T011-T017 | N/A | 1.5 hours | Sequential |
| Phase 3 | T018-T026 | 4 hours | 7 hours | Mixed |
| Phase 4 | T027-T035 | 5 hours | 8.5 hours | Mixed |
| **Total** | **35 tasks** | **12 hours** | **18.5 hours** | **~16 hours** |

**Note**: Mixed parallel/sequential execution yields ~16 hours (matches research estimate of 16-24 hours)

---

## Task Completion Checklist

### Phase 0: Prerequisites ✓
- [ ] T001: markdown-link-check installed
- [ ] T002: readme_renderer installed
- [ ] T003: twine installed
- [ ] T004: Environment verified

### Phase 1: Critical Files ✓
- [ ] T005: CONTRIBUTING.md created
- [ ] T006: CODE_OF_CONDUCT.md created
- [ ] T007: SECURITY.md created
- [ ] T008: bug_report.yml created
- [ ] T009: feature_request.yml created
- [ ] T010: PR template created

### Phase 2: Fixes ✓
- [ ] T011: README links absolute
- [ ] T012: Broken references removed
- [ ] T013: Acronyms defined
- [ ] T014: Classifier updated
- [ ] T015: Changelog URL added
- [ ] T016: Description matches
- [ ] T017: LICENSE year current

### Phase 3: Quality ✓
- [ ] T018: TROUBLESHOOTING.md created
- [ ] T019: examples/README.md enhanced
- [ ] T020: examples/02_pytest_basic.py created
- [ ] T021: examples/05_ci_cd.py created
- [ ] T022: examples/09_enterprise.py created
- [ ] T023: 01_quickstart.py output added
- [ ] T024: 04_pytest_fixtures.py output added
- [ ] T025: 08_auto_discovery.py output added
- [ ] T026: All examples tested

### Phase 4: Polish ✓
- [ ] T027: containers/ docstrings audited
- [ ] T028: connections/ docstrings audited
- [ ] T029: testing/ docstrings audited
- [ ] T030: Version consistency verified
- [ ] T031: Contact emails validated
- [ ] T032: PyPI rendering validated
- [ ] T033: Links validated
- [ ] T034: Package builds successfully
- [ ] T035: 70-requirement compliance validated

---

## Notes

### Task Execution Guidelines
- **[P] tasks**: Can be executed in parallel (different files, no dependencies)
- **Sequential tasks**: Must be executed in order (same file or dependencies)
- **Validation**: Test after each task, commit if successful
- **Rollback**: Use git to revert if task fails

### Common Pitfalls to Avoid
- ❌ Don't skip validation steps - they catch issues early
- ❌ Don't modify multiple files in parallel if they reference each other
- ❌ Don't forget to test examples in fresh environment (not just dev environment)
- ❌ Don't skip link validation - broken links on PyPI look unprofessional

### Success Criteria (Overall)
Before marking this feature complete:
1. All 35 tasks completed and validated
2. All 70 requirements from spec.md verified
3. README renders correctly in PyPI preview
4. All examples run without errors
5. All links resolve (no 404s)
6. Package builds and passes twine check
7. Version consistent across all files
8. Community health files present (GitHub "Insights" tab shows complete)

---

## Task Generation Rules Followed

✅ **Different files = [P] parallel**: T005-T010, T020-T022, T027-T029
✅ **Same file = sequential**: T011-T013 (README), T014-T016 (pyproject.toml)
✅ **Tests before implementation**: N/A (documentation feature, no TDD)
✅ **Setup before core**: Phase 0 before all others
✅ **Core before integration**: Phase 1-2 before Phase 3
✅ **Everything before polish**: Phases 0-3 before Phase 4
✅ **Validation last**: T032-T035 at end of Phase 4

---

**Tasks Status**: ✅ Ready for Execution

**Next Step**: Execute tasks in order, validating each before proceeding. Use parallel execution where marked [P] to optimize time.

**Estimated Completion**: 16-24 hours (12 hours if maximally parallel, 18.5 hours if sequential, ~16 hours with optimal mixed approach)
