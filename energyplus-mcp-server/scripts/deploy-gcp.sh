#!/bin/bash
# =============================================================================
# EnergyPlus MCP Server - GCP Deployment Script (Bash)
# =============================================================================
#
# Usage:
#   ./deploy-gcp.sh              # Full deployment
#   ./deploy-gcp.sh --skip-build # Skip Docker build
#   ./deploy-gcp.sh --skip-push  # Skip GCR push
#   ./deploy-gcp.sh --test-local # Test locally before deploy
#   ./deploy-gcp.sh --help       # Show help
#
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="gcr.io/lotsawatts/energyplus-mcp"
IMAGE_TAG="${IMAGE_NAME}:latest"
VM_NAME="qsdsan-vm"
VM_ZONE="us-central1-a"
CONTAINER_NAME="energyplus-mcp"
CONTAINER_PORT=8081

# Flags
SKIP_BUILD=false
SKIP_PUSH=false
SKIP_DEPLOY=false
TEST_LOCAL=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
step() { echo -e "\n${CYAN}==> $1${NC}"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

show_help() {
    cat << EOF
EnergyPlus MCP Server - GCP Deployment Script

Usage: $(basename "$0") [OPTIONS]

Options:
    --skip-build    Skip Docker build (use existing local image)
    --skip-push     Skip pushing to GCR
    --skip-deploy   Skip VM deployment (only build and push)
    --test-local    Test container locally before deployment
    --tag TAG       Docker image tag (default: latest)
    --help          Show this help message

Examples:
    $(basename "$0")                    # Full deployment
    $(basename "$0") --skip-build       # Deploy using existing image
    $(basename "$0") --test-local       # Test locally first
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --skip-push) SKIP_PUSH=true; shift ;;
        --skip-deploy) SKIP_DEPLOY=true; shift ;;
        --test-local) TEST_LOCAL=true; shift ;;
        --tag) IMAGE_TAG="${IMAGE_NAME}:$2"; shift 2 ;;
        --help|-h) show_help ;;
        *) error "Unknown option: $1" ;;
    esac
done

# Banner
echo -e "${BLUE}"
cat << 'EOF'
=====================================================
  EnergyPlus MCP Server - GCP Deployment Script
=====================================================
EOF
echo -e "  Project: ${PROJECT_DIR}"
echo -e "  Image:   ${IMAGE_TAG}"
echo -e "  VM:      ${VM_NAME} (${VM_ZONE})"
echo -e "  Port:    ${CONTAINER_PORT}"
echo -e "====================================================="
echo -e "${NC}"

# Check prerequisites
step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
fi

if ! command -v gcloud &> /dev/null; then
    error "gcloud CLI is not installed or not in PATH"
fi

success "Prerequisites OK"

# Step 1: Build Docker image
if [ "$SKIP_BUILD" = false ]; then
    step "Building Docker image..."

    cd "$PROJECT_DIR"
    echo "Running: docker build -f Dockerfile.gcp -t $IMAGE_TAG ."

    docker build -f Dockerfile.gcp -t "$IMAGE_TAG" .

    success "Docker image built: $IMAGE_TAG"

    # Show image size
    docker images "$IMAGE_NAME" --format "Image size: {{.Size}}"
else
    warn "Skipping build step"
fi

# Step 2: Test locally (optional)
if [ "$TEST_LOCAL" = true ]; then
    step "Testing container locally..."

    # Stop existing test container
    docker stop energyplus-test 2>/dev/null || true
    docker rm energyplus-test 2>/dev/null || true

    # Run test container
    echo "Starting container on port $CONTAINER_PORT..."
    docker run -d --name energyplus-test -p "${CONTAINER_PORT}:${CONTAINER_PORT}" "$IMAGE_TAG"

    # Wait for container to start
    echo "Waiting for container to start..."
    sleep 5

    # Test health endpoint
    echo "Testing health endpoint..."
    if curl -sf "http://localhost:$CONTAINER_PORT/health"; then
        echo ""
        success "Health check passed"
    else
        warn "Health check failed"
        echo "Container logs:"
        docker logs energyplus-test --tail 50
    fi

    # Cleanup prompt
    read -p "Remove test container? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop energyplus-test
        docker rm energyplus-test
        success "Test container removed"
    fi

    if [ "$SKIP_DEPLOY" = true ]; then
        echo -e "\n${CYAN}Local testing complete. Exiting.${NC}"
        exit 0
    fi
fi

# Step 3: Push to GCR
if [ "$SKIP_PUSH" = false ]; then
    step "Pushing image to Google Container Registry..."

    # Configure Docker for GCR
    echo "Configuring Docker authentication..."
    gcloud auth configure-docker --quiet 2>/dev/null

    # Push image
    echo "Pushing: $IMAGE_TAG"
    docker push "$IMAGE_TAG"

    success "Image pushed to GCR"
else
    warn "Skipping push step"
fi

# Step 4: Deploy to VM
if [ "$SKIP_DEPLOY" = false ]; then
    step "Deploying to GCP VM ($VM_NAME)..."

    # Get access token for VM
    echo "Getting access token..."
    ACCESS_TOKEN=$(gcloud auth print-access-token)

    if [ -z "$ACCESS_TOKEN" ]; then
        error "Failed to get access token"
    fi

    # Create deployment script for VM
    cat << VMSCRIPT > /tmp/deploy-energyplus.sh
#!/bin/bash
set -e

echo "==> Authenticating with GCR..."
echo "$ACCESS_TOKEN" | docker login -u oauth2accesstoken --password-stdin gcr.io

echo "==> Creating network if needed..."
docker network create qsdsan-network 2>/dev/null || true

echo "==> Pulling latest image..."
docker pull $IMAGE_TAG

echo "==> Stopping old container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "==> Starting new container..."
docker run -d \\
  --name $CONTAINER_NAME \\
  --restart unless-stopped \\
  --network qsdsan-network \\
  -p ${CONTAINER_PORT}:${CONTAINER_PORT} \\
  -v energyplus_outputs:/app/outputs \\
  -v energyplus_logs:/app/logs \\
  -e OPENAI_API_KEY="\${OPENAI_API_KEY:-}" \\
  -e LOG_LEVEL=INFO \\
  $IMAGE_TAG

echo "==> Waiting for container to start..."
sleep 5

echo "==> Checking health..."
curl -f http://localhost:$CONTAINER_PORT/health || echo "Health check pending..."

echo "==> Container status:"
docker ps | grep $CONTAINER_NAME

echo "==> Deployment complete!"
VMSCRIPT

    echo "Connecting to VM and deploying..."

    # Copy script to VM and execute
    gcloud compute scp /tmp/deploy-energyplus.sh "${VM_NAME}:/tmp/deploy-energyplus.sh" --zone="$VM_ZONE" --quiet
    gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="chmod +x /tmp/deploy-energyplus.sh && /tmp/deploy-energyplus.sh"

    rm /tmp/deploy-energyplus.sh

    success "Deployment complete!"

    # Final status
    echo -e "${GREEN}"
    cat << EOF

=====================================================
  Deployment Summary
=====================================================
  Container: $CONTAINER_NAME
  Port:      $CONTAINER_PORT

  Endpoints:
    Health:  http://34.28.104.162:$CONTAINER_PORT/health
    API:     http://34.28.104.162:$CONTAINER_PORT/docs

  Commands:
    SSH:     gcloud compute ssh $VM_NAME --zone=$VM_ZONE
    Logs:    docker logs $CONTAINER_NAME --tail 100
    Status:  docker ps | grep $CONTAINER_NAME
=====================================================

EOF
    echo -e "${NC}"

else
    warn "Skipping deployment step"
fi

echo -e "${CYAN}Done!${NC}"
