# GitHub Actions Local Testing Guide

This guide explains how to test GitHub Actions workflows locally before pushing to GitHub, preventing CI/CD failures and saving development time.

## Overview

We use [Act](https://github.com/nektos/act) to run GitHub Actions workflows locally in Docker containers that simulate the GitHub Actions environment. This allows you to:

- ✅ Test workflows without pushing to GitHub
- ✅ Debug failures quickly with local access
- ✅ Save GitHub Actions minutes
- ✅ Iterate faster on workflow development

## Installation

### Prerequisites
- Docker Desktop or Docker Engine installed and running
- Command line access

### Install Act

#### macOS
```bash
brew install act
```

#### Linux
```bash
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

#### Windows
```powershell
choco install act-cli
# or
scoop install act
```

#### Manual Installation
Download from [Act releases](https://github.com/nektos/act/releases)

## Quick Start

### 1. Test All Workflows
```bash
./scripts/test_github_actions_locally.sh all
```

### 2. Test Configuration Validation
```bash
./scripts/test_github_actions_locally.sh validate
```

### 3. List Available Workflows
```bash
./scripts/test_github_actions_locally.sh list
```

### 4. Test Push Event
```bash
./scripts/test_github_actions_locally.sh push
```

## Configuration

### `.actrc` File
The `.actrc` file in the repository root configures Act defaults:

```bash
# Use GitHub-compatible images
-P ubuntu-latest=catthehacker/ubuntu:act-latest

# Architecture matching GitHub
--container-architecture linux/amd64

# Reuse containers for speed
--reuse

# Local artifact storage
--artifact-server-path /tmp/act-artifacts
```

### Event Simulation
The `.github/workflows/event.json` file contains sample events for testing different triggers.

## Common Use Cases

### Testing Before Push
Always run this before pushing changes that modify workflows:
```bash
# Test the specific workflow you modified
act -W .github/workflows/configuration-validation.yml

# Or test all workflows
./scripts/test_github_actions_locally.sh all
```

### Debugging Failed Workflows
```bash
# Run with verbose output
act --verbose

# Start interactive shell in workflow container
act -b
```

### Testing Specific Jobs
```bash
# Run only the 'validate-config' job
act -j validate-config
```

### Using Secrets
Create a `.secrets` file (git-ignored):
```bash
JWT_SECRET_KEY=test-secret
DEAN_API_KEY=test-api-key
```

Run with secrets:
```bash
act --secret-file .secrets
```

## Advanced Usage

### Custom Docker Images
Modify `.actrc` to use different runner images:
```bash
-P ubuntu-latest=custom/image:tag
```

### Matrix Testing
Test matrix strategies locally:
```bash
act -W .github/workflows/test.yml --matrix os:ubuntu-latest
```

### Debugging Container Issues
```bash
# Keep containers after run for inspection
act --rm=false

# Use specific Docker network
act --network host
```

## Limitations

1. **Platform Support**: Only Linux-based jobs work locally (no Windows/macOS runners)
2. **GitHub Services**: Some GitHub-hosted services aren't available:
   - GitHub Packages
   - GitHub Container Registry (partial support)
   - Some marketplace actions
3. **Hardware**: Local hardware may differ from GitHub runners

## Troubleshooting

### Docker Not Running
```
Error: Cannot connect to the Docker daemon
```
**Solution**: Start Docker Desktop or Docker daemon

### Image Pull Errors
```
Error: failed to pull image
```
**Solution**: Check internet connection or use different image in `.actrc`

### Out of Disk Space
```
Error: no space left on device
```
**Solution**: 
```bash
# Clean up old containers and images
docker system prune -a
./scripts/test_github_actions_locally.sh clean
```

### Workflow Not Found
```
Error: Could not find any workflows
```
**Solution**: Ensure you're in the repository root with `.github/workflows/` directory

## Integration with Development Workflow

### Pre-commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Test workflows if they were modified
if git diff --cached --name-only | grep -q ".github/workflows/"; then
    echo "Testing modified workflows..."
    ./scripts/test_github_actions_locally.sh dry-run
fi
```

### VS Code Integration
Install the "GitHub Actions" extension and configure it to use Act for local testing.

### CI/CD Pipeline
Before merging PRs:
1. Run `./scripts/test_github_actions_locally.sh all`
2. Fix any issues locally
3. Push changes
4. Verify GitHub Actions pass

## Best Practices

1. **Test Locally First**: Always test workflows locally before pushing
2. **Use Dry Run**: Run `act -n` to see what would execute
3. **Cache Images**: First run downloads images; subsequent runs are faster
4. **Version Control**: Don't commit `.secrets` or `.env` files
5. **Resource Limits**: Be mindful of local resource constraints vs GitHub runners

## Comparison: Local vs GitHub

| Feature | Local (Act) | GitHub Actions |
|---------|------------|----------------|
| Speed | Fast (seconds) | Slower (minutes) |
| Cost | Free | Limited free minutes |
| Debugging | Easy local access | Logs only |
| Environment | Docker containers | GitHub runners |
| Secrets | Local file | GitHub secrets |
| Artifacts | Local directory | GitHub storage |

## Additional Resources

- [Act Documentation](https://github.com/nektos/act#readme)
- [Act Community Images](https://github.com/catthehacker/docker_images)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Our CI/CD Workflows](.github/workflows/README.md)

## Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Run with `--verbose` flag for detailed output
3. Check Act GitHub issues
4. Ask in the team chat

Remember: The goal is to catch CI/CD issues before they reach GitHub, saving time and maintaining a clean commit history.