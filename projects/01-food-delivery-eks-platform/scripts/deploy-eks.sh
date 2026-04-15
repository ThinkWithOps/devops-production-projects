#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-food-delivery-dev}"
K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../k8s" && pwd)"

echo "============================================"
echo "  FoodRush — EKS Deployment"
echo "  Cluster: ${CLUSTER_NAME}"
echo "  Region:  ${AWS_REGION}"
echo "============================================"

echo "[1/6] Updating kubeconfig..."
aws eks update-kubeconfig --region "${AWS_REGION}" --name "${CLUSTER_NAME}"
kubectl cluster-info

echo "[2/6] Installing metrics-server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
echo "  Waiting for metrics-server to be ready..."
kubectl rollout status deployment/metrics-server -n kube-system --timeout=120s

echo "[3/6] Applying Kubernetes manifests..."

echo "  Applying namespace..."
kubectl apply -f "${K8S_DIR}/namespace.yaml"

echo "  Applying ConfigMap..."
kubectl apply -f "${K8S_DIR}/configmap.yaml"

echo "  Deploying services..."
for SVC in user-service restaurant-service order-service delivery-service; do
  echo "  Deploying ${SVC}..."
  kubectl apply -f "${K8S_DIR}/${SVC}-deployment.yaml"
  kubectl apply -f "${K8S_DIR}/${SVC}-service.yaml"
  kubectl apply -f "${K8S_DIR}/${SVC}-hpa.yaml"
done

echo "  Applying Ingress..."
kubectl apply -f "${K8S_DIR}/ingress/ingress.yaml"

echo "[4/6] Waiting for deployments to be ready..."
for SVC in user-service restaurant-service order-service delivery-service; do
  echo "  Waiting for ${SVC}..."
  kubectl rollout status deployment/"${SVC}" -n food-delivery --timeout=300s
done

echo "[5/6] Verifying pods..."
kubectl get pods -n food-delivery
kubectl get services -n food-delivery
kubectl get hpa -n food-delivery

echo "[6/6] Getting LoadBalancer URL..."
echo "  Waiting for ingress to get external address (up to 3 minutes)..."
for i in $(seq 1 18); do
  LB_HOST=$(kubectl get ingress food-delivery-ingress -n food-delivery \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
  if [ -n "${LB_HOST}" ]; then
    break
  fi
  echo -n "."
  sleep 10
done

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
if [ -n "${LB_HOST:-}" ]; then
  echo "  App URL:       http://${LB_HOST}"
  echo "  Users API:     http://${LB_HOST}/api/users"
  echo "  Restaurants:   http://${LB_HOST}/api/restaurants"
  echo "  Orders:        http://${LB_HOST}/api/orders"
  echo "  Delivery:      http://${LB_HOST}/api/delivery"
else
  echo "  LoadBalancer hostname not yet available. Run:"
  echo "  kubectl get ingress -n food-delivery"
fi
echo "============================================"
