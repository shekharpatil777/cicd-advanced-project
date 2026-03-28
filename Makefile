.PHONY: help setup deploy clean test lint docker build push logs

# Variables
DOCKER_USERNAME ?= chandrashekharpatil
DOCKER_IMAGE ?= $(DOCKER_USERNAME)/cicd-app
DOCKER_TAG ?= latest
CLUSTER_NAME ?= cicd-app-cluster
AWS_REGION ?= us-east-1
NAMESPACE ?= default

# Help target
help:
	@echo "Available targets:"
	@echo "  make setup              - Run initial setup"
	@echo "  make docker-build       - Build Docker image"
	@echo "  make docker-push        - Push to Docker Hub"
	@echo "  make deploy             - Deploy to Kubernetes"
	@echo "  make deploy-argocd      - Deploy via ArgoCD"
	@echo "  make deploy-canary      - Deploy canary version"
	@echo "  make test               - Run tests"
	@echo "  make logs               - View application logs"
	@echo "  make clean              - Clean up resources"
	@echo "  make helm-install       - Install Helm"
	@echo "  make argocd-ui          - Port forward to ArgoCD UI"
	@echo "  make prometheus-ui      - Port forward to Prometheus"
	@echo "  make cluster-info       - Show cluster info"

# Setup target
setup:
	@echo "Running setup..."
	./setup.sh

# Docker build
docker-build:
	@echo "Building Docker image: $(DOCKER_IMAGE):$(DOCKER_TAG)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):latest

# Docker push
docker-push: docker-build
	@echo "Pushing to Docker Hub..."
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE):latest

# Deploy to Kubernetes
deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f k8s/secret.yaml
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl rollout status deployment/cicd-app -n $(NAMESPACE)

# Deploy via ArgoCD
deploy-argocd:
	@echo "Deploying via ArgoCD..."
	kubectl apply -f argocd-app.yaml
	@echo "Checking ArgoCD sync status..."
	kubectl get application -n argocd
	@echo "Describe application:"
	kubectl describe application cicd-app -n argocd

# Deploy canary
deploy-canary:
	@echo "Deploying canary..."
	kubectl apply -f k8s/canary-deployment.yaml
	kubectl rollout status deployment/cicd-app-canary -n $(NAMESPACE)

# Run tests
test:
	@echo "Running tests..."
	cd app && python -m pytest || echo "No tests found"

# View logs
logs:
	@echo "Streaming logs from deployment/cicd-app..."
	kubectl logs -f deployment/cicd-app -n $(NAMESPACE)

# Tail logs from canary
logs-canary:
	@echo "Streaming logs from deployment/cicd-app-canary..."
	kubectl logs -f deployment/cicd-app-canary -n $(NAMESPACE)

# Clean up
clean:
	@echo "Cleaning up resources..."
	kubectl delete deployment cicd-app -n $(NAMESPACE) || true
	kubectl delete deployment cicd-app-canary -n $(NAMESPACE) || true
	kubectl delete service cicd-app -n $(NAMESPACE) || true
	kubectl delete service cicd-service -n $(NAMESPACE) || true
	@echo "Cleanup complete"

# ArgoCD UI
argocd-ui:
	@echo "Forwarding ArgoCD UI to http://localhost:8080"
	@echo "Username: admin"
	@echo "Password: (from setup output)"
	kubectl port-forward -n argocd svc/argocd-server 8080:443

# Prometheus UI
prometheus-ui:
	@echo "Forwarding Prometheus UI to http://localhost:9090"
	kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Cluster info
cluster-info:
	@echo "Cluster Information:"
	kubectl cluster-info
	@echo "\nNodes:"
	kubectl get nodes
	@echo "\nNamespaces:"
	kubectl get namespaces
	@echo "\nPods:"
	kubectl get pods -A
	@echo "\nServices:"
	kubectl get services -A

# Get kubeconfig
get-kubeconfig:
	@echo "Updating kubeconfig for $(CLUSTER_NAME)..."
	aws eks update-kubeconfig --region $(AWS_REGION) --name $(CLUSTER_NAME)
	@echo "Kubeconfig updated"

# Install ArgoCD
install-argocd:
	@echo "Installing ArgoCD..."
	kubectl create namespace argocd || true
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "Waiting for ArgoCD to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Install Prometheus
install-prometheus:
	@echo "Installing Prometheus..."
	kubectl create namespace monitoring || true
	kubectl apply -f monitoring/prometheus.yaml

# Get app info
app-info:
	@echo "Application Information:"
	@echo "Deployment:"
	kubectl get deployment cicd-app -n $(NAMESPACE) -o wide
	@echo "\nPods:"
	kubectl get pods -n $(NAMESPACE) -l app=cicd-app -o wide
	@echo "\nServices:"
	kubectl get service -n $(NAMESPACE) -l app=cicd-app -o wide
	@echo "\nEndpoints:"
	kubectl get endpoints -n $(NAMESPACE) -l app=cicd-app

# Port forward to app
port-forward:
	@echo "Forwarding port 8000:5000"
	kubectl port-forward -n $(NAMESPACE) svc/cicd-app 8000:80

# Restart deployment
restart:
	@echo "Restarting deployment..."
	kubectl rollout restart deployment/cicd-app -n $(NAMESPACE)
	kubectl rollout status deployment/cicd-app -n $(NAMESPACE)

# Scale deployment
scale:
	@echo "Current replicas:"
	kubectl get deployment cicd-app -n $(NAMESPACE) -o jsonpath='{.spec.replicas}'
	@echo "\nEnter new number of replicas:"
	@read REPLICAS; kubectl scale deployment cicd-app --replicas=$$REPLICAS -n $(NAMESPACE)

# Lint Kubernetes manifests
lint-k8s:
	@echo "Linting Kubernetes manifests..."
	kubectl apply -f k8s/ --dry-run=client -o yaml > /dev/null
	@echo "Manifests are valid"

# Terraform targets
terraform-init:
	cd terraform && terraform init -var="aws_region=$(AWS_REGION)"

terraform-plan:
	cd terraform && terraform plan -var="aws_region=$(AWS_REGION)"

terraform-apply:
	cd terraform && terraform apply -var="aws_region=$(AWS_REGION)"

terraform-destroy:
	cd terraform && terraform destroy -var="aws_region=$(AWS_REGION)"

# MLOps targets
train:
	@echo "Running training pipeline..."
	python mlops/train.py

# Development targets
dev:
	@echo "Starting development server..."
	cd app && python app.py

requirements:
	@echo "Installing requirements..."
	pip install -r app/requirements.txt

# All-in-one deployment
full-deploy: setup docker-push deploy install-argocd deploy-argocd install-prometheus
	@echo "Full deployment complete!"

# Monitor deployment
watch:
	@watch -n 2 kubectl get pods

.DEFAULT_GOAL := help
