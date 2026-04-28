#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${BASE_DIR}/docker-compose.yml"

# Detect whether to use 'docker compose' (v2) or 'docker-compose' (v1)
if docker compose version &>/dev/null; then
  DOCKER_COMPOSE="docker compose"
else
  DOCKER_COMPOSE="docker-compose"
fi

echo "============================================"
echo "  FoodRush — Local Bootstrap"
echo "============================================"

# Create data directories so volumes work correctly
mkdir -p "${BASE_DIR}/data/user-service"
mkdir -p "${BASE_DIR}/data/restaurant-service"
mkdir -p "${BASE_DIR}/data/order-service"
mkdir -p "${BASE_DIR}/data/delivery-service"

echo "[1/4] Building and starting all services..."
echo "      Using: ${DOCKER_COMPOSE}"
${DOCKER_COMPOSE} -f "${COMPOSE_FILE}" up -d --build

echo "[2/4] Waiting for services to become healthy..."

wait_healthy() {
  local service=$1
  local url=$2
  local max_attempts=30
  local attempt=0

  echo -n "  Waiting for ${service}..."
  while [ $attempt -lt $max_attempts ]; do
    if curl -sf "${url}" > /dev/null 2>&1; then
      echo " ready"
      return 0
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 3
  done
  echo " TIMEOUT"
  return 1
}

wait_healthy "user-service"      "http://localhost:8001/health"
wait_healthy "restaurant-service" "http://localhost:8002/health"
wait_healthy "order-service"      "http://localhost:8003/health"
wait_healthy "delivery-service"   "http://localhost:8004/health"
wait_healthy "nginx"              "http://localhost:8080/"

echo ""
echo "[3/4] Running quick smoke tests..."

check_endpoint() {
  local label=$1
  local url=$2
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" "${url}")
  if [ "${status}" = "200" ]; then
    echo "  [OK] ${label} — HTTP ${status}"
  else
    echo "  [FAIL] ${label} — HTTP ${status}"
  fi
}

check_endpoint "GET /api/restaurants"     "http://localhost:8080/api/restaurants"
check_endpoint "GET /health (user)"       "http://localhost:8001/health"
check_endpoint "GET /health (restaurant)" "http://localhost:8002/health"
check_endpoint "GET /health (order)"      "http://localhost:8003/health"
check_endpoint "GET /health (delivery)"   "http://localhost:8004/health"
check_endpoint "Prometheus UI"            "http://localhost:9090/-/ready"

echo ""
echo "[4/4] All systems operational!"
echo ""
echo "============================================"
echo "  Service URLs"
echo "============================================"
echo "  Frontend (via nginx):    http://localhost:8080"
echo "  User Service:            http://localhost:8001"
echo "  Restaurant Service:      http://localhost:8002"
echo "  Order Service:           http://localhost:8003"
echo "  Delivery Service:        http://localhost:8004"
echo "  Prometheus:              http://localhost:9090"
echo "  Grafana:                 http://localhost:3000  (admin / foodrush123)"
echo "============================================"
echo ""
echo "To enable failure mode:  ORDER_SERVICE_FAILURE_MODE=true ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} up -d order-service"
echo "To stop everything:      ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} down"
echo ""
