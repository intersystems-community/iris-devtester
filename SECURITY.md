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

1. **Keep Updated**: Use the latest version of iris-devtools
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
- iris-devtools automatically resets passwords on container startup
- Always use unique credentials in production

### Container Isolation
- Test containers should run on isolated networks
- Avoid exposing container ports to public networks
- Clean up containers after tests complete

### Dependency Chain
- iris-devtools depends on testcontainers-python and docker-py
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
