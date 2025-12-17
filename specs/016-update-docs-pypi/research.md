# Research: Update Documentation and PyPI Metadata

**Feature**: 016-update-docs-pypi
**Date**: 2025-12-16

## R1: Current State Analysis

### Problem Statement

The `iris-devtester` package on PyPI contains incorrect repository links pointing to `iris-devtools` (a repository that doesn't exist). This prevents users from finding documentation, reporting issues, or contributing.

### Findings

**pyproject.toml project.urls (lines 99-104)**:
```toml
[project.urls]
Homepage = "https://github.com/intersystems-community/iris-devtools"  # WRONG
Documentation = "https://github.com/intersystems-community/iris-devtools#readme"  # WRONG
Repository = "https://github.com/intersystems-community/iris-devtools"  # WRONG
Issues = "https://github.com/intersystems-community/iris-devtools/issues"  # WRONG
Changelog = "https://github.com/intersystems-community/iris-devtools/blob/main/CHANGELOG.md"  # WRONG
```

**README.md incorrect links** (~12 occurrences):
- Constitution link
- Troubleshooting Guide link
- Codified Learnings link
- Examples link
- Contributing link
- License link
- GitHub Issues link
- Documentation link
- CI/CD workflow example
- Test coverage badge

**CHANGELOG.md incorrect links** (2 occurrences):
- Release v1.0.0 link
- Unreleased comparison link

### Decision

Replace all `iris-devtools` references with `iris-devtester` in user-facing documentation.

### Alternatives Considered

1. **Rename package to iris-devtools**: Rejected - would break existing installations
2. **Create iris-devtools as redirect**: Rejected - adds complexity, confuses naming
3. **Update links only (keep README structure)**: Rejected - README too long, reorganization needed

---

## R2: README Reorganization Strategy

### Problem Statement

Current README.md is 363 lines - too long for quick comprehension. Users must scroll extensively to find installation instructions or specific features.

### Current Structure Analysis

| Section | Lines | Status |
|---------|-------|--------|
| Header + badges | 8 | Keep |
| What is This? | 5 | Keep |
| The Problem It Solves | 10 | Keep |
| Quick Start | 30 | Keep (condense) |
| Key Features | 50 | Keep (condense) |
| Example: Enterprise Setup | 15 | Move to docs/ |
| Example: DAT Fixtures | 30 | Move to docs/ |
| Example: Performance Monitoring | 20 | Move to docs/ |
| Example: Docker-Compose | 55 | Move to docs/ |
| Architecture | 10 | Keep |
| Constitution | 15 | Condense |
| Documentation links | 10 | Keep |
| Real-World Use Cases | 35 | Condense |
| Performance | 10 | Move to docs/ |
| Requirements | 8 | Keep |
| AI-Assisted Development | 15 | Move to CONTRIBUTING |
| Contributing | 8 | Keep |
| Credits | 10 | Keep |
| License + Support | 12 | Keep |

### Proposed Structure

```markdown
# IRIS DevTools (~145 lines total)

[Badges]

## Table of Contents
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Documentation](#documentation)
- [Examples](#examples)
- [Contributing](#contributing)

## What is This? (5 lines)

## The Problem It Solves (10 lines, condensed)

## Quick Start (25 lines)
- Installation (3 options)
- Zero-config usage (minimal example)
- pytest integration (minimal example)

## Key Features (30 lines)
- Brief descriptions with links to detailed docs
- No code examples here

## Documentation (10 lines)
- Links to docs/ files
- Links to examples/

## Examples (15 lines)
- 1-2 condensed examples
- Links to examples/ directory

## Requirements (5 lines)

## Contributing (5 lines + link)

## Credits + License (10 lines)
```

### Decision

Reorganize README to ~145 lines with TOC, moving detailed examples to docs/features/.

### Alternatives Considered

1. **Use collapsible sections**: Rejected - doesn't render on PyPI
2. **Separate README for PyPI**: Rejected - maintenance burden
3. **Keep current length, add TOC only**: Rejected - still overwhelming

---

## R3: Feature Documentation Files

### Problem Statement

Detailed feature documentation embedded in README makes it long and hard to maintain. Dedicated docs allow deeper content without overwhelming the README.

### Files to Create

| File | Content Source | Estimated Lines |
|------|---------------|-----------------|
| `docs/features/dat-fixtures.md` | README DAT Fixtures section | 80 |
| `docs/features/docker-compose.md` | README Docker-Compose section | 100 |
| `docs/features/performance-monitoring.md` | README Performance Monitoring section | 60 |
| `docs/features/testcontainers.md` | README Key Features + Enterprise Setup | 80 |

### Directory Structure

```
docs/
├── features/
│   ├── dat-fixtures.md
│   ├── docker-compose.md
│   ├── performance-monitoring.md
│   └── testcontainers.md
├── learnings/           # Existing
├── TROUBLESHOOTING.md   # Existing (update links)
└── ...
```

### Decision

Create 4 new feature documentation files in `docs/features/`.

### Alternatives Considered

1. **Use GitHub Wiki**: Rejected - not visible on PyPI, harder to version
2. **Use Read the Docs**: Rejected - adds infrastructure, overkill for current needs
3. **Single docs/FEATURES.md file**: Rejected - same length problem, just moved

---

## R4: PyPI Publishing Strategy

### Problem Statement

PyPI metadata (project.urls) only updates when a new version is published. Cannot update links without releasing a new version.

### Current Version

`1.2.1` (per pyproject.toml)

### Decision

Bump to `1.2.2` with documentation-only changes.

**Changelog entry**:
```markdown
## [1.2.2] - 2025-12-16

### Fixed
- Fixed incorrect repository links in PyPI metadata (iris-devtools → iris-devtester)
- Fixed broken documentation links in README.md

### Changed
- Reorganized README.md with table of contents for better navigation
- Moved detailed feature documentation to dedicated files in docs/features/
```

### Alternatives Considered

1. **Wait for next feature release**: Rejected - broken links are user-facing bug
2. **Major version bump**: Rejected - no breaking changes
3. **Skip version bump, just update repo**: Rejected - PyPI links won't update

---

## R5: Files Requiring Updates

### User-Facing (MUST update)

| File | Changes Required |
|------|------------------|
| `pyproject.toml` | 5 URLs + version bump |
| `README.md` | ~12 links + full reorganization |
| `CHANGELOG.md` | 2 links + new entry |
| `CONTRIBUTING.md` | Repository references |

### Internal (MAY retain historical references)

| File | Decision |
|------|----------|
| `CLAUDE.md` | Keep - internal development context |
| `AGENTS.md` | Review - may have user-visible links |
| `specs/*.md` | Keep - historical context |
| `CONSTITUTION.md` | Update example URLs if user-facing |

### Verification Commands

```bash
# Find all iris-devtools references
grep -r "iris-devtools" --include="*.md" --include="*.toml" .

# Count README lines
wc -l README.md

# Verify links work (after update)
# Manual: Click each link on GitHub
```
