"""Main entry point for the DEAN CLI command.

This module serves as the primary entry point for the `dean` command
as specified in pyproject.toml. It imports and delegates to the
interactive CLI implementation.
"""

import sys
from typing import Optional

# Import the actual CLI implementation
from ..interfaces.cli.dean_cli import cli as dean_cli


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the dean command.
    
    Args:
        args: Command line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Pass through to the Click CLI
        return dean_cli(args or sys.argv[1:], standalone_mode=False) or 0
    except SystemExit as e:
        # Click raises SystemExit, extract the code
        return e.code if isinstance(e.code, int) else 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())