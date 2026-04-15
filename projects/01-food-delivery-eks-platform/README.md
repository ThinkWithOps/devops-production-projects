# FoodRush — Production-Grade Food Delivery Platform on AWS EKS

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)
![Terraform](https://img.shields.io/badge/Terraform-1.5+-7B42BC.svg)
![AWS EKS](https://img.shields.io/badge/AWS-EKS-FF9900.svg)

---

## Project Description

FoodRush is a production-grade food delivery platform (think mini Uber Eats / Swiggy) built to demonstrate what real DevOps looks like — not a tutorial app, not a hello-world demo.

It is built around **4 independent FastAPI microservices** (user, restaurant, order, delivery), each with its own database, communicating over HTTP. A React frontend ties it together through an NGINX gateway. The entire stack runs locally with a single command via Docker Compose, and deploys to **AWS EKS** using Terraform with a full **GitHub Actions CI/CD pipeline**.

The project includes a built-in **observability demo**: flip `ORDER_SERVICE_FAILURE_MODE=true`, run the load test, and watch the error rate spike to 50% in Grafana — then fix it and watch it recover. This is the kind of incident workflow you'd follow at 3 AM on-call.

Built for DevOps engineers who want a portfolio project that shows real infrastructure decisions: IAM least privilege, multi-AZ VPC, HPA autoscaling, rolling deployments with zero downtime, and Prometheus metrics that actually mean something.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [AWS Cost Breakdown](#aws-cost-breakdown)
- [Quick Start — Local Dev](#quick-start--local-dev-3-commands)
- [AWS EKS Deployment](#aws-eks-deployment)
- [GitHub Actions Setup](#github-actions-setup) (includes where Docker images are stored)
- [Observability Demo](#observability-demo)
- [API Endpoints](#api-endpoints)
- [How to Run Tests](#how-to-run-tests)
- [Project Structure](#project-structure)
- [What This Teaches](#what-this-teaches)
- [Real Challenges and Solutions](#real-challenges-and-solutions)
- [Contact](#contact)

---

## Architecture

```
                                   ┌─────────────────────────────────────────────────────┐
                                   │                  AWS EKS Cluster                    │
  ┌──────────┐   ┌───────────┐     │  ┌─────────────────────────────────────────────┐    │
  │  Browser │──▶│  NGINX    │     │  │            food-delivery namespace           │    │
  │  / curl  │   │  :8080    │     │  │                                              │    │
  └──────────┘   │  (proxy)  │     │  │  ┌──────────────┐   ┌────────────────────┐  │    │
                 └─────┬─────┘     │  │  │ user-service │   │restaurant-service  │  │    │
                       │           │  │  │   :8001      │   │    :8002           │  │    │
          ┌────────────┼──────────┐│  │  │  (2 replicas)│   │  (2 replicas)      │  │    │
          │            │          ││  │  └──────────────┘   └────────────────────┘  │    │
          ▼            ▼          ▼│  │                                              │    │
   /api/users  /api/restaurants  /api/orders   ┌──────────────┐  ┌───────────────┐  │    │
          │            │          ││  │  │  │ order-service│  │delivery-service│  │    │
          ▼            ▼          ▼│  │  │  │   :8003      │  │    :8004       │  │    │
   user-service  restaurant-  order-svc│  │  │  (2 replicas)│  │  (2 replicas)  │  │    │
      :8001        service:8002  :8003 │  │  └──────┬───────┘  └───────────────┘  │    │
                                       │  │         │ HTTP call                    │    │
   SQLite DB    SQLite DB    SQLite DB  │  │         ▼ restaurant-service           │    │
                                       │  │  ┌─────────────────────────────────┐   │    │
                                       │  │  │  HPA (min=2, max=6, CPU=70%)    │   │    │
                                       │  │  └─────────────────────────────────┘   │    │
 ┌───────────────────────────────────┐ │  └─────────────────────────────────────────┘    │
 │        Observability Stack        │ │                                                  │
 │  Prometheus :9090  Grafana :3000  │ │  ┌─────────────┐  ┌──────────┐  ┌───────────┐  │
 │  /metrics scrape every 15s        │ │  │     VPC     │  │  2 AZs   │  │ NAT GW    │  │
 └───────────────────────────────────┘ │  └─────────────┘  └──────────┘  └───────────┘  │
                                       └─────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Services | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| Auth | python-jose (JWT HS256), passlib bcrypt |
| Database | SQLite (aiosqlite) — per-service |
| HTTP Client | httpx (async, 5s timeout) |
| Frontend | React 18 (CDN), Tailwind CSS (CDN), single HTML file |
| Reverse Proxy | NGINX (gzip, access log with response time) |
| Containers | Docker, multi-stage builds, non-root user |
| Orchestration | Kubernetes 1.29, EKS, HPA, Rolling Updates |
| IaC | Terraform 1.5+, modules: vpc / eks / ecr / iam |
| CI/CD | GitHub Actions (deploy, pr-checks, destroy) |
| Monitoring | Prometheus + Grafana (kube-prometheus-stack) |
| Registry | Amazon ECR (scan on push, keep last 10 images) |

---

## AWS Cost Breakdown

| Resource | Cost |
|---|---|
| EKS Control Plane | $0.10/hr |
| t3.small nodes (×2) | $0.046/hr (~$0.023 each) |
| NAT Gateway | $0.045/hr + data transfer |
| ECR storage | ~$0.10/GB/month |
| **Total (running)** | **~$0.19/hr (~$4.56/day)** |

> Run `terraform destroy` after recording your demo to stop all charges.

---

## Quick Start — Local Dev (3 Commands)

```bash
git clone https://github.com/vijayb-aiops/devops-production-projects
cd projects/01-food-delivery-eks-platform
bash scripts/bootstrap.sh
```

Then open: http://localhost:8080

---

## AWS EKS Deployment

### Prerequisites
- AWS CLI configured
- Terraform 1.5+
- kubectl
- Docker

### Step 1 — Provision Infrastructure

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

### Step 2 — Build and Push Docker Images

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1
ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password | docker login --username AWS --password-stdin "$ECR"

for SVC in user-service restaurant-service order-service delivery-service; do
  docker build -t "${ECR}/food-delivery/${SVC}:latest" services/${SVC}/
  docker push "${ECR}/food-delivery/${SVC}:latest"
done
```

### Step 3 — Deploy to EKS

```bash
# Update image references in manifests
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
for f in k8s/*-deployment.yaml; do
  sed -i "s/ACCOUNT_ID/${ACCOUNT_ID}/g" "$f"
done

bash scripts/deploy-eks.sh
```

---

## GitHub Actions Setup

### Where Docker Images Are Stored

```
Your Laptop
├── docker compose up
│   └── builds images LOCALLY in Docker Desktop
│       (stored on your machine only, never pushed anywhere)
│
└── when you push code to GitHub
        ↓
    GitHub Actions builds the image
        ↓
    Pushes to ECR (your AWS account)
        ↓
    EKS pulls from ECR to run the pods
```

Images in ECR are tagged with the **git commit SHA** (e.g. `abc1234`) so you
always know exactly which version of the code is running in production.
A lifecycle policy keeps the last 10 images and deletes older ones automatically.

---

### Secrets Setup

Add these secrets in **Settings → Secrets and variables → Actions**:

| Secret Name | How to Get It |
|---|---|
| `AWS_ACCESS_KEY_ID` | `terraform output -raw github_actions_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | `terraform output -raw github_actions_secret_access_key` |
| `AWS_ACCOUNT_ID` | `aws sts get-caller-identity --query Account --output text` |

Workflows:
- **deploy.yml** — triggered on push to `main`, detects changed services, builds + pushes to ECR, rolls out to EKS
- **pr-checks.yml** — flake8 lint, pytest, terraform fmt + validate
- **destroy.yml** — manual workflow with confirmation input to tear down infrastructure

---

## Observability Demo

### 1. Enable Failure Mode

```bash
# Flip 50% of order requests to return HTTP 500
docker compose up -d -e ORDER_SERVICE_FAILURE_MODE=true order-service
```

### 2. Run Load Test

```bash
bash scripts/load-test.sh
# 300 requests, 10 concurrent — watch Grafana in real time
```

### 3. View in Grafana

Open http://localhost:3000 (admin / foodrush123)

Navigate to **Dashboards → Food Delivery → Food Delivery Platform**

Panels to observe:
- **Error Rate per Service** — order-service climbs to ~50%
- **Request Rate per Service** — all services during load
- **P95 Latency** — latency distribution under load
- **Total Failed Orders** — counter rises during failure mode
- **Order Throughput** — req/s per outcome

### 4. Disable Failure Mode

```bash
docker compose up -d -e ORDER_SERVICE_FAILURE_MODE=false order-service
```

---

## API Endpoints

### User Service (port 8001)

```bash
# Register
curl -X POST http://localhost:8001/users/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jordan Lee","email":"jordan@example.com","password":"Secret123!"}'

# Login
curl -X POST http://localhost:8001/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jordan@example.com","password":"Secret123!"}'

# Get profile (JWT required)
TOKEN="<token from login>"
curl http://localhost:8001/users/1 -H "Authorization: Bearer $TOKEN"

# Health
curl http://localhost:8001/health
```

### Restaurant Service (port 8002)

```bash
# List all restaurants
curl http://localhost:8002/restaurants

# Get restaurant + full menu
curl http://localhost:8002/restaurants/1

# Health
curl http://localhost:8002/health
```

### Order Service (port 8003)

```bash
# Place an order
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "restaurant_id": 1,
    "items": [{"menu_item_id": 1, "name": "Butter Chicken", "quantity": 2, "unit_price": 16.99}],
    "delivery_address": "42 Main Street, Brooklyn, NY"
  }'

# Get order status
curl http://localhost:8003/orders/1

# All orders for a user
curl http://localhost:8003/orders/user/1

# Update order status
curl -X PATCH http://localhost:8003/orders/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

### Delivery Service (port 8004)

```bash
# Assign delivery agent
curl -X POST http://localhost:8004/delivery \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "pickup_address": "The Golden Spice, 245 Curry Lane, Manhattan",
    "delivery_address": "42 Main Street, Brooklyn, NY"
  }'

# Get delivery status
curl http://localhost:8004/delivery/1

# Update delivery location
curl -X PATCH http://localhost:8004/delivery/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "picked_up", "current_location": "En route - 5th Ave & 34th St", "estimated_minutes": 20}'
```

---

## How to Run Tests

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx fastapi uvicorn pydantic \
  python-jose passlib bcrypt aiosqlite prometheus-fastapi-instrumentator \
  prometheus-client python-multipart

# Run all tests
pytest tests/ -v

# Run a specific service test
pytest tests/test_user_service.py -v

# Run against live docker-compose stack
USER_SERVICE_URL=http://localhost:8001 \
RESTAURANT_SERVICE_URL=http://localhost:8002 \
ORDER_SERVICE_URL=http://localhost:8003 \
DELIVERY_SERVICE_URL=http://localhost:8004 \
pytest tests/ -v
```

---

## Project Structure

```
01-food-delivery-eks-platform/
├── services/
│   ├── user-service/           # JWT auth, user registration/login (port 8001)
│   │   ├── main.py             # FastAPI app, routes
│   │   ├── database.py         # SQLite init + seed data
│   │   ├── auth.py             # JWT helpers (python-jose)
│   │   ├── requirements.txt
│   │   ├── Dockerfile          # Multi-stage, non-root
│   │   └── .dockerignore
│   ├── restaurant-service/     # Restaurant + menu catalog (port 8002)
│   ├── order-service/          # Order placement, failure mode (port 8003)
│   ├── delivery-service/       # Delivery agent assignment (port 8004)
│   └── frontend/               # Single-page React app via CDN
├── nginx/
│   └── nginx.conf              # Reverse proxy, gzip, response time logging
├── monitoring/
│   ├── prometheus.yml          # Scrape configs for all 4 services
│   ├── grafana-dashboard.json  # Pre-built dashboard (import manually or auto-provisioned)
│   ├── grafana-datasource.yml  # Auto-provisioned Prometheus datasource
│   └── grafana-dashboard-provider.yml
├── infra/terraform/
│   ├── modules/
│   │   ├── vpc/                # VPC, subnets, IGW, NAT, route tables
│   │   ├── eks/                # EKS cluster + node group + IAM roles
│   │   ├── ecr/                # 4 ECR repos, scan on push, lifecycle policy
│   │   └── iam/                # GitHub Actions IAM user + least-privilege policy
│   ├── main.tf                 # Root module — wires everything together
│   ├── variables.tf
│   ├── outputs.tf
│   ├── backend.tf              # Local by default, S3 commented out
│   └── terraform.tfvars.example
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml          # Service URLs for inter-service communication
│   ├── *-deployment.yaml       # 4 deployments (2 replicas, rolling update)
│   ├── *-service.yaml          # 4 ClusterIP services
│   ├── *-hpa.yaml              # 4 HPAs (min=2, max=6, CPU=70%)
│   ├── ingress/ingress.yaml    # NGINX ingress routing
│   └── monitoring/prometheus-values.yaml  # Helm values for kube-prometheus-stack
├── .github/workflows/
│   ├── deploy.yml              # Push to main → detect changes → build → deploy
│   ├── pr-checks.yml           # lint + test + terraform fmt/validate
│   └── destroy.yml             # Manual teardown with confirmation
├── tests/
│   ├── conftest.py
│   ├── test_user_service.py
│   ├── test_restaurant_service.py
│   ├── test_order_service.py
│   └── test_delivery_service.py
├── scripts/
│   ├── bootstrap.sh            # docker compose up + health checks + print URLs
│   ├── deploy-eks.sh           # Full EKS deploy script
│   └── load-test.sh            # 300 concurrent order requests
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## What This Teaches

| Concept | Where You'll See It |
|---|---|
| Microservice communication | order-service calls restaurant-service with httpx (5s timeout) |
| JWT authentication | user-service issues HS256 tokens, protected endpoints verify them |
| Custom Prometheus metrics | orders_total counter, order_processing_seconds histogram, failed_orders_total |
| Chaos engineering | ORDER_SERVICE_FAILURE_MODE injects 50% failures, observable in Grafana |
| Multi-stage Docker builds | All 4 service Dockerfiles: builder stage + slim final stage |
| Non-root containers | UID 1001 appuser in every service container |
| Kubernetes HPA | CPU-based autoscaling from 2 to 6 replicas per service |
| Rolling deployments | maxSurge=1, maxUnavailable=0 — zero-downtime updates |
| Terraform modules | vpc / eks / ecr / iam modules with clean input/output contracts |
| Least-privilege IAM | GitHub Actions user gets only the ECR + EKS permissions it needs |
| ECR lifecycle policies | Keep last 10 images, scan on push to catch CVEs |
| GitOps change detection | deploy.yml only builds the service whose files actually changed |
| Observability provisioning | Grafana datasource + dashboard auto-provisioned via YAML |

---

## Real Challenges and Solutions

1. **Inter-service communication failure** — When order-service can't reach restaurant-service (network partition, slow start), the 5-second httpx timeout prevents request pile-up. The error bubbles up as HTTP 503 with a clear message, and the failed_orders_total counter increments so Grafana can alert.

2. **Database isolation per service** — Each service owns a separate SQLite file mounted as a Docker volume. This enforces service boundaries and makes it obvious that in production, each service would have its own RDS instance. Migrations are handled by init_db() on startup.

3. **Startup ordering in docker-compose** — Services use `depends_on: condition: service_healthy` so the order-service waits for restaurant-service to be serving traffic before accepting requests, preventing startup race conditions.

4. **JWT secret management** — The JWT secret is injected as an environment variable (not hardcoded). The .env.example documents it, and the Kubernetes manifests show how it would be wired as a Secret in production. The same key works across multiple user-service replicas.

5. **Non-root containers failing to write DB** — The SQLite database is mounted to /data which is chowned to the appuser before the USER instruction in the Dockerfile. The data directory is created by docker-compose volumes, and the volume mount gives the container write access.

6. **Terraform EKS node connectivity** — EKS worker nodes run in private subnets and need the NAT Gateway to pull ECR images and reach the Kubernetes API. The VPC module creates a single NAT Gateway in the first public subnet, and the private route table routes 0.0.0.0/0 through it.

7. **Prometheus scraping inside Docker Compose** — Services register their /metrics endpoint via prometheus-fastapi-instrumentator on startup. The prometheus.yml uses Docker DNS names (user-service:8001) which resolve within the food-delivery-network bridge network.

8. **GitHub Actions only deploys changed services** — The deploy workflow uses `git diff HEAD~1 HEAD` to check which service directories changed, then uses a matrix strategy to only build and deploy the affected services, keeping CI fast and avoiding unnecessary ECR pushes.

---

## Contact

- YouTube: [@ThinkWithOps](https://youtube.com/@ThinkWithOps)
- GitHub: [vijayb-aiops](https://github.com/vijayb-aiops)
