#!/usr/bin/env python3
"""
Repository Management System for DEAN
Handles repository registration, initialization, and tracking
"""

import os
import json
import git
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass, asdict
import asyncpg
import aioredis

logger = logging.getLogger(__name__)


@dataclass
class Repository:
    """Repository information"""
    id: str
    name: str
    path: str
    url: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


class RepositoryManager:
    """
    Manages repository lifecycle for DEAN system.
    Handles registration, initialization, and tracking.
    """
    
    def __init__(
        self,
        base_path: str = "/repos",
        db_pool: Optional[asyncpg.Pool] = None,
        redis_client: Optional[aioredis.Redis] = None
    ):
        """
        Initialize repository manager.
        
        Args:
            base_path: Base directory for repositories
            db_pool: PostgreSQL connection pool
            redis_client: Redis client for caching
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.db_pool = db_pool
        self.redis = redis_client
        self.repositories: Dict[str, Repository] = {}
        
    async def register_repository(
        self,
        repo_path: str,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a repository with the Evolution API.
        
        Args:
            repo_path: Path to repository
            url: Optional remote URL
            metadata: Additional metadata
            
        Returns:
            Repository ID
        """
        # Generate unique ID
        repo_name = Path(repo_path).name
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        repo_id = f"repo_{repo_name}_{timestamp}"
        
        # Create repository object
        repo = Repository(
            id=repo_id,
            name=repo_name,
            path=str(repo_path),
            url=url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store in memory
        self.repositories[repo_id] = repo
        
        # Store in database if available
        if self.db_pool:
            await self._store_repository_db(repo)
        
        # Cache in Redis if available
        if self.redis:
            await self._cache_repository(repo)
        
        logger.info(f"Registered repository {repo_id} at {repo_path}")
        return repo_id
    
    async def initialize_test_repository(
        self,
        name: str,
        template: str = "default",
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Initialize a test repository with sample code.
        
        Args:
            name: Repository name
            template: Template to use
            language: Programming language
            
        Returns:
            Repository information
        """
        # Create repository directory
        repo_path = self.base_path / name
        repo_path.mkdir(exist_ok=True)
        
        # Initialize git repository
        repo = git.Repo.init(repo_path)
        
        # Create structure based on template
        if template == "python_package":
            await self._create_python_package_structure(repo_path, name)
        elif template == "web_app":
            await self._create_web_app_structure(repo_path, name)
        else:
            await self._create_default_structure(repo_path, name, language)
        
        # Initial commit
        repo.index.add("*")
        repo.index.commit("Initial commit - DEAN test repository")
        
        # Register repository
        repo_id = await self.register_repository(
            str(repo_path),
            metadata={
                "template": template,
                "language": language,
                "type": "test"
            }
        )
        
        return {
            "id": repo_id,
            "name": name,
            "path": str(repo_path),
            "template": template,
            "language": language,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _create_default_structure(
        self,
        repo_path: Path,
        name: str,
        language: str
    ):
        """Create default repository structure"""
        # README
        readme_content = f"""# {name}

A test repository created by DEAN for agent evolution experiments.

## Structure

- `src/`: Source code
- `tests/`: Test files
- `docs/`: Documentation

## Getting Started

This repository was automatically generated for testing evolutionary agents.
"""
        (repo_path / "README.md").write_text(readme_content)
        
        # Create directories
        (repo_path / "src").mkdir(exist_ok=True)
        (repo_path / "tests").mkdir(exist_ok=True)
        (repo_path / "docs").mkdir(exist_ok=True)
        
        # Language-specific files
        if language == "python":
            # Main module
            main_content = '''#!/usr/bin/env python3
"""Main module for {name}"""

def main():
    """Main entry point"""
    print(f"Hello from {name}!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
'''.format(name=name)
            (repo_path / "src" / "main.py").write_text(main_content)
            
            # Test file
            test_content = '''"""Tests for main module"""
import pytest
from src.main import main

def test_main():
    """Test main function"""
    assert main() == 0

def test_placeholder():
    """Placeholder test - TODO: implement real tests"""
    assert True
'''
            (repo_path / "tests" / "test_main.py").write_text(test_content)
            
            # Requirements
            (repo_path / "requirements.txt").write_text("pytest>=7.0.0\n")
            
        elif language == "javascript":
            # Package.json
            package_json = {
                "name": name,
                "version": "0.1.0",
                "description": f"Test repository for {name}",
                "main": "src/index.js",
                "scripts": {
                    "test": "jest",
                    "start": "node src/index.js"
                },
                "devDependencies": {
                    "jest": "^27.0.0"
                }
            }
            (repo_path / "package.json").write_text(
                json.dumps(package_json, indent=2)
            )
            
            # Main file
            index_content = f'''// Main module for {name}

function main() {{
    console.log("Hello from {name}!");
    return 0;
}}

module.exports = {{ main }};

if (require.main === module) {{
    process.exit(main());
}}
'''
            (repo_path / "src" / "index.js").write_text(index_content)
            
            # Test file
            test_content = '''const { main } = require('../src/index');

describe('main', () => {
    test('should return 0', () => {
        expect(main()).toBe(0);
    });
});
'''
            (repo_path / "tests" / "index.test.js").write_text(test_content)
    
    async def _create_python_package_structure(
        self,
        repo_path: Path,
        name: str
    ):
        """Create Python package structure"""
        # Package directory
        package_dir = repo_path / name.replace("-", "_")
        package_dir.mkdir(exist_ok=True)
        
        # __init__.py
        (package_dir / "__init__.py").write_text(
            f'"""Package {name}"""\n\n__version__ = "0.1.0"\n'
        )
        
        # Core module
        core_content = '''"""Core functionality"""

class Calculator:
    """Simple calculator for testing"""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers"""
        return a + b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers"""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide two numbers"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''
        (package_dir / "core.py").write_text(core_content)
        
        # Utils module with TODO
        utils_content = '''"""Utility functions"""

def validate_input(value):
    """Validate input value
    
    TODO: Implement proper validation logic
    """
    # Placeholder implementation
    return True

def format_output(value):
    """Format output value
    
    TODO: Add formatting options
    """
    return str(value)

def calculate_metrics(data):
    """Calculate performance metrics
    
    TODO: Implement metric calculations
    """
    raise NotImplementedError("Metrics calculation not yet implemented")
'''
        (package_dir / "utils.py").write_text(utils_content)
        
        # Tests
        tests_dir = repo_path / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "__init__.py").write_text("")
        
        test_core_content = f'''"""Tests for core module"""
import pytest
from {name.replace("-", "_")}.core import Calculator

class TestCalculator:
    def setup_method(self):
        self.calc = Calculator()
    
    def test_add(self):
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
    
    def test_multiply(self):
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(0, 5) == 0
    
    def test_divide(self):
        assert self.calc.divide(10, 2) == 5
        with pytest.raises(ValueError):
            self.calc.divide(10, 0)
'''
        (tests_dir / "test_core.py").write_text(test_core_content)
        
        # Setup files
        setup_py = f'''from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    python_requires=">=3.8",
)
'''
        (repo_path / "setup.py").write_text(setup_py)
        
        # Additional files
        (repo_path / "requirements.txt").write_text("pytest>=7.0.0\npytest-cov>=3.0.0\n")
        (repo_path / "requirements-dev.txt").write_text("-r requirements.txt\nblack\nflake8\nmypy\n")
        (repo_path / ".gitignore").write_text("__pycache__/\n*.pyc\n.pytest_cache/\n.coverage\nhtmlcov/\n*.egg-info/\n")
        
        # README with TODOs
        readme = f'''# {name}

A Python package created for DEAN evolution testing.

## Installation

```bash
pip install -e .
```

## Usage

```python
from {name.replace("-", "_")}.core import Calculator

calc = Calculator()
result = calc.add(2, 3)
```

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

## TODO

- [ ] Implement validation logic in utils.validate_input
- [ ] Add formatting options to utils.format_output
- [ ] Implement metrics calculation
- [ ] Add more test coverage
- [ ] Write comprehensive documentation
'''
        (repo_path / "README.md").write_text(readme)
    
    async def _create_web_app_structure(
        self,
        repo_path: Path,
        name: str
    ):
        """Create web application structure"""
        # This would create a more complex web app structure
        # For now, delegate to default structure
        await self._create_default_structure(repo_path, name, "javascript")
    
    async def _store_repository_db(self, repo: Repository):
        """Store repository in database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO repositories (id, name, path, url, metadata, status, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        updated_at = EXCLUDED.updated_at,
                        metadata = EXCLUDED.metadata
                """, repo.id, repo.name, repo.path, repo.url,
                    json.dumps(repo.metadata), repo.status,
                    repo.created_at, repo.updated_at)
        except Exception as e:
            logger.error(f"Failed to store repository in database: {e}")
    
    async def _cache_repository(self, repo: Repository):
        """Cache repository in Redis"""
        if not self.redis:
            return
        
        try:
            key = f"repository:{repo.id}"
            await self.redis.setex(
                key,
                3600,  # 1 hour TTL
                json.dumps(repo.to_dict())
            )
        except Exception as e:
            logger.error(f"Failed to cache repository: {e}")
    
    async def get_repository(self, repo_id: str) -> Optional[Repository]:
        """Get repository by ID"""
        # Check memory
        if repo_id in self.repositories:
            return self.repositories[repo_id]
        
        # Check Redis cache
        if self.redis:
            try:
                key = f"repository:{repo_id}"
                data = await self.redis.get(key)
                if data:
                    repo_data = json.loads(data)
                    repo = Repository(
                        id=repo_data['id'],
                        name=repo_data['name'],
                        path=repo_data['path'],
                        url=repo_data.get('url'),
                        created_at=datetime.fromisoformat(repo_data['created_at']),
                        updated_at=datetime.fromisoformat(repo_data['updated_at']),
                        metadata=repo_data.get('metadata', {}),
                        status=repo_data.get('status', 'active')
                    )
                    self.repositories[repo_id] = repo
                    return repo
            except Exception as e:
                logger.error(f"Failed to get repository from cache: {e}")
        
        # Check database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM repositories WHERE id = $1",
                        repo_id
                    )
                    if row:
                        repo = Repository(
                            id=row['id'],
                            name=row['name'],
                            path=row['path'],
                            url=row['url'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at'],
                            metadata=json.loads(row['metadata']) if row['metadata'] else {},
                            status=row['status']
                        )
                        self.repositories[repo_id] = repo
                        await self._cache_repository(repo)
                        return repo
            except Exception as e:
                logger.error(f"Failed to get repository from database: {e}")
        
        return None
    
    async def list_repositories(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Repository]:
        """List repositories"""
        repos = []
        
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    query = "SELECT * FROM repositories"
                    params = []
                    
                    if status:
                        query += " WHERE status = $1"
                        params.append(status)
                    
                    query += " ORDER BY created_at DESC LIMIT ${}".format(len(params) + 1)
                    params.append(limit)
                    
                    rows = await conn.fetch(query, *params)
                    
                    for row in rows:
                        repo = Repository(
                            id=row['id'],
                            name=row['name'],
                            path=row['path'],
                            url=row['url'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at'],
                            metadata=json.loads(row['metadata']) if row['metadata'] else {},
                            status=row['status']
                        )
                        repos.append(repo)
                        self.repositories[repo.id] = repo
            except Exception as e:
                logger.error(f"Failed to list repositories: {e}")
        else:
            # Return from memory
            repos = list(self.repositories.values())
            if status:
                repos = [r for r in repos if r.status == status]
            repos = repos[:limit]
        
        return repos