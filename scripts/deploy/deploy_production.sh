#!/bin/bash
# Deploy DEAN orchestration to production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Deployment configuration (can be overridden by environment)
DEPLOY_ENV="${DEPLOY_ENV:-production}"
DEPLOY_REGION="${DEPLOY_REGION:-us-east-1}"
DEPLOY_NAMESPACE="${DEPLOY_NAMESPACE:-dean-system}"
DEPLOY_STRATEGY="${DEPLOY_STRATEGY:-blue-green}"

echo -e "${GREEN}DEAN Production Deployment Script${NC}"
echo "===================================="
echo "Environment: $DEPLOY_ENV"
echo "Region: $DEPLOY_REGION"
echo "Namespace: $DEPLOY_NAMESPACE"
echo "Strategy: $DEPLOY_STRATEGY"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "${RED}Missing required tools: ${missing_tools[*]}${NC}"
        echo "Please install missing tools before proceeding."
        exit 1
    fi
    
    # Check kubectl context
    local current_context=$(kubectl config current-context 2>/dev/null || echo "none")
    echo "Current kubectl context: $current_context"
    
    if [[ ! "$current_context" =~ "production" ]]; then
        echo -e "${YELLOW}Warning: kubectl context doesn't appear to be production${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
}

# Function to build and push Docker image
build_and_push_image() {
    echo "Building production Docker image..."
    
    # Get version from pyproject.toml
    VERSION=$(grep "version = " "$PROJECT_ROOT/pyproject.toml" | cut -d'"' -f2)
    IMAGE_TAG="${VERSION}-$(git rev-parse --short HEAD)"
    IMAGE_REPO="${DOCKER_REGISTRY:-docker.io}/dean/orchestration"
    
    cd "$PROJECT_ROOT"
    
    # Create production Dockerfile
    cat > Dockerfile.production <<EOF
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements/base.txt requirements/base.txt
RUN pip install --user --no-cache-dir -r requirements/base.txt

# Copy source code
COPY src/ src/
COPY pyproject.toml .
COPY configs/ configs/

# Install the package
RUN pip install --user -e .

# Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /build/src /app/src
COPY --from=builder /build/configs /app/configs
COPY --from=builder /build/pyproject.toml /app/

# Add user for security
RUN useradd -m -u 1000 dean && chown -R dean:dean /app
USER dean

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Expose port
EXPOSE 8082

# Run the server
CMD ["dean-server"]
EOF

    # Build image
    docker build -f Dockerfile.production -t "$IMAGE_REPO:$IMAGE_TAG" .
    docker tag "$IMAGE_REPO:$IMAGE_TAG" "$IMAGE_REPO:latest"
    
    # Push to registry
    echo "Pushing image to registry..."
    docker push "$IMAGE_REPO:$IMAGE_TAG"
    docker push "$IMAGE_REPO:latest"
    
    echo -e "${GREEN}✓ Image built and pushed: $IMAGE_REPO:$IMAGE_TAG${NC}"
    
    # Export for later use
    export DEAN_IMAGE="$IMAGE_REPO:$IMAGE_TAG"
}

# Function to deploy using Helm
deploy_with_helm() {
    echo "Deploying with Helm..."
    
    # Create Helm chart if it doesn't exist
    CHART_DIR="$PROJECT_ROOT/helm/dean-orchestration"
    
    if [ ! -d "$CHART_DIR" ]; then
        echo "Creating Helm chart..."
        mkdir -p "$CHART_DIR"
        
        # Create Chart.yaml
        cat > "$CHART_DIR/Chart.yaml" <<EOF
apiVersion: v2
name: dean-orchestration
description: DEAN Orchestration System Helm Chart
type: application
version: 0.1.0
appVersion: "0.1.0"
EOF
        
        # Create values.yaml
        cat > "$CHART_DIR/values.yaml" <<EOF
replicaCount: 3

image:
  repository: ${DOCKER_REGISTRY:-docker.io}/dean/orchestration
  pullPolicy: IfNotPresent
  tag: ""  # Overridden during deployment

service:
  type: LoadBalancer
  port: 80
  targetPort: 8082

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: dean.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: dean-tls
      hosts:
        - dean.example.com

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

persistence:
  enabled: true
  storageClass: "gp3"
  size: 10Gi

postgresql:
  enabled: false  # Use external database in production
  external:
    host: postgres.dean-system.svc.cluster.local
    port: 5432
    database: dean_orchestration
    existingSecret: dean-db-credentials

redis:
  enabled: false  # Use external Redis in production
  external:
    host: redis.dean-system.svc.cluster.local
    port: 6379
    existingSecret: dean-redis-credentials

monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true

security:
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  
  networkPolicies:
    enabled: true

backup:
  enabled: true
  schedule: "0 2 * * *"
  retention: 30
EOF
        
        # Create templates directory
        mkdir -p "$CHART_DIR/templates"
        
        echo -e "${GREEN}✓ Helm chart created${NC}"
    fi
    
    # Update dependencies
    helm dependency update "$CHART_DIR"
    
    # Deploy based on strategy
    case "$DEPLOY_STRATEGY" in
        "blue-green")
            deploy_blue_green
            ;;
        "canary")
            deploy_canary
            ;;
        "rolling")
            deploy_rolling
            ;;
        *)
            echo -e "${RED}Unknown deployment strategy: $DEPLOY_STRATEGY${NC}"
            exit 1
            ;;
    esac
}

# Blue-Green deployment
deploy_blue_green() {
    echo "Performing Blue-Green deployment..."
    
    # Deploy to green environment
    helm upgrade --install dean-green "$CHART_DIR" \
        --namespace "$DEPLOY_NAMESPACE" \
        --create-namespace \
        --set image.tag="$DEAN_IMAGE" \
        --set-string deployment.color=green \
        --wait
    
    # Run smoke tests
    echo "Running smoke tests on green environment..."
    if ! run_smoke_tests "dean-green"; then
        echo -e "${RED}Smoke tests failed. Rolling back...${NC}"
        helm rollback dean-green 0 --namespace "$DEPLOY_NAMESPACE"
        exit 1
    fi
    
    # Switch traffic to green
    echo "Switching traffic to green environment..."
    kubectl patch service dean-orchestration \
        --namespace "$DEPLOY_NAMESPACE" \
        --patch '{"spec":{"selector":{"deployment.color":"green"}}}'
    
    # Wait for traffic to stabilize
    sleep 30
    
    # Delete blue deployment
    helm uninstall dean-blue --namespace "$DEPLOY_NAMESPACE" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Blue-Green deployment completed${NC}"
}

# Canary deployment
deploy_canary() {
    echo "Performing Canary deployment..."
    
    # Deploy canary version
    helm upgrade --install dean-canary "$CHART_DIR" \
        --namespace "$DEPLOY_NAMESPACE" \
        --create-namespace \
        --set image.tag="$DEAN_IMAGE" \
        --set replicaCount=1 \
        --set-string deployment.type=canary \
        --wait
    
    # Gradually increase traffic
    for percentage in 10 25 50 75 100; do
        echo "Routing $percentage% traffic to canary..."
        
        # Update ingress or service mesh rules
        # This is a placeholder - actual implementation depends on ingress controller
        kubectl annotate ingress dean-orchestration \
            --namespace "$DEPLOY_NAMESPACE" \
            nginx.ingress.kubernetes.io/canary-weight="$percentage" \
            --overwrite
        
        # Monitor metrics
        echo "Monitoring canary metrics for 5 minutes..."
        sleep 300
        
        # Check canary health
        if ! check_canary_health; then
            echo -e "${RED}Canary deployment failed. Rolling back...${NC}"
            kubectl annotate ingress dean-orchestration \
                --namespace "$DEPLOY_NAMESPACE" \
                nginx.ingress.kubernetes.io/canary-weight="0" \
                --overwrite
            helm uninstall dean-canary --namespace "$DEPLOY_NAMESPACE"
            exit 1
        fi
    done
    
    # Promote canary to stable
    helm upgrade --install dean-orchestration "$CHART_DIR" \
        --namespace "$DEPLOY_NAMESPACE" \
        --set image.tag="$DEAN_IMAGE" \
        --wait
    
    # Remove canary
    helm uninstall dean-canary --namespace "$DEPLOY_NAMESPACE"
    
    echo -e "${GREEN}✓ Canary deployment completed${NC}"
}

# Rolling deployment
deploy_rolling() {
    echo "Performing Rolling deployment..."
    
    helm upgrade --install dean-orchestration "$CHART_DIR" \
        --namespace "$DEPLOY_NAMESPACE" \
        --create-namespace \
        --set image.tag="$DEAN_IMAGE" \
        --wait
    
    echo -e "${GREEN}✓ Rolling deployment completed${NC}"
}

# Run smoke tests
run_smoke_tests() {
    local deployment=$1
    local service_url="http://$deployment.$DEPLOY_NAMESPACE.svc.cluster.local:8082"
    
    echo "Running smoke tests against $service_url..."
    
    # Test health endpoint
    if ! kubectl run smoke-test --rm -i --restart=Never \
        --image=curlimages/curl:latest \
        --namespace="$DEPLOY_NAMESPACE" \
        -- curl -f "$service_url/health"; then
        return 1
    fi
    
    # Test API endpoints
    # Add more comprehensive tests here
    
    return 0
}

# Check canary health
check_canary_health() {
    # This is a placeholder - implement actual health checks
    # Check error rates, latency, resource usage, etc.
    return 0
}

# Post-deployment tasks
post_deployment() {
    echo "Running post-deployment tasks..."
    
    # Update DNS if needed
    echo "Updating DNS records..."
    # Add DNS update logic here
    
    # Notify monitoring systems
    echo "Notifying monitoring systems..."
    # Add notification logic here
    
    # Create backup
    echo "Creating post-deployment backup..."
    kubectl exec -n "$DEPLOY_NAMESPACE" deployment/dean-orchestration -- \
        dean-admin backup create post-deploy-$(date +%Y%m%d-%H%M%S)
    
    echo -e "${GREEN}✓ Post-deployment tasks completed${NC}"
}

# Main deployment flow
main() {
    echo -e "${BLUE}Starting DEAN production deployment...${NC}"
    
    check_prerequisites
    build_and_push_image
    deploy_with_helm
    post_deployment
    
    echo ""
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo ""
    echo "Deployment summary:"
    echo "  Environment: $DEPLOY_ENV"
    echo "  Image: $DEAN_IMAGE"
    echo "  Namespace: $DEPLOY_NAMESPACE"
    echo "  Strategy: $DEPLOY_STRATEGY"
    echo ""
    echo "Access the application at: https://dean.example.com"
    echo ""
    
    # Show deployment status
    kubectl get deployments,services,ingress -n "$DEPLOY_NAMESPACE"
}

# Run main function
main "$@"