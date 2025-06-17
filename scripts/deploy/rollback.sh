#!/bin/bash
# Rollback script for DEAN orchestration deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_NAMESPACE="${DEPLOY_NAMESPACE:-dean-system}"
HELM_RELEASE="${HELM_RELEASE:-dean-orchestration}"

echo -e "${YELLOW}DEAN Orchestration Rollback Script${NC}"
echo "===================================="
echo ""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --revision <number>    Rollback to specific revision"
    echo "  -l, --list                 List available revisions"
    echo "  -d, --dry-run             Show what would be rolled back"
    echo "  -f, --force               Force rollback without confirmation"
    echo "  -n, --namespace <name>    Kubernetes namespace (default: $DEPLOY_NAMESPACE)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list                 # List all revisions"
    echo "  $0 --revision 5           # Rollback to revision 5"
    echo "  $0                        # Rollback to previous revision"
}

# Parse command line arguments
REVISION=""
LIST_ONLY=false
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--revision)
            REVISION="$2"
            shift 2
            ;;
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--namespace)
            DEPLOY_NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Check prerequisites
if ! command -v kubectl >/dev/null 2>&1; then
    echo -e "${RED}kubectl is not installed${NC}"
    exit 1
fi

if ! command -v helm >/dev/null 2>&1; then
    echo -e "${RED}helm is not installed${NC}"
    exit 1
fi

# Check if release exists
if ! helm list -n "$DEPLOY_NAMESPACE" | grep -q "$HELM_RELEASE"; then
    echo -e "${RED}Helm release '$HELM_RELEASE' not found in namespace '$DEPLOY_NAMESPACE'${NC}"
    exit 1
fi

# List revisions
if [ "$LIST_ONLY" = true ]; then
    echo "Available revisions for $HELM_RELEASE:"
    echo ""
    helm history "$HELM_RELEASE" -n "$DEPLOY_NAMESPACE"
    exit 0
fi

# Get current revision info
echo "Current deployment status:"
echo "-------------------------"
CURRENT_REVISION=$(helm list -n "$DEPLOY_NAMESPACE" -o json | jq -r ".[] | select(.name==\"$HELM_RELEASE\") | .revision")
echo "Release: $HELM_RELEASE"
echo "Namespace: $DEPLOY_NAMESPACE"
echo "Current Revision: $CURRENT_REVISION"

# Get current deployment status
kubectl get deployment -n "$DEPLOY_NAMESPACE" -l "app.kubernetes.io/instance=$HELM_RELEASE" \
    -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas

echo ""

# Determine target revision
if [ -z "$REVISION" ]; then
    # Rollback to previous revision
    TARGET_REVISION=$((CURRENT_REVISION - 1))
    if [ "$TARGET_REVISION" -lt 1 ]; then
        echo -e "${RED}Cannot rollback: already at first revision${NC}"
        exit 1
    fi
else
    TARGET_REVISION="$REVISION"
fi

# Show rollback plan
echo "Rollback Plan:"
echo "--------------"
echo "From Revision: $CURRENT_REVISION"
echo "To Revision: $TARGET_REVISION"
echo ""

# Get revision details
echo "Target revision details:"
helm history "$HELM_RELEASE" -n "$DEPLOY_NAMESPACE" | grep "^$TARGET_REVISION"

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    echo ""
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
    echo ""
    echo "Would execute:"
    echo "  helm rollback $HELM_RELEASE $TARGET_REVISION -n $DEPLOY_NAMESPACE"
    exit 0
fi

# Confirmation
if [ "$FORCE" != true ]; then
    echo ""
    echo -e "${YELLOW}Warning: This will rollback the production deployment!${NC}"
    read -p "Are you sure you want to continue? (yes/no) " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Rollback cancelled"
        exit 0
    fi
fi

# Create backup before rollback
echo ""
echo "Creating backup of current state..."
BACKUP_FILE="rollback-backup-$(date +%Y%m%d-%H%M%S).yaml"
kubectl get all,configmap,secret,ingress -n "$DEPLOY_NAMESPACE" \
    -l "app.kubernetes.io/instance=$HELM_RELEASE" \
    -o yaml > "$BACKUP_FILE"
echo "Backup saved to: $BACKUP_FILE"

# Perform rollback
echo ""
echo "Performing rollback..."
if helm rollback "$HELM_RELEASE" "$TARGET_REVISION" -n "$DEPLOY_NAMESPACE" --wait; then
    echo -e "${GREEN}✓ Rollback initiated successfully${NC}"
else
    echo -e "${RED}✗ Rollback failed${NC}"
    exit 1
fi

# Monitor rollback progress
echo ""
echo "Monitoring rollback progress..."
TIMEOUT=300  # 5 minutes
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check deployment status
    READY=$(kubectl get deployment -n "$DEPLOY_NAMESPACE" \
        -l "app.kubernetes.io/instance=$HELM_RELEASE" \
        -o jsonpath='{.items[*].status.conditions[?(@.type=="Available")].status}')
    
    if [[ "$READY" == *"True"* ]]; then
        echo -e "${GREEN}✓ Rollback completed successfully${NC}"
        break
    fi
    
    echo -n "."
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo ""
    echo -e "${RED}Rollback timeout - deployment may still be in progress${NC}"
    echo "Check status with: kubectl get pods -n $DEPLOY_NAMESPACE"
fi

# Run health check
echo ""
echo "Running health check..."
if [ -x "$(dirname "$0")/health_check.sh" ]; then
    "$(dirname "$0")/health_check.sh" || true
else
    echo -e "${YELLOW}Health check script not found${NC}"
fi

# Show final status
echo ""
echo "Final Status:"
echo "-------------"
NEW_REVISION=$(helm list -n "$DEPLOY_NAMESPACE" -o json | jq -r ".[] | select(.name==\"$HELM_RELEASE\") | .revision")
echo "Current Revision: $NEW_REVISION"

kubectl get deployment,pods -n "$DEPLOY_NAMESPACE" \
    -l "app.kubernetes.io/instance=$HELM_RELEASE"

echo ""
echo -e "${GREEN}Rollback completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Verify application functionality"
echo "2. Check application logs for errors"
echo "3. Monitor metrics and alerts"
echo "4. Investigate the issue that caused the rollback"

# Save rollback information
ROLLBACK_LOG="rollback-log-$(date +%Y%m%d-%H%M%S).txt"
cat > "$ROLLBACK_LOG" <<EOF
Rollback performed at: $(date)
From revision: $CURRENT_REVISION
To revision: $TARGET_REVISION
Final revision: $NEW_REVISION
Reason: Manual rollback
Operator: $(whoami)
EOF

echo ""
echo "Rollback log saved to: $ROLLBACK_LOG"