# Quick Start Guide (5 Minutes)

Get up and running with the CI/CD Advanced Project in just 5 minutes!

## Prerequisites
- Docker installed
- Git installed
- AWS account (optional)
- Kubernetes cluster access (optional)

## Option 1: Local Development (2 minutes)

### Start everything locally
```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/cicd-advanced-project.git
cd cicd-advanced-project

# Start services (includes app, DB, monitoring)
docker-compose up -d

# Wait a few seconds for services to start
sleep 10

# Test the application
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/version
```

### Access dashboards
- **Application**: http://localhost:5000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **pgAdmin**: http://localhost:5050 (admin@example.com/admin)

### Stop services
```bash
docker-compose down
```

---

## Option 2: Kubernetes Deployment (5 minutes)

### Prerequisites
- kubectl configured
- Kubernetes cluster running (Minikube, EKS, GKE, etc.)

### Deploy
```bash
# 1. Update your Docker username
DOCKER_USER="your-dockerhub-username"
sed -i "s/your-dockerhub-username/$DOCKER_USER/g" \
  k8s/*.yaml argocd-app.yaml Jenkinsfile

# 2. Create namespace and secrets
kubectl create namespace default
kubectl apply -f k8s/secret.yaml

# 3. Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 4. Check deployment
kubectl get pods
kubectl logs -f deployment/cicd-app
```

### Access application
```bash
# Get service IP
kubectl get svc cicd-app

# Port forward (if no external IP)
kubectl port-forward svc/cicd-app 8000:80

# Test
curl http://localhost:8000/
```

### Deploy with ArgoCD (GitOps)
```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Deploy application via GitOps
kubectl apply -f argocd-app.yaml

# Access UI
kubectl port-forward -n argocd svc/argocd-server 8080:443 &

# Open https://localhost:8080 (admin/shown-at-setup)
```

---

## Option 3: Using Makefile (Easiest)

```bash
# Build and push Docker image
make docker-push

# Deploy to Kubernetes
make deploy

# View logs
make logs

# Access Prometheus
make prometheus-ui

# Access ArgoCD
make argocd-ui
```

---

## Useful Commands

### View Application Logs
```bash
# Docker Compose
docker-compose logs -f app

# Kubernetes
kubectl logs -f deployment/cicd-app
```

### Test Endpoints
```bash
# Main endpoint
curl http://localhost:5000/

# Health check
curl http://localhost:5000/health

# Readiness check
curl http://localhost:5000/ready

# Version info
curl http://localhost:5000/version
```

### Scale Application
```bash
# Kubernetes
kubectl scale deployment cicd-app --replicas=5
```

### Restart Application
```bash
# Kubernetes
kubectl rollout restart deployment/cicd-app
```

### View Metrics
```bash
# Get CPU and memory usage
kubectl top pods
kubectl top nodes
```

---

## Troubleshooting

### Pod not starting?
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Service not accessible?
```bash
# Check service
kubectl get svc
kubectl describe svc cicd-app

# Try port forward
kubectl port-forward svc/cicd-app 8000:80
```

### Docker Compose not starting?
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart

# Rebuild images
docker-compose up -d --build
```

---

## Next Steps

1. **Configure GitHub**
   - Create GitHub repository
   - Push code: `git push origin main`
   - Set webhook for CI/CD

2. **Setup Jenkins** (if using)
   - Create pipeline job
   - Link to this GitHub repo
   - Add credentials

3. **Deploy Canary**
   ```bash
   kubectl apply -f k8s/canary-deployment.yaml
   ```

4. **Monitor**
   - Check Prometheus: http://localhost:9090
   - Setup Grafana dashboards
   - Configure alerts

---

## Full Documentation

- **README.md** - Complete project overview
- **DEPLOYMENT.md** - Step-by-step deployment guide
- **TESTING.md** - Testing strategies
- **IMPLEMENTATION_SUMMARY.md** - What was implemented

---

## Key Features

✅ **Secrets Management** - Kubernetes & AWS Secrets Manager  
✅ **Monitoring** - Prometheus + Grafana ready  
✅ **Canary Deployment** - Safe rollout strategy  
✅ **MLOps** - Training pipeline included  
✅ **GitOps** - ArgoCD for continuous deployment  
✅ **CI/CD** - Jenkins pipeline  
✅ **Infrastructure** - Terraform for AWS EKS  
✅ **Security** - Production-ready security configs  

---

## Support

- Check logs: `kubectl logs deployment/cicd-app`
- View events: `kubectl get events`
- Describe resources: `kubectl describe pod <name>`
- Read documentation: See README.md or DEPLOYMENT.md

---

**Time to Deploy**: ~5 minutes  
**Complexity**: Beginner-friendly  
**Status**: ✅ Ready to use

