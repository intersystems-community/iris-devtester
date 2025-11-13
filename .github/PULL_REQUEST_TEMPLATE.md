# Pull Request

## Description

<!-- Provide a clear and concise description of your changes -->

## Related Issues

<!-- Link to any related issues using #issue_number -->
Closes #

## Type of Change

<!-- Check all that apply -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test coverage improvement

## Changes Made

<!-- Describe the changes in detail -->

-
-
-

## Constitutional Compliance

<!-- Verify your changes align with the 8 constitutional principles -->

- [ ] **Automatic Remediation**: Errors are auto-fixed where possible
- [ ] **Choose the Right Tool**: DBAPI preferred over JDBC (if applicable)
- [ ] **Isolation by Default**: Tests use isolated containers/namespaces
- [ ] **Zero Configuration**: Changes work with `pip install && pytest`
- [ ] **Fail Fast with Guidance**: Error messages include remediation steps
- [ ] **Enterprise Ready, Community Friendly**: Works with both IRIS editions
- [ ] **Medical-Grade Reliability**: Test coverage maintained at 95%+
- [ ] **Document the Blind Alleys**: Learnings documented in `docs/learnings/`

## Testing

<!-- Describe the tests you've added or run -->

### Test Coverage

- [ ] Added unit tests for new functionality
- [ ] Added integration tests (if applicable)
- [ ] All existing tests pass
- [ ] Coverage remains at or above 95%

### Manual Testing

<!-- Describe any manual testing performed -->

```bash
# Commands used for testing
pytest tests/unit/
pytest tests/integration/
```

### Test Results

<!-- Include relevant test output or screenshots -->

```
# Paste test output here
```

## Code Quality Checklist

- [ ] Code follows project style guidelines (black, isort, flake8)
- [ ] All public APIs have Google-style docstrings with examples
- [ ] Type hints added where applicable
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Documentation updated (if applicable)

## Breaking Changes

<!-- If this PR includes breaking changes, describe them here and provide migration guidance -->

None / N/A

**Migration guide** (if applicable):
<!-- Explain how users should update their code -->

## Additional Context

<!-- Add any other context, screenshots, or information about the PR here -->

## Pre-submission Checklist

- [ ] I have read and followed the [Contributing Guidelines](https://github.com/intersystems-community/iris-devtools/blob/main/CONTRIBUTING.md)
- [ ] I have verified constitutional compliance for all changes
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] I have maintained or improved test coverage (≥95%)
- [ ] I have updated documentation where necessary
- [ ] All CI checks pass
