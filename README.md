# Loan Processing Microservices System

A distributed loan processing system built with microservices architecture, using FastAPI, Celery, RabbitMQ, and Redis.

## Prerequisites

- Docker and Docker Compose
- Git
- Make (optional, for Makefile usage)
- Minikube (for Kubernetes deployment)
- kubectl (for Kubernetes deployment)

## Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd loan-processing-system
```

2. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

3. Configure your environment variables (see Environment Variables section below)

## Running the System (Docker Compose)

1. Start all services:

```bash
docker-compose up -d
```

2. Check service health:

```bash
docker-compose ps
```

3. Access service endpoints:
   - Loan Request Service: http://localhost:8000
   - Credit Check Service: http://localhost:8001
   - Property Evaluation Service: http://localhost:8002
   - Decision Service: http://localhost:8003
   - Notification Service: http://localhost:8004

## Kubernetes Deployment Guide

This section provides step-by-step instructions for building Docker images and deploying the Loan Processing System on a Kubernetes cluster using Minikube.

### Setting Up Minikube

#### 1. Start Minikube with appropriate resources

```bash
minikube start --cpus=2 --memory=4096 --disk-size=20g --driver=docker
```

#### 2. Enable required Minikube addons

```bash
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard
```

#### 3. Configure Docker to use Minikube's Docker daemon

```bash
# For Linux/macOS
eval $(minikube -p minikube docker-env)

# For PowerShell
& minikube -p minikube docker-env | Invoke-Expression
```

### Building Docker Images

#### 1. Build the Loan Request Service Image

```bash
docker build -t localhost/loan-request-service:latest -f ../services/loan_request/Dockerfile ..
```

#### 2. Build the Credit Check Service Image

```bash
docker build -t localhost/credit-check-service:latest -f ../services/credit_check/Dockerfile ..
```

#### 3. Build the Property Evaluation Service Image

```bash
docker build -t localhost/property-evaluation-service:latest -f ../services/property_evaluation/Dockerfile ..
```

#### 4. Build the Decision Service Image

```bash
docker build -t localhost/decision-service:latest -f ../services/decision/Dockerfile ..
```

#### 5. Build the Notification Service Image

```bash
docker build -t localhost/notification-service:latest -f ../services/notification/Dockerfile ..
```

#### 6. Build the Celery Worker Image

```bash
docker build -t localhost/celery-worker:latest -f ../docker/celery/Dockerfile ..
```

#### 7. Verify Docker Images

```bash
docker images
```

### Deploying to Kubernetes

#### 1. Create Namespace

```bash
kubectl apply -f kubernetes/manifests/namespace.yaml
```

#### 2. Create Persistent Volumes

```bash
kubectl apply -f kubernetes/manifests/persistent-volumes.yaml
```

#### 3. Create ConfigMaps and Secrets

```bash
kubectl apply -f kubernetes/manifests/configmap.yaml
kubectl apply -f kubernetes/manifests/secrets.yaml
```

#### 4. Deploy Infrastructure Components

```bash
kubectl apply -f kubernetes/manifests/infrastructure.yaml
```

Wait for infrastructure components to be ready (approximately 15 seconds)

```bash
kubectl get pods -n loan-system
```

#### 5. Deploy Monitoring Stack

```bash
kubectl apply -f kubernetes/manifests/monitoring.yaml
```

#### 6. Deploy Application Services

```bash
# Deploy services individually
kubectl apply -f kubernetes/manifests/loan-request-service.yaml
kubectl apply -f kubernetes/manifests/credit-check-service.yaml
kubectl apply -f kubernetes/manifests/property-evaluation-service.yaml
kubectl apply -f kubernetes/manifests/decision-service.yaml
kubectl apply -f kubernetes/manifests/notification-service.yaml
kubectl apply -f kubernetes/manifests/celery-worker.yaml

# Or deploy multiple services at once
kubectl apply -f kubernetes/manifests/credit-check-service.yaml -f kubernetes/manifests/property-evaluation-service.yaml -f kubernetes/manifests/decision-service.yaml -f kubernetes/manifests/notification-service.yaml -f kubernetes/manifests/celery-worker.yaml
```

#### 7. Apply Network Policies

```bash
kubectl apply -f kubernetes/manifests/network-policies.yaml
```

#### 8. Configure Autoscaling

```bash
kubectl apply -f kubernetes/manifests/autoscaling.yaml
```

#### 9. Deploy Ingress

```bash
kubectl apply -f kubernetes/manifests/ingress.yaml
```

### Verifying the Deployment

#### 1. Check Pods Status

```bash
kubectl get pods -n loan-system
```

#### 2. Check Services

```bash
kubectl get services -n loan-system
```

#### 3. Check Persistent Volume Claims

```bash
kubectl get pvc -n loan-system
```

#### 4. Check Horizontal Pod Autoscalers

```bash
kubectl get hpa -n loan-system
```

#### 5. Check Network Policies

```bash
kubectl get networkpolicies -n loan-system
```

#### 6. Check Ingress

```bash
kubectl get ingress -n loan-system
```

#### 7. Open Kubernetes Dashboard

```bash
minikube dashboard --url
```

### Accessing the Application

#### Using Ingress (if configured)

- Main application: http://loan-system.local
- Monitoring: http://monitoring.loan-system.local

#### Using Port Forwarding (without Ingress)

```bash
kubectl port-forward -n loan-system svc/loan-request-service 8000:8000
```

Then access the application at: http://localhost:8000

### Monitoring the Application

#### Access Grafana Dashboard

```bash
kubectl port-forward -n loan-system svc/grafana 3000:3000
```

Then access Grafana at: http://localhost:3000

#### Access Prometheus Dashboard

```bash
kubectl port-forward -n loan-system svc/prometheus 9090:9090
```

Then access Prometheus at: http://localhost:9090

### Troubleshooting

#### Check Pod Logs

```bash
kubectl logs -n loan-system <pod-name>
```

#### Describe Pod for Detailed Information

```bash
kubectl describe pod -n loan-system <pod-name>
```

#### Restart a Deployment

```bash
kubectl rollout restart deployment -n loan-system <deployment-name>
```

### Cleanup

#### Delete All Resources in the Namespace

```bash
kubectl delete namespace loan-system
```

#### Stop Minikube

```bash
minikube stop
```

## Monitoring (Docker Compose)

- RabbitMQ Management: http://localhost:15672
  - Username: guest
  - Password: guest
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
  - Username: admin
  - Password: admin

## Shutting Down (Docker Compose)

```bash
docker-compose down
```

To remove all data (including volumes):

```bash
docker-compose down -v
```

## Environment Variables Explanation

Here's a detailed explanation of the environment variables needed in your `.env` file:

```env
# Market Data API Configuration
MARKET_DATA_API_KEY=your_api_key_here    # API key for property market data service

# Email Service Configuration
SMTP_HOST=smtp.example.com               # SMTP server hostname (e.g., smtp.gmail.com)
SMTP_PORT=587                             # SMTP port (587 for TLS, 465 for SSL)
SMTP_USERNAME=your_username               # SMTP account username
SMTP_PASSWORD=your_password               # SMTP account password
EMAIL_SENDER=noreply@yourdomain.com       # Email address used as sender

# RabbitMQ Configuration (optional, defaults provided)
RABBITMQ_USER=guest                       # RabbitMQ username
RABBITMQ_PASSWORD=guest                   # RabbitMQ password
RABBITMQ_HOST=rabbitmq                     # RabbitMQ hostname
RABBITMQ_PORT=5672                         # RabbitMQ AMQP port
RABBITMQ_VHOST=/                           # RabbitMQ virtual host

# Redis Configuration (optional, defaults provided)
REDIS_HOST=redis                           # Redis hostname
REDIS_PORT=6379                            # Redis port
REDIS_PASSWORD=                            # Redis password (if required)
REDIS_DB=0                                 # Redis database number

# Service Ports (optional, defaults provided)
LOAN_REQUEST_PORT=8000                     # Loan Request Service port
CREDIT_CHECK_PORT=8001                     # Credit Check Service port
PROPERTY_EVAL_PORT=8002                     # Property Evaluation Service port
DECISION_PORT=8003                          # Decision Service port
NOTIFICATION_PORT=8004                      # Notification Service port

# Monitoring Configuration (optional, defaults provided)
PROMETHEUS_PORT=9090                        # Prometheus port
GRAFANA_PORT=3000                           # Grafana port
GRAFANA_ADMIN_PASSWORD=admin                # Grafana admin password
```

### Required Variables
The following variables must be set for the system to function properly:
- `MARKET_DATA_API_KEY`: For property valuation service
- `SMTP_*` variables: For email notifications
- `EMAIL_SENDER`: For notification service

### Optional Variables
The other variables have default values but can be customized if needed:
- RabbitMQ configuration
- Redis configuration
- Service ports
- Monitoring configuration

You can create a `.env.example` file with these variables (using dummy values) to serve as a template for other developers.
