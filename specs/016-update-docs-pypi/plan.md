# Implementation Plan: Update Documentation and PyPI Metadata

**Branch**: `016-update-docs-pypi` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-update-docs-pypi/spec.md`

## Summary

Update all documentation to fix incorrect repository references (`iris-devtools` → `iris-devtester`), reorganize README.md for better scannability with a table of contents, and split detailed feature documentation into separate files in `docs/`. Publish new PyPI version to update metadata links.

## Technical Context

**Language/Version**: N/A (documentation-only changes)
**Primary Dependencies**: N/A
**Storage**: N/A
**Testing**: Manual link verification, line count validation
**Target Platform**: GitHub, PyPI
**Project Type**: Documentation restructure
**Performance Goals**: N/A
**Constraints**: README core content under 150 lines; at least 3 features split to docs/
**Scale/Scope**: ~15 files to update, 3+ new docs files to create

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicable? | Status | Notes |
|-----------|-------------|--------|-------|
| 1. Automatic Remediation | No | N/A | Documentation-only feature |
| 2. Choose Right Tool | No | N/A | No code changes |
| 3. Isolation by Default | No | N/A | No test infrastructure changes |
| 4. Zero Configuration Viable | Yes | PASS | README reorganization maintains zero-config quickstart |
| 5. Fail Fast with Guidance | Yes | PASS | Links must work, errors visible immediately (404) |
| 6. Enterprise Ready, Community Friendly | Yes | PASS | Documentation serves both editions |
| 7. Medical-Grade Reliability | Yes | PASS | All links verified, no broken references |
| 8. Document the Blind Alleys | Yes | PASS | Preserves historical context in internal docs |

**Gate Result**: PASS - No violations. Documentation-only feature with straightforward requirements.

## Project Structure

### Documentation (this feature)

```text
specs/016-update-docs-pypi/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (file structure)
├── quickstart.md        # Phase 1 output (validation steps)
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Files to UPDATE (fix iris-devtools → iris-devtester)
pyproject.toml           # project.urls section
README.md                # All repository links + reorganize
CHANGELOG.md             # Release links
CONTRIBUTING.md          # Repository references
GETTING_STARTED.md       # Repository references (if exists)

# Files to CREATE (split from README)
docs/
├── features/
│   ├── dat-fixtures.md           # DAT Fixture Management guide
│   ├── docker-compose.md         # Docker-Compose Integration guide
│   ├── performance-monitoring.md # Performance Monitoring guide
│   └── testcontainers.md         # Testcontainers Integration guide
└── TROUBLESHOOTING.md            # Already exists - update links
```

**Structure Decision**: Documentation-only feature. No source code changes. Focus on docs/ directory expansion and README condensation.

## Complexity Tracking

> No violations to justify. Simple documentation update.

## Phase 0: Research Summary

### R1: Current State Analysis

**Decision**: Update all references in user-facing docs
**Rationale**: Currently pyproject.toml and README.md contain 15+ incorrect links to `iris-devtools`
**Files identified for update**:
- `pyproject.toml`: 5 URLs in project.urls
- `README.md`: ~12 links to wrong repository
- `CHANGELOG.md`: 2 release links
- `CONTRIBUTING.md`: Repository references

### R2: README Reorganization Strategy

**Decision**: Keep core content concise, split details to docs/
**Rationale**: Current README is 363 lines; overwhelming for new users
**Structure**:
1. Header + badges (5 lines)
2. Table of Contents (15 lines)
3. What is This? (5 lines)
4. The Problem It Solves (10 lines)
5. Quick Start: Installation + Basic Example (25 lines)
6. Key Features (brief list with links) (30 lines)
7. Documentation links (10 lines)
8. Real-World Use Cases (condensed) (20 lines)
9. Requirements + Contributing + Credits (25 lines)
**Total**: ~145 lines (under 150 target)

### R3: Feature Docs to Create

**Decision**: Create 4 feature documentation files
**Rationale**: Detailed examples and configuration don't belong in README
**Files**:
1. `docs/features/dat-fixtures.md` - Move DAT fixture examples
2. `docs/features/docker-compose.md` - Move Docker-Compose integration
3. `docs/features/performance-monitoring.md` - Move monitoring setup
4. `docs/features/testcontainers.md` - Move testcontainers details

### R4: PyPI Publishing Strategy

**Decision**: Version bump to 1.2.2 required
**Rationale**: PyPI metadata only updates on new version publish
**Process**:
1. Update pyproject.toml version
2. Update CHANGELOG.md
3. Build and publish

## Phase 1: Design Artifacts

See generated files:
- `data-model.md` - File structure and content map
- `quickstart.md` - Validation checklist
- No API contracts needed (documentation-only)
