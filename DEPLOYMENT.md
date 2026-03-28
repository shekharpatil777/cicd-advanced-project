# Deployment Guide

This guide provides step-by-step instructions for deploying the CI/CD Advanced Project to production.

## Prerequisites

Ensure you have the following installed:
- Docker
- Kubernetes CLI (kubectl)
- Git
- AWS CLI
- Terraform
- eksctl (optional but recommended)

## Quick Start (5 minutes)

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/cicd-advanced-project.git
cd cicd-advanced-project

# Make setup script executable
chmod +x setup.sh

# Run setup (interactive)
./setup.sh
```

### 2. Verify Deployment

```bash
# Check ArgoCD sync
kubectl port-forward -n argocd svc/argocd-server 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (shown in setup output)

# Check application pods
kubectl get pods
kubectl logs -f deployment/cicd-app
```

## Step-by-Step Manual Deployment

### Step 1: Prerequisites Setup

```bash
# Update configuration
export DOCKER_USERNAME="your-docker-username"
export GITHUB_USERNAME="your-github-username"
export REPO_NAME="cicd-advanced-project"
export AWS_REGION="us-east-1"

# Update all config files
sed -i "s/your-dockerhub-username/$DOCKER_USERNAME/g" \
  Dockerfile Jenkinsfile k8s/canary-deployment.yaml k8s/deployment.yaml

sed -i "s|https://github.com/your-username/cicd-devops-project.git|https://github.com/$GITHUB_USERNAME/$REPO_NAME.git|g" \
  argocd-app.yaml
```

### Step 2: Push to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Advanced CI/CD Project"

# Add remote repository
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 3: Setup AWS Infrastructure

#### Option A: Using Terraform

```bash
cd terraform/

# Initialize Terraform
terraform init -var="aws_region=$AWS_REGION"

# Review plan
terraform plan -var="aws_region=$AWS_REGION"

# Apply configuration
terraform apply -var="aws_region=$AWS_REGION"

cd ..
```

#### Option B: Using eksctl (Faster)

```bash
# Create EKS cluster
eksctl create cluster \
  --name cicd-app-cluster \
  --region $AWS_REGION \
  --nodes 3 \
  --node-type t3.medium \
  --enable-ssm

# Get kubeconfig
aws eks update-kubeconfig \
  --region $AWS_REGION \
  --name cicd-app-cluster
```

### Step 4: Configure Kubernetes

```bash
# Verify cluster connection
kubectl cluster-info
kubectl get nodes

# Create namespaces
kubectl create namespace default
kubectl create namespace argocd
kubectl create namespace monitoring
```

### Step 5: Install ArgoCD

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s \
  deployment/argocd-server -n argocd

# Port forward to access UI
kubectl port-forward -n argocd svc/argocd-server 8080:443 &

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Change password (recommended)
argocd account update-password \
  --account admin \
  --new-password "your-new-password"
```

### Step 6: Deploy Secrets and Application

```bash
# Deploy Kubernetes secrets
kubectl apply -f k8s/secret.yaml

# Deploy application via ArgoCD
kubectl apply -f argocd-app.yaml

# Monitor sync
kubectl get application -n argocd
kubectl describe application cicd-app -n argocd

# Check pod status
kubectl get pods
kubectl logs -f deployment/cicd-app
```

### Step 7: Setup Jenkins Pipeline

#### Jenkins Configuration

1. **Create Jenkins Job**
   - Go to Jenkins dashboard
   - Create new item → Pipeline
   - Name: `cicd-app-pipeline`

2. **Configure Pipeline**
   - Pipeline section → Definition: Pipeline script from SCM
   - SCM: Git
   - Repository URL: `https://github.com/$GITHUB_USERNAME/$REPO_NAME.git`
   - Branch: `*/main`
   - Script path: `Jenkinsfile`

3. **Add Credentials**
   - Manage Jenkins → Manage Credentials
   - Add credentials:
     - **Docker Hub**: Username with password
       - Username: `dockerhub-credentials-id`
     - **Kubernetes**: Secret file
       - File: `kubeconfig`
       - ID: `kubeconfig-credential-id`
     - **GitHub**: Personal access token
       - Token: `github-token`

4. **Configure GitHub Webhook**
   - GitHub repo → Settings → Webhooks → Add webhook
   - Payload URL: `http://jenkins.example.com/github-webhook/`
   - Events: Push events

### Step 8: Deploy Monitoring

```bash
# Deploy Prometheus ConfigMap
kubectl apply -f monitoring/prometheus.yaml

# Port forward to access Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090 &

# Access at http://localhost:9090
```

## Deployment Flow

```
Code Push to GitHub
    ↓ (webhook triggers)
Jenkins Pipeline
    ↓
Build Docker image
Push to Docker Hub
    ↓
Deploy to Canary
    ↓
Run smoke tests
    ↓
Manual approval
    ↓
Update deployment.yaml
Push to GitHub
    ↓ (ArgoCD detects change)
ArgoCD Sync
    ↓
Rolling update to Production
    ↓
Monitoring and Logging
```

## Testing the Deployment

### 1. Test Application Endpoints

```bash
# Get LoadBalancer IP
kubectl get svc cicd-app

# Test endpoints
export APP_URL="http://<EXTERNAL-IP>"

curl $APP_URL/               # Main endpoint
curl $APP_URL/health         # Health check
curl $APP_URL/ready          # Readiness check
curl $APP_URL/version        # Version info
```

### 2. Test Canary Deployment

```bash
# Deploy new version
kubectl set image deployment/cicd-app-canary \
  cicd-app=your-dockerhub-username/cicd-app:new-version

# Monitor canary
kubectl logs -f deployment/cicd-app-canary

# Check metrics
kubectl top pods -l version=canary
```

### 3. Test Secrets Access

```bash
# Verify secret is mounted
kubectl exec -it deployment/cicd-app -- \
  sh -c 'echo $MY_SECRET'

# Should output the secret value
```

## Troubleshooting

### Pod won't start

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # If crashed

# Check resource limits
kubectl top pod <pod-name>
```

### ImagePullBackOff

```bash
# Check image exists in registry
docker pull your-dockerhub-username/cicd-app:latest

# Check image pull secrets
kubectl get secrets
kubectl get imagepullsecrets

# Create pull secret if needed
kubectl create secret docker-registry dockerhub \
  --docker-server=docker.io \
  --docker-username=USERNAME \
  --docker-password=PASSWORD \
  --docker-email=EMAIL
```

### ArgoCD sync issues

```bash
# Check ArgoCD application status
kubectl get application -n argocd
kubectl describe application cicd-app -n argocd

# Check ArgoCD controller logs
kubectl logs -n argocd deployment/argocd-application-controller

# Force sync
argocd app sync cicd-app
```

### Jenkins pipeline failures

```bash
# Check Jenkins logs
kubectl logs -f deployment/jenkins

# Verify credentials
# Jenkins UI → Credentials → Verify each credential

# Verify kubeconfig
kubectl config view  # Ensure it's valid

# Test docker login
docker login -u USERNAME
```

## Scaling the Application

### Scale Deployment

```bash
# Scale production deployment
kubectl scale deployment cicd-app --replicas=5

# Verify scaling
kubectl get deployment cicd-app
```

### Auto-scaling

```bash
# Install metrics-server
kubectl apply -f \
  https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create HPA
kubectl autoscale deployment cicd-app \
  --min=2 --max=10 \
  --cpu-percent=80

# Check HPA status
kubectl get hpa
```

## Monitoring and Logging

### View Application Logs

```bash
# Real-time logs
kubectl logs -f deployment/cicd-app

# Last 100 lines
kubectl logs deployment/cicd-app --tail=100

# Previous logs (if pod restarted)
kubectl logs deployment/cicd-app --previous
```

### Monitor with Prometheus

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Query examples:
# - Container restarts: rate(container_last_termination_reason_count[1h])
# - CPU usage: sum(rate(container_cpu_usage_seconds_total[5m]))
# - Memory usage: sum(container_memory_working_set_bytes)
```

## Cleanup

### Delete entire deployment

```bash
# Delete ArgoCD application (cascades to resources)
kubectl delete application cicd-app -n argocd

# Delete namespaces
kubectl delete namespace argocd monitoring

# Destroy infrastructure (if using Terraform)
cd terraform/
terraform destroy -var="aws_region=$AWS_REGION"
```

## Backup and Recovery

### Backup ArgoCD configuration

```bash
# Export ArgoCD state
kubectl get application -n argocd -o yaml > argocd-backup.yaml

# Backup etcd
kubectl exec -n kube-system etcd-master \
  -- etcdctl snapshot save /tmp/etcd-backup.db
```

### Restore from backup

```bash
# Apply ArgoCD configuration
kubectl apply -f argocd-backup.yaml

# Restore etcd
kubectl exec -n kube-system etcd-master \
  -- etcdctl snapshot restore /tmp/etcd-backup.db
```

## Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)

---

**Last Updated**: March 28, 2026
**Version**: 1.0.0
