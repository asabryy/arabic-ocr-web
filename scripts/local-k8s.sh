#!/usr/bin/env bash
# local-k8s.sh — spin up the full Textara stack in a local k3d cluster
# Usage: ./scripts/local-k8s.sh
set -euo pipefail

CLUSTER_NAME="textara"
NAMESPACE="textara"

echo "=== Building Docker images ==="
docker build -t auth-service:local ./auth-service
docker build -t doc-manager:local ./doc-manager
docker build \
  --build-arg VITE_AUTH_API_URL="" \
  --build-arg VITE_DOC_API_URL="" \
  --build-arg VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID:-}" \
  -t frontend:local ./frontend

echo "=== Creating k3d cluster ==="
if k3d cluster list | grep -q "^${CLUSTER_NAME}"; then
  echo "Cluster '${CLUSTER_NAME}' already exists, skipping creation."
else
  k3d cluster create "${CLUSTER_NAME}" \
    --port "80:80@loadbalancer" \
    --k3s-arg "--disable=traefik@server:0"
fi

echo "=== Importing images into cluster ==="
k3d image import auth-service:local doc-manager:local frontend:local -c "${CLUSTER_NAME}"

echo "=== Applying base manifests ==="
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/main-ingress.yaml -n "${NAMESPACE}"

echo "=== Applying local-only resources (postgres) ==="
kubectl apply -f k8s/local/postgres/ -n "${NAMESPACE}"

echo "=== Applying secrets ==="
# Load from .env.local if present
if [ -f .env.local ]; then
  set -a; source .env.local; set +a
fi

kubectl create secret generic auth-service-secret \
  --from-literal=DATABASE_URL="${AUTH_DATABASE_URL:-postgresql://textara:textara@postgres:5432/textara}" \
  --from-literal=SECRET_KEY="${AUTH_SECRET_KEY:-local-dev-secret-key}" \
  --from-literal=SENDGRID_API_KEY="${SENDGRID_API_KEY:-}" \
  -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic doc-manager-secret \
  --from-literal=SECRET_KEY="${AUTH_SECRET_KEY:-local-dev-secret-key}" \
  --from-literal=RABBITMQ_PASS="${RABBITMQ_PASS:-guest}" \
  --from-literal=R2_ENDPOINT_URL="${R2_ENDPOINT_URL:-}" \
  --from-literal=R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:-}" \
  --from-literal=R2_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:-}" \
  --from-literal=R2_BUCKET_NAME="${R2_BUCKET_NAME:-}" \
  --from-literal=MODAL_TOKEN_ID="${MODAL_TOKEN_ID:-}" \
  --from-literal=MODAL_TOKEN_SECRET="${MODAL_TOKEN_SECRET:-}" \
  -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "=== Applying app manifests ==="
kubectl apply -f k8s/rabbitmq/ -n "${NAMESPACE}"
kubectl apply -f k8s/auth-service/ -n "${NAMESPACE}"
kubectl apply -f k8s/doc-manager/ -n "${NAMESPACE}"
kubectl apply -f k8s/doc-worker/ -n "${NAMESPACE}"
kubectl apply -f k8s/frontend/ -n "${NAMESPACE}"

echo "=== Patching configmaps for local dev ==="
kubectl patch configmap auth-service-config -n "${NAMESPACE}" --type=merge -p '{
  "data": {
    "FRONTEND_BASE_URL": "http://textara.local",
    "CORS_ORIGINS": "https://textara.app,https://www.textara.app,http://textara.local,http://localhost:5173",
    "GOOGLE_CLIENT_ID": "'"${VITE_GOOGLE_CLIENT_ID:-}"'"
  }
}'

kubectl patch configmap doc-manager-config -n "${NAMESPACE}" --type=merge -p '{
  "data": {
    "OCR_BACKEND": "http",
    "OCR_HTTP_URL": "http://192.168.65.254:8002"
  }
}'

echo "=== Patching deployments to use local images ==="
kubectl set image deployment/auth-service auth-service=auth-service:local -n "${NAMESPACE}"
kubectl set image deployment/doc-manager doc-manager=doc-manager:local -n "${NAMESPACE}"
kubectl set image deployment/doc-worker doc-worker=doc-manager:local -n "${NAMESPACE}"
kubectl set image deployment/frontend frontend=frontend:local -n "${NAMESPACE}"

# Disable imagePullPolicy so k3d doesn't try to pull from registry
kubectl patch deployment auth-service -n "${NAMESPACE}" \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"auth-service","imagePullPolicy":"IfNotPresent"}]}}}}'
kubectl patch deployment doc-manager -n "${NAMESPACE}" \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"doc-manager","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment doc-worker -n "${NAMESPACE}" \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"doc-worker","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment frontend -n "${NAMESPACE}" \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"frontend","imagePullPolicy":"IfNotPresent"}]}}}}'

echo "=== Waiting for RabbitMQ to be ready ==="
echo "  (this can take up to 2 minutes on first start)"
kubectl rollout status statefulset/rabbitmq -n "${NAMESPACE}" --timeout=3m
# Extra wait for RabbitMQ to finish internal init before workers connect
for i in $(seq 1 24); do
  if kubectl exec -n "${NAMESPACE}" rabbitmq-0 -- rabbitmq-diagnostics ping &>/dev/null; then
    echo "  RabbitMQ ready."
    break
  fi
  echo "  Waiting for RabbitMQ... (${i}/24)"
  sleep 5
done

echo "=== Waiting for all deployments ==="
kubectl rollout status deployment/auth-service -n "${NAMESPACE}" --timeout=3m
kubectl rollout status deployment/doc-manager -n "${NAMESPACE}" --timeout=3m
kubectl rollout status deployment/doc-worker -n "${NAMESPACE}" --timeout=3m
kubectl rollout status deployment/frontend -n "${NAMESPACE}" --timeout=3m

echo ""
echo "=== Done! ==="
echo "  App:        http://textara.local"
echo "  RabbitMQ:   http://textara.local:15672  (guest / <RABBITMQ_PASS>)"
echo "  Vite dev:   cd frontend && npm run dev"
