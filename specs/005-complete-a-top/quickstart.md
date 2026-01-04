# Quickstart: Documentation Audit & Remediation

**Feature**: 005-complete-a-top
**Audience**: Maintainers preparing for PyPI release
**Time**: 16-24 hours total

## Goal

Ensure all 70 functional requirements are met for a professional PyPI release, providing new users with an excellent first impression and comprehensive documentation.

## Prerequisites

- Access to repository with write permissions
- Familiarity with project structure
- Understanding of PyPI packaging standards
- Ability to test PyPI rendering locally

## Phase 1: Critical Fixes (4-6 hours)

### Priority 0: Files That Must Exist

#### 1. Create CONTRIBUTING.md

```bash
# Create from template
cat > CONTRIBUTING.md << 'EOF'
# Contributing to IRIS DevTools

Thank you for considering contributing to IRIS DevTools! This project embodies years of production experience with InterSystems IRIS, and we welcome contributions that build on that foundation.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Bug reports are tracked as GitHub Issues. When creating a bug report:
1. Use the bug report template
2. Include iris-devtester version, Python version, IRIS edition
3. Provide minimal reproduction steps
4. Include relevant log output

### Suggesting Enhancements

Feature requests are also tracked as GitHub Issues. When suggesting enhancements:
1. Use the feature request template
2. Explain the problem this feature would solve
3. Describe your proposed solution
4. Consider alternatives and trade-offs

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following our development guidelines (below)
4. Run tests and linters
5. Submit a pull request using the PR template

## Development Setup

### Prerequisites
- Python 3.9+
- Docker Desktop
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/intersystems-community/iris-devtester.git
cd iris-devtester

# Install in development mode with all dependencies
pip install -e ".[all,dev,test]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit/

# Integration tests only (requires Docker)
pytest tests/integration/

# With coverage report
pytest --cov=iris_devtester --cov-report=html
```

### Code Style

This project uses:
- **black** (line length 100)
- **isort** (compatible with black)
- **mypy** (type checking)
- **flake8** (linting)

Run all checks:
```bash
black .
isort .
mypy iris_devtester/
flake8 iris_devtester/
pytest
```

Pre-commit hooks will run these automatically.

## Project Structure

```
iris_devtester/
├── connections/    # DBAPI/JDBC connection management
├── containers/     # Testcontainers wrapper with auto-remediation
├── testing/        # pytest fixtures and utilities
├── config/         # Configuration discovery
└── cli/            # CLI commands

tests/
├── unit/           # Unit tests (no external dependencies)
├── integration/    # Integration tests (require IRIS container)
└── e2e/            # End-to-end workflow tests

docs/
└── learnings/      # Production insights and "why not X?" docs
```

## Testing Guidelines

### Test Coverage Requirements
- Minimum: 95% overall coverage
- All error paths must be tested
- All public APIs must have tests

### Test Organization
- **Unit tests**: Mock external dependencies (IRIS, Docker)
- **Integration tests**: Use real IRIS containers via testcontainers
- **E2E tests**: Full workflow validation

### Writing Tests

Follow these patterns:

```python
# Unit test example
def test_connection_config_parsing():
    """Unit test - no external dependencies"""
    config = ConnectionConfig.from_dict({"host": "localhost"})
    assert config.host == "localhost"

# Integration test example
@pytest.mark.integration
def test_iris_connection(iris_container):
    """Integration test - uses real IRIS"""
    conn = iris_container.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

## Constitutional Compliance

All contributions must follow the [8 Constitutional Principles](CONSTITUTION.md):

1. **Automatic Remediation Over Manual Intervention** - No "run this command" errors
2. **Choose the Right Tool** - DBAPI for SQL, iris.connect() for ObjectScript
3. **Isolation by Default** - Each test gets its own container/namespace
4. **Zero Configuration Viable** - `pip install && pytest` must work
5. **Fail Fast with Guidance** - Errors include "what went wrong" + "how to fix it"
6. **Enterprise Ready, Community Friendly** - Support both editions
7. **Medical-Grade Reliability** - 95%+ coverage, all error paths tested
8. **Document the Blind Alleys** - Add to `docs/learnings/` when you discover "why not X"

**Before submitting a PR**, verify your changes align with these principles.

## Governance

### Maintainers
- Primary maintainers listed in pyproject.toml
- Governance model: Benevolent Dictator For Life (BDFL) with community input

### Decision Process
1. Propose changes via GitHub Issues or Discussions
2. Gather community feedback (1-2 weeks for major changes)
3. Maintainers make final decision based on:
   - Constitutional alignment
   - Production evidence
   - Community consensus
   - Backwards compatibility

### Release Process
- Semantic versioning (MAJOR.MINOR.PATCH)
- CHANGELOG updated for all releases
- Git tags for all versions
- PyPI releases automated via CI

## Documentation Contributions

### Adding to docs/learnings/

When you discover a "blind alley" (something that didn't work), document it:

1. Create `docs/learnings/your-learning.md`
2. Use this template:
```markdown
# Learning: [Title]

## Problem
[What you were trying to solve]

## What We Tried
[Approach that didn't work]

## Why It Didn't Work
[Root cause, with evidence]

## What We Did Instead
[Successful approach]

## Evidence
[Benchmarks, logs, test results]

## Date
[When this was discovered]
```

### Updating API Documentation

- All public APIs need Google-style docstrings
- Include a minimal working example in each docstring
- Document all parameters and return values
- Specify any exceptions raised

## Questions?

- **General questions**: GitHub Discussions
- **Bug reports**: GitHub Issues (use template)
- **Feature requests**: GitHub Issues (use template)
- **Security issues**: See [SECURITY.md](SECURITY.md)

## Thank You!

Your contributions make this project better for everyone. Every principle in our constitution was learned through production debugging—your contribution helps others avoid those same pitfalls.
EOF
```

#### 2. Create CODE_OF_CONDUCT.md

```bash
# Use Contributor Covenant 2.1
curl -o CODE_OF_CONDUCT.md https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md

# Customize enforcement contact
sed -i '' 's/\[INSERT CONTACT METHOD\]/community@intersystems.com/g' CODE_OF_CONDUCT.md
```

#### 3. Create SECURITY.md

```bash
cat > SECURITY.md << 'EOF'
# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: security@intersystems.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: <7 days, High: <30 days, Medium: <90 days)

### Disclosure Policy

- We follow coordinated vulnerability disclosure
- Security advisories published after fixes are released
- Credit given to reporters (unless they prefer to remain anonymous)

## Security Best Practices

### For Package Users

1. **Keep Updated**: Use the latest version of iris-devtester
2. **Review Dependencies**: Regularly update testcontainers and other deps
3. **Secure Credentials**: Never commit IRIS credentials to version control
4. **Container Security**: Use official IRIS images from trusted sources
5. **Network Isolation**: Run test containers on isolated networks

### For Contributors

1. **No Secrets in Code**: Never hardcode passwords, API keys, or tokens
2. **Dependency Auditing**: Run `pip-audit` before adding new dependencies
3. **Input Validation**: Validate all external inputs (connection strings, file paths)
4. **Error Messages**: Don't expose sensitive information in error messages
5. **Test Coverage**: Ensure security-critical paths have 100% test coverage

## Known Security Considerations

### IRIS Credentials
- Default IRIS credentials are well-known (\_SYSTEM/SYS)
- iris-devtester automatically resets passwords on container startup
- Always use unique credentials in production

### Container Isolation
- Test containers should run on isolated networks
- Avoid exposing container ports to public networks
- Clean up containers after tests complete

### Dependency Chain
- iris-devtester depends on testcontainers-python and docker-py
- Security is inherited from these dependencies
- We monitor security advisories for all dependencies

## Security Update Process

When a security vulnerability is reported:

1. **Triage** (24 hours): Assess severity and impact
2. **Fix Development** (varies): Create patch in private fork
3. **Testing** (1-2 days): Comprehensive security testing
4. **Release** (1 day): Version bump, changelog, PyPI release
5. **Disclosure** (same day): GitHub Security Advisory published
6. **Communication** (1 week): Notify users via GitHub, PyPI, mailing list

## Contact

- **Security Issues**: security@intersystems.com
- **General Questions**: GitHub Discussions
- **Non-Security Bugs**: GitHub Issues

Thank you for helping keep IRIS DevTools secure!
EOF
```

#### 4. Create GitHub Issue Templates

```bash
mkdir -p .github/ISSUE_TEMPLATE

# Bug report template
cat > .github/ISSUE_TEMPLATE/bug_report.yml << 'EOF'
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
      description: Describe the bug and what you expected to happen
      placeholder: When I run X, I expected Y but got Z
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
      placeholder: "3.11.5"
    validations:
      required: true

  - type: dropdown
    id: iris-edition
    attributes:
      label: IRIS Edition
      options:
        - Community
        - Enterprise
        - Not applicable
    validations:
      required: true

  - type: dropdown
    id: operating-system
    attributes:
      label: Operating System
      options:
        - macOS
        - Linux
        - Windows
        - Other
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: Minimal code or commands that reproduce the issue
      placeholder: |
        1. Run `python example.py`
        2. Observe error
      render: shell
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Relevant log output
      description: Error messages, stack traces, or relevant logs
      render: shell

  - type: textarea
    id: additional
    attributes:
      label: Additional Context
      description: Anything else that might be relevant (Docker version, network setup, etc.)
EOF

# Feature request template
cat > .github/ISSUE_TEMPLATE/feature_request.yml << 'EOF'
name: Feature Request
description: Suggest a new feature or enhancement
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for suggesting an improvement!

  - type: textarea
    id: problem
    attributes:
      label: Problem Description
      description: What problem would this feature solve?
      placeholder: "I'm always frustrated when..."
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: How should this feature work?
      placeholder: "The feature should..."
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
      description: What other solutions have you considered?
      placeholder: "I've considered X, but..."

  - type: dropdown
    id: contribution
    attributes:
      label: Would you like to contribute this feature?
      options:
        - "Yes, I'd like to implement this"
        - "Maybe, with guidance"
        - "No, just suggesting"
    validations:
      required: true

  - type: textarea
    id: additional
    attributes:
      label: Additional Context
      description: Examples, mockups, or references
EOF

# PR template
cat > .github/PULL_REQUEST_TEMPLATE.md << 'EOF'
## Description
<!-- Describe your changes in detail -->

## Related Issue
<!-- Link to related issue: Fixes #123, Closes #456 -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Checklist
- [ ] Tests added/updated
- [ ] All tests pass locally (`pytest`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Code formatted (`black . && isort .`)
- [ ] Type checking passes (`mypy iris_devtester/`)
- [ ] Follows constitutional principles (see CONSTITUTION.md)

## Test Plan
<!-- How did you test this? Include:
- Unit tests added
- Integration tests added
- Manual testing performed
- Edge cases considered
-->

## Constitutional Compliance
<!-- Which constitutional principles does this change affect?
Check all that apply:
- [ ] Principle 1: Automatic Remediation
- [ ] Principle 2: Choose the Right Tool
- [ ] Principle 3: Isolation by Default
- [ ] Principle 4: Zero Configuration
- [ ] Principle 5: Fail Fast with Guidance
- [ ] Principle 6: Enterprise & Community Support
- [ ] Principle 7: Medical-Grade Reliability
- [ ] Principle 8: Document Blind Alleys

Explain how this change aligns with checked principles:
-->

## Screenshots / Output
<!-- If applicable, add screenshots or sample output -->

## Breaking Changes
<!-- If this is a breaking change, describe:
- What breaks
- Migration path for users
- Why it's necessary
-->

## Additional Notes
<!-- Anything else reviewers should know -->
EOF
```

#### 5. Fix README Links

```bash
# This requires manual editing - scan README for relative links
# Convert patterns like:
#   [CONTRIBUTING.md](CONTRIBUTING.md)
# To:
#   [CONTRIBUTING.md](https://github.com/intersystems-community/iris-devtester/blob/main/CONTRIBUTING.md)

# Also remove references to non-existent files:
#   - docs/quickstart.md (doesn't exist)
#   - docs/best-practices.md (doesn't exist)
#   - docs/troubleshooting.md (doesn't exist yet)
```

#### 6. Update pyproject.toml Classifier

```toml
# Change from:
"Development Status :: 4 - Beta"

# To (for v1.0.0):
"Development Status :: 5 - Production/Stable"
```

## Phase 2: Quality Improvements (8-12 hours)

### Create Troubleshooting Guide

Create `docs/TROUBLESHOOTING.md` with top 5 issues from research.md.

### Add Missing Examples

Create:
- `examples/05_ci_cd.py` - GitHub Actions integration
- `examples/09_enterprise.py` - Enterprise edition features

### Enhance examples/README.md

Add learning path and expected outputs.

### Audit Docstrings

Check all public APIs in:
- `iris_devtester/containers/`
- `iris_devtester/connections/`
- `iris_devtester/testing/`

### Add Example Testing to CI

Update `.github/workflows/test.yml` to run all examples.

## Phase 3: Polish (4-6 hours)

### Accessibility Review

- Define acronyms on first use in README
- Remove "obviously", "simply" from docs
- Use plain language

### Add Expected Output to Examples

All code blocks should show:
```python
# Expected output: ...
```

### Version Consistency Check

Verify version matches in:
- README.md
- pyproject.toml
- iris_devtester/__init__.py
- CHANGELOG.md

## Validation

### Local PyPI Preview

```bash
# Build package
python -m build

# Check rendering
twine check dist/*

# Preview README
python -m readme_renderer README.md -o /tmp/preview.html
open /tmp/preview.html  # View in browser
```

### Link Checking

```bash
# Install link checker
npm install -g markdown-link-check

# Check all markdown files
find . -name "*.md" -not -path "./node_modules/*" -not -path "./.venv/*" | xargs markdown-link-check
```

### Example Testing

```bash
# Run all examples
for example in examples/*.py; do
    echo "Testing $example..."
    python "$example" || echo "FAILED: $example"
done
```

## Success Criteria

Before PyPI release, verify:
- [ ] All P0 files exist (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, templates)
- [ ] README uses absolute URLs
- [ ] No broken links in any markdown file
- [ ] PyPI preview renders correctly
- [ ] All examples run without errors
- [ ] Version consistent across all files
- [ ] pyproject.toml classifier matches version (Production/Stable for v1.0+)

## Timeline

- **Day 1 Morning** (3-4 hours): Phase 1 (critical files)
- **Day 1 Afternoon** (2-3 hours): Phase 1 (link fixes, validation)
- **Day 2 Morning** (4-5 hours): Phase 2 (troubleshooting, examples)
- **Day 2 Afternoon** (4-5 hours): Phase 2 (docstrings, CI)
- **Day 3 Morning** (3-4 hours): Phase 3 (accessibility, polish)
- **Day 3 Afternoon** (1-2 hours): Final validation

**Total**: 16-24 hours over 3 days

## Next Steps

After completing this audit:
1. Commit all changes to feature branch
2. Create pull request for review
3. Address review feedback
4. Merge to main
5. Create git tag for version
6. Build and upload to PyPI
7. Announce release

## Resources

- [PyPI Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Contributor Covenant](https://www.contributor-covenant.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
