# DEAN Orchestration Makefile
# Provides standard targets for development and operations

.PHONY: help install install-dev test test-unit test-integration lint format type-check serve clean build docs

# Default target - show help
help:
	@echo "DEAN Orchestration - Available targets:"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint          - Run code quality checks (ruff)"
	@echo "  make format        - Format code (black)"
	@echo "  make type-check    - Run type checking (mypy)"
	@echo "  make serve         - Start the orchestration server"
	@echo "  make clean         - Remove generated files"
	@echo "  make build         - Build distribution packages"
	@echo "  make docs          - Build documentation"

# Install production dependencies
install:
	pip install --upgrade pip
	pip install -e .

# Install development dependencies
install-dev:
	pip install --upgrade pip
	pip install -e ".[dev,test,docs]"
	pre-commit install

# Run all tests
test:
	python -m pytest

# Run unit tests only
test-unit:
	python -m pytest -m unit

# Run integration tests only
test-integration:
	python -m pytest -m integration

# Run linting
lint:
	python -m ruff check src tests scripts

# Format code
format:
	python -m black src tests scripts
	python -m ruff check --fix src tests scripts

# Run type checking
type-check:
	python -m mypy src

# Start the orchestration server
serve:
	@echo "Starting DEAN orchestration server..."
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && uvicorn dean_orchestration.server:app --reload --host 0.0.0.0 --port 8093; \
	else \
		uvicorn dean_orchestration.server:app --reload --host 0.0.0.0 --port 8093; \
	fi

# Clean generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

# Build distribution packages
build: clean
	python -m build

# Build documentation
docs:
	mkdocs build

# Development shortcuts
.PHONY: dev check fix

# Run all development checks
check: lint type-check test

# Fix auto-fixable issues
fix: format

# Quick development test
dev: fix check