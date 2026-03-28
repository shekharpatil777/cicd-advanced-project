# Deployment Guide

## Overview

This guide covers deploying the CI/CD + MLOps system to three environments:
1. **Local Development** (Docker Compose)
2. **Kubernetes** (Minikube or AWS EKS)
3. **Production** (AWS EKS + GitOps)

## Prerequisites

### Local Development
```bash
# Required
- Docker Desktop (with Docker Compose)
- Python 3.11+
- Git

# Optional
- curl (for testing APIs)
- make (for build commands)
```

### Kubernetes Deployment
```bash
# Required
- kubectl (v1.27+)
- Minikube (for local testing) OR AWS CLI configured
- Terraform (v1.5+, for AWS infrastructure)
- Git

# Recommended
- k9s (cluster monitoring)
- helm (package management)
```

---

## 1. Local Development (Docker Compose)

### Quick Start (5 minutes)

```bash
# Clone repository
git clone https://github.com/shekharpatil777/cicd-advanced-project.git
cd cicd-advanced-project

# Start services
docker-compose up -d

# Wait for services to be ready
docker-compose ps
# Status should show: "Up"

# Train ML model
docker-compose exec api python mlops/train.py

# Test API
curl http://localhost:5000/health
# Should return: {"status": "ok"}

# Make prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [45, 85000, 720, 250000, 8]
  }'

# View logs
docker-compose logs -f api

# Stop services
docker-compose down -v
```

### What's Running

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Flask API | 5000 | http://localhost:5000 | Application + ML serving |
| Prometheus | 9090 | http://localhost:9090 | Metrics collection |
| Grafana | 3000 | http://localhost:3000 | Dashboards (admin/admin) |
| PostgreSQL | 5432 | localhost:5432 | Database (optional) |

### Common Tasks

#### Train ML Model
```bash
docker-compose exec api python mlops/train.py
# Output:
# ============================================================
# Starting ML Training Pipeline
# ============================================================
# Loading training data...
# Loaded 1000 samples with 6 features
# ...
# Model saved to: models/v1.0_20240115_143022/
```

#### Check Prometheus Metrics
```bash
# In browser: http://localhost:9090

# Query examples:
# - requests_total (total API requests)
# - request_duration_seconds (latency)
# - model_predictions_total (prediction count)
```

#### View Grafana Dashboards
```bash
# In browser: http://localhost:3000
# Login: admin / admin
# Dashboards should auto-load
```

#### Run Tests
```bash
docker-compose exec api pytest app/tests/ -v --cov=app

# Output should show:
# PASSED - test_health_endpoint
# PASSED - test_predict_endpoint
# Coverage: 85%+
```

#### Debug API Issues
```bash
# View logs
docker-compose logs api

# Check container health
docker-compose exec api /bin/bash
# Inside container:
ps aux                  # Check running processes
ls -la models/latest/   # Check model files
python -c "import app; print('OK')"  # Check imports
```

---

## 2. Kubernetes with Minikube (Local Testing)

### Setup Minikube (10 minutes)

```bash
# Start Minikube cluster
minikube start --cpus 4 --memory 8192 --disk-size 20g

# Verify cluster is running
kubectl cluster-info
kubectl get nodes

# Enable metrics server (for HPA)
minikube addons enable metrics-server

# Enable ingress (for external access)
minikube addons enable ingress
```

### Deploy to Minikube

#### Step 1: Create Namespaces
```bash
kubectl create namespace cicd-app
kubectl create namespace monitoring
kubectl create namespace argocd
```

#### Step 2: Deploy Application
```bash
# Create ConfigMap with app config
kubectl create configmap app-config \
  --from-literal=ENVIRONMENT=development \
  -n cicd-app

# Deploy application
kubectl apply -f k8s/deployment.yaml -n cicd-app
kubectl apply -f k8s/service.yaml -n cicd-app
kubectl apply -f k8s/secret.yaml -n cicd-app

# Verify deployment
kubectl get pods -n cicd-app
kubectl get svc -n cicd-app

# Wait for pods to be ready
kubectl wait --for=condition=ready pod \
  -l app=cicd-app -n cicd-app --timeout=300s
```

#### Step 3: Deploy Monitoring
```bash
# Deploy Prometheus
kubectl apply -f monitoring/prometheus.yaml -n monitoring

# Deploy Grafana
kubectl apply -f monitoring/grafana.yaml -n monitoring

# Verify
kubectl get pods -n monitoring
```

#### Step 4: Train ML Model
```bash
# Option A: Interactive training
kubectl run -it ml-train \
  --image chandrashekharpatil/cicd-app:latest \
  --restart=Never \
  -n cicd-app \
  -- python mlops/train.py

# Option B: Background job (recommended)
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: cicd-app
spec:
  template:
    spec:
      containers:
      - name: trainer
        image: chandrashekharpatil/cicd-app:latest
        command: ["python", "mlops/train.py"]
      restartPolicy: Never
EOF

# Monitor training
kubectl logs -f job/ml-training -n cicd-app
```

### Access Services

#### Port Forwarding
```bash
# API
kubectl port-forward svc/cicd-app-service 5000:5000 -n cicd-app &

# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring &

# Now accessible:
# API:        http://localhost:5000
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000
```

#### Via Minikube Service
```bash
# Get external IPs/URLs
minikube service cicd-app-service -n cicd-app

# Or open in browser
minikube service -n monitoring grafana
```

### Test Deployment

```bash
# API health check
curl http://localhost:5000/health

# Get model info
curl http://localhost:5000/model-info

# Make prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [45, 85000, 720, 250000, 8]}'

# Check pod logs
kubectl logs deployment/cicd-app -n cicd-app

# Get pod details
kubectl describe pod <pod-name> -n cicd-app
```

### Canary Deployment Testing

```bash
# Deploy canary
kubectl apply -f k8s/canary-deployment.yaml -n cicd-app

# Monitor canary progress
kubectl describe canary cicd-app-canary -n cicd-app

# View Flagger logs
kubectl logs -n istio-system deployment/flagger

# Manually promote
kubectl patch canary cicd-app-canary \
  -n cicd-app \
  --type merge -p '{"status":{"phase":"Succeeded"}}'
```

### Cleanup

```bash
# Delete all deployments
kubectl delete namespace cicd-app monitoring argocd

# Stop Minikube
minikube stop

# Delete Minikube (warning: removes cluster)
minikube delete
```

---

## 3. Production Deployment (AWS EKS)

### Prerequisites

```bash
# AWS credentials configured
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Required tools
- Terraform v1.5+
- kubectl v1.27+
- AWS CLI v2
```

### Step 1: Create Infrastructure with Terraform

```bash
cd terraform/

# Initialize Terraform
terraform init

# Plan deployment (dry-run)
terraform plan -out=tfplan

# Review the plan, then apply
terraform apply tfplan

# Get outputs
terraform output

# Example outputs:
# cluster_endpoint = "https://xxx.eks.amazonaws.com"
# cluster_name = "cicd-app-cluster"
# node_iam_role_arn = "arn:aws:iam::xxx:role/eks-node-role"
```

### Step 2: Configure kubectl

```bash
# Get cluster credentials
aws eks update-kubeconfig \
  --name cicd-app-cluster \
  --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes

# Should show 3 nodes in Ready state
```

### Step 3: Setup ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available \
  --timeout=300s \
  deployment/argocd-server \
  -n argocd

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Port-forward to ArgoCD (optional)
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
# Access: https://localhost:8080 (login with admin/PASSWORD)
```

### Step 4: Configure ArgoCD Application

```bash
# Update argocd-app.yaml with your Git credentials
# Edit the repoURL to your forked repository
# repoURL: https://github.com/<YOUR-USERNAME>/cicd-advanced-project.git

# Deploy ArgoCD application
kubectl apply -f cicd/argocd-app.yaml

# Monitor sync
kubectl get applications -n argocd
kubectl describe application cicd-app -n argocd

# Wait for sync to complete
kubectl wait --for=condition=Synced \
  application/cicd-app \
  -n argocd \
  --timeout=300s
```

### Step 5: Verify Deployment

```bash
# Check pods
kubectl get pods -n cicd-app

# Check services
kubectl get svc -n cicd-app

# Get Load Balancer endpoint
kubectl get svc cicd-app-service -n cicd-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Test API
curl http://<LOAD_BALANCER_ENDPOINT>/health

# Check pod logs
kubectl logs deployment/cicd-app -n cicd-app
```

### Step 6: Deploy Monitoring Stack

```bash
# Install Prometheus
kubectl apply -f monitoring/prometheus.yaml -n monitoring

# Install Grafana
kubectl apply -f monitoring/grafana.yaml -n monitoring

# Get Grafana endpoint
kubectl get svc -n monitoring grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Login to Grafana with default credentials
# username: admin
# password: admin
```

### Step 7: Train ML Model

```bash
# Run training job
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training-prod
  namespace: cicd-app
spec:
  backoffLimit: 3
  template:
    spec:
      serviceAccountName: ml-trainer
      containers:
      - name: trainer
        image: chandrashekharpatil/cicd-app:latest
        command: ["python", "mlops/train.py"]
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      restartPolicy: Never
EOF

# Monitor training
kubectl logs -f job/ml-training-prod -n cicd-app

# Copy model to persistent storage
kubectl cp cicd-app/<POD-NAME>:/app/models ./models-backup
```

### Production Checklist

```
Pre-Deployment:
  ☐ Terraform plan reviewed
  ☐ All AWS resources tagged for cost tracking
  ☐ Backup of previous environment created
  ☐ Monitoring alerts configured
  ☐ Runbook updated

Deployment:
  ☐ Infrastructure created successfully
  ☐ All nodes in Ready state
  ☐ ArgoCD synced
  ☐ All pods running
  ☐ Load balancers created

Post-Deployment:
  ☐ Health checks passing
  ☐ ML model trained
  ☐ Metrics flowing to Prometheus
  ☐ Grafana dashboards showing data
  ☐ Alerts triggered on test
  ☐ Team notified
```

---

## CI/CD Pipeline Integration

### Jenkins to Kubernetes

The Jenkins pipeline automatically deploys to Kubernetes:

```groovy
// In Jenkinsfile:
stage('Deploy') {
  steps {
    sh '''
      # Get cluster credentials
      aws eks update-kubeconfig --name cicd-app-cluster

      # Deploy with kubectl
      kubectl set image deployment/cicd-app \
        cicd-app=chandrashekharpatil/cicd-app:${BUILD_NUMBER} \
        -n cicd-app

      # Wait for rollout
      kubectl rollout status deployment/cicd-app -n cicd-app
    '''
  }
}
```

### GitOps with ArgoCD

ArgoCD automatically syncs Kubernetes manifests from Git:

```bash
# Any Git commit to k8s/ triggers ArgoCD sync
git add k8s/deployment.yaml
git commit -m "Update deployment replicas"
git push origin main

# ArgoCD detects change within 3 minutes
# Automatically updates K8s deployment
# No manual kubectl apply needed!
```

---

## Scaling & Optimization

### Horizontal Pod Autoscaling

```bash
# Check current HPA status
kubectl get hpa -n cicd-app

# Manually scale
kubectl scale deployment/cicd-app --replicas=10 -n cicd-app

# Monitor scaling
kubectl get hpa -w -n cicd-app
```

### Load Balancer Configuration

```bash
# Get load balancer details
kubectl get svc cicd-app-service -n cicd-app -o yaml

# To change to NLB (Network Load Balancer):
kubectl patch svc cicd-app-service -n cicd-app \
  -p '{"spec":{"type":"LoadBalancer","externalTrafficPolicy":"Local"}}'
```

### Database Configuration

```bash
# Create RDS instance (optional)
aws rds create-db-instance \
  --db-instance-identifier cicd-app-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password "<PASSWORD>"

# Create secret in Kubernetes
kubectl create secret generic db-creds \
  --from-literal=host=<RDS-ENDPOINT> \
  --from-literal=user=admin \
  --from-literal=password=<PASSWORD> \
  -n cicd-app
```

---

## Troubleshooting

### Pod Fails to Start

```bash
# Get pod details
kubectl describe pod <POD-NAME> -n cicd-app

# Check logs
kubectl logs <POD-NAME> -n cicd-app
kubectl logs <POD-NAME> -n cicd-app --previous

# Check events
kubectl get events -n cicd-app --sort-by='.lastTimestamp'

# Common issues:
# - Image not found: Check Docker Hub image name
# - OOMKilled: Increase memory limits
# - CrashLoopBackOff: Check application logs for startup errors
```

### Cannot Connect to Service

```bash
# Check service exists
kubectl get svc -n cicd-app

# Check endpoints
kubectl get endpoints cicd-app-service -n cicd-app

# Test connectivity from pod
kubectl exec -it <POD-NAME> -n cicd-app -- /bin/bash
curl http://cicd-app-service:5000/health
```

### Model Not Loading

```bash
# Check model files exist
kubectl exec <POD-NAME> -n cicd-app -- ls -la models/latest/

# Check model can be loaded
kubectl exec <POD-NAME> -n cicd-app -- python -c "import joblib; joblib.load('models/latest/model.joblib')"

# Check disk space
kubectl exec <POD-NAME> -n cicd-app -- df -h
```

---

## Cost Optimization (AWS)

```bash
# Set Spot Instances for cost savings (vs On-Demand)
# In terraform/main.tf:
capacity_type = "SPOT"
# Saves ~70% on compute costs

# Set resource limits to prevent runaway costs
# In k8s/deployment.yaml:
resources:
  limits:
    cpu: "500m"
    memory: "512Mi"

# Monitor costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity DAILY \
  --metrics "BlendedCost"
```

---

## Disaster Recovery

### Backup Procedures

```bash
# Backup Kubernetes state
kubectl get all -A -o yaml > k8s-backup-$(date +%Y%m%d).yaml

# Backup persistent volumes
kubectl get pvc -A -o yaml > pvc-backup-$(date +%Y%m%d).yaml

# Backup secrets
kubectl get secrets -n cicd-app -o yaml > secrets-backup-$(date +%Y%m%d).yaml
```

### Restore Procedures

```bash
# Restore from backup
kubectl apply -f k8s-backup-20240115.yaml

# Verify restoration
kubectl get pods -n cicd-app

# Verify services
kubectl get svc -n cicd-app
```

---

## Next Steps

1. ✅ Deployment complete
2. Set up monitoring alerts
3. Configure log aggregation (ELK/CloudWatch)
4. Setup backup/restore procedures
5. Performance testing & optimization
6. Security hardening (network policies, RBAC)
