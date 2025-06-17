# DEAN Scripts

This directory contains operational scripts for the DEAN orchestration system.

## Directory Structure

- `deploy/` - Deployment scripts
  - Single-machine deployment
  - Distributed deployment
  - Health verification

- `utilities/` - Utility scripts
  - Environment setup
  - Configuration generation
  - Dependency validation

## Purpose

These scripts provide:

1. **Automated Deployment**: Consistent deployment across environments
2. **Environment Setup**: Preparing systems for DEAN operation
3. **Operational Tasks**: Common maintenance and verification tasks
4. **Configuration Management**: Generating and validating configurations

## Script Standards

- All scripts include help documentation
- Error handling with clear messages
- Idempotent operations where possible
- No modification of external repositories
- Proper exit codes for automation