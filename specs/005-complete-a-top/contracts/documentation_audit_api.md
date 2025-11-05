# Contract: Documentation Audit API

**Feature**: 005-complete-a-top
**Type**: Process Contract (not code API)
**Purpose**: Define the audit process, criteria, and acceptance standards

## Audit Process Contract

### Input

**Artifacts to Audit**:
- Root documentation files (README.md, CONTRIBUTING.md, etc.)
- Package metadata (pyproject.toml)
- Code examples (examples/*.py)
- API docstrings (all public modules)
- Support resources (issue templates, troubleshooting guides)

**Audit Criteria**:
- 70 functional requirements from spec.md
- Constitutional principles (8 principles from CONSTITUTION.md)
- PyPI packaging standards
- Accessibility guidelines

### Output

**Audit Report Structure**:
```yaml
audit_results:
  timestamp: "2025-11-03T..."
  version_audited: "1.0.0"

  summary:
    total_requirements: 70
    requirements_met: int
    requirements_partial: int
    requirements_not_met: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int

  findings:
    - id: "FR-001"
      requirement: "PyPI package metadata MUST include..."
      status: "met" | "partial" | "not_met"
      severity: "critical" | "high" | "medium" | "low"
      evidence: "..."
      recommendation: "..."

  missing_files:
    - path: "CONTRIBUTING.md"
      priority: "P0"
      requirement_ids: ["FR-041", "FR-042", "FR-043"]

  broken_links:
    - file: "README.md"
      line: 142
      link: "docs/quickstart.md"
      target_exists: false
      recommendation: "Remove or create file"

  constitutional_issues:
    - principle: "Principle 8: Document Blind Alleys"
      status: "compliant"
      evidence: "docs/learnings/ has 14 files"
```

## File Existence Contract

### Critical Files (Must Exist)

**Priority 0** (Blocks release):
```
/
├── README.md                                 # FR-003, FR-005, FR-011
├── CONTRIBUTING.md                           # FR-041, FR-042, FR-043
├── CODE_OF_CONDUCT.md                        # FR-044
├── SECURITY.md                               # Community standard
├── CHANGELOG.md                              # FR-053
├── LICENSE                                   # FR-010, FR-058
├── pyproject.toml                            # FR-001, FR-002, FR-066-070
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml                    # FR-036
│   │   └── feature_request.yml               # FR-036
│   └── PULL_REQUEST_TEMPLATE.md              # FR-048
└── examples/
    ├── README.md                             # FR-025
    └── *.py (4+ examples)                    # FR-023
```

**Priority 1** (Improves quality):
```
docs/
├── TROUBLESHOOTING.md                        # FR-031, FR-032, FR-033
└── learnings/ (already exists)               # FR-047
```

### File Content Contracts

#### README.md Contract

**Required Sections** (in order):
1. Title + Tagline
2. Badges (PyPI, Python, License, Coverage)
3. "What is This?"
4. "The Problem It Solves" (before installation)
5. Quick Start
6. Key Features
7. Examples
8. Architecture
9. Constitution (link + summary)
10. Documentation (with absolute URLs)
11. Real-World Use Cases
12. Performance (with benchmarks)
13. Requirements
14. Contributing (link to CONTRIBUTING.md)
15. Credits (acknowledge dependencies)
16. License
17. Support (channels + expected response)

**Link Format**:
- All links MUST be absolute URLs
- Format: `https://github.com/intersystems-community/iris-devtools/blob/main/{file}`
- Not: `[file](file)` or `[file](./file)`

**Code Example Requirements**:
- All imports explicit (no assumed imports)
- Expected output shown as comment
- Runnable as-is (no hidden prerequisites)
- Completes in <1 minute

#### pyproject.toml Contract

**[project] Section Validation**:
```toml
[project]
name = "iris-devtools"                        # Must match package directory
version = "X.Y.Z"                             # Must match README, __init__.py, CHANGELOG
description = "..."                            # Must match README tagline exactly
readme = "README.md"                          # Must exist and render
requires-python = ">=3.9"                     # Minimum supported
license = {text = "MIT"}                      # SPDX identifier
authors = [{name = "...", email = "..."}]     # Valid, monitored email
keywords = [...]                              # Must include: "iris testing", "iris docker", "testcontainers"

classifiers = [
    "Development Status :: 5 - Production/Stable",  # For v1.0+
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Testing",
    "Topic :: Database",
    "Framework :: Pytest",
]

[project.urls]
Homepage = "https://github.com/intersystems-community/iris-devtools"
Documentation = "https://github.com/intersystems-community/iris-devtools#readme"
Repository = "https://github.com/intersystems-community/iris-devtools"
Issues = "https://github.com/intersystems-community/iris-devtools/issues"
Changelog = "https://github.com/intersystems-community/iris-devtools/blob/main/CHANGELOG.md"  # Add if missing
```

**Validation Rules**:
- description matches README tagline (character-for-character)
- version appears in: README badge, __init__.py, CHANGELOG
- all URLs resolve (HTTP 200)
- classifiers match package maturity (v1.0+ = Production/Stable)

## Example Quality Contract

### Example File Template

**Structure**:
```python
"""
Example: <Title>

Demonstrates:
- <Feature 1>
- <Feature 2>

Prerequisites:
- Docker Desktop running
- pip install iris-devtools[<extras>]

Expected Runtime: <X> minutes
Expected Output:
- <What user should see>

Constitutional Principles:
- Principle #<N>: <Demonstrated principle>
"""

# All imports explicit (FR-017)
from iris_devtools.containers import IRISContainer

def main():
    """<Intent explanation>"""

    # Comments explain WHY, not WHAT (FR-024)
    with IRISContainer.community() as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]

        # Show expected output (FR-018)
        print(f"✅ Connected: {version}")
        # Expected output: ✅ Connected: IRIS for UNIX (Ubuntu Server LTS...

if __name__ == "__main__":
    main()
```

**Requirements**:
- Docstring includes: title, demonstrations, prerequisites, expected output
- All imports at top (no hidden imports)
- Inline comments explain intent
- Expected output shown in comments
- Runnable as-is
- Completes in stated timeframe

## Docstring Quality Contract

### Google Style Docstring Template

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Short description (one line).

    Longer description with more context. Explain what the function does,
    why it exists, and when to use it.

    Args:
        param1: Description of param1
        param2: Description of param2. Defaults to 0.

    Returns:
        Description of return value.

    Raises:
        ValueError: When input is invalid.
        ConnectionError: When IRIS is not accessible.

    Examples:
        Basic usage:

        >>> from iris_devtools import function_name
        >>> result = function_name("test")
        >>> print(result)
        True

        With optional parameter:

        >>> result = function_name("test", param2=5)
        >>> print(result)
        True

    Note:
        Additional notes, warnings, or best practices.
    """
    pass
```

**Requirements** (FR-021, FR-022):
- One-line summary
- Extended description
- All parameters documented
- Return value documented
- All raised exceptions documented
- At least one working example
- Examples show imports
- Examples show expected output

## Link Validation Contract

### Absolute URL Format

**Pattern**:
```
https://github.com/{org}/{repo}/blob/{branch}/{path}
```

**Examples**:
```markdown
# ✅ Correct
[CONTRIBUTING.md](https://github.com/intersystems-community/iris-devtools/blob/main/CONTRIBUTING.md)
[Constitution](https://github.com/intersystems-community/iris-devtools/blob/main/CONSTITUTION.md)

# ❌ Wrong
[CONTRIBUTING.md](CONTRIBUTING.md)
[Constitution](./CONSTITUTION.md)
[Constitution](CONSTITUTION.md)
```

### Link Resolution

**Validation**:
- All `https://` links return HTTP 200
- No 404 errors
- No redirects to unexpected domains
- Badge URLs point to correct package (iris-devtools, not other packages)

## Constitutional Compliance Contract

### Principle Coverage Checklist

**Principle 5: Fail Fast with Guidance**:
- [ ] Error messages structured: "What went wrong" + "How to fix it"
- [ ] Error messages reference documentation URLs (FR-038)
- [ ] All errors tested (FR-028)

**Principle 8: Document the Blind Alleys**:
- [ ] docs/learnings/ directory exists
- [ ] At least 5 documented learnings
- [ ] README links to learnings (FR-047)
- [ ] Each learning explains: what we tried, why it failed, what we did instead

## Acceptance Criteria

### Phase 1 Complete (Critical)

- [ ] All P0 files exist
- [ ] README uses absolute URLs
- [ ] No broken links
- [ ] pyproject.toml classifier matches version
- [ ] No references to non-existent files
- [ ] PyPI preview renders correctly

### Phase 2 Complete (Quality)

- [ ] All examples run without errors
- [ ] All examples show expected output
- [ ] Troubleshooting guide addresses top 5 issues
- [ ] All public APIs have Google-style docstrings
- [ ] Examples tested in CI

### Phase 3 Complete (Polish)

- [ ] Acronyms defined on first use
- [ ] No "obviously" or "simply" in docs
- [ ] Version consistent across all files
- [ ] LICENSE year current (2024/2025)
- [ ] Contact emails valid and monitored

## Metrics

### Coverage Metrics

```yaml
requirements_coverage:
  discovery_first_impressions:  # FR-001 to FR-010
    total: 10
    met: int
    partial: int
    not_met: int

  installation_quickstart:      # FR-011 to FR-020
    total: 10
    met: int
    partial: int
    not_met: int

  api_documentation:            # FR-021 to FR-030
    total: 10
    met: int
    partial: int
    not_met: int

  troubleshooting:              # FR-031 to FR-040
    total: 10
    met: int
    partial: int
    not_met: int

  contributing_governance:      # FR-041 to FR-050
    total: 10
    met: int
    partial: int
    not_met: int

  consistency_accuracy:         # FR-051 to FR-060
    total: 10
    met: int
    partial: int
    not_met: int

  accessibility:                # FR-061 to FR-065
    total: 5
    met: int
    partial: int
    not_met: int

  pypi_specific:                # FR-066 to FR-070
    total: 5
    met: int
    partial: int
    not_met: int
```

### Quality Score

```
Total Requirements: 70
Requirements Met: X
Coverage Percentage: (X / 70) * 100%

Quality Tiers:
- 95-100%: Excellent (PyPI ready)
- 85-94%: Good (minor improvements needed)
- 75-84%: Acceptable (quality improvements recommended)
- <75%: Needs work (not release ready)
```

## Tools

### Validation Tools

```bash
# PyPI rendering preview
python -m readme_renderer README.md -o /tmp/preview.html

# Link checking
markdown-link-check README.md

# Package build validation
python -m build
twine check dist/*

# Docstring validation
pydocstyle iris_devtools/

# Example testing
pytest examples/  # If tests exist
# Or manual: python examples/*.py
```

### Automation Opportunities

- Pre-commit hook: Check for relative links in markdown
- CI check: Validate pyproject.toml description matches README
- CI check: Ensure all examples run without errors
- CI check: Verify version consistency across files
