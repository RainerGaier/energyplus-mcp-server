<#
.SYNOPSIS
    Deploy EnergyPlus MCP Server to GCP VM

.DESCRIPTION
    This script automates the build, push, and deployment of the EnergyPlus MCP
    Server to the GCP VM (qsdsan-vm). It handles:
    - Building the Docker image from Dockerfile.gcp
    - Pushing to Google Container Registry
    - SSHing to the VM and deploying the container

.PARAMETER SkipBuild
    Skip the Docker build step (use existing local image)

.PARAMETER SkipPush
    Skip pushing to GCR (use existing remote image)

.PARAMETER SkipDeploy
    Skip VM deployment (only build and push)

.PARAMETER TestLocal
    Run container locally for testing before deployment

.PARAMETER Tag
    Docker image tag (default: latest)

.EXAMPLE
    .\deploy-gcp.ps1
    Full deployment: build, push, and deploy

.EXAMPLE
    .\deploy-gcp.ps1 -SkipBuild -SkipPush
    Deploy using existing image on GCR

.EXAMPLE
    .\deploy-gcp.ps1 -TestLocal
    Build and test locally without deploying

.NOTES
    Author: Rainer Gaier
    Date: February 2026
    Requires: Docker, gcloud CLI, PowerShell 5.1+
#>

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [switch]$SkipDeploy,
    [switch]$TestLocal,
    [string]$Tag = "latest"
)

# Configuration
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$ImageName = "gcr.io/lotsawatts/energyplus-mcp"
$ImageTag = "${ImageName}:${Tag}"
$VMName = "qsdsan-vm"
$VMZone = "us-central1-a"
$ContainerName = "energyplus-mcp"
$ContainerPort = 8081

# Colors for output
function Write-Step { param($Message) Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

# Banner
Write-Host @"

=====================================================
  EnergyPlus MCP Server - GCP Deployment Script
=====================================================
  Project: $ProjectDir
  Image:   $ImageTag
  VM:      $VMName ($VMZone)
  Port:    $ContainerPort
=====================================================

"@ -ForegroundColor Blue

# Check prerequisites
Write-Step "Checking prerequisites..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH"
    exit 1
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "gcloud CLI is not installed or not in PATH"
    exit 1
}

Write-Success "Prerequisites OK"

# Step 1: Build Docker image
if (-not $SkipBuild) {
    Write-Step "Building Docker image..."

    Push-Location $ProjectDir
    try {
        $buildCmd = "docker build -f Dockerfile.gcp -t $ImageTag ."
        Write-Host "Running: $buildCmd" -ForegroundColor Gray

        docker build -f Dockerfile.gcp -t $ImageTag .

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Docker build failed"
            exit 1
        }

        Write-Success "Docker image built: $ImageTag"

        # Show image size
        $imageInfo = docker images $ImageName --format "{{.Size}}"
        Write-Host "Image size: $imageInfo" -ForegroundColor Gray
    }
    finally {
        Pop-Location
    }
} else {
    Write-Warning "Skipping build step"
}

# Step 2: Test locally (optional)
if ($TestLocal) {
    Write-Step "Testing container locally..."

    # Stop existing test container
    docker stop energyplus-test 2>$null
    docker rm energyplus-test 2>$null

    # Run test container
    Write-Host "Starting container on port $ContainerPort..." -ForegroundColor Gray
    docker run -d --name energyplus-test -p ${ContainerPort}:${ContainerPort} $ImageTag

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start test container"
        exit 1
    }

    # Wait for container to start
    Write-Host "Waiting for container to start..." -ForegroundColor Gray
    Start-Sleep -Seconds 5

    # Test health endpoint
    Write-Host "Testing health endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$ContainerPort/health" -TimeoutSec 10
        Write-Success "Health check passed: $($response | ConvertTo-Json -Compress)"
    }
    catch {
        Write-Warning "Health check failed: $_"
        Write-Host "Container logs:" -ForegroundColor Yellow
        docker logs energyplus-test --tail 50
    }

    # Cleanup prompt
    $cleanup = Read-Host "Remove test container? (y/n)"
    if ($cleanup -eq 'y') {
        docker stop energyplus-test
        docker rm energyplus-test
        Write-Success "Test container removed"
    }

    if ($SkipDeploy) {
        Write-Host "`nLocal testing complete. Exiting." -ForegroundColor Cyan
        exit 0
    }
}

# Step 3: Push to GCR
if (-not $SkipPush) {
    Write-Step "Pushing image to Google Container Registry..."

    # Configure Docker for GCR
    Write-Host "Configuring Docker authentication..." -ForegroundColor Gray
    gcloud auth configure-docker --quiet 2>$null

    # Push image
    Write-Host "Pushing: $ImageTag" -ForegroundColor Gray
    docker push $ImageTag

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push image to GCR"
        exit 1
    }

    Write-Success "Image pushed to GCR"
} else {
    Write-Warning "Skipping push step"
}

# Step 4: Deploy to VM
if (-not $SkipDeploy) {
    Write-Step "Deploying to GCP VM ($VMName)..."

    # Get access token for VM
    Write-Host "Getting access token..." -ForegroundColor Gray
    $accessToken = gcloud auth print-access-token

    if (-not $accessToken) {
        Write-Error "Failed to get access token"
        exit 1
    }

    # Create deployment script for VM
    $vmScript = @"
#!/bin/bash
set -e

echo "==> Authenticating with GCR..."
echo "$accessToken" | docker login -u oauth2accesstoken --password-stdin gcr.io

echo "==> Creating network if needed..."
docker network create qsdsan-network 2>/dev/null || true

echo "==> Pulling latest image..."
docker pull $ImageTag

echo "==> Stopping old container..."
docker stop $ContainerName 2>/dev/null || true
docker rm $ContainerName 2>/dev/null || true

echo "==> Starting new container..."
docker run -d \
  --name $ContainerName \
  --restart unless-stopped \
  --network qsdsan-network \
  -p ${ContainerPort}:${ContainerPort} \
  -v energyplus_outputs:/app/outputs \
  -v energyplus_logs:/app/logs \
  -e OPENAI_API_KEY="\`${OPENAI_API_KEY:-}\`" \
  -e LOG_LEVEL=INFO \
  $ImageTag

echo "==> Waiting for container to start..."
sleep 5

echo "==> Checking health..."
curl -f http://localhost:$ContainerPort/health || echo "Health check pending..."

echo "==> Container status:"
docker ps | grep $ContainerName

echo "==> Deployment complete!"
"@

    # Save script temporarily
    $tempScript = [System.IO.Path]::GetTempFileName()
    $vmScript | Out-File -FilePath $tempScript -Encoding utf8 -NoNewline

    try {
        Write-Host "Connecting to VM and deploying..." -ForegroundColor Gray

        # Copy script to VM and execute
        gcloud compute scp $tempScript ${VMName}:/tmp/deploy-energyplus.sh --zone=$VMZone --quiet
        gcloud compute ssh $VMName --zone=$VMZone --command="chmod +x /tmp/deploy-energyplus.sh && /tmp/deploy-energyplus.sh"

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Deployment failed on VM"
            exit 1
        }

        Write-Success "Deployment complete!"
    }
    finally {
        Remove-Item $tempScript -ErrorAction SilentlyContinue
    }

    # Final status
    Write-Host @"

=====================================================
  Deployment Summary
=====================================================
  Container: $ContainerName
  Port:      $ContainerPort

  Endpoints:
    Health:  http://34.28.104.162:$ContainerPort/health
    API:     http://34.28.104.162:$ContainerPort/docs

  Commands:
    SSH:     gcloud compute ssh $VMName --zone=$VMZone
    Logs:    docker logs $ContainerName --tail 100
    Status:  docker ps | grep $ContainerName
=====================================================

"@ -ForegroundColor Green

} else {
    Write-Warning "Skipping deployment step"
}

Write-Host "Done!" -ForegroundColor Cyan
