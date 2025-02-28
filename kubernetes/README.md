# Loan Processing System - Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Loan Processing System on a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (local or cloud-based)
- kubectl CLI tool installed and configured
- Docker images for all services built and pushed to a registry

## Directory Structure

```
kubernetes/
├── manifests/
│   ├── namespace.yaml                  # Namespace definition
│   ├── configmap.yaml                  # Configuration values
│   ├── secrets.yaml                    # Sensitive information (credentials, API keys)
│   ├── infrastructure.yaml             # RabbitMQ and Redis deployments
│   ├── loan-request-service.yaml       # Loan request service deployment
│   ├── credit-check-service.yaml       # Credit check service deployment
│   ├── property-evaluation-service.yaml # Property evaluation service deployment
│   ├── decision-service.yaml           # Decision service deployment
│   ├── notification-service.yaml       # Notification service deployment
│   ├── celery-worker.yaml              # Celery worker deployment
│   ├── monitoring.yaml                 # Prometheus and Grafana deployments
│   ├── ingress.yaml                    # Ingress configuration for external access
│   ├── autoscaling.yaml                # Horizontal Pod Autoscaler configurations
│   ├── network-policies.yaml           # Network policies for securing service communication
│   ├── persistent-volumes.yaml         # Persistent Volume Claims for data storage
│   └── dashboard-admin.yaml            # Kubernetes dashboard admin configuration
├── deploy.ps1                          # Deployment script
├── cleanup.ps1                         # Cleanup script
├── monitor.ps1                         # Monitoring script
├── build-images.ps1                    # Docker image build script
├── setup-minikube.ps1                  # Minikube setup script
└── README.md                           # This file
```

## Deployment Instructions

### 1. Build and Push Docker Images

Before deploying to Kubernetes, you need to build and push your Docker images to a registry:

```bash
# Set your Docker registry (replace with your actual registry)
export DOCKER_REGISTRY=your-registry.com

# Build and push images for each service
docker build -t $DOCKER_REGISTRY/loan-request-service:latest -f services/loan_request/Dockerfile .
docker push $DOCKER_REGISTRY/loan-request-service:latest

# Repeat for other services
docker build -t $DOCKER_REGISTRY/credit-check-service:latest -f services/credit_check/Dockerfile .
docker push $DOCKER_REGISTRY/credit-check-service:latest

docker build -t $DOCKER_REGISTRY/property-evaluation-service:latest -f services/property_evaluation/Dockerfile .
docker push $DOCKER_REGISTRY/property-evaluation-service:latest

docker build -t $DOCKER_REGISTRY/decision-service:latest -f services/decision/Dockerfile .
docker push $DOCKER_REGISTRY/decision-service:latest

docker build -t $DOCKER_REGISTRY/notification-service:latest -f services/notification/Dockerfile .
docker push $DOCKER_REGISTRY/notification-service:latest

docker build -t $DOCKER_REGISTRY/celery-worker:latest -f docker/celery/Dockerfile .
docker push $DOCKER_REGISTRY/celery-worker:latest
```

Alternatively, you can use the `build-images.ps1` script to build and push images:

```bash
# Build Docker images
./build-images.ps1
```

### 2. Update Image References (if needed)

If you're using a private Docker registry, update the image references in the deployment YAML files:

```bash
# Example: Update image references in all deployment files
sed -i 's|${DOCKER_REGISTRY:-localhost}|your-registry.com|g' kubernetes/manifests/*.yaml
```

### 3. Update Secrets

Edit the `secrets.yaml` file to include your actual secret values:

```bash
# Edit the secrets file
nano kubernetes/manifests/secrets.yaml
```

### 4. Deploy to Kubernetes

Apply the manifests in the following order:

```bash
# Create namespace
kubectl apply -f kubernetes/manifests/namespace.yaml

# Create ConfigMaps and Secrets
kubectl apply -f kubernetes/manifests/configmap.yaml
kubectl apply -f kubernetes/manifests/secrets.yaml

# Deploy infrastructure components
kubectl apply -f kubernetes/manifests/infrastructure.yaml

# Deploy application services
kubectl apply -f kubernetes/manifests/loan-request-service.yaml
kubectl apply -f kubernetes/manifests/credit-check-service.yaml
kubectl apply -f kubernetes/manifests/property-evaluation-service.yaml
kubectl apply -f kubernetes/manifests/decision-service.yaml
kubectl apply -f kubernetes/manifests/notification-service.yaml
kubectl apply -f kubernetes/manifests/celery-worker.yaml

# Deploy monitoring
kubectl apply -f kubernetes/manifests/monitoring.yaml

# Deploy ingress (if using)
kubectl apply -f kubernetes/manifests/ingress.yaml
```

Alternatively, you can apply all manifests at once:

```bash
kubectl apply -f kubernetes/manifests/
```

### 5. Verify Deployment

Check if all pods are running:

```bash
kubectl get pods -n loan-system
```

Check services:

```bash
kubectl get services -n loan-system
```

### 6. Access the Application

If you're using Ingress:

1. Add the following entries to your `/etc/hosts` file (for local development):
   ```
   127.0.0.1 loan-system.local
   127.0.0.1 monitoring.loan-system.local
   ```

2. Access the application at:
   - Main application: http://loan-system.local
   - Monitoring: http://monitoring.loan-system.local

If you're not using Ingress, you can use port-forwarding to access the services:

```bash
# Forward the loan-request-service port
kubectl port-forward -n loan-system svc/loan-request-service 8000:8000
```

## Monitoring and Management

The Loan Processing System includes several scripts to help with monitoring and managing the Kubernetes deployment:

### Setup Minikube (Local Development)

For local development, you can use Minikube to set up a local Kubernetes cluster:

```bash
# Set up Minikube
./setup-minikube.ps1
```

This script will:
- Check if Minikube and kubectl are installed
- Configure and start Minikube with appropriate resources
- Enable necessary Minikube addons (ingress, metrics-server, dashboard)
- Configure kubectl to use Minikube

### Build Docker Images

Before deploying, you need to build Docker images for your services:

```bash
# Build Docker images
./build-images.ps1
```

This script will:
- Build Docker images for all services
- Optionally push images to a registry
- Support building directly in Minikube's Docker daemon

### Monitor Deployment

To monitor your deployment, use the monitoring script:

```bash
# Monitor deployment
./monitor.ps1
```

This script provides a menu-driven interface to:
- View pods, services, deployments, and other resources
- View logs for specific pods
- Port-forward to services for local access
- View resource usage (CPU, memory)
- Access Grafana, Prometheus, and RabbitMQ dashboards

## Advanced Features

### Autoscaling

The deployment includes Horizontal Pod Autoscalers (HPAs) for all services, which automatically scale the number of pods based on CPU and memory usage. The configuration is in `manifests/autoscaling.yaml`.

### Network Policies

Network policies are defined in `manifests/network-policies.yaml` to secure communication between services. These policies:
- Deny all ingress and egress traffic by default
- Allow specific ingress traffic between services based on their dependencies
- Allow egress traffic to infrastructure components (RabbitMQ, Redis)

### Persistent Storage

Persistent Volume Claims are defined in `manifests/persistent-volumes.yaml` to provide persistent storage for:
- RabbitMQ data
- Redis data
- Prometheus data
- Grafana data

### Kubernetes Dashboard

To access the Kubernetes Dashboard, first apply the dashboard admin configuration:

```bash
kubectl apply -f kubernetes/manifests/dashboard-admin.yaml
```

Then, get the token for the admin user:

```bash
kubectl -n kubernetes-dashboard create token admin-user
```

Use this token to log in to the Kubernetes Dashboard.

## Scaling

To scale a service, use the kubectl scale command:

```bash
# Example: Scale the loan-request-service to 3 replicas
kubectl scale deployment -n loan-system loan-request-service --replicas=3
```

## Troubleshooting

To view logs for a specific service:

```bash
# Get pod names
kubectl get pods -n loan-system

# View logs for a specific pod
kubectl logs -n loan-system <pod-name>

# Follow logs
kubectl logs -n loan-system <pod-name> -f
```

To describe a pod and see its events:

```bash
kubectl describe pod -n loan-system <pod-name>
```

## Cleanup

To remove the entire deployment:

```bash
kubectl delete namespace loan-system
```
