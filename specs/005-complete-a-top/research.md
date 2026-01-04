# Research: PyPI Pre-Release Documentation Audit

**Feature**: 005-complete-a-top
**Phase**: 0 (Research)
**Date**: 2025-11-03

## Research Goal

Understand current documentation state, identify gaps against 70 functional requirements, and determine remediation priorities for PyPI release readiness.

## Current State Inventory

### Existing Documentation Files

Based on project inspection:

**Root-level Documentation**:
- ✅ `README.md` - 221 lines, comprehensive, includes quickstart
- ✅ `CHANGELOG.md` - Exists, tracks changes
- ✅ `CONSTITUTION.md` - 416 lines, 8 principles well documented
- ✅ `LICENSE` - MIT license present
- ✅ `CLAUDE.md` - Project-specific guidance (11,184 bytes)
- ✅ `pyproject.toml` - Package metadata configured
- ❌ `CONTRIBUTING.md` - **MISSING** (FR-041)
- ❌ `CODE_OF_CONDUCT.md` - **MISSING** (FR-044)
- ❌ `SECURITY.md` - **MISSING** (required for security-conscious users)

**Examples Directory**:
- ✅ `examples/` exists with 3 files:
  - `01_quickstart.py` (1,162 bytes)
  - `04_pytest_fixtures.py` (2,948 bytes)
  - `08_auto_discovery.py` (3,018 bytes)
- ✅ `examples/README.md` (1,981 bytes)
- ⚠️  Gap: Missing CI/CD example, enterprise setup example (FR-023)

**docs/ Directory Structure**:
```
docs/
├── examples/          # Empty or minimal
├── features/          # Feature documentation
├── learnings/         # 14 files - production insights (FR-047 compliant)
├── IMPACT_ANALYSIS.md
├── PHASE_2_PLAN.md
├── RAG_TEMPLATES_ANALYSIS.md
├── SQL_VS_OBJECTSCRIPT.md
```

**Learnings Directory** (FR-047):
- ✅ Well-populated: 14 documented learnings
- ✅ Aligns with Constitution Principle #8 (Document the Blind Alleys)
- Examples: `callin-service-requirement.md`, `dbapi-bulk-insert-performance-issue.md`

**Issue Templates**:
- ❌ `.github/ISSUE_TEMPLATE/` - **MISSING** (FR-036)
- ❌ `.github/PULL_REQUEST_TEMPLATE.md` - **MISSING** (FR-048)

### pyproject.toml Analysis (FR-066 to FR-070)

**Current Status**:
```toml
[project]
name = "iris-devtester"
version = "1.0.0"
description = "Battle-tested InterSystems IRIS infrastructure utilities for Python development"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
```

**Compliance Check**:
- ✅ FR-067: README as long_description (implicit via `readme = "README.md"`)
- ✅ FR-070: Semantic versioning (1.0.0)
- ⚠️  FR-066: Classifiers present but could be enhanced
- ⚠️  FR-069: Project URLs present but no explicit changelog URL

**Current Classifiers** (24 total):
```python
"Development Status :: 4 - Beta"  # ⚠️  Should be "5 - Production/Stable" for v1.0.0
```

### README.md Deep Analysis

**Structure** (current):
1. Title + badges (✅)
2. "What is This?" (✅)
3. "The Problem It Solves" (✅ FR-005 compliant)
4. Quick Start (✅)
5. Key Features (✅)
6. Example: Enterprise Setup (✅)
7. Architecture (✅)
8. Constitution (✅ FR-046 compliant)
9. Documentation (⚠️ some broken links)
10. Real-World Use Cases (✅)
11. Performance (✅ FR-060 - benchmarks present)
12. Requirements (✅ FR-007)
13. Contributing (⚠️ links to non-existent CONTRIBUTING.md)
14. Credits (✅ FR-045)
15. License (✅ FR-010)
16. Support (✅ FR-034)

**Gaps Identified**:
- FR-009: Some links are relative, not absolute (will break on PyPI)
- FR-012: Installation options explained, but "when to choose" could be clearer
- FR-015: "What happens next" after quickstart - partially covered
- FR-031: Links to `docs/troubleshooting.md` which doesn't exist as standalone file
- FR-057: References to `docs/quickstart.md`, `docs/best-practices.md` (don't exist)

### Code Example Audit (FR-013, FR-014, FR-017, FR-018)

**README Quickstart Example**:
```python
from iris_devtester.containers import IRISContainer

with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone())
```

**Compliance**:
- ✅ FR-013: Runnable as-is (no hidden prereqs except Docker)
- ✅ FR-017: All imports explicit
- ⚠️  FR-018: Expected output not shown
- ⚠️  FR-014: Should complete <1 minute (need to verify with fresh install)

### Docstring Audit (FR-021, FR-022)

**Sample Check** (`iris_devtester/containers/__init__.py`):
- Need to audit all public APIs for:
  - Google-style docstrings
  - Working examples in docstrings
  - Parameter documentation
  - Return type documentation

## PyPI Rendering Analysis

### Potential Issues

1. **Relative Links** (FR-009):
   - Current: `[CONTRIBUTING.md](CONTRIBUTING.md)`
   - Should be: `[CONTRIBUTING.md](https://github.com/intersystems-community/iris-devtester/blob/main/CONTRIBUTING.md)`

2. **README Length** (FR-068):
   - Current: 221 lines (~6,729 bytes)
   - PyPI limit: ~512 KB for rendered HTML
   - ✅ Well under limit

3. **Badge URLs** (FR-004):
   - Need to verify all badges point to correct URLs for PyPI package
   - PyPI badge currently shows `iris-devtester` (correct)

## Gap Analysis by Requirement Category

### Critical Gaps (Block PyPI Release)

| ID | Requirement | Status | Priority |
|----|-------------|--------|----------|
| FR-041 | CONTRIBUTING.md | ❌ Missing | P0 |
| FR-044 | CODE_OF_CONDUCT.md | ❌ Missing | P0 |
| FR-036 | Issue templates | ❌ Missing | P0 |
| FR-048 | PR template | ❌ Missing | P0 |
| FR-009 | Absolute URLs in README | ⚠️  Partial | P0 |
| FR-057 | Remove broken doc links | ⚠️  Partial | P0 |

### High-Priority Gaps (Improve First Impression)

| ID | Requirement | Status | Priority |
|----|-------------|--------|----------|
| FR-018 | Show expected output in examples | ⚠️  Partial | P1 |
| FR-023 | CI/CD + Enterprise examples | ⚠️  Partial | P1 |
| FR-025 | Examples README with learning order | ⚠️  Partial | P1 |
| FR-031 | Dedicated troubleshooting doc | ❌ Missing | P1 |
| FR-062 | Define acronyms on first use | ⚠️  Needs check | P1 |

### Medium-Priority Gaps (Quality Improvements)

| ID | Requirement | Status | Priority |
|----|-------------|--------|----------|
| FR-012 | Explain when to choose each install option | ⚠️  Partial | P2 |
| FR-015 | "What happens next" after quickstart | ⚠️  Partial | P2 |
| FR-021 | All APIs have Google-style docstrings | ⚠️  Needs audit | P2 |
| FR-022 | Docstrings include examples | ⚠️  Needs audit | P2 |
| FR-027 | Examples tested in CI | ⚠️  Needs verification | P2 |
| FR-038 | Error messages reference docs | ⚠️  Needs audit | P2 |
| FR-066 | Classifiers for discoverability | ⚠️  Can improve | P2 |

### Low-Priority Gaps (Nice-to-Have)

| ID | Requirement | Status | Priority |
|----|-------------|--------|----------|
| FR-039 | Migration guide for major versions | N/A | P3 |
| FR-050 | Maintenance status | ⚠️  Should clarify | P3 |
| FR-059 | Valid contact emails | ⚠️  Check if monitored | P3 |
| FR-064 | Avoid "obviously"/"simply" | ⚠️  Needs review | P3 |

## Constitutional Alignment

### Relevant Principles for Documentation

**Principle #5: Fail Fast with Guidance**
- Current: Error messages in code are comprehensive
- Gap: Need to ensure all error messages reference documentation URLs (FR-038)

**Principle #8: Document the Blind Alleys**
- ✅ Excellent compliance: `docs/learnings/` has 14 documented learnings
- ✅ Constitution includes "Why not X?" sections
- Enhancement: Link from README to learnings directory (FR-047)

## Best Practices Research

### PyPI Package Standards (2024-2025)

1. **Community Health Files** (GitHub):
   - CONTRIBUTING.md (required for "Insights > Community" tab)
   - CODE_OF_CONDUCT.md (recommended for all public packages)
   - SECURITY.md (recommended for production packages)
   - Issue/PR templates (improve contributor experience)

2. **Markdown Compatibility**:
   - PyPI supports CommonMark
   - GitHub-flavored markdown mostly compatible
   - Avoid: Task lists (`- [ ]`), GitHub-specific extensions
   - Safe: Tables, code blocks, links, images, headings

3. **README Best Practices**:
   - Keep under 5000 words for readability
   - Problem statement before solution
   - Quick start within first scroll
   - Visual aids (badges, comparison tables)
   - Absolute URLs for all links

4. **Classifier Recommendations**:
   - For v1.0.0: Use `Development Status :: 5 - Production/Stable`
   - Include all relevant topics for discovery
   - Specify framework (pytest)
   - Declare typing support if applicable

## Tool Recommendations

### Documentation Validation Tools

1. **pyproject.toml validation**:
   ```bash
   python -m build --check
   twine check dist/*
   ```

2. **Link checking**:
   ```bash
   markdown-link-check README.md
   # Or use https://github.com/tcort/markdown-link-check
   ```

3. **PyPI README preview**:
   ```bash
   python -m readme_renderer README.md -o /tmp/readme.html
   ```

4. **Docstring validation**:
   ```bash
   pydocstyle iris_devtester/
   # Or use darglint for docstring/signature matching
   ```

## Risk Assessment

### High Risk (Block Release)

1. **Broken links on PyPI**: Relative links will 404
   - Impact: Users cannot navigate to referenced docs
   - Mitigation: Convert all relative links to absolute URLs

2. **Missing CONTRIBUTING.md**: GitHub shows "No contributing guidelines"
   - Impact: Contribu confusion, lower quality PRs
   - Mitigation: Create comprehensive CONTRIBUTING.md

3. **Missing CODE_OF_CONDUCT.md**: Community health incomplete
   - Impact: Unclear expectations, potential conflicts
   - Mitigation: Adopt standard Contributor Covenant

### Medium Risk (Reduce Quality Perception)

1. **Development Status classifier**: Currently "Beta" for v1.0.0
   - Impact: Users may perceive as unstable
   - Mitigation: Update to "Production/Stable"

2. **Broken documentation links**: README references non-existent files
   - Impact: 404 errors, frustration
   - Mitigation: Remove or create referenced files

3. **Incomplete examples**: Missing CI/CD, enterprise patterns
   - Impact: Users don't see full value proposition
   - Mitigation: Add 2-3 more examples

### Low Risk (Minor Polish)

1. **Acronym definitions**: DBAPI, JDBC mentioned without definition
   - Impact: Beginners may be confused
   - Mitigation: Add acronym definitions on first use

2. **Expected output in examples**: Users can't verify success
   - Impact: Uncertainty after running examples
   - Mitigation: Add `# Output: ...` comments

## Recommendations for Planning Phase

### Phase 1: Critical Fixes (Pre-Release Blockers)

1. Create `CONTRIBUTING.md` with standard template
2. Create `CODE_OF_CONDUCT.md` (Contributor Covenant)
3. Create `SECURITY.md` with disclosure policy
4. Create `.github/ISSUE_TEMPLATE/` (bug + feature request)
5. Create `.github/PULL_REQUEST_TEMPLATE.md`
6. Convert all README relative links to absolute
7. Remove or create files referenced in README
8. Update pyproject.toml classifier to "Production/Stable"

### Phase 2: Quality Improvements (Post-Release Acceptable)

1. Audit all public API docstrings
2. Add CI/CD example to examples/
3. Add enterprise setup example to examples/
4. Create standalone `docs/TROUBLESHOOTING.md`
5. Add expected output to all code examples
6. Define acronyms on first use in README
7. Add examples testing to CI pipeline

### Phase 3: Polish (Continuous Improvement)

1. Accessibility review (language, jargon)
2. Enhance CHANGELOG with migration guides
3. Version compatibility matrix
4. Error message URL references
5. Enhanced pyproject.toml classifiers

## Success Criteria

### Minimum Viable PyPI Release

- [x] README renders correctly on PyPI preview
- [ ] All links are absolute and functional
- [ ] No references to non-existent files
- [ ] CONTRIBUTING.md exists
- [ ] CODE_OF_CONDUCT.md exists
- [ ] Issue templates exist
- [ ] Development status matches version number
- [ ] Examples run without errors
- [ ] License year is current (2024/2025)

### Excellent Developer Experience

- [ ] New developer can install and run first example in <5 minutes
- [ ] Troubleshooting guide addresses top 5 issues
- [ ] All examples include expected output
- [ ] Docstrings complete for all public APIs
- [ ] CI tests all examples automatically
- [ ] CHANGELOG documents all breaking changes

## Timeline Estimate

Based on requirement complexity:

- **Phase 1 (Critical)**: 4-6 hours (templated files + link fixes)
- **Phase 2 (Quality)**: 8-12 hours (docstring audit + examples + troubleshooting)
- **Phase 3 (Polish)**: 4-6 hours (accessibility + enhancements)

**Total**: 16-24 hours for comprehensive audit and remediation

## References

- [PyPI Classifiers](https://pypi.org/classifiers/)
- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
- [Contributor Covenant](https://www.contributor-covenant.org/)
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
