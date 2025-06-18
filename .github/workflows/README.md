# GitHub Actions Workflows

This directory contains CI/CD workflows for the DEAN orchestration system.

## Workflow Overview

### Continuous Integration (ci.yml)
**Purpose**: Ensure code quality and test coverage on every change.

**Triggers**:
- Push to main/develop branches
- Pull requests to main/develop
- Manual dispatch

**Jobs**:
1. **Linting**: Code formatting and style checks
2. **Testing**: Unit and integration tests with coverage
3. **Security**: Vulnerability scanning
4. **Build**: Docker image creation
5. **Documentation**: Build and validate docs
6. **Integration**: End-to-end system tests

### Continuous Deployment (cd.yml)
**Purpose**: Deploy code to staging and production environments.

**Triggers**:
- Push to main (staging deployment)
- Version tags (production deployment)
- Manual dispatch with environment selection

**Features**:
- Multiple deployment strategies (blue-green, canary, rolling)
- Automatic rollback on failure
- Smoke testing
- Backup creation before deployment

### Release Management (release.yml)
**Purpose**: Automate the release process with proper versioning.

**Triggers**:
- Manual dispatch with version or release type

**Process**:
1. Determine version (manual or auto-increment)
2. Generate changelog from commits
3. Update version in files
4. Create release branch and PR
5. Tag and create GitHub release
6. Optional PyPI publishing

### Security Scanning (security.yml)
**Purpose**: Comprehensive security analysis of code and dependencies.

**Triggers**:
- Daily schedule (2 AM UTC)
- Push to main/develop
- Pull requests
- Manual dispatch

**Scans**:
- Dependency vulnerabilities
- Static code analysis
- Container security
- Secret detection
- License compliance

## Required Secrets

### AWS Credentials
- `AWS_ACCESS_KEY_ID`: Staging AWS access
- `AWS_SECRET_ACCESS_KEY`: Staging AWS secret
- `PROD_AWS_ACCESS_KEY_ID`: Production AWS access
- `PROD_AWS_SECRET_ACCESS_KEY`: Production AWS secret

### Notification Services
- `SLACK_WEBHOOK_URL`: Slack notifications
- `PAGERDUTY_KEY`: PagerDuty integration

### Optional Secrets
- `PYPI_API_TOKEN`: For PyPI package publishing
- `SONARCLOUD_TOKEN`: Code quality analysis
- `DOCKER_USERNAME`: Docker Hub credentials
- `DOCKER_PASSWORD`: Docker Hub credentials

## Usage Examples

### Running Workflows Manually

#### Deploy to Specific Environment
```bash
# Via GitHub UI:
# 1. Go to Actions tab
# 2. Select "CD Pipeline"
# 3. Click "Run workflow"
# 4. Choose environment and strategy
```

#### Create a Release
```bash
# Via GitHub UI:
# 1. Go to Actions tab
# 2. Select "Release Pipeline"
# 3. Click "Run workflow"
# 4. Enter version or select release type
```

### Local Testing with Act

Install [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install Act
# macOS: brew install act
# Linux: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
# Windows: choco install act-cli

# Use our testing script
./scripts/test_github_actions_locally.sh all

# Or use Act directly:
# List all workflows
act -l

# Run CI pipeline
act push

# Run configuration validation
act -W .github/workflows/configuration-validation.yml

# Dry run to see what would execute
act --dryrun

# Run with secrets (create .secrets file first)
act --secret-file .secrets

# Run specific job
act -j validate-config
```

See [GitHub Actions Local Testing Guide](../../docs/development/GITHUB_ACTIONS_LOCAL_TESTING.md) for detailed instructions.

## Workflow Configuration

### Environment Variables
Common variables used across workflows:
- `PYTHON_VERSION`: Default Python version (3.11)
- `NODE_VERSION`: Default Node.js version (18)
- `REGISTRY`: Container registry URL
- `IMAGE_NAME`: Docker image name

### Caching Strategy
- pip packages cached by requirements hash
- Docker layers cached with buildx
- Test results cached between jobs

### Deployment Strategies

#### Blue-Green
- Zero-downtime deployment
- Full environment switch
- Instant rollback capability
- Best for critical production updates

#### Canary
- Gradual traffic shifting
- Risk mitigation through phases
- Metrics-based promotion
- Best for major changes

#### Rolling
- Sequential pod updates
- Resource efficient
- Simple rollback
- Best for minor updates

## Troubleshooting

### Common Issues

#### Workflow Not Triggering
- Check branch protection rules
- Verify workflow file syntax
- Ensure proper permissions

#### Test Failures
- Review test logs in job output
- Check for environment-specific issues
- Verify service dependencies

#### Deployment Failures
- Check cluster connectivity
- Verify image availability
- Review Kubernetes events
- Check resource quotas

### Debug Mode
Enable debug logging:
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

## Best Practices

1. **Fast Feedback**: Keep CI jobs under 10 minutes
2. **Parallel Execution**: Run independent jobs concurrently
3. **Fail Fast**: Stop on first critical failure
4. **Cache Wisely**: Cache dependencies, not build artifacts
5. **Secure Secrets**: Never log sensitive information
6. **Document Changes**: Update this README when modifying workflows

## Monitoring

### Metrics to Track
- Build success rate
- Deployment frequency
- Lead time for changes
- Mean time to recovery
- Test coverage trends

### Notifications
- **Success**: Optional Slack notification
- **Failure**: Slack + PagerDuty (production)
- **Security Issues**: Direct to security team

## Contributing

When modifying workflows:
1. Test locally with `act` first
2. Create PR with workflow changes
3. Document any new secrets required
4. Update this README
5. Test in staging before production