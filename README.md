![CI](https://img.shields.io/badge/CI-Jenkins-blue)
![CD](https://img.shields.io/badge/CD-ArgoCD-green)
![Container](https://img.shields.io/badge/Container-Docker-blue)
![Orchestration](https://img.shields.io/badge/Orchestration-Kubernetes-blue)
![Cloud](https://img.shields.io/badge/Cloud-AWS-orange)
![IaC](https://img.shields.io/badge/IaC-Terraform-purple)
![Monitoring](https://img.shields.io/badge/Monitoring-Prometheus-red)
![Visualization](https://img.shields.io/badge/Dashboard-Grafana-yellow)
![MLOps](https://img.shields.io/badge/MLOps-Enabled-brightgreen)

# Advanced CI/CD + GitOps + MLOps Project

A complete, production-ready DevOps project demonstrating:
- Jenkins CI/CD Pipeline
- Docker containerization
- Kubernetes (EKS ready)
- ArgoCD GitOps
- Terraform (AWS infrastructure)
- Prometheus + Grafana Monitoring
- Canary Deployment Strategy
- AWS Secrets Manager integration
- MLOps pipeline (basic)
- Security best practices

## Project Structure

```
├── app/                          # Flask application
│   ├── app.py                   # Main application with health/readiness endpoints
│   └── requirements.txt         # Python dependencies
├── k8s/                         # Kubernetes manifests
│   ├── deployment.yaml          # Production deployment with security configs
│   ├── canary-deployment.yaml   # Canary deployment for safe rollouts
│   ├── secret.yaml              # Kubernetes secrets
│   └── service.yaml             # Service configurations
├── monitoring/                  # Monitoring stack
│   └── prometheus.yaml          # Prometheus configuration
├── mlops/                       # Machine Learning pipeline
│   └── train.py                 # Training script with MLflow integration
├── terraform/                   # Infrastructure as Code
│   └── main.tf                  # AWS EKS cluster setup
├── Dockerfile                   # Container image definition
├── Jenkinsfile                  # CI/CD pipeline stages
└── argocd-app.yaml             # GitOps application manifest
```

## 🔐 Secrets Management

### Kubernetes Secrets (`k8s/secret.yaml`)
- Stores application secrets (passwords, API keys)
- Read by app via environment variables
- Base64 encoded (not encrypted by default)

### AWS Secrets Manager Integration (Production)
```yaml
# For production, use AWS Secrets Store CSI driver
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: app-secrets
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "prod/app/db-password"
        objectType: "secretsmanager"
```

**How to implement:**
1. Enable IRSA (IAM Roles for Service Accounts) on EKS
2. Install Secrets Store CSI driver
3. Create IAM policy allowing access to Secrets Manager
4. Update deployment to mount secrets via CSI

## 📊 Monitoring

### Prometheus Configuration (`monitoring/prometheus.yaml`)
- Scrapes Kubernetes API server, nodes, and pods
- 15-second scrape interval
- Monitors application metrics
- Ready for Alertmanager integration

### Extension Options
- **Grafana**: Dashboard visualization
- **AlertManager**: Alert routing and notifications
- **Custom metrics**: Add Prometheus client to Flask app

**To add custom metrics to Flask:**
```python
from prometheus_client import Counter, Histogram

requests_total = Counter('app_requests_total', 'Total requests')
request_duration = Histogram('app_request_duration_seconds', 'Request duration')

@app.route('/metrics')
def metrics():
    return prometheus.generate_latest()
```

## 🚦 Canary Deployment

### How It Works
1. New version deploys to canary (1 replica)
2. Monitor canary for errors/performance issues
3. Gradually shift traffic (10% → 50% → 100%)
4. On success, deploy to stable (production)
5. On failure, rollback canary

### Using Flagger + Istio (Recommended)
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: cicd-app
spec:
  targetRef:
    name: cicd-app
    kind: Deployment
  canary:
    interval: 1m
    threshold: 10
    metrics:
    - name: error-rate
      thresholdRange:
        max: 1
    - name: latency
      interval: 30s
      thresholdRange:
        max: 500m
  skipAnalysis: false
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
```

## 🧠 MLOps Pipeline

### Training Script (`mlops/train.py`)
Demonstrates the ML training workflow:
1. **Data Loading** - Load from S3/GCS/database
2. **Preprocessing** - Feature engineering and normalization
3. **Model Training** - Train ML model
4. **Evaluation** - Compute metrics (accuracy, precision, recall)
5. **Save Artifacts** - Store model and metadata

### Running Training
```bash
python mlops/train.py
```

### Extension with MLflow
```bash
pip install mlflow
mlflow run mlops/ -b basic
mlflow ui  # View experiments at localhost:5000
```

### Extension with Kubeflow
```yaml
apiVersion: kubeflow.org/v1
kind: Experiment
metadata:
  name: cicd-app-training
spec:
  algorithm:
    algorithmName: random
  parallelTrialCount: 3
  trialTemplate:
    spec:
      apiVersion: batch/v1
      kind: Job
      spec:
        template:
          spec:
            containers:
            - name: training-container
              image: your-dockerhub-username/cicd-app:latest
              command: ["python", "mlops/train.py"]
```

## ⚙️ Core DevOps Components

### Dockerfile
- Python 3.9 slim image
- Multi-stage support for optimization
- Ready for production deployment

### Jenkinsfile Pipeline
1. **Checkout** - Pull source code
2. **Build** - Build Docker image with multiple tags
3. **Push** - Push to Docker Hub
4. **Canary Deploy** - Deploy to canary environment
5. **Test** - Run smoke tests
6. **Approve** - Manual approval gate
7. **Production Deploy** - Deploy via ArgoCD (GitOps)

### ArgoCD Configuration (`argocd-app.yaml`)
- Continuous deployment from Git
- Auto-sync on changes
- Automatic pruning of deleted resources
- Retry logic for failed syncs

### Terraform (`terraform/main.tf`)
- AWS EKS cluster setup
- VPC and networking
- Auto-scaling groups
- Ready for production

## 🧪 Quick Start Guide

### Prerequisites
- Docker installed
- Kubernetes cluster (local `minikube` or AWS EKS)
- Jenkins server
- GitHub account

### Step 1: Upload to GitHub
```bash
# Extract the zip file
cd cicd-advanced-project

# Initialize git
git init
git add .
git commit -m "Initial commit: Advanced CI/CD Project"

# Add remote (create repo on GitHub first)
git remote add origin https://github.com/YOUR_USERNAME/cicd-advanced-project.git
git branch -M main
git push -u origin main
```

### Step 2: Update Configuration Values

#### Update Docker Hub username
```bash
# In Dockerfile, argocd-app.yaml, Jenkinsfile, k8s/canary-deployment.yaml
sed -i 's/your-dockerhub-username/YOUR_DOCKER_USERNAME/g' \
  Dockerfile Jenkinsfile k8s/canary-deployment.yaml
```

#### Update GitHub repository URL
```bash
# In argocd-app.yaml
sed -i 's|https://github.com/your-username/cicd-devops-project.git|YOUR_REPO_URL|g' \
  argocd-app.yaml
```

#### Update AWS details (if using Terraform)
```bash
# Edit terraform/main.tf
# Set your AWS region, VPC CIDR blocks, cluster name
```

### Step 3: Deploy Infrastructure

#### Using Terraform
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

#### Using eksctl (simpler)
```bash
# Create EKS cluster
eksctl create cluster --name cicd-app --region us-east-1 --nodes 3

# Get kubeconfig
aws eks update-kubeconfig --region us-east-1 --name cicd-app
```

### Step 4: Setup Kubernetes

#### Install ArgoCD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Port forward to access UI
kubectl port-forward -n argocd svc/argocd-server 8080:443
# Access at https://localhost:8080
```

#### Create Kubernetes secrets
```bash
kubectl apply -f k8s/secret.yaml
```

#### Deploy secrets and app
```bash
kubectl apply -f argocd-app.yaml  # This triggers ArgoCD to deploy everything
```

### Step 5: Setup Jenkins Pipeline

#### Jenkins Configuration
1. Go to Jenkins dashboard
2. Create new Pipeline job
3. Configure Git repository
4. Connect to GitHub
5. Link to Jenkinsfile in repository

#### Required Jenkins Credentials
```groovy
// Manage Jenkins → Manage Credentials
- dockerhub-credentials-id (Docker Hub login)
- kubeconfig-credential-id (Kubernetes config file)
- github-token (GitHub Personal Access Token)
```

#### Run Pipeline
```bash
# Push changes to main branch - triggers Jenkins automatically
git push origin main
```

### Step 6: Monitor Deployment

#### Check ArgoCD sync
```bash
kubectl port-forward -n argocd svc/argocd-server 8080:443
# https://localhost:8080
```

#### Check Pod status
```bash
kubectl get pods
kubectl logs -f deployment/cicd-app
```

#### Monitor with Prometheus
```bash
# Deploy Prometheus from monitoring/prometheus.yaml
kubectl apply -f monitoring/prometheus.yaml

# Port forward
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Access at http://localhost:9090
```

## 🔄 Deployment Flow

```
1. Code Push to main
         ↓
2. GitHub webhook triggers Jenkins
         ↓
3. Jenkins stages:
   - Build Docker image
   - Push to Docker Hub
   - Deploy to Canary
   - Run smoke tests
         ↓
4. Manual approval
         ↓
5. Update deployment.yaml in Git
         ↓
6. ArgoCD detects Git change
         ↓
7. Automatic sync to production
         ↓
8. Rolling update (maxSurge: 1, maxUnavailable: 0)
```

## 🛡️ Security Best Practices Implemented

✅ **Container Security**
- Run as non-root user (UID 1000)
- Read-only root filesystem
- Drop all capabilities
- No privilege escalation

✅ **Kubernetes Security**
- Network policies
- RBAC with minimal permissions
- Resource limits
- Health checks (liveness + readiness)

✅ **Secrets Management**
- Secrets not hardcoded
- AWS Secrets Manager integration
- Secrets Store CSI driver support

✅ **GitOps Security**
- All changes tracked in Git
- Code review before deployment
- Automated rollback capabilities

## 🚀 Production Checklist

- [ ] Update Docker Hub username
- [ ] Configure AWS account
- [ ] Create GitHub repository
- [ ] Setup Jenkins with credentials
- [ ] Create Kubernetes cluster
- [ ] Install and configure ArgoCD
- [ ] Enable AWS Secrets Manager
- [ ] Setup Prometheus + Grafana
- [ ] Configure backup strategy
- [ ] Setup monitoring alerts
- [ ] Document runbooks
- [ ] Test disaster recovery

## 📝 Troubleshooting

### Pod won't start
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### ImagePullBackOff error
```bash
# Check Docker credentials are correct
kubectl get secrets
kubectl describe imagepullsecrets
```

### ArgoCD sync issues
```bash
# Check ArgoCD logs
kubectl logs -n argocd deployment/argocd-application-controller

# Check Application status
kubectl get application -n argocd
kubectl describe application cicd-app -n argocd
```

### Jenkins pipeline failures
- Check Jenkins logs
- Verify credentials in Jenkins UI
- Check kubeconfig validity
- Verify Docker Hub credentials

## 📚 Resources

- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [Kubernetes Docs](https://kubernetes.io/docs/)
- [ArgoCD User Guide](https://argo-cd.readthedocs.io/)
- [Prometheus Guide](https://prometheus.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs: `kubectl logs`, `jenkins logs`
3. Check Git status and ArgoCD sync
4. Open an issue on GitHub

---

**Last Updated**: March 28, 2026
**Version**: 1.0.0
**Maintainer**: DevOps Team
