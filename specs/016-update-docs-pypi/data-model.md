# Data Model: Update Documentation and PyPI Metadata

**Feature**: 016-update-docs-pypi
**Date**: 2025-12-16

## Overview

This feature involves documentation files only - no database entities or runtime data models. This document describes the file structure and content organization.

## File Entities

### 1. pyproject.toml

**Location**: `/pyproject.toml`
**Purpose**: Python package configuration including PyPI metadata
**Format**: TOML

**Fields to Update**:

| Field | Current Value | New Value |
|-------|--------------|-----------|
| `project.version` | `"1.2.1"` | `"1.2.2"` |
| `project.urls.Homepage` | `iris-devtools` URL | `iris-devtester` URL |
| `project.urls.Documentation` | `iris-devtools` URL | `iris-devtester` URL |
| `project.urls.Repository` | `iris-devtools` URL | `iris-devtester` URL |
| `project.urls.Issues` | `iris-devtools` URL | `iris-devtester` URL |
| `project.urls.Changelog` | `iris-devtools` URL | `iris-devtester` URL |

---

### 2. README.md

**Location**: `/README.md`
**Purpose**: Primary user-facing documentation (rendered on GitHub and PyPI)
**Format**: Markdown

**Current Structure** (363 lines):
```
├── Header + Badges
├── What is This?
├── The Problem It Solves
├── Quick Start
│   ├── Installation
│   └── Zero-Config Usage + Pytest Integration
├── Key Features (detailed)
│   ├── Automatic Password Management
│   ├── Testcontainers Integration
│   ├── Docker-Compose Support (NEW)
│   ├── DBAPI-First Performance
│   ├── DAT Fixture Management
│   ├── Performance Monitoring
│   └── Production-Ready Testing + Zero Configuration
├── Example: Enterprise Setup
├── Example: DAT Fixtures (with CLI)
├── Example: Performance Monitoring
├── Example: Docker-Compose Integration (with CLI + docker-compose.yml)
├── Architecture
├── Constitution (8 principles listed)
├── Documentation (links)
├── Real-World Use Cases (3 examples with code)
├── Performance (benchmarks)
├── Requirements
├── AI-Assisted Development
├── Contributing
├── Credits
├── License
└── Support
```

**New Structure** (~145 lines):
```
├── Header + Badges (5 lines)
├── Table of Contents (15 lines)
├── What is This? (5 lines)
├── The Problem It Solves (10 lines, condensed bullet list)
├── Quick Start (25 lines)
│   ├── Installation (3 options, no explanation)
│   ├── Zero-Config Usage (minimal example)
│   └── Pytest Integration (minimal example)
├── Key Features (30 lines)
│   ├── Brief list with links to docs/features/
│   └── No code examples
├── Documentation (10 lines)
│   ├── Link to docs/features/
│   ├── Link to examples/
│   └── Link to TROUBLESHOOTING.md
├── Examples (15 lines)
│   ├── 1 condensed example
│   └── Link to examples/ for more
├── Architecture (5 lines)
├── Constitution (5 lines + link)
├── Requirements (5 lines)
├── Contributing (5 lines + link)
├── Credits (5 lines)
└── License + Support (10 lines)
```

---

### 3. CHANGELOG.md

**Location**: `/CHANGELOG.md`
**Purpose**: Version history with release notes
**Format**: Markdown (Keep a Changelog format)

**Changes Required**:
1. Add `[1.2.2]` section with documentation fixes
2. Update release links at bottom of file

---

### 4. New Feature Documentation Files

**Location**: `/docs/features/`
**Purpose**: Detailed feature guides split from README
**Format**: Markdown

#### 4.1 dat-fixtures.md

```markdown
# DAT Fixture Management

[Moved from README - detailed examples, CLI usage, Python API]

## Quick Start
## Python API
## CLI Commands
## Best Practices
## Troubleshooting
```

#### 4.2 docker-compose.md

```markdown
# Docker-Compose Integration

[Moved from README - attach to existing containers, CLI, docker-compose.yml example]

## Overview
## Python API
## CLI Commands
## Docker-Compose Example
## Troubleshooting
```

#### 4.3 performance-monitoring.md

```markdown
# Performance Monitoring

[Moved from README - auto-configure, resource-aware, Task Manager]

## Overview
## Python API
## Configuration Options
## Resource-Aware Auto-Disable
```

#### 4.4 testcontainers.md

```markdown
# Testcontainers Integration

[Moved from README - basic + enterprise setup, isolation, cleanup]

## Overview
## Community Edition
## Enterprise Edition
## Test Isolation
## Fixture Scopes
```

---

## Content Migration Map

| Source (README) | Destination | Lines Moved |
|-----------------|-------------|-------------|
| Key Features: DAT Fixture Management (detailed) | `docs/features/dat-fixtures.md` | ~30 |
| Example: DAT Fixtures | `docs/features/dat-fixtures.md` | ~25 |
| Key Features: Docker-Compose Support | `docs/features/docker-compose.md` | ~10 |
| Example: Docker-Compose Integration | `docs/features/docker-compose.md` | ~55 |
| Key Features: Performance Monitoring | `docs/features/performance-monitoring.md` | ~8 |
| Example: Performance Monitoring | `docs/features/performance-monitoring.md` | ~15 |
| Key Features: Testcontainers Integration | `docs/features/testcontainers.md` | ~10 |
| Example: Enterprise Setup | `docs/features/testcontainers.md` | ~15 |
| Performance (benchmarks) | `docs/features/testcontainers.md` | ~10 |
| AI-Assisted Development | `CONTRIBUTING.md` | ~15 |

---

## Link Correction Map

| File | Pattern to Find | Replace With |
|------|-----------------|--------------|
| All | `github.com/intersystems-community/iris-devtools` | `github.com/intersystems-community/iris-devtester` |
| All | `iris-devtools.readthedocs.io` | Remove or replace with GitHub docs link |

---

## Validation Rules

1. **Line Count**: README.md < 150 lines (core content before Documentation section)
2. **Link Validity**: All `github.com/intersystems-community/iris-devtester` links return 200
3. **No Broken References**: Zero `iris-devtools` occurrences in user-facing docs
4. **TOC Anchors**: All TOC links resolve to valid headings
5. **New Files Exist**: All 4 docs/features/*.md files created
