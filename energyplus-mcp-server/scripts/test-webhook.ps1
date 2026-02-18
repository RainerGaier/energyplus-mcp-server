# EnergyPlus v0.4 Webhook Test Script
# Usage: .\test-webhook.ps1 [-TestMode] [-Scenario <number>]
#
# -TestMode: Use n8n test webhook URL instead of production webhook URL
# -Scenario: Skip menu and run specific scenario (1-5)

param(
    [switch]$TestMode,
    [int]$Scenario = 0
)

# Configuration
$N8N_BASE = "https://n8n.panicle.org"
$WEBHOOK_PATH = "energyplus-building"

if ($TestMode) {
    $WEBHOOK_URL = "${N8N_BASE}/webhook-test/${WEBHOOK_PATH}"
    Write-Host "`n[TEST MODE] Using n8n test webhook URL" -ForegroundColor Yellow
} else {
    $WEBHOOK_URL = "${N8N_BASE}/webhook/${WEBHOOK_PATH}"
    Write-Host "`n[PRODUCTION] Using production webhook URL" -ForegroundColor Green
}

Write-Host "Webhook URL: $WEBHOOK_URL`n" -ForegroundColor Cyan

# Define test scenarios
$scenarios = @{
    1 = @{
        Name = "Cambridge UK Data Center (Design Day)"
        Body = @{
            session_id = "Test_Cambridge-$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"
            analysis_type = "Building"
            latitude = 52.2053
            longitude = 0.1218
            location_name = "Cambridge_UK"
            project_name = "Cambridge Test Data Center"
            building_type = "manufacturing"
            data_center = @{
                rack_count = 25
                watts_per_rack = 2000
            }
            simulation = @{
                annual = $false
                design_day = $true
            }
            export = @{
                supabase = $true
                google_drive = $false
            }
        }
    }
    2 = @{
        Name = "London Office (Design Day)"
        Body = @{
            session_id = "Test_London-$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"
            analysis_type = "Building"
            latitude = 51.5074
            longitude = -0.1278
            location_name = "London_UK"
            project_name = "London Office Building"
            building_type = "manufacturing"
            data_center = @{
                rack_count = 10
                watts_per_rack = 1500
            }
            simulation = @{
                annual = $false
                design_day = $true
            }
            export = @{
                supabase = $true
                google_drive = $false
            }
        }
    }
    3 = @{
        Name = "Frankfurt DC (Annual Simulation)"
        Body = @{
            session_id = "Test_Frankfurt-$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"
            analysis_type = "Building"
            latitude = 50.1109
            longitude = 8.6821
            location_name = "Frankfurt_DE"
            project_name = "Frankfurt Data Center"
            building_type = "manufacturing"
            data_center = @{
                rack_count = 50
                watts_per_rack = 3000
            }
            simulation = @{
                annual = $true
                design_day = $false
            }
            export = @{
                supabase = $false
                google_drive = $false
            }
        }
    }
    4 = @{
        Name = "Cambridge Factory (Supabase Export)"
        Body = @{
            session_id = "Test_Cambridge-$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"
            analysis_type = "Building"
            latitude = 52.2053
            longitude = 0.1218
            location_name = "Cambridge_UK"
            project_name = "Cambridge Factory"
            building_type = "manufacturing"
            data_center = @{
                rack_count = 25
                watts_per_rack = 2000
            }
            simulation = @{
                annual = $false
                design_day = $true
            }
            export = @{
                supabase = $true
                google_drive = $false
            }
        }
    }
}

# Show menu or use provided scenario

if ($Scenario -eq 0) {
    Write-Host "========================================" -ForegroundColor White
    Write-Host " EnergyPlus v0.4 Webhook Test Scenarios" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor White
    Write-Host ""
    Write-Host "  1) Cambridge UK Data Center (Design Day)"
    Write-Host "  2) London Office (Design Day)"
    Write-Host "  3) Frankfurt DC (Annual Simulation)"
    Write-Host "  4) Cambridge Factory (Supabase Export)"
    Write-Host "  5) Custom JSON"
    Write-Host "  99) Quit"
    Write-Host ""
    $selection = Read-Host "Select scenario (1-5)"
    $Scenario = [int]$selection
}
if ($Selection -eq 99) {
	exit 0
}
if ($Scenario -ge 1 -and $Scenario -le 4) {
    $selected = $scenarios[$Scenario]
    $jsonBody = $selected.Body | ConvertTo-Json -Depth 5

    Write-Host "`nScenario: $($selected.Name)" -ForegroundColor Magenta
    Write-Host "Session ID: $($selected.Body.session_id)" -ForegroundColor Gray
    Write-Host "Analysis Type: $($selected.Body.analysis_type)" -ForegroundColor Gray
    Write-Host "Export to Supabase: $($selected.Body.export.supabase)" -ForegroundColor Gray
    Write-Host ""
}
elseif ($Scenario -eq 5) {
    Write-Host "`nEnter custom JSON body (paste and press Enter twice):" -ForegroundColor Yellow
    $lines = @()
    $emptyCount = 0
    while ($true) {
        $line = Read-Host
        if ([string]::IsNullOrEmpty($line)) {
            $emptyCount++
            if ($emptyCount -ge 1) { break }
        } else {
            $emptyCount = 0
            $lines += $line
        }
    }
    $jsonBody = $lines -join "`n"

    # Validate JSON
    try {
        $null = $jsonBody | ConvertFrom-Json
        Write-Host "JSON validated successfully." -ForegroundColor Green
    } catch {
        Write-Host "Invalid JSON! Error: $_" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "Invalid scenario. Please select 1-5." -ForegroundColor Red
    exit 1
}

# Display request
Write-Host "--- Request Body ---" -ForegroundColor DarkGray
Write-Host $jsonBody -ForegroundColor DarkGray
Write-Host "--------------------`n" -ForegroundColor DarkGray

# Send webhook request
Write-Host "Sending POST to $WEBHOOK_URL ..." -ForegroundColor Cyan
Write-Host ""

try {
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri $WEBHOOK_URL -Method POST -Body $jsonBody -ContentType "application/json" -TimeoutSec 600
    $elapsed = (Get-Date) - $startTime

    Write-Host "=== Response (${elapsed.TotalSeconds}s) ===" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host
    Write-Host ""

    # Display summary if available
    if ($response.workflow_name) {
        Write-Host "--- Summary ---" -ForegroundColor Cyan
        Write-Host "  Workflow:    $($response.workflow_name)"
        Write-Host "  Status:      $($response.status)"
        Write-Host "  Session:     $($response.session_id)"
        Write-Host "  Analysis:    $($response.analysis_type)"
        Write-Host "  Project:     $($response.project_name)"
        Write-Host "  Location:    $($response.location)"
        if ($response.supabase_export.skipped) {
            Write-Host "  Supabase:    Skipped" -ForegroundColor Yellow
        } else {
            Write-Host "  Supabase:    $($response.supabase_export.bucket)/$($response.supabase_export.folder)" -ForegroundColor Green
        }
        Write-Host "---------------" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Request failed!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red

    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "HTTP Status: $statusCode" -ForegroundColor Red

        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response Body: $responseBody" -ForegroundColor Red
        } catch {}
    }
    exit 1
}
