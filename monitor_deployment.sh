#!/bin/bash
# Monitor DEAN deployment on Windows PC

echo "=== DEAN Deployment Monitor ==="
echo "Press Ctrl+C to exit"

while true; do
    clear
    echo "DEAN Deployment Status - $(date)"
    echo "================================"
    
    # Get container status
    echo -e "\nContainer Status:"
    ssh deployer@10.7.0.2 "powershell.exe -Command 'docker ps --filter name=dean --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\"'" 2>/dev/null
    
    echo -e "\nHealth Checks:"
    # Check orchestrator
    ssh deployer@10.7.0.2 "powershell.exe -Command 'try { Invoke-WebRequest -Uri \"http://localhost:8082/health\" -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host \"✓ Orchestrator API: Healthy\" } catch { Write-Host \"✗ Orchestrator API: Down\" }'" 2>/dev/null
    
    # Check nginx
    ssh deployer@10.7.0.2 "powershell.exe -Command 'try { Invoke-WebRequest -Uri \"https://localhost\" -UseBasicParsing -TimeoutSec 2 -SkipCertificateCheck | Out-Null; Write-Host \"✓ Nginx HTTPS: Healthy\" } catch { Write-Host \"✗ Nginx HTTPS: Down\" }'" 2>/dev/null
    
    sleep 5
done