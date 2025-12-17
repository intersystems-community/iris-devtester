# Quickstart: Update Documentation and PyPI Metadata

**Feature**: 016-update-docs-pypi
**Date**: 2025-12-16

## Overview

This guide provides step-by-step instructions for implementing the documentation updates and publishing to PyPI.

## Prerequisites

- Write access to the repository
- PyPI credentials for publishing (or TestPyPI for testing)
- Python with `build` and `twine` installed

## Implementation Steps

### Step 1: Fix pyproject.toml URLs

Update `/pyproject.toml` lines 99-104:

```toml
[project.urls]
Homepage = "https://github.com/intersystems-community/iris-devtester"
Documentation = "https://github.com/intersystems-community/iris-devtester#readme"
Repository = "https://github.com/intersystems-community/iris-devtester"
Issues = "https://github.com/intersystems-community/iris-devtester/issues"
Changelog = "https://github.com/intersystems-community/iris-devtester/blob/main/CHANGELOG.md"
```

Bump version on line 7:
```toml
version = "1.2.2"
```

### Step 2: Create docs/features/ Directory

```bash
mkdir -p docs/features
```

### Step 3: Create Feature Documentation Files

Create 4 new files by extracting content from README.md:

1. `docs/features/dat-fixtures.md`
2. `docs/features/docker-compose.md`
3. `docs/features/performance-monitoring.md`
4. `docs/features/testcontainers.md`

### Step 4: Reorganize README.md

1. Add Table of Contents after badges
2. Condense feature descriptions (remove detailed examples)
3. Replace detailed examples with links to docs/features/
4. Fix all `iris-devtools` → `iris-devtester` links
5. Target: ~145 lines

### Step 5: Update CHANGELOG.md

Add new section at top:

```markdown
## [1.2.2] - 2025-12-16

### Fixed
- Fixed incorrect repository links in PyPI metadata (iris-devtools → iris-devtester)
- Fixed broken documentation links in README.md

### Changed
- Reorganized README.md with table of contents for better navigation
- Moved detailed feature documentation to dedicated files in docs/features/
```

Update release links at bottom:
```markdown
[1.2.2]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.2.2
[1.2.1]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.2.1
...
[Unreleased]: https://github.com/intersystems-community/iris-devtester/compare/v1.2.2...HEAD
```

### Step 6: Update Other Files

Fix links in:
- `CONTRIBUTING.md`
- `docs/TROUBLESHOOTING.md`

### Step 7: Verify Changes

```bash
# Check no iris-devtools references remain in user-facing docs
grep -r "iris-devtools" README.md pyproject.toml CHANGELOG.md CONTRIBUTING.md

# Count README lines
wc -l README.md
# Should be ~145 lines

# Verify TOC links work (manual check on GitHub preview)
```

### Step 8: Commit and Push

```bash
git add -A
git commit -m "docs: fix repository links and reorganize README

- Fix incorrect iris-devtools → iris-devtester URLs in pyproject.toml
- Reorganize README.md with TOC and condensed content (~145 lines)
- Move detailed feature docs to docs/features/
- Update CHANGELOG.md with v1.2.2 entry
- Fix links in CONTRIBUTING.md and TROUBLESHOOTING.md"

git push origin 016-update-docs-pypi
```

### Step 9: Create PR and Merge

Create PR, get review, merge to main.

### Step 10: Publish to PyPI

```bash
# Ensure on main branch with latest changes
git checkout main
git pull

# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/iris_devtester-1.2.2*
```

### Step 11: Verify PyPI

1. Go to https://pypi.org/project/iris-devtester/
2. Click each project link (Homepage, Repository, Documentation, Issues)
3. Verify all links go to `iris-devtester` repository

---

## Validation Checklist

### Success Criteria Verification

- [ ] **SC-001**: All 5 pyproject.toml URLs point to iris-devtester
- [ ] **SC-002**: All README.md links resolve (no 404s)
- [ ] **SC-003**: Zero `iris-devtools` in user-facing docs
- [ ] **SC-004**: PyPI project links work correctly
- [ ] **SC-005**: PyPI → GitHub Issues in 2 clicks
- [ ] **SC-006**: README core content < 150 lines
- [ ] **SC-007**: TOC with working anchor links
- [ ] **SC-008**: 3+ feature sections in docs/features/
- [ ] **SC-009**: Installation findable in 10 seconds

### Quick Verification Commands

```bash
# SC-001: Check pyproject.toml URLs
grep -A5 "\[project.urls\]" pyproject.toml | grep iris-devtester
# Should show 5 lines

# SC-003: Check for iris-devtools in user-facing docs
grep -l "iris-devtools" README.md pyproject.toml CHANGELOG.md CONTRIBUTING.md 2>/dev/null
# Should return nothing

# SC-006: Count README lines
wc -l README.md
# Should be < 150

# SC-008: Check docs/features/ files
ls docs/features/*.md | wc -l
# Should be >= 3
```

---

## Rollback Procedure

If issues discovered after PyPI publish:

1. **Cannot unpublish from PyPI** - versions are permanent
2. Publish `1.2.3` with fixes
3. Yank `1.2.2` if severely broken: `twine yank iris-devtester 1.2.2`

---

## Common Issues

### Issue: TOC links don't work

GitHub auto-generates anchor IDs. Ensure:
- Heading: `## Quick Start`
- TOC link: `[Quick Start](#quick-start)`
- Rule: lowercase, spaces → hyphens

### Issue: PyPI not showing updated links

- Wait 5-10 minutes for CDN cache
- Hard refresh the page
- Verify correct version was uploaded

### Issue: README too long

- Move more content to docs/features/
- Remove redundant examples
- Condense bullet points
