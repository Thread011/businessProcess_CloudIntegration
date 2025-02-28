# Loan Processing System - Kubernetes Monitoring Script
# This script helps monitor the Kubernetes deployment of the Loan Processing System

# Function to display colored output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Display banner
Write-ColorOutput Green "==============================================================="
Write-ColorOutput Green "      Loan Processing System - Kubernetes Monitoring Tool      "
Write-ColorOutput Green "==============================================================="
Write-ColorOutput Yellow "This script helps monitor the Kubernetes deployment of the Loan Processing System."

# Check if kubectl is installed
try {
    $kubectl_version = kubectl version --client --output=json
    Write-ColorOutput Green "✓ kubectl is installed"
} catch {
    Write-ColorOutput Red "✗ kubectl is not installed or not in PATH"
    Write-ColorOutput Red "Please install kubectl before continuing."
    exit 1
}

# Check if connected to a Kubernetes cluster
try {
    $cluster_info = kubectl cluster-info
    Write-ColorOutput Green "✓ Connected to Kubernetes cluster"
} catch {
    Write-ColorOutput Red "✗ Not connected to a Kubernetes cluster"
    Write-ColorOutput Red "Please configure kubectl to connect to a cluster before continuing."
    exit 1
}

# Check if namespace exists
$namespace_exists = kubectl get namespace loan-system 2>$null
if (-not $namespace_exists) {
    Write-ColorOutput Red "✗ Namespace 'loan-system' does not exist."
    Write-ColorOutput Yellow "Please deploy the Loan Processing System first using deploy.ps1."
    exit 1
}

# Function to display menu
function Show-Menu {
    Write-ColorOutput Green "==============================================================="
    Write-ColorOutput Green "                        MONITORING MENU                        "
    Write-ColorOutput Green "==============================================================="
    Write-ColorOutput Yellow "1. View all pods"
    Write-ColorOutput Yellow "2. View all services"
    Write-ColorOutput Yellow "3. View all deployments"
    Write-ColorOutput Yellow "4. View all persistent volume claims"
    Write-ColorOutput Yellow "5. View all ingresses"
    Write-ColorOutput Yellow "6. View all horizontal pod autoscalers"
    Write-ColorOutput Yellow "7. View pod logs"
    Write-ColorOutput Yellow "8. Describe pod"
    Write-ColorOutput Yellow "9. Port forward to a service"
    Write-ColorOutput Yellow "10. View resource usage"
    Write-ColorOutput Yellow "11. View events"
    Write-ColorOutput Yellow "12. Access Grafana dashboard"
    Write-ColorOutput Yellow "13. Access Prometheus dashboard"
    Write-ColorOutput Yellow "14. Access RabbitMQ management console"
    Write-ColorOutput Yellow "0. Exit"
    Write-ColorOutput Green "==============================================================="
}

# Function to view pod logs
function View-PodLogs {
    Write-ColorOutput Yellow "Available pods:"
    kubectl get pods -n loan-system
    $pod_name = Read-Host "Enter pod name"
    $container_name = Read-Host "Enter container name (leave empty if only one container)"
    $lines = Read-Host "Enter number of lines to show (default: 100)"
    if (-not $lines) {
        $lines = 100
    }
    
    if ($container_name) {
        kubectl logs -n loan-system $pod_name -c $container_name --tail=$lines
    } else {
        kubectl logs -n loan-system $pod_name --tail=$lines
    }
    
    $follow = Read-Host "Follow logs? (y/n)"
    if ($follow -eq "y") {
        if ($container_name) {
            kubectl logs -n loan-system $pod_name -c $container_name -f
        } else {
            kubectl logs -n loan-system $pod_name -f
        }
    }
}

# Function to describe pod
function Describe-Pod {
    Write-ColorOutput Yellow "Available pods:"
    kubectl get pods -n loan-system
    $pod_name = Read-Host "Enter pod name"
    kubectl describe pod -n loan-system $pod_name
}

# Function to port forward to a service
function Port-Forward {
    Write-ColorOutput Yellow "Available services:"
    kubectl get services -n loan-system
    $service_name = Read-Host "Enter service name"
    $local_port = Read-Host "Enter local port"
    $remote_port = Read-Host "Enter remote port"
    
    Write-ColorOutput Yellow "Starting port forwarding. Press Ctrl+C to stop."
    kubectl port-forward -n loan-system service/$service_name $local_port`:$remote_port
}

# Function to view resource usage
function View-ResourceUsage {
    Write-ColorOutput Yellow "Resource usage for pods:"
    kubectl top pods -n loan-system
    
    Write-ColorOutput Yellow "Resource usage for nodes:"
    kubectl top nodes
}

# Function to access Grafana dashboard
function Access-Grafana {
    Write-ColorOutput Yellow "Starting port forwarding to Grafana. Press Ctrl+C to stop."
    Write-ColorOutput Yellow "Access Grafana at http://localhost:3000"
    Write-ColorOutput Yellow "Username: admin"
    Write-ColorOutput Yellow "Password: admin"
    kubectl port-forward -n loan-system service/grafana 3000:3000
}

# Function to access Prometheus dashboard
function Access-Prometheus {
    Write-ColorOutput Yellow "Starting port forwarding to Prometheus. Press Ctrl+C to stop."
    Write-ColorOutput Yellow "Access Prometheus at http://localhost:9090"
    kubectl port-forward -n loan-system service/prometheus 9090:9090
}

# Function to access RabbitMQ management console
function Access-RabbitMQ {
    Write-ColorOutput Yellow "Starting port forwarding to RabbitMQ management console. Press Ctrl+C to stop."
    Write-ColorOutput Yellow "Access RabbitMQ management console at http://localhost:15672"
    Write-ColorOutput Yellow "Username: guest"
    Write-ColorOutput Yellow "Password: guest"
    kubectl port-forward -n loan-system service/rabbitmq 15672:15672
}

# Main loop
while ($true) {
    Show-Menu
    $choice = Read-Host "Enter your choice"
    
    switch ($choice) {
        "1" {
            Write-ColorOutput Yellow "Pods in loan-system namespace:"
            kubectl get pods -n loan-system -o wide
        }
        "2" {
            Write-ColorOutput Yellow "Services in loan-system namespace:"
            kubectl get services -n loan-system
        }
        "3" {
            Write-ColorOutput Yellow "Deployments in loan-system namespace:"
            kubectl get deployments -n loan-system
        }
        "4" {
            Write-ColorOutput Yellow "Persistent Volume Claims in loan-system namespace:"
            kubectl get pvc -n loan-system
        }
        "5" {
            Write-ColorOutput Yellow "Ingresses in loan-system namespace:"
            kubectl get ingress -n loan-system
        }
        "6" {
            Write-ColorOutput Yellow "Horizontal Pod Autoscalers in loan-system namespace:"
            kubectl get hpa -n loan-system
        }
        "7" {
            View-PodLogs
        }
        "8" {
            Describe-Pod
        }
        "9" {
            Port-Forward
        }
        "10" {
            View-ResourceUsage
        }
        "11" {
            Write-ColorOutput Yellow "Events in loan-system namespace:"
            kubectl get events -n loan-system --sort-by='.lastTimestamp'
        }
        "12" {
            Access-Grafana
        }
        "13" {
            Access-Prometheus
        }
        "14" {
            Access-RabbitMQ
        }
        "0" {
            Write-ColorOutput Green "Exiting..."
            exit 0
        }
        default {
            Write-ColorOutput Red "Invalid choice. Please try again."
        }
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
    Clear-Host
}
