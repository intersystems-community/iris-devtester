# Data Model: Documentation & Metadata Entities

**Feature**: 005-complete-a-top
**Phase**: 1 (Design)
**Date**: 2025-11-03

## Overview

This feature deals with documentation artifacts and package metadata, not runtime data structures. The "data model" consists of file relationships, metadata schemas, and documentation structure.

## Entity Relationships

```
README.md [1]
    ├──> references CONTRIBUTING.md [1]
    ├──> references CHANGELOG.md [1]
    ├──> references LICENSE [1]
    ├──> references CODE_OF_CONDUCT.md [1]
    ├──> references SECURITY.md [0..1]
    ├──> references examples/ [1..*]
    └──> references docs/ [1..*]

CONTRIBUTING.md [1]
    ├──> references CODE_OF_CONDUCT.md [1]
    └──> references pyproject.toml [dev dependencies]

pyproject.toml [1]
    ├──> defines project.name [1]
    ├──> defines project.version [1]
    ├──> defines project.description [1]
    ├──> defines project.urls [1..*]
    ├──> defines project.classifiers [1..*]
    └──> defines project.dependencies [0..*]

examples/ [directory]
    ├──> examples/README.md [1]
    ├──> examples/*.py [1..*]
    └──> all tested in CI

docs/ [directory]
    ├──> docs/learnings/ [1..*]
    └──> docs/TROUBLESHOOTING.md [0..1]

.github/ [directory]
    ├──> ISSUE_TEMPLATE/ [1..*]
    └──> PULL_REQUEST_TEMPLATE.md [1]
```

## Documentation Artifacts

### README.md

**Purpose**: Primary package documentation, PyPI landing page, first impression

**Attributes**:
- `title`: Package name
- `tagline`: Short description (<200 chars)
- `badges`: Version, Python versions, license, coverage
- `sections[]`: Ordered list of content sections
- `code_examples[]`: Runnable code snippets with imports
- `links[]`: References to other documentation

**Structure**:
```markdown
# Title
## What is This?
## The Problem It Solves
## Quick Start
## Key Features
## Examples
## Architecture
## Constitution
## Documentation
## Real-World Use Cases
## Performance
## Requirements
## Contributing
## Credits
## License
## Support
```

**Validation Rules**:
- Length < 512 KB (PyPI limit)
- All links absolute URLs
- All code examples include imports
- All references resolve
- Tagline matches pyproject.toml description
- Version mentioned matches pyproject.toml

### CONTRIBUTING.md

**Purpose**: Contributor onboarding and development guidelines

**Required Sections**:
```markdown
# Contributing to iris-devtester

## Welcome
## Code of Conduct
## How to Contribute
  - Reporting Bugs
  - Suggesting Enhancements
  - Pull Requests
## Development Setup
  - Prerequisites
  - Installation
  - Running Tests
  - Code Style
## Project Structure
## Testing Guidelines
  - Unit Tests
  - Integration Tests
  - Coverage Requirements
## Governance
  - Maintainers
  - Decision Process
## Questions?
```

**Validation Rules**:
- References CODE_OF_CONDUCT.md
- Includes complete dev setup instructions
- Lists all test commands
- Explains code style (black, isort, mypy)
- Includes governance/maintainer info

### CODE_OF_CONDUCT.md

**Purpose**: Community behavioral expectations

**Standard**: Contributor Covenant v2.1

**Attributes**:
- `version`: 2.1
- `pledge`: Our commitment
- `standards`: Expected behavior
- `responsibilities`: Maintainer duties
- `scope`: Where it applies
- `enforcement`: How violations are handled
- `contact`: Enforcement email

**Source**: https://www.contributor-covenant.org/version/2/1/code_of_conduct/

### SECURITY.md

**Purpose**: Security vulnerability disclosure process

**Required Sections**:
```markdown
# Security Policy

## Supported Versions
  - Which versions receive security updates

## Reporting a Vulnerability
  - How to report
  - What to include
  - Response timeline
  - Disclosure policy

## Security Best Practices
  - For package users
```

**Validation Rules**:
- Includes supported version table
- Provides contact method (email/form)
- States expected response time
- Explains responsible disclosure

### CHANGELOG.md

**Purpose**: Version history and migration guidance

**Format**: Keep a Changelog (https://keepachangelog.com/)

**Structure**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [1.0.0] - 2025-10-18
### Added
- Initial release
...
```

**Validation Rules**:
- Follows Keep a Changelog format
- Uses semantic versioning
- Includes date for each release
- Documents breaking changes prominently
- Provides migration guidance for major versions
- Links to git tags/commits

### LICENSE

**Purpose**: Legal terms for package use

**Type**: MIT License

**Attributes**:
- `license_type`: "MIT"
- `copyright_year`: 2024 or 2025
- `copyright_holder`: "InterSystems Community"
- `spdx_identifier`: "MIT"

**Validation Rules**:
- Year is current (2024-2025)
- Holder matches pyproject.toml authors
- SPDX ID matches pyproject.toml license

## Package Metadata (pyproject.toml)

### [project] Section

**Schema**:
```toml
[project]
name = "iris-devtester"                    # MUST match package directory
version = "X.Y.Z"                         # Semantic versioning
description = "<200 char tagline>"        # MUST match README tagline
readme = "README.md"                      # Implies text/markdown
requires-python = ">=3.9"                 # Minimum Python version
license = {text = "MIT"}                  # SPDX identifier
authors = [                               # Package maintainers
    {name = "...", email = "..."}
]
keywords = [...]                          # PyPI search terms
classifiers = [...]                       # PyPI categories
dependencies = [...]                      # Runtime dependencies

[project.optional-dependencies]
dbapi = [...]                             # Optional dep groups
jdbc = [...]
all = [...]
test = [...]
dev = [...]
docs = [...]

[project.scripts]
iris-devtester = "iris_devtester.cli:main"  # CLI entry point

[project.urls]
Homepage = "..."
Documentation = "..."
Repository = "..."
Issues = "..."
Changelog = "..."                         # Add if missing
```

**Validation Rules**:
- `description` matches README tagline exactly
- `version` matches README badge and `__init__.py`
- `classifiers` includes:
  - Development Status (5 - Production/Stable for v1.0+)
  - Intended Audience :: Developers
  - License :: OSI Approved :: MIT License
  - Programming Language :: Python :: 3.9/3.10/3.11/3.12
  - Topic :: Software Development :: Testing
  - Topic :: Database
  - Framework :: Pytest
- `keywords` enable discovery ("iris testing", "iris docker", "testcontainers iris")
- `urls` all resolve and use https://
- `dependencies` versions not overly restrictive
- `readme` file exists and renders correctly

### Classifier Taxonomy

**Required Classifiers** (for optimal discoverability):

```python
classifiers = [
    # Development Status (MUST match version)
    "Development Status :: 5 - Production/Stable",  # For v1.0.0+
    # or "Development Status :: 4 - Beta",          # For v0.x

    # Audience
    "Intended Audience :: Developers",
    "Intended Audience :: Healthcare Industry",     # Domain-specific

    # License
    "License :: OSI Approved :: MIT License",

    # Python versions (all supported)
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3 :: Only",

    # Topics (for search)
    "Topic :: Software Development :: Testing",
    "Topic :: Software Development :: Quality Assurance",
    "Topic :: Database",
    "Topic :: System :: Systems Administration",

    # Framework integration
    "Framework :: Pytest",

    # Environment
    "Operating System :: OS Independent",
    "Environment :: Console",

    # Typing support (if applicable)
    "Typing :: Typed",                              # If py.typed exists
]
```

## Code Examples

### examples/README.md

**Purpose**: Guide users through example progression

**Structure**:
```markdown
# IRIS DevTools Examples

This directory contains runnable examples demonstrating key features.

## Learning Path

Recommended order for new users:

1. **01_quickstart.py** - Minimal "hello world" (2 minutes)
2. **02_pytest_basic.py** - Basic pytest integration (5 minutes)
3. **04_pytest_fixtures.py** - Advanced fixtures (10 minutes)
4. **05_ci_cd.py** - GitHub Actions setup (10 minutes)
5. **08_auto_discovery.py** - Configuration discovery (10 minutes)
6. **09_enterprise.py** - Enterprise edition features (15 minutes)

## Prerequisites

All examples require:
- Python 3.9+
- Docker Desktop running
- `pip install iris-devtester[all]`

## Running Examples

```bash
# Run any example directly
python examples/01_quickstart.py

# Expected output: IRIS version information
```

## What Each Example Demonstrates

### 01_quickstart.py
- Zero-configuration container startup
- Basic SQL query execution
- Automatic cleanup

### 02_pytest_basic.py
- Basic pytest fixture
- Test isolation
- Module-scoped container

... (continue for each example)
```

### Individual Example File

**Template**:
```python
"""
Example: <Title>

Demonstrates:
- <Feature 1>
- <Feature 2>

Prerequisites:
- Docker Desktop running
- pip install iris-devtester[<extras>]

Expected output:
- <What you should see>
"""

# All imports explicit (FR-017)
from iris_devtester.containers import IRISContainer
import sys

def main():
    """<Docstring explaining intent>"""

    # Inline comments explain WHY, not WHAT (FR-024)
    with IRISContainer.community() as iris:
        # Get connection using auto-configuration
        conn = iris.get_connection()
        cursor = conn.cursor()

        # Query IRIS version to verify connectivity
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]

        print(f"✅ Connected to IRIS: {version}")
        # Expected output: ✅ Connected to IRIS: IRIS for UNIX ... (FR-018)

if __name__ == "__main__":
    main()
```

## Support Resources

### docs/TROUBLESHOOTING.md

**Purpose**: Common issue resolution without GitHub Issues

**Structure** (Symptom → Diagnosis → Solution → Prevention):

```markdown
# Troubleshooting Guide

## Common Issues

### Issue 1: "Docker daemon not running"

**Symptom**:
```
ConnectionError: Could not connect to Docker daemon
```

**Diagnosis**:
Docker Desktop is not running or not installed.

**Solution**:
1. Start Docker Desktop
2. Wait for "Docker Desktop is running" indicator
3. Retry your command

**Prevention**:
Add Docker Desktop to startup applications.

---

### Issue 2: "Password change required"

**Symptom**:
```
Password change required: <READ>zf+Password1+Password2
```

**Diagnosis**:
IRIS default password needs changing on first use.

**Solution**:
This is automatically handled by iris-devtester. If you see this error:
1. Ensure you're using `IRISContainer` from iris-devtester (not raw testcontainers)
2. Wait 5 seconds and retry

**Prevention**:
Always use `iris_devtester.containers.IRISContainer` wrapper.

---

... (5+ common issues total)
```

### .github/ISSUE_TEMPLATE/

**bug_report.yml**:
```yaml
name: Bug Report
description: File a bug report
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us what you expected to happen
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: iris-devtester version
      placeholder: "1.0.0"
    validations:
      required: true
  - type: input
    id: python-version
    attributes:
      label: Python version
      placeholder: "3.11"
    validations:
      required: true
  - type: dropdown
    id: iris-edition
    attributes:
      label: IRIS Edition
      options:
        - Community
        - Enterprise
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Relevant log output
      render: shell
```

**feature_request.yml**:
```yaml
name: Feature Request
description: Suggest a new feature
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem Description
      description: What problem does this feature solve?
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: How should it work?
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
```

### .github/PULL_REQUEST_TEMPLATE.md

```markdown
## Description
<!-- Describe your changes -->

## Related Issue
<!-- Link to issue if applicable: Fixes #123 -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Code passes `black . && isort . && mypy iris_devtester/`
- [ ] All tests pass (`pytest`)
- [ ] Follows constitutional principles

## Test Plan
<!-- How did you test this? -->
```

## Validation Checklist

### Pre-Release Checklist

**File Existence**:
- [ ] README.md
- [ ] CONTRIBUTING.md
- [ ] CODE_OF_CONDUCT.md
- [ ] SECURITY.md
- [ ] CHANGELOG.md
- [ ] LICENSE
- [ ] pyproject.toml
- [ ] examples/README.md
- [ ] examples/*.py (4+ files)
- [ ] .github/ISSUE_TEMPLATE/bug_report.yml
- [ ] .github/ISSUE_TEMPLATE/feature_request.yml
- [ ] .github/PULL_REQUEST_TEMPLATE.md
- [ ] docs/TROUBLESHOOTING.md

**Content Validation**:
- [ ] README uses absolute URLs
- [ ] README tagline matches pyproject.toml description
- [ ] Version consistent across README, pyproject.toml, __init__.py, CHANGELOG
- [ ] All code examples include imports
- [ ] All code examples include expected output
- [ ] LICENSE year is 2024 or 2025
- [ ] pyproject.toml classifiers match package maturity
- [ ] No broken links in any markdown file
- [ ] No references to non-existent files

**Rendering Validation**:
- [ ] README renders correctly in PyPI preview
- [ ] CHANGELOG renders correctly on GitHub
- [ ] All markdown files render without warnings
- [ ] Badges display correctly

**Example Validation**:
- [ ] All examples run without errors
- [ ] All examples produce expected output
- [ ] Examples are tested in CI
- [ ] Examples README lists learning path

## References

- [PyPI Classifiers Trove](https://pypi.org/classifiers/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Contributor Covenant](https://www.contributor-covenant.org/)
- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
