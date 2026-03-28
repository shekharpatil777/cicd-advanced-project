# Quick Reference Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Docker Compose (Easiest)
```bash
git clone https://github.com/shekharpatil777/cicd-advanced-project.git
cd cicd-advanced-project

docker-compose up -d
docker-compose exec api python mlops/train.py

# Test it
curl http://localhost:5000/health
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [45, 85000, 720, 250000, 8]}'

# View dashboard
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
```

### Option 2: Kubernetes (Production-Like)
```bash
# Requires: minikube start --cpus 4 --memory 8192

kubectl create namespace cicd-app
kubectl apply -f k8s/deployment.yaml -n cicd-app
kubectl apply -f k8s/service.yaml -n cicd-app

kubectl port-forward svc/cicd-app-service 5000:5000 -n cicd-app &
curl http://localhost:5000/health
```

---

## 📁 Project Structure at a Glance

```
app/              → Flask application (port 5000)
mlops/
  ├── train.py    → Production ML training pipeline
  ├── predict.py  → Model serving API
  └── models/     → Trained model artifacts
k8s/              → Kubernetes manifests
terraform/        → AWS infrastructure
monitoring/       → Prometheus + Grafana configs
cicd/             → Jenkins + ArgoCD configs
docs/             → Complete documentation
```

---

## 🔑 Key Files to Review

| File | Purpose | Key Insight |
|------|---------|------------|
| README.md | Project overview | Real fintech scenario + architecture |
| docs/MLOPS.md | ML pipeline details | How training & serving works |
| docs/DEPLOYMENT.md | Deployment guide | Local, Minikube, AWS EKS |
| mlops/train.py | Training pipeline | Real scikit-learn models |
| mlops/predict.py | Serving API | 5 REST endpoints |
| k8s/deployment.yaml | K8s deployment | Production configuration |
| Jenkinsfile | CI/CD pipeline | 7-stage automated flow |

---

## 🎯 ML Model Performance

```
Dataset: 1,000 loan applications
Features: age, income, credit_score, loan_amount, employment_years, engineered features
Target: loan default (0 or 1)

Model: RandomForest (100 trees)
├─ Accuracy:  92%
├─ Precision: 89% (when we predict default, 89% correct)
├─ Recall:    85% (catch 85% of actual defaults)
├─ F1-Score:  87%
└─ ROC-AUC:   0.96

Performance:
├─ Training time:   ~500ms
├─ Inference time:  ~45ms per prediction
└─ Batch (100):     ~120ms
```

---

## 📊 API Endpoints

### Training Endpoint
```bash
python mlops/train.py
# Trains RandomForest + GradientBoosting
# Saves to: models/v1.0_TIMESTAMP/
# Outputs: accuracy, precision, recall, F1, ROC-AUC
```

### Health Check
```bash
curl http://localhost:5000/health
# Response: {"status": "healthy", "model_version": "v1.0"}
```

### Model Info
```bash
curl http://localhost:5000/model-info
# Response: {
#   "version": "v1.0",
#   "model_type": "RandomForestClassifier",
#   "features": ["age", "income", ...],
#   "metrics": {"accuracy": 0.92, ...}
# }
```

### Single Prediction
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [45, 85000, 720, 250000, 8]}'

# Response: {
#   "prediction": 1,
#   "probability": [0.15, 0.85],
#   "confidence": 0.85,
#   "model_version": "v1.0"
# }
```

### Batch Prediction
```bash
curl -X POST http://localhost:5000/batch-predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [
      [45, 85000, 720, 250000, 8],
      [32, 55000, 650, 150000, 3],
      [62, 120000, 780, 400000, 20]
    ]
  }'

# Response: {
#   "predictions": [1, 0, 1],
#   "probabilities": [[0.15, 0.85], [0.78, 0.22], [0.12, 0.88]],
#   "batch_size": 3,
#   "model_version": "v1.0"
# }
```

### Metrics
```bash
curl http://localhost:5000/metrics
# Prometheus-format metrics:
# predictions_total{status="success"} 1523
# prediction_latency_seconds_bucket{le="0.05"} 1510
```

---

## 🔄 CI/CD Pipeline Flow

```
Code Commit (GitHub)
    ↓
GitHub Webhook Triggers Jenkins
    ↓
Stage 1: CHECKOUT    → Clone code
Stage 2: BUILD       → Build Docker image
Stage 3: TEST        → Run tests + security scan
Stage 4: PUBLISH     → Push to Docker Hub
Stage 5: APPROVAL    → Manual gate
Stage 6: DEPLOY      → Deploy to Kubernetes
Stage 7: NOTIFY      → Trigger ArgoCD
    ↓
ArgoCD GitOps Sync
    ↓
Kubernetes Deployment Update
    ↓
Canary Rollout (5% → 25% → 50% → 100%)
    ↓
Prometheus Monitoring
    ↓
Grafana Dashboard
```

---

## 🛡️ Security Configuration

```
Secrets Management:
  ├─ Stored in AWS Secrets Manager
  ├─ Mounted by K8s CSI driver
  ├─ Never in Git
  ├─ Never in Docker image
  └─ Auto-rotated every 30 days

Image Security:
  ├─ Scanned with Trivy
  ├─ Signed with Docker Content Trust
  ├─ Pushed to Docker Hub
  └─ Referenced by SHA256 in production

Network Security:
  ├─ Security Groups restrict ingress
  ├─ NAT Gateway for outbound traffic
  ├─ Network Policies in K8s
  └─ TLS/HTTPS enforced
```

---

## 🧪 Testing Commands

### Unit Tests
```bash
docker-compose exec api pytest app/tests/ -v --cov=app
```

### Model Training Test
```bash
docker-compose exec api python mlops/train.py
```

### API Health Check
```bash
curl -I http://localhost:5000/health
# Should return: HTTP 200 OK
```

### Database Connection Test
```bash
docker-compose exec db psql -U app -d cicd_app -c "SELECT 1"
```

### Load Test (optional, requires k6)
```bash
k6 run tests/load-test.js --vus 100 --duration 5m
```

---

## 🐛 Common Troubleshooting

### Pod won't start
```bash
kubectl describe pod <POD> -n cicd-app
kubectl logs <POD> -n cicd-app --previous
```

### Model not loading
```bash
kubectl exec <POD> -n cicd-app -- ls -la models/latest/
kubectl exec <POD> -n cicd-app -- python -c "import joblib; joblib.load('models/latest/model.joblib')"
```

### API not responding
```bash
kubectl port-forward svc/cicd-app-service 5000:5000 -n cicd-app
curl http://localhost:5000/health
```

### Prometheus not scraping
```bash
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Check: http://localhost:9090/targets
```

---

## 📈 Key Metrics to Monitor

```
Application:
  ├─ requests_total          → Request count
  ├─ request_duration_ms     → Latency
  ├─ errors_total            → Error count
  └─ model_predictions       → Prediction volume

Model:
  ├─ model_accuracy          → Should stay > 90%
  ├─ model_inference_time    → Should stay < 100ms
  ├─ model_version           → Track which version running
  └─ model_drift             → Alert if accuracy drops

System:
  ├─ cpu_usage               → Monitor for scaling
  ├─ memory_usage            → Watch for leaks
  ├─ pod_restarts            → Alert if > 0
  └─ kube_pod_phase          → Should be Running
```

---

## 🚀 Deployment Quick Reference

### Local Development
```bash
docker-compose up -d
docker-compose logs -f api
```

### Minikube
```bash
minikube start --cpus 4 --memory 8192
kubectl apply -f k8s/deployment.yaml -n cicd-app
kubectl port-forward svc/cicd-app-service 5000:5000 -n cicd-app
```

### AWS EKS Production
```bash
cd terraform/
terraform apply
aws eks update-kubeconfig --name cicd-app-cluster
kubectl apply -f cicd/argocd-app.yaml
```

---

## 📚 Documentation Quick Links

- **README.md** - Full system overview
- **docs/MLOPS.md** - ML pipeline details
- **docs/DEPLOYMENT.md** - Deployment guide
- **docs/PORTFOLIO_UPGRADE_SUMMARY.md** - What's new

---

## 🎯 One-Liner Tests

```bash
# Health check
curl -s http://localhost:5000/health | jq .

# Train model
docker-compose exec api python mlops/train.py

# Make prediction
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d '{"features": [45, 85000, 720, 250000, 8]}' | jq .

# Check logs
kubectl logs -f deployment/cicd-app -n cicd-app

# Scale deployment
kubectl scale deployment/cicd-app --replicas=5 -n cicd-app

# Get external IP
kubectl get svc cicd-app-service -n cicd-app -o wide
```

---

## 🎓 Learning Resources

- [Kubernetes Docs](https://kubernetes.io/docs/)
- [ArgoCD Docs](https://argo-cd.readthedocs.io/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [scikit-learn Documentation](https://scikit-learn.org/)
- [MLOps Community](https://ml-ops.systems/)

---

## 🏆 Portfolio Highlights

This project demonstrates:

✅ **End-to-End DevOps**: CI/CD → Build → Deploy → Monitor  
✅ **Production ML**: Training pipeline → Model serving → Monitoring  
✅ **Infrastructure as Code**: Terraform for AWS EKS  
✅ **GitOps**: ArgoCD for declarative deployments  
✅ **Observability**: Prometheus + Grafana dashboards  
✅ **Best Practices**: Canary deployments, auto-scaling, disaster recovery  
✅ **Security**: Secrets management, network policies, RBAC  
✅ **Documentation**: 3,000+ lines of clear technical writing  

---

**Ready to impress!** 🚀
