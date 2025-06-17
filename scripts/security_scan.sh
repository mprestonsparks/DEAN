#\!/bin/bash
set -e

echo "DEAN Repository Security Scan"
echo "============================"

# Check for secrets
echo -n "Scanning for hardcoded secrets... "
if grep -r -i -E "(password|secret|key|token)\s*=\s*['\"][^'\"]+['\"]" . \
   --exclude-dir=".git" \
   --exclude="*.template" \
   --exclude="security_scan.sh" \
   --exclude-dir="node_modules" \
   --exclude-dir="venv" 2>/dev/null; then
    echo "FAILED - Secrets found\!"
    exit 1
else
    echo "PASSED"
fi

# Check for sensitive files
echo -n "Checking for sensitive files... "
sensitive_files=(.env .env.* *.pem *.key *.crt *.p12 *.pfx)
found=0
for pattern in "${sensitive_files[@]}"; do
    if find . -name "$pattern" -not -path "./.git/*" -not -name "*.template" -not -name "*.example" 2>/dev/null | grep -q .; then
        found=1
        echo "FAILED - Found $pattern files"
    fi
done
if [ $found -eq 0 ]; then
    echo "PASSED"
fi

# Check Python dependencies for vulnerabilities
echo -n "Checking Python dependencies... "
if command -v safety &> /dev/null; then
    safety check --json || echo "WARNING - Some vulnerabilities found"
else
    echo "SKIPPED - 'safety' not installed"
fi

echo -e "\nSecurity scan complete"
EOF < /dev/null