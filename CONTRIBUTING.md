# Contributing to DEAN

Thank you for your interest in contributing to the Distributed Evolutionary Agent Network (DEAN) project! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Exact steps to reproduce the problem
- Expected behavior vs actual behavior
- System information (OS, Python version, etc.)
- Relevant logs and error messages
- Code samples that demonstrate the issue

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- Detailed description of the proposed enhancement
- Rationale for why this would be useful
- Possible implementation approach
- Any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create your branch from `develop`
2. **Follow our coding standards** (see below)
3. **Write tests** for new functionality
4. **Ensure all tests pass** with >90% coverage
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

## Development Process

### Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/your-username/DEAN.git
cd DEAN

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Run tests to verify setup
make test
```

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our standards

3. Run quality checks:
   ```bash
   make format    # Auto-format code
   make lint      # Check code style
   make type-check # Type checking
   make test      # Run all tests
   make check     # Run all checks
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "feat(scope): descriptive message"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a pull request via GitHub

## Code Standards

### Python Code Style

- **PEP 8 compliance required** - enforced by Black and Ruff
- **Type hints required** for all functions
- **Docstrings required** for all public modules, classes, and functions
- Maximum line length: 100 characters
- Use meaningful variable and function names

Example:
```python
from typing import List, Optional

def process_agents(
    agents: List[Agent], 
    fitness_threshold: float = 0.8
) -> Optional[Agent]:
    """
    Process a list of agents and return the best performer.
    
    Args:
        agents: List of Agent instances to process
        fitness_threshold: Minimum fitness score required
        
    Returns:
        Best performing agent or None if none meet threshold
        
    Raises:
        ValueError: If agents list is empty
    """
    if not agents:
        raise ValueError("Agents list cannot be empty")
    
    # Implementation here
    pass
```

### Documentation Standards

- Use Markdown for all documentation
- Include code examples where relevant
- Keep documentation up-to-date with code changes
- Follow the existing documentation structure

### Testing Standards

- **Minimum 90% test coverage required**
- Write both unit and integration tests
- Use descriptive test names
- Mock external dependencies
- Test edge cases and error conditions

Example:
```python
import pytest
from unittest.mock import Mock

def test_agent_evolution_with_valid_params():
    """Test agent evolution with valid parameters."""
    # Arrange
    agent = Mock()
    agent.fitness_score = 0.7
    
    # Act
    result = evolve_agent(agent, mutation_rate=0.1)
    
    # Assert
    assert result.fitness_score > agent.fitness_score
    assert result.generation == agent.generation + 1
```

### Commit Message Format

Follow the Conventional Commits specification:

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

**Examples:**
```
feat(evolution): add diversity-based selection algorithm

Implemented Shannon entropy calculation for population diversity.
This ensures maintaining genetic diversity during evolution.

Closes #123
```

```
fix(auth): correct token expiration handling

Token refresh was failing due to timezone mismatch.
Now using UTC consistently across all token operations.
```

## Review Process

### Pull Request Review Criteria

1. **Code Quality**
   - Follows coding standards
   - No code smells or anti-patterns
   - Efficient and maintainable

2. **Testing**
   - Adequate test coverage (>90%)
   - Tests are meaningful and comprehensive
   - All tests pass

3. **Documentation**
   - Code is well-documented
   - README updated if needed
   - API documentation current

4. **Security**
   - No hardcoded secrets
   - Input validation implemented
   - Security best practices followed

### Review Timeline

- Initial review within 48 hours
- Follow-up reviews within 24 hours
- Merge decision within 1 week

## Release Process

1. Features merged to `develop`
2. Release candidate created from `develop`
3. Testing and validation
4. Merge to `main` with version tag
5. Deploy to production
6. Update release notes

## Getting Help

- Check the [documentation](docs/)
- Search existing [issues](https://github.com/dean-project/DEAN/issues)
- Join our [community discussions](https://github.com/dean-project/DEAN/discussions)
- Contact maintainers via email

## Recognition

Contributors will be recognized in:
- Release notes
- Contributors file
- Project documentation

Thank you for contributing to DEAN!