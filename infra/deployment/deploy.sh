#!/usr/bin/env bash
# Pyhron Trading Platform - Deployment Script
# Usage:
#   ./deploy.sh [environment] [version]
#   ./deploy.sh production v1.2.3
#   ./deploy.sh staging latest
#   ./deploy.sh --rollback production

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io/pyhron}"
IMAGE_NAME="pyhron-api"
K8S_NAMESPACE="pyhron"
ROLLBACK_TIMEOUT=300
DEPLOY_TIMEOUT=600
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log_info()  { echo -e "${BLUE}[INFO]${NC}  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"; }

usage() {
    echo "Usage: $0 [--rollback] <environment> [version]"
    echo ""
    echo "Arguments:"
    echo "  environment   Target environment (development, staging, production)"
    echo "  version       Docker image tag (default: latest)"
    echo ""
    echo "Options:"
    echo "  --rollback    Rollback to previous deployment"
    echo "  --dry-run     Show what would be deployed without applying"
    echo "  --skip-tests  Skip running tests before deployment"
    echo "  --help        Show this help message"
    exit 1
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    local missing=()

    for cmd in docker kubectl helm jq curl; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi

    # Verify kubectl context
    local context
    context=$(kubectl config current-context 2>/dev/null || echo "none")
    log_info "Current kubectl context: ${context}"

    if [[ "$ENVIRONMENT" == "production" && "$context" != *"production"* ]]; then
        log_warn "kubectl context does not appear to be production. Proceed? (y/N)"
        read -r confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_error "Deployment cancelled by user."
            exit 1
        fi
    fi

    log_ok "Prerequisites check passed."
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warn "Skipping tests (--skip-tests flag set)."
        return 0
    fi

    log_info "Running test suite..."

    cd "$ROOT_DIR"

    # Unit tests
    log_info "Running unit tests..."
    if ! python -m pytest tests/unit/ -v --tb=short -q 2>&1; then
        log_error "Unit tests failed. Aborting deployment."
        exit 1
    fi
    log_ok "Unit tests passed."

    # Integration tests (skip in production deploy, run separately)
    if [[ "$ENVIRONMENT" != "production" ]]; then
        log_info "Running integration tests..."
        if ! python -m pytest tests/integration/ -v --tb=short -q 2>&1; then
            log_error "Integration tests failed. Aborting deployment."
            exit 1
        fi
        log_ok "Integration tests passed."
    fi
}

build_image() {
    log_info "Building Docker image: ${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}"

    cd "$ROOT_DIR"

    docker build \
        --file infra/docker/Dockerfile \
        --tag "${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}" \
        --tag "${DOCKER_REGISTRY}/${IMAGE_NAME}:latest" \
        --build-arg PYTHON_VERSION=3.11 \
        --label "org.opencontainers.image.version=${VERSION}" \
        --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" \
        .

    log_ok "Docker image built successfully."
}

scan_image() {
    log_info "Scanning image for vulnerabilities with Trivy..."

    if command -v trivy &> /dev/null; then
        trivy image \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            --no-progress \
            "${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}" || {
            log_error "Trivy scan found HIGH/CRITICAL vulnerabilities."
            if [[ "$ENVIRONMENT" == "production" ]]; then
                log_error "Cannot deploy to production with known vulnerabilities."
                exit 1
            else
                log_warn "Continuing deployment to ${ENVIRONMENT} despite vulnerabilities."
            fi
        }
        log_ok "Trivy scan passed."
    else
        log_warn "Trivy not installed. Skipping vulnerability scan."
    fi
}

push_image() {
    log_info "Pushing Docker image to registry..."

    docker push "${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}"
    docker push "${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"

    log_ok "Docker image pushed to ${DOCKER_REGISTRY}."
}

apply_kubernetes() {
    log_info "Applying Kubernetes manifests..."

    cd "$ROOT_DIR"

    # Apply namespace first
    kubectl apply -f infra/kubernetes/namespace.yaml

    # Apply deployment with image tag substitution
    cat infra/kubernetes/deployment.yaml | \
        sed "s|image: pyhron-api:latest|image: ${DOCKER_REGISTRY}/${IMAGE_NAME}:${VERSION}|g" | \
        kubectl apply -f -

    log_ok "Kubernetes manifests applied."
}

wait_for_rollout() {
    log_info "Waiting for deployment rollout (timeout: ${DEPLOY_TIMEOUT}s)..."

    if ! kubectl rollout status deployment/pyhron-api \
        --namespace "$K8S_NAMESPACE" \
        --timeout="${DEPLOY_TIMEOUT}s"; then
        log_error "Deployment rollout failed or timed out."
        return 1
    fi

    log_ok "Deployment rollout completed."
}

health_check() {
    log_info "Running post-deployment health checks..."

    local api_url
    api_url=$(kubectl get svc pyhron-api \
        --namespace "$K8S_NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "localhost")

    local retries=0
    while [ $retries -lt $HEALTH_CHECK_RETRIES ]; do
        if curl -sf "http://${api_url}/health" > /dev/null 2>&1; then
            log_ok "Health check passed."
            return 0
        fi
        retries=$((retries + 1))
        log_info "Health check attempt ${retries}/${HEALTH_CHECK_RETRIES}..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "Health check failed after ${HEALTH_CHECK_RETRIES} attempts."
    return 1
}

rollback() {
    log_info "Initiating rollback for deployment pyhron-api..."

    kubectl rollout undo deployment/pyhron-api \
        --namespace "$K8S_NAMESPACE"

    log_info "Waiting for rollback to complete..."
    if kubectl rollout status deployment/pyhron-api \
        --namespace "$K8S_NAMESPACE" \
        --timeout="${ROLLBACK_TIMEOUT}s"; then
        log_ok "Rollback completed successfully."
    else
        log_error "Rollback failed! Manual intervention required."
        exit 1
    fi
}

deploy() {
    local start_time
    start_time=$(date +%s)

    log_info "=============================================="
    log_info "Deploying Pyhron API"
    log_info "  Environment: ${ENVIRONMENT}"
    log_info "  Version:     ${VERSION}"
    log_info "  Registry:    ${DOCKER_REGISTRY}"
    log_info "  Dry Run:     ${DRY_RUN}"
    log_info "=============================================="

    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_warn "PRODUCTION DEPLOYMENT - Confirm? (type 'deploy-production' to continue)"
        read -r confirm
        if [[ "$confirm" != "deploy-production" ]]; then
            log_error "Deployment cancelled."
            exit 1
        fi
    fi

    check_prerequisites
    run_tests
    build_image
    scan_image

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete. No changes applied."
        exit 0
    fi

    push_image
    apply_kubernetes

    if ! wait_for_rollout; then
        log_error "Rollout failed. Initiating automatic rollback..."
        rollback
        exit 1
    fi

    if ! health_check; then
        log_error "Health check failed. Initiating automatic rollback..."
        rollback
        exit 1
    fi

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_ok "=============================================="
    log_ok "Deployment complete!"
    log_ok "  Duration: ${duration}s"
    log_ok "  Version:  ${VERSION}"
    log_ok "=============================================="
}

# Main
DO_ROLLBACK=false
DRY_RUN=false
SKIP_TESTS=false
ENVIRONMENT=""
VERSION="latest"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rollback)
            DO_ROLLBACK=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            if [[ -z "$ENVIRONMENT" ]]; then
                ENVIRONMENT="$1"
            else
                VERSION="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment is required."
    usage
fi

if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: ${ENVIRONMENT}"
    usage
fi

if [[ "$DO_ROLLBACK" == "true" ]]; then
    rollback
else
    deploy
fi
