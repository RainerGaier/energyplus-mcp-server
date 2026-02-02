# GCP VM Multi-Service Deployment Guide

**Purpose:** Deploy multiple MCP/API services on a shared GCP VM with common infrastructure.

**Last Updated:** February 2026

---

## Overview

This guide explains how to deploy the EnergyPlus MCP Server alongside existing services (QSDsan Engine) on the same GCP VM, sharing common components like Gotenberg (PDF conversion).

### Current VM Setup (qsdsan-vm)

| Service | Port | Container Name | Image |
|---------|------|----------------|-------|
| QSDsan Engine | 8080 | qsdsan-engine-mcp | gcr.io/lotsawatts/qsdsan-engine-mcp:3.0.9 |
| Gotenberg (PDF) | 3000 | gotenberg | gotenberg/gotenberg:8 |
| n8n | 5678 | n8n | n8nio/n8n:latest |

### Target Setup (with EnergyPlus)

| Service | Port | Container Name | Image |
|---------|------|----------------|-------|
| QSDsan Engine | 8080 | qsdsan-engine-mcp | gcr.io/lotsawatts/qsdsan-engine-mcp:3.0.9 |
| **EnergyPlus MCP** | **8081** | **energyplus-mcp** | **gcr.io/lotsawatts/energyplus-mcp:latest** |
| Gotenberg (PDF) | 3000 | gotenberg | gotenberg/gotenberg:8 (shared) |
| n8n | 5678 | n8n | n8nio/n8n:latest |

---

## Quick Start

For automated deployment, use the provided script:

```powershell
# From development machine (Windows PowerShell)
.\scripts\deploy-gcp.ps1

# Or with custom options
.\scripts\deploy-gcp.ps1 -SkipBuild -SkipPush
```

See [scripts/deploy-gcp.ps1](../scripts/deploy-gcp.ps1) for full automation.

---

## Project Files

The following files are used for GCP deployment:

| File | Purpose |
|------|---------|
| `Dockerfile.gcp` | Production Dockerfile optimized for GCP VM |
| `docker-compose.gcp.yaml` | Docker Compose for multi-service deployment |
| `scripts/deploy-gcp.ps1` | PowerShell deployment automation script |
| `.dockerignore` | Files to exclude from Docker build |
| `.env.example` | Environment variable template |

---

## Step 1: Build Docker Image

The production Dockerfile (`Dockerfile.gcp`) includes:
- Python 3.12-slim base image
- EnergyPlus 25.2.0 (auto-detects x86_64/arm64)
- All required system dependencies (X11 libs, Graphviz)
- uv package manager with dependencies
- Health check configuration
- Proper environment variables

### Build locally:

```powershell
# Navigate to project directory
cd C:\Users\gaierr\Energy_Projects\projects\EnergyPlus-MCP\energyplus-mcp-server

# Build the Docker image
docker build -f Dockerfile.gcp -t gcr.io/lotsawatts/energyplus-mcp:latest .

# Verify the build
docker images | findstr energyplus-mcp
```

### Test locally (optional):

```powershell
# Run container locally
docker run -d --name energyplus-test -p 8081:8081 gcr.io/lotsawatts/energyplus-mcp:latest

# Test health endpoint
curl http://localhost:8081/health

# View logs
docker logs energyplus-test

# Cleanup
docker stop energyplus-test && docker rm energyplus-test
```

---

## Step 2: Push to Google Container Registry

```powershell
# Authenticate with GCR (one-time setup)
gcloud auth configure-docker

# Push the image
docker push gcr.io/lotsawatts/energyplus-mcp:latest
```

---

## Step 3: Deploy to GCP VM

### 3.1 SSH to VM

```bash
gcloud compute ssh qsdsan-vm --zone=us-central1-a
```

### 3.2 Authenticate Docker with GCR

```bash
# Get access token (run on local machine first)
gcloud auth print-access-token

# On VM, login with token
echo "YOUR_ACCESS_TOKEN" | docker login -u oauth2accesstoken --password-stdin gcr.io
```

### 3.3 Ensure Network Exists

```bash
# Create shared network if it doesn't exist
docker network create qsdsan-network 2>/dev/null || true
```

### 3.4 Deploy Container

**Option A: Using docker run (recommended for single container)**

```bash
# Pull latest image
docker pull gcr.io/lotsawatts/energyplus-mcp:latest

# Stop and remove old container if exists
docker stop energyplus-mcp 2>/dev/null || true
docker rm energyplus-mcp 2>/dev/null || true

# Run new container
docker run -d \
  --name energyplus-mcp \
  --restart unless-stopped \
  --network qsdsan-network \
  -p 8081:8081 \
  -v energyplus_outputs:/app/outputs \
  -v energyplus_logs:/app/logs \
  -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  -e LOG_LEVEL=INFO \
  gcr.io/lotsawatts/energyplus-mcp:latest
```

**Option B: Using docker-compose**

```bash
# Copy docker-compose.gcp.yaml to VM first, then:
cd /home/gaierr
docker compose -f docker-compose.gcp.yaml pull
docker compose -f docker-compose.gcp.yaml up -d
```

### 3.5 Verify Deployment

```bash
# Check container is running
docker ps | grep energyplus-mcp

# Check health endpoint
curl http://localhost:8081/health

# View logs
docker logs energyplus-mcp --tail 50

# Check from external IP
curl http://34.28.104.162:8081/health
```

---

## Step 4: Configure Firewall (if needed)

If port 8081 isn't accessible externally:

```bash
gcloud compute firewall-rules create allow-energyplus-8081 \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8081 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=http-server
```

---

## Shared Services

### Gotenberg (PDF Conversion)

Both QSDsan and EnergyPlus can use the same Gotenberg instance:

- **Internal URL (within Docker network):** `http://gotenberg:3000`
- **External URL:** `http://34.28.104.162:3000`

Example usage in Python:

```python
import httpx

async def convert_html_to_pdf(html_content: str) -> bytes:
    """Convert HTML to PDF using shared Gotenberg service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://gotenberg:3000/forms/chromium/convert/html",
            files={"files": ("index.html", html_content, "text/html")},
            data={"marginTop": "0.5", "marginBottom": "0.5"},
        )
        return response.content
```

### OpenAI API Key

Both services can share the same `OPENAI_API_KEY` environment variable from the VM's `.env` file.

---

## Quick Reference

### Service Endpoints on VM (34.28.104.162)

| Service | Health Check | API Docs |
|---------|--------------|----------|
| QSDsan Engine | `curl http://34.28.104.162:8080/health` | `http://34.28.104.162:8080/docs` |
| EnergyPlus MCP | `curl http://34.28.104.162:8081/health` | `http://34.28.104.162:8081/docs` |
| Gotenberg | `curl http://34.28.104.162:3000/health` | N/A |
| n8n | N/A | `http://34.28.104.162:5678` |

### Container Management

```bash
# SSH to VM
gcloud compute ssh qsdsan-vm --zone=us-central1-a

# List all containers
docker ps -a

# View logs
docker logs energyplus-mcp --tail 100 -f

# Restart container
docker restart energyplus-mcp

# Stop container
docker stop energyplus-mcp

# Remove container
docker rm energyplus-mcp

# Update to new image
docker stop energyplus-mcp && docker rm energyplus-mcp
docker pull gcr.io/lotsawatts/energyplus-mcp:latest
# Then run command from Step 3.4
```

### Deployment Checklist

- [x] Create Dockerfile.gcp (production Dockerfile)
- [x] Create docker-compose.gcp.yaml
- [x] Create .dockerignore
- [x] Create .env.example
- [x] Create deployment script (scripts/deploy-gcp.ps1)
- [ ] Build Docker image locally
- [ ] Push image to GCR
- [ ] SSH to VM
- [ ] Authenticate Docker with GCR
- [ ] Update .env file if needed
- [ ] Pull and run container
- [ ] Verify health endpoint
- [ ] Configure firewall if needed
- [ ] Test from n8n workflow

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `unauthorized` when pulling image | Run `docker login` with fresh access token |
| Port already in use | Check with `docker ps`, stop conflicting container |
| Container exits immediately | Check logs with `docker logs energyplus-mcp` |
| Can't connect externally | Check firewall rules, ensure port is exposed |
| Network not found | Create network: `docker network create qsdsan-network` |
| EnergyPlus simulation fails | Check `/app/logs` in container for error details |
| Health check failing | Verify uvicorn started: `docker logs energyplus-mcp` |

### Common Log Commands

```bash
# Application logs
docker logs energyplus-mcp --tail 100

# Follow logs in real-time
docker logs energyplus-mcp -f

# Check container status
docker inspect energyplus-mcp --format='{{.State.Status}}'

# View resource usage
docker stats energyplus-mcp --no-stream
```

---

## Architecture Reference

For detailed architecture information, see:
- [Architecture Document](./ARCHITECTURE.md)
- [Development Roadmap](../roadmap/ROADMAP.md)
- [n8n Integration Guide](./n8n-integration.md)
