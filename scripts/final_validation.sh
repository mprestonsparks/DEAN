#\!/bin/bash
set -e

echo "DEAN Repository Final Validation"
echo "==============================="

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
    else
        echo "✗ Missing: $1"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo "✓ $1/"
    else
        echo "✗ Missing: $1/"
        return 1
    fi
}

echo -e "\nChecking core files..."
check_file "README.md"
check_file "LICENSE.md"
check_file "docker-compose.prod.yml"
check_file ".env.production.template"
check_file "deploy_windows.ps1"

echo -e "\nChecking documentation..."
check_file "docs/deployment/SECURITY_CHECKLIST.md"

echo -e "\nChecking directories..."
check_dir "src"
check_dir "scripts"
check_dir "docs"

echo -e "\nRepository validation complete!"