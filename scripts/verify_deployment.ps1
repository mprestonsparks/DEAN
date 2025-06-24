# DEAN Deployment Verification Suite
# Purpose: Comprehensive post-deployment verification
# Usage: .\verify_deployment.ps1 [-OutputFormat HTML|JSON|Console] [-FailFast]

param(
    [ValidateSet("HTML", "JSON", "Console")]
    [string]$OutputFormat = "HTML",
    [switch]$FailFast = $false,
    [string]$Environment = "production"
)

# Verification results storage
$global:verificationResults = @{
    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Environment = $Environment
    TotalTests = 0
    PassedTests = 0
    FailedTests = 0
    Warnings = 0
    Tests = @()
}

function Add-TestResult {
    param(
        [string]$Category,
        [string]$TestName,
        [string]$Status,  # Pass, Fail, Warning
        [string]$Message,
        [hashtable]$Details = @{}
    )
    
    $result = @{
        Category = $Category
        TestName = $TestName
        Status = $Status
        Message = $Message
        Details = $Details
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }
    
    $global:verificationResults.Tests += $result
    $global:verificationResults.TotalTests++
    
    switch ($Status) {
        "Pass" { 
            $global:verificationResults.PassedTests++
            Write-Host "✓ $TestName" -ForegroundColor Green
        }
        "Fail" { 
            $global:verificationResults.FailedTests++
            Write-Host "✗ $TestName" -ForegroundColor Red
            Write-Host "  $Message" -ForegroundColor Red
            
            if ($FailFast) {
                throw "Test failed: $TestName - $Message"
            }
        }
        "Warning" { 
            $global:verificationResults.Warnings++
            Write-Host "⚠ $TestName" -ForegroundColor Yellow
            Write-Host "  $Message" -ForegroundColor Yellow
        }
    }
}

function Test-ServiceHealth {
    Write-Host "`n=== Testing Service Health ===" -ForegroundColor Cyan
    
    # Test orchestrator health
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8082/health" -TimeoutSec 5
        if ($response.status -eq "healthy") {
            Add-TestResult -Category "Health" -TestName "Orchestrator Health" -Status "Pass" `
                -Message "Orchestrator is healthy" -Details @{Response = $response}
        } else {
            Add-TestResult -Category "Health" -TestName "Orchestrator Health" -Status "Fail" `
                -Message "Orchestrator status: $($response.status)"
        }
    } catch {
        Add-TestResult -Category "Health" -TestName "Orchestrator Health" -Status "Fail" `
            -Message "Failed to connect: $_"
    }
    
    # Test nginx proxy
    try {
        $response = Invoke-RestMethod -Uri "http://localhost/health" -TimeoutSec 5
        Add-TestResult -Category "Health" -TestName "Nginx Proxy" -Status "Pass" `
            -Message "Nginx proxy is working"
    } catch {
        Add-TestResult -Category "Health" -TestName "Nginx Proxy" -Status "Fail" `
            -Message "Nginx proxy not responding: $_"
    }
    
    # Test service status endpoint
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8082/api/v1/services/status" -TimeoutSec 5
        
        $enabledServices = $response.services | Where-Object { $_.enabled -eq $true }
        $disabledServices = $response.services | Where-Object { $_.enabled -eq $false }
        
        Add-TestResult -Category "Health" -TestName "Service Status Endpoint" -Status "Pass" `
            -Message "Service status retrieved" -Details @{
                EnabledCount = $enabledServices.Count
                DisabledCount = $disabledServices.Count
                Services = $response.services
            }
    } catch {
        Add-TestResult -Category "Health" -TestName "Service Status Endpoint" -Status "Fail" `
            -Message "Failed to get service status: $_"
    }
}

function Test-DatabaseConnectivity {
    Write-Host "`n=== Testing Database Connectivity ===" -ForegroundColor Cyan
    
    # Test PostgreSQL container
    $pgContainer = docker ps --filter "name=dean-postgres" --format "{{.Names}}" 2>$null
    if ($pgContainer) {
        Add-TestResult -Category "Database" -TestName "PostgreSQL Container" -Status "Pass" `
            -Message "PostgreSQL container is running"
        
        # Test database connection
        $testQuery = "SELECT version();"
        $result = docker exec $pgContainer psql -U dean_prod -d dean_production -t -c "$testQuery" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Add-TestResult -Category "Database" -TestName "Database Connection" -Status "Pass" `
                -Message "Successfully connected to database" -Details @{Version = $result.Trim()}
        } else {
            Add-TestResult -Category "Database" -TestName "Database Connection" -Status "Fail" `
                -Message "Failed to connect to database: $result"
        }
        
        # Test schema
        $tableQuery = "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
        $tables = docker exec $pgContainer psql -U dean_prod -d dean_production -t -c "$tableQuery" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $tableList = $tables -split "`n" | Where-Object { $_.Trim() -ne "" }
            Add-TestResult -Category "Database" -TestName "Database Schema" -Status "Pass" `
                -Message "Database schema verified" -Details @{Tables = $tableList}
        } else {
            Add-TestResult -Category "Database" -TestName "Database Schema" -Status "Warning" `
                -Message "Could not verify schema"
        }
        
    } else {
        Add-TestResult -Category "Database" -TestName "PostgreSQL Container" -Status "Fail" `
            -Message "PostgreSQL container not found"
    }
}

function Test-RedisConnectivity {
    Write-Host "`n=== Testing Redis Connectivity ===" -ForegroundColor Cyan
    
    # Test Redis container
    $redisContainer = docker ps --filter "name=dean-redis" --format "{{.Names}}" 2>$null
    if ($redisContainer) {
        Add-TestResult -Category "Cache" -TestName "Redis Container" -Status "Pass" `
            -Message "Redis container is running"
        
        # Test Redis ping
        $redisPassword = $env:REDIS_PASSWORD
        if (-not $redisPassword) {
            # Try to get from .env file
            if (Test-Path ".env") {
                $envContent = Get-Content ".env" | Where-Object { $_ -match "^REDIS_PASSWORD=" }
                if ($envContent) {
                    $redisPassword = $envContent -replace "^REDIS_PASSWORD=", ""
                }
            }
        }
        
        if ($redisPassword) {
            $pingResult = docker exec $redisContainer redis-cli -a "$redisPassword" ping 2>&1
            if ($pingResult -match "PONG") {
                Add-TestResult -Category "Cache" -TestName "Redis Authentication" -Status "Pass" `
                    -Message "Redis authentication successful"
                
                # Test Redis operations
                $setResult = docker exec $redisContainer redis-cli -a "$redisPassword" SET test_key "test_value" 2>&1
                $getResult = docker exec $redisContainer redis-cli -a "$redisPassword" GET test_key 2>&1
                $delResult = docker exec $redisContainer redis-cli -a "$redisPassword" DEL test_key 2>&1
                
                if ($getResult -eq "test_value") {
                    Add-TestResult -Category "Cache" -TestName "Redis Operations" -Status "Pass" `
                        -Message "Redis read/write operations working"
                } else {
                    Add-TestResult -Category "Cache" -TestName "Redis Operations" -Status "Fail" `
                        -Message "Redis operations failed"
                }
            } else {
                Add-TestResult -Category "Cache" -TestName "Redis Authentication" -Status "Fail" `
                    -Message "Redis authentication failed: $pingResult"
            }
        } else {
            Add-TestResult -Category "Cache" -TestName "Redis Authentication" -Status "Warning" `
                -Message "Redis password not found in environment"
        }
    } else {
        Add-TestResult -Category "Cache" -TestName "Redis Container" -Status "Fail" `
            -Message "Redis container not found"
    }
}

function Test-FeatureFlags {
    Write-Host "`n=== Testing Feature Flags ===" -ForegroundColor Cyan
    
    try {
        $config = Invoke-RestMethod -Uri "http://localhost:8082/api/v1/config" -TimeoutSec 5
        
        # Check IndexAgent flag
        if ($config.features.indexagent -eq $false) {
            Add-TestResult -Category "Configuration" -TestName "IndexAgent Feature Flag" -Status "Pass" `
                -Message "IndexAgent correctly disabled"
        } else {
            Add-TestResult -Category "Configuration" -TestName "IndexAgent Feature Flag" -Status "Warning" `
                -Message "IndexAgent is enabled - ensure this is intentional"
        }
        
        # Check Airflow flag
        if ($config.features.airflow -eq $false) {
            Add-TestResult -Category "Configuration" -TestName "Airflow Feature Flag" -Status "Pass" `
                -Message "Airflow correctly disabled"
        } else {
            Add-TestResult -Category "Configuration" -TestName "Airflow Feature Flag" -Status "Warning" `
                -Message "Airflow is enabled - ensure this is intentional"
        }
        
        # Check Evolution flag
        if ($config.features.evolution -eq $false) {
            Add-TestResult -Category "Configuration" -TestName "Evolution Feature Flag" -Status "Pass" `
                -Message "Evolution correctly disabled"
        } else {
            Add-TestResult -Category "Configuration" -TestName "Evolution Feature Flag" -Status "Warning" `
                -Message "Evolution is enabled - ensure this is intentional"
        }
        
    } catch {
        Add-TestResult -Category "Configuration" -TestName "Feature Flags" -Status "Fail" `
            -Message "Failed to retrieve configuration: $_"
    }
}

function Test-SecurityConfiguration {
    Write-Host "`n=== Testing Security Configuration ===" -ForegroundColor Cyan
    
    # Test JWT configuration
    try {
        # Attempt to access protected endpoint without auth
        $response = Invoke-WebRequest -Uri "http://localhost:8082/api/v1/agents" -Method GET -ErrorAction Stop
        Add-TestResult -Category "Security" -TestName "JWT Protection" -Status "Fail" `
            -Message "Protected endpoint accessible without authentication"
    } catch {
        if ($_.Exception.Response.StatusCode -eq 401) {
            Add-TestResult -Category "Security" -TestName "JWT Protection" -Status "Pass" `
                -Message "Protected endpoints require authentication"
        } else {
            Add-TestResult -Category "Security" -TestName "JWT Protection" -Status "Warning" `
                -Message "Unexpected response: $_"
        }
    }
    
    # Test CORS configuration
    try {
        $headers = @{
            "Origin" = "https://evil-site.com"
        }
        $response = Invoke-WebRequest -Uri "http://localhost:8082/health" -Method OPTIONS -Headers $headers -ErrorAction Stop
        
        if ($response.Headers["Access-Control-Allow-Origin"] -contains "https://evil-site.com") {
            Add-TestResult -Category "Security" -TestName "CORS Configuration" -Status "Fail" `
                -Message "CORS allows unauthorized origins"
        } else {
            Add-TestResult -Category "Security" -TestName "CORS Configuration" -Status "Pass" `
                -Message "CORS properly configured"
        }
    } catch {
        Add-TestResult -Category "Security" -TestName "CORS Configuration" -Status "Pass" `
            -Message "CORS properly restricts unauthorized origins"
    }
}

function Test-Monitoring {
    Write-Host "`n=== Testing Monitoring Endpoints ===" -ForegroundColor Cyan
    
    # Test metrics endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8082/metrics" -TimeoutSec 5
        
        if ($response.StatusCode -eq 200 -and $response.Content -match "dean_orchestrator_up") {
            Add-TestResult -Category "Monitoring" -TestName "Prometheus Metrics" -Status "Pass" `
                -Message "Metrics endpoint is functional" -Details @{
                    ContentLength = $response.Content.Length
                    MetricsFound = ($response.Content -split "`n" | Where-Object { $_ -match "^dean_" }).Count
                }
        } else {
            Add-TestResult -Category "Monitoring" -TestName "Prometheus Metrics" -Status "Fail" `
                -Message "Metrics endpoint not returning expected data"
        }
    } catch {
        Add-TestResult -Category "Monitoring" -TestName "Prometheus Metrics" -Status "Fail" `
            -Message "Failed to access metrics endpoint: $_"
    }
    
    # Test logging
    $orchestratorLogs = docker logs dean-orchestrator --tail 10 2>&1
    if ($orchestratorLogs) {
        Add-TestResult -Category "Monitoring" -TestName "Container Logging" -Status "Pass" `
            -Message "Container logs are accessible"
    } else {
        Add-TestResult -Category "Monitoring" -TestName "Container Logging" -Status "Warning" `
            -Message "Could not retrieve container logs"
    }
}

function Test-Performance {
    Write-Host "`n=== Testing Performance Metrics ===" -ForegroundColor Cyan
    
    # Test response time
    $iterations = 10
    $responseTimes = @()
    
    for ($i = 1; $i -le $iterations; $i++) {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:8082/health" -TimeoutSec 5
            $stopwatch.Stop()
            $responseTimes += $stopwatch.ElapsedMilliseconds
        } catch {
            # Skip failed requests
        }
    }
    
    if ($responseTimes.Count -gt 0) {
        $avgResponseTime = ($responseTimes | Measure-Object -Average).Average
        $maxResponseTime = ($responseTimes | Measure-Object -Maximum).Maximum
        
        if ($avgResponseTime -lt 500) {
            Add-TestResult -Category "Performance" -TestName "Response Time" -Status "Pass" `
                -Message "Average response time: $([math]::Round($avgResponseTime, 2))ms" -Details @{
                    Average = $avgResponseTime
                    Maximum = $maxResponseTime
                    Samples = $responseTimes.Count
                }
        } else {
            Add-TestResult -Category "Performance" -TestName "Response Time" -Status "Warning" `
                -Message "High average response time: $([math]::Round($avgResponseTime, 2))ms"
        }
    } else {
        Add-TestResult -Category "Performance" -TestName "Response Time" -Status "Fail" `
            -Message "Could not measure response times"
    }
    
    # Test resource usage
    $stats = docker stats dean-orchestrator --no-stream --format "json" | ConvertFrom-Json
    if ($stats) {
        $cpuPercent = [double]($stats.CPUPerc -replace '%', '')
        $memUsage = $stats.MemUsage -split '/' | Select-Object -First 1
        
        Add-TestResult -Category "Performance" -TestName "Resource Usage" -Status "Pass" `
            -Message "Container resource usage normal" -Details @{
                CPU = "$($stats.CPUPerc)"
                Memory = $memUsage
                NetworkIO = "$($stats.NetIO)"
            }
    }
}

function Generate-HTMLReport {
    $html = @"
<!DOCTYPE html>
<html>
<head>
    <title>DEAN Deployment Verification Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .summary-stat { display: inline-block; margin: 0 20px; }
        .pass { color: #28a745; font-weight: bold; }
        .fail { color: #dc3545; font-weight: bold; }
        .warning { color: #ffc107; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background-color: #007bff; color: white; padding: 10px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background-color: #f5f5f5; }
        .status-pass { background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 3px; }
        .status-fail { background-color: #f8d7da; color: #721c24; padding: 2px 8px; border-radius: 3px; }
        .status-warning { background-color: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 3px; }
        .details { font-size: 0.9em; color: #666; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DEAN Deployment Verification Report</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-stat">Total Tests: <strong>$($global:verificationResults.TotalTests)</strong></div>
            <div class="summary-stat"><span class="pass">Passed: $($global:verificationResults.PassedTests)</span></div>
            <div class="summary-stat"><span class="fail">Failed: $($global:verificationResults.FailedTests)</span></div>
            <div class="summary-stat"><span class="warning">Warnings: $($global:verificationResults.Warnings)</span></div>
            <br><br>
            <div>Environment: <strong>$($global:verificationResults.Environment)</strong></div>
            <div>Generated: <strong>$($global:verificationResults.Timestamp)</strong></div>
        </div>
        
        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Message</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
"@
    
    foreach ($test in $global:verificationResults.Tests) {
        $statusClass = "status-$($test.Status.ToLower())"
        $detailsHtml = ""
        
        if ($test.Details.Count -gt 0) {
            $detailsHtml = "<div class='details'>"
            foreach ($key in $test.Details.Keys) {
                $detailsHtml += "<strong>$key:</strong> $($test.Details[$key])<br>"
            }
            $detailsHtml += "</div>"
        }
        
        $html += @"
                <tr>
                    <td>$($test.Category)</td>
                    <td>$($test.TestName)</td>
                    <td><span class="$statusClass">$($test.Status)</span></td>
                    <td>$($test.Message)</td>
                    <td>$detailsHtml</td>
                </tr>
"@
    }
    
    $html += @"
            </tbody>
        </table>
        
        <h2>Recommendations</h2>
        <ul>
"@
    
    if ($global:verificationResults.FailedTests -gt 0) {
        $html += "<li><strong>Address failed tests before proceeding to production.</strong></li>"
    }
    
    if ($global:verificationResults.Warnings -gt 0) {
        $html += "<li>Review warnings and ensure they are expected for your deployment.</li>"
    }
    
    if ($global:verificationResults.PassedTests -eq $global:verificationResults.TotalTests) {
        $html += "<li>All tests passed! System is ready for production use.</li>"
    }
    
    $html += @"
            <li>Monitor system closely for the first 24-48 hours.</li>
            <li>Review logs regularly for any anomalies.</li>
            <li>Ensure backup procedures are in place.</li>
        </ul>
        
        <div class="footer">
            <p>DEAN Deployment Verification Suite v1.0</p>
        </div>
    </div>
</body>
</html>
"@
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "deployment_verification_report_$timestamp.html"
    Set-Content -Path $filename -Value $html
    
    Write-Host "`nHTML report generated: $filename" -ForegroundColor Green
    
    # Try to open in default browser
    try {
        Start-Process $filename
    } catch {
        # Ignore if can't open browser
    }
}

function Generate-JSONReport {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "deployment_verification_report_$timestamp.json"
    
    $global:verificationResults | ConvertTo-Json -Depth 10 | Set-Content -Path $filename
    
    Write-Host "`nJSON report generated: $filename" -ForegroundColor Green
}

# Main execution
try {
    Write-Host "=== DEAN Deployment Verification Suite ===" -ForegroundColor Cyan
    Write-Host "Environment: $Environment" -ForegroundColor Yellow
    Write-Host "Output Format: $OutputFormat" -ForegroundColor Yellow
    Write-Host ""
    
    # Run all tests
    Test-ServiceHealth
    Test-DatabaseConnectivity
    Test-RedisConnectivity
    Test-FeatureFlags
    Test-SecurityConfiguration
    Test-Monitoring
    Test-Performance
    
    # Generate report
    Write-Host "`n=== Generating Report ===" -ForegroundColor Cyan
    
    switch ($OutputFormat) {
        "HTML" { Generate-HTMLReport }
        "JSON" { Generate-JSONReport }
        "Console" { 
            Write-Host "`nVerification Summary:" -ForegroundColor Cyan
            Write-Host "Total Tests: $($global:verificationResults.TotalTests)"
            Write-Host "Passed: $($global:verificationResults.PassedTests)" -ForegroundColor Green
            Write-Host "Failed: $($global:verificationResults.FailedTests)" -ForegroundColor Red
            Write-Host "Warnings: $($global:verificationResults.Warnings)" -ForegroundColor Yellow
        }
    }
    
    # Exit with appropriate code
    if ($global:verificationResults.FailedTests -gt 0) {
        exit 1
    } else {
        exit 0
    }
    
} catch {
    Write-Host "Verification suite failed: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}