#!/bin/bash

# CICD Advanced Project - Setup Script
# This script helps initialize and deploy the entire CI/CD infrastructure

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    print_success "$1 found"
    return 0
}

# Main setup
print_header "CI/CD Advanced Project Setup"

# Check prerequisites
print_header "Checking Prerequisites"
MISSING_TOOLS=0

check_command "docker" || MISSING_TOOLS=1
check_command "git" || MISSING_TOOLS=1
check_command "kubectl" || MISSING_TOOLS=1
check_command "terraform" || MISSING_TOOLS=1
check_command "aws" || MISSING_TOOLS=1

if [ $MISSING_TOOLS -eq 1 ]; then
    print_error "Some required tools are missing. Please install them first."
    exit 1
fi

# Collect user input
print_header "Configuration"

read -p "Enter your Docker Hub username: " DOCKER_USERNAME
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your GitHub repository name: " REPO_NAME
read -p "Enter AWS region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Update configuration files
print_header "Updating Configuration Files"

# Update Dockerfile
sed -i "s|your-dockerhub-username|$DOCKER_USERNAME|g" Dockerfile
print_success "Updated Dockerfile"

# Update Jenkinsfile
sed -i "s|your-dockerhub-username|$DOCKER_USERNAME|g" Jenkinsfile
print_success "Updated Jenkinsfile"

# Update K8s manifests
sed -i "s|your-dockerhub-username|$DOCKER_USERNAME|g" k8s/canary-deployment.yaml
sed -i "s|your-dockerhub-username|$DOCKER_USERNAME|g" k8s/deployment.yaml
print_success "Updated K8s manifests"

# Update ArgoCD config
sed -i "s|https://github.com/your-username/cicd-devops-project.git|https://github.com/$GITHUB_USERNAME/$REPO_NAME.git|g" argocd-app.yaml
print_success "Updated ArgoCD configuration"

# Initialize Git
print_header "Initializing Git Repository"

if [ -d ".git" ]; then
    print_warning "Git repository already exists"
else
    git init
    git add .
    git commit -m "Initial commit: Advanced CI/CD Project"
    print_success "Git repository initialized"
fi

# Setup Terraform
print_header "Setting up Terraform"

cd terraform/
terraform init -var="aws_region=$AWS_REGION"
print_success "Terraform initialized"

print_header "Plan Infrastructure"
print_warning "Review the Terraform plan below before applying:"
terraform plan -var="aws_region=$AWS_REGION" -out=tfplan

read -p "Apply Terraform plan? (yes/no): " APPLY_TF
if [ "$APPLY_TF" = "yes" ]; then
    terraform apply tfplan
    print_success "Infrastructure created"
else
    print_warning "Terraform plan not applied"
fi

cd ..

# Setup Kubernetes access
print_header "Configuring Kubernetes Access"

CLUSTER_NAME="cicd-app-cluster"
read -p "Enter EKS cluster name (default: $CLUSTER_NAME): " CUSTOM_CLUSTER_NAME
CLUSTER_NAME=${CUSTOM_CLUSTER_NAME:-$CLUSTER_NAME}

aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
print_success "Kubernetes access configured"

# Deploy ArgoCD
print_header "Deploying ArgoCD"

kubectl create namespace argocd || true
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
print_success "ArgoCD deployed"

print_warning "Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd || true

# Get ArgoCD admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
print_success "ArgoCD admin password: $ARGOCD_PASSWORD"

# Deploy Kubernetes secrets
print_header "Deploying Secrets"

kubectl apply -f k8s/secret.yaml
print_success "Kubernetes secrets deployed"

# Deploy application via ArgoCD
print_header "Deploying Application"

kubectl apply -f argocd-app.yaml
print_success "ArgoCD application created"

print_header "Setup Complete!"

echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Push to GitHub:"
echo "   git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "2. Access ArgoCD UI:"
echo "   kubectl port-forward -n argocd svc/argocd-server 8080:443"
echo "   Open: https://localhost:8080"
echo "   Username: admin"
echo "   Password: $ARGOCD_PASSWORD"
echo ""
echo "3. Check deployment status:"
echo "   kubectl get pods"
echo "   kubectl logs -f deployment/cicd-app"
echo ""
echo "4. Setup Jenkins pipeline with this repository"
echo ""

print_success "All done!"
