#!/usr/bin/env python3
"""
File path verification tool for DEAN orchestration system.

Scans all files for path references and verifies they exist.
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Set
import json
from collections import defaultdict

# Try to import yaml, but make it optional
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Path patterns to check
PATH_PATTERNS = {
    'python_import': re.compile(r'(?:from|import)\s+([a-zA-Z_][\w.]*)', re.MULTILINE),
    'file_operation': re.compile(r'(?:open|Path|read_text|write_text|exists|mkdir|glob)\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE),
    'static_file': re.compile(r'(?:src|href|url)\s*[=:]\s*["\']/?([^"\']+\.[a-zA-Z]+)["\']', re.MULTILINE),
    'config_reference': re.compile(r'["\']([^"\']+\.(?:yaml|yml|json|toml|ini))["\']', re.MULTILINE),
    'dockerfile': re.compile(r'(?:COPY|ADD|WORKDIR|RUN.*?cp)\s+([^\s]+)', re.MULTILINE),
}

class PathVerifier:
    """Verifies file paths across the DEAN codebase."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.issues = []
        self.verified_paths = []
        self.file_inventory = defaultdict(list)
        
    def scan_directory(self, start_path: Path = None) -> Dict[str, List[Tuple[str, str, str]]]:
        """Scan directory for all file path references."""
        if start_path is None:
            start_path = self.root_dir
            
        references = defaultdict(list)
        
        for file_path in start_path.rglob('*'):
            if file_path.is_file() and not self._should_skip(file_path):
                self._scan_file(file_path, references)
                
        return references
        
    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        skip_extensions = {'.pyc', '.pyo', '.so', '.dylib', '.dll'}
        
        # Skip if in ignored directory
        for part in file_path.parts:
            if part in skip_dirs:
                return True
                
        # Skip binary files
        if file_path.suffix in skip_extensions:
            return True
            
        return False
        
    def _scan_file(self, file_path: Path, references: Dict) -> None:
        """Scan a single file for path references."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return  # Skip files that can't be read as text
            
        relative_path = file_path.relative_to(self.root_dir)
        
        # Check Python imports
        if file_path.suffix == '.py':
            self._check_python_imports(file_path, content, references)
            
        # Check all patterns
        for pattern_name, pattern in PATH_PATTERNS.items():
            if pattern_name == 'python_import' and file_path.suffix != '.py':
                continue
                
            for match in pattern.finditer(content):
                path_ref = match.group(1)
                references[pattern_name].append((str(relative_path), path_ref, match.group(0)))
                
    def _check_python_imports(self, file_path: Path, content: str, references: Dict) -> None:
        """Check Python import statements."""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        references['python_import'].append(
                            (str(file_path.relative_to(self.root_dir)), alias.name, f"import {alias.name}")
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        full_import = f"{module}.{alias.name}" if module else alias.name
                        references['python_import'].append(
                            (str(file_path.relative_to(self.root_dir)), full_import, f"from {module} import {alias.name}")
                        )
        except SyntaxError:
            pass  # Skip files with syntax errors
            
    def verify_references(self, references: Dict) -> List[Dict]:
        """Verify that referenced paths exist."""
        issues = []
        
        for ref_type, refs in references.items():
            for source_file, path_ref, context in refs:
                if ref_type == 'python_import':
                    if not self._verify_python_import(path_ref):
                        issues.append({
                            'type': ref_type,
                            'source': source_file,
                            'reference': path_ref,
                            'context': context,
                            'issue': 'Import not found'
                        })
                else:
                    resolved_path = self._resolve_path(source_file, path_ref)
                    if resolved_path and not resolved_path.exists():
                        issues.append({
                            'type': ref_type,
                            'source': source_file,
                            'reference': path_ref,
                            'context': context,
                            'issue': f'File not found: {resolved_path}'
                        })
                        
        return issues
        
    def _verify_python_import(self, import_path: str) -> bool:
        """Verify Python import path."""
        # Check if it's a standard library or third-party import
        parts = import_path.split('.')
        
        # Common standard library and third-party modules to skip
        skip_modules = {
            'os', 'sys', 'json', 'yaml', 're', 'ast', 'pathlib', 'typing',
            'collections', 'datetime', 'asyncio', 'aiohttp', 'fastapi',
            'pydantic', 'structlog', 'rich', 'click', 'pytest', 'psycopg2',
            'redis', 'requests', 'uvicorn', 'numpy', 'pandas', 'gzip',
            'hashlib', 'argparse'
        }
        
        if parts[0] in skip_modules:
            return True
            
        # Check if it's a relative import within the project
        if parts[0] in ['dean_orchestration', 'src']:
            # Try to find the module
            module_path = self.root_dir / 'src' / parts[0].replace('.', '/')
            return module_path.exists() or (module_path.with_suffix('.py')).exists()
            
        # For other imports, assume they're valid if we can't verify
        return True
        
    def _resolve_path(self, source_file: str, path_ref: str) -> Path:
        """Resolve a path reference relative to source file."""
        source_path = self.root_dir / source_file
        source_dir = source_path.parent
        
        # Try different resolution strategies
        candidates = [
            self.root_dir / path_ref,  # Absolute from project root
            source_dir / path_ref,      # Relative to source file
            self.root_dir / 'src' / path_ref,  # Relative to src
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
                
        # Return the most likely candidate for error reporting
        if path_ref.startswith('/'):
            return Path(path_ref)
        elif path_ref.startswith('./') or path_ref.startswith('../'):
            return source_dir / path_ref
        else:
            return self.root_dir / path_ref
            
    def create_file_inventory(self) -> Dict[str, List[str]]:
        """Create inventory of all files in the project."""
        inventory = defaultdict(list)
        
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file() and not self._should_skip(file_path):
                relative_path = file_path.relative_to(self.root_dir)
                extension = file_path.suffix
                
                if extension:
                    inventory[extension].append(str(relative_path))
                else:
                    inventory['no_extension'].append(str(relative_path))
                    
        return inventory
        
    def generate_report(self, output_file: Path = None) -> str:
        """Generate verification report."""
        references = self.scan_directory()
        issues = self.verify_references(references)
        inventory = self.create_file_inventory()
        
        report = []
        report.append("# DEAN File Path Verification Report")
        report.append(f"\nGenerated: {Path(__file__).stat().st_mtime}")
        report.append(f"Root Directory: {self.root_dir}")
        
        # Summary
        report.append("\n## Summary")
        report.append(f"- Total files scanned: {sum(len(files) for files in inventory.values())}")
        report.append(f"- Total references found: {sum(len(refs) for refs in references.values())}")
        report.append(f"- Issues found: {len(issues)}")
        
        # Issues
        if issues:
            report.append("\n## Issues Found")
            
            issues_by_type = defaultdict(list)
            for issue in issues:
                issues_by_type[issue['type']].append(issue)
                
            for issue_type, type_issues in issues_by_type.items():
                report.append(f"\n### {issue_type.replace('_', ' ').title()}")
                for issue in type_issues:
                    report.append(f"\n**Source**: `{issue['source']}`")
                    report.append(f"**Reference**: `{issue['reference']}`")
                    report.append(f"**Context**: `{issue['context']}`")
                    report.append(f"**Issue**: {issue['issue']}")
        else:
            report.append("\n## No Issues Found")
            report.append("All file path references are valid.")
            
        # File Inventory
        report.append("\n## File Inventory by Extension")
        for ext, files in sorted(inventory.items()):
            report.append(f"\n### {ext} ({len(files)} files)")
            if len(files) <= 20:
                for file in sorted(files)[:5]:
                    report.append(f"- {file}")
                if len(files) > 5:
                    report.append(f"- ... and {len(files) - 5} more")
                    
        # Reference Statistics
        report.append("\n## Reference Statistics")
        for ref_type, refs in references.items():
            report.append(f"- {ref_type.replace('_', ' ').title()}: {len(refs)} references")
            
        report_text = '\n'.join(report)
        
        if output_file:
            output_file.write_text(report_text)
            
        return report_text


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify file paths in DEAN codebase")
    parser.add_argument('--root', type=Path, default=Path(__file__).parent.parent.parent,
                       help='Root directory to scan')
    parser.add_argument('--output', type=Path, help='Output report file')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    
    args = parser.parse_args()
    
    verifier = PathVerifier(args.root)
    
    if args.json:
        references = verifier.scan_directory()
        issues = verifier.verify_references(references)
        inventory = verifier.create_file_inventory()
        
        output = {
            'root_directory': str(verifier.root_dir),
            'summary': {
                'files_scanned': sum(len(files) for files in inventory.values()),
                'references_found': sum(len(refs) for refs in references.values()),
                'issues_found': len(issues)
            },
            'issues': issues,
            'inventory': inventory,
            'references': {k: len(v) for k, v in references.items()}
        }
        
        print(json.dumps(output, indent=2))
    else:
        report = verifier.generate_report(args.output)
        
        if not args.output:
            print(report)
        else:
            print(f"Report saved to: {args.output}")
            
        # Exit with error code if issues found
        references = verifier.scan_directory()
        issues = verifier.verify_references(references)
        sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()