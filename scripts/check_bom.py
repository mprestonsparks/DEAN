#!/usr/bin/env python3
"""
Check for Byte Order Mark (BOM) in configuration files.
BOM characters can cause parsing failures in configuration files.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# BOM signatures for different encodings
BOM_SIGNATURES = {
    b'\xef\xbb\xbf': 'UTF-8 BOM',
    b'\xff\xfe': 'UTF-16 LE BOM',
    b'\xfe\xff': 'UTF-16 BE BOM',
    b'\xff\xfe\x00\x00': 'UTF-32 LE BOM',
    b'\x00\x00\xfe\xff': 'UTF-32 BE BOM'
}

# File extensions to check
CONFIG_EXTENSIONS = {
    '.yml', '.yaml', '.json', '.env', '.conf', '.cfg', '.ini', 
    '.properties', '.xml', '.toml', '.sh', '.ps1', '.py', '.js',
    '.md', '.txt', '.sql'
}

def has_bom(file_path: Path) -> Tuple[bool, str]:
    """
    Check if a file has a BOM.
    
    Returns:
        Tuple of (has_bom, bom_type)
    """
    try:
        with open(file_path, 'rb') as f:
            # Read first 4 bytes (longest BOM is 4 bytes)
            start = f.read(4)
            
            # Check each BOM signature
            for bom_bytes, bom_type in BOM_SIGNATURES.items():
                if start.startswith(bom_bytes):
                    return True, bom_type
                    
        return False, ""
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, ""

def remove_bom(file_path: Path, bom_type: str) -> bool:
    """
    Remove BOM from a file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Determine BOM length
        bom_length = 0
        for bom_bytes, bt in BOM_SIGNATURES.items():
            if bt == bom_type and content.startswith(bom_bytes):
                bom_length = len(bom_bytes)
                break
        
        if bom_length == 0:
            return False
        
        # Write content without BOM
        with open(file_path, 'wb') as f:
            f.write(content[bom_length:])
        
        return True
    except Exception as e:
        print(f"Error removing BOM from {file_path}: {e}")
        return False

def find_files_with_bom(root_dir: Path, fix: bool = False) -> List[Tuple[Path, str]]:
    """
    Find all configuration files with BOM in the given directory.
    
    Args:
        root_dir: Root directory to search
        fix: If True, remove BOM from files
        
    Returns:
        List of (file_path, bom_type) tuples
    """
    files_with_bom = []
    
    # Directories to skip
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache'}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Check if file has a config extension or no extension (like Dockerfile)
            if file_path.suffix in CONFIG_EXTENSIONS or (not file_path.suffix and file_path.name not in ['LICENSE']):
                has_bom_flag, bom_type = has_bom(file_path)
                
                if has_bom_flag:
                    files_with_bom.append((file_path, bom_type))
                    print(f"Found BOM ({bom_type}) in: {file_path}")
                    
                    if fix:
                        if remove_bom(file_path, bom_type):
                            print(f"  ✓ Removed BOM from {file_path}")
                        else:
                            print(f"  ✗ Failed to remove BOM from {file_path}")
    
    return files_with_bom

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check and fix BOM in configuration files")
    parser.add_argument('--fix', action='store_true', help='Remove BOM from files')
    parser.add_argument('--path', default='.', help='Path to check (default: current directory)')
    
    args = parser.parse_args()
    
    root_path = Path(args.path).resolve()
    print(f"Checking for BOM in configuration files under: {root_path}\n")
    
    files_with_bom = find_files_with_bom(root_path, fix=args.fix)
    
    if files_with_bom:
        print(f"\n{'Fixed' if args.fix else 'Found'} {len(files_with_bom)} file(s) with BOM")
        if not args.fix:
            print("\nTo remove BOM from these files, run:")
            print(f"  {sys.argv[0]} --fix")
        return 1
    else:
        print("✓ No files with BOM found")
        return 0

if __name__ == "__main__":
    sys.exit(main())