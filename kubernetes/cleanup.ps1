# Loan Processing System - Kubernetes Cleanup Script
# This script helps clean up Kubernetes resources for the Loan Processing System

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
Write-ColorOutput Green "      Loan Processing System - Kubernetes Cleanup Tool        "
Write-ColorOutput Green "==============================================================="
Write-ColorOutput Yellow "This script will remove Kubernetes resources for the Loan Processing System."

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
    Write-ColorOutput Yellow "Namespace 'loan-system' does not exist. Nothing to clean up."
    exit 0
}

# Prompt for confirmation
Write-ColorOutput Red "WARNING: This will delete all resources in the 'loan-system' namespace."
Write-ColorOutput Red "This action is irreversible and will result in data loss."
$confirm = Read-Host "Are you sure you want to continue? (yes/no)"

if ($confirm -ne "yes") {
    Write-ColorOutput Yellow "Cleanup cancelled."
    exit 0
}

# Delete resources
Write-ColorOutput Yellow "Deleting resources in the 'loan-system' namespace..."

# Option to delete specific resources or the entire namespace
$delete_option = Read-Host "Delete entire namespace (1) or specific resources (2)? (1/2)"

if ($delete_option -eq "1") {
    # Delete the entire namespace
    Write-ColorOutput Yellow "Deleting the entire 'loan-system' namespace..."
    kubectl delete namespace loan-system
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput Red "✗ Failed to delete namespace"
        exit 1
    }
    
    Write-ColorOutput Green "✓ Namespace 'loan-system' deleted successfully"
} else {
    # Delete specific resources
    Write-ColorOutput Yellow "Deleting deployments..."
    kubectl delete deployment -n loan-system --all
    
    Write-ColorOutput Yellow "Deleting services..."
    kubectl delete service -n loan-system --all
    
    Write-ColorOutput Yellow "Deleting configmaps..."
    kubectl delete configmap -n loan-system --all
    
    Write-ColorOutput Yellow "Deleting secrets..."
    kubectl delete secret -n loan-system --all
    
    Write-ColorOutput Yellow "Deleting ingress..."
    kubectl delete ingress -n loan-system --all
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput Red "✗ Failed to delete some resources"
    } else {
        Write-ColorOutput Green "✓ Resources deleted successfully"
    }
    
    # Prompt to delete the namespace
    $delete_namespace = Read-Host "Delete the 'loan-system' namespace as well? (y/n)"
    if ($delete_namespace -eq "y") {
        kubectl delete namespace loan-system
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput Red "✗ Failed to delete namespace"
        } else {
            Write-ColorOutput Green "✓ Namespace 'loan-system' deleted successfully"
        }
    }
}

Write-ColorOutput Green "==============================================================="
Write-ColorOutput Green "      Cleanup Complete!                                      "
Write-ColorOutput Green "==============================================================="
