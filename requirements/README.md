# DEAN Requirements

This directory contains Python dependency specifications for the DEAN orchestration system.

## Files

- `base.txt` - Core dependencies required for DEAN operation
- `dev.txt` - Development dependencies (testing, linting, formatting)
- `test.txt` - Testing-specific dependencies

## Purpose

Dependency management ensures:

1. **Reproducible Environments**: Consistent dependencies across installations
2. **Version Control**: Explicit version pinning for stability
3. **Security**: Known, vetted dependencies
4. **Minimal Footprint**: Only necessary dependencies included

## Dependency Philosophy

- Minimal external dependencies
- Well-maintained, popular libraries
- Security-first selection process
- Clear separation of runtime vs development dependencies
- Regular updates with careful testing