# Testing Guide

This guide covers testing strategies for the CI/CD Advanced Project including unit tests, integration tests, and deployment validation.

## Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_app.py
│   └── test_handlers.py
├── integration/          # Integration tests
│   ├── test_kubernetes.py
│   └── test_deployment.py
└── e2e/                 # End-to-end tests
    ├── test_pipeline.py
    └── test_canary.py
```

## Unit Tests

### Application Tests (`tests/unit/test_app.py`)

```python
import pytest
from app.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_hello_endpoint(client):
    """Test main endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'message' in response.json

def test_health_endpoint(client):
    """Test health check"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_ready_endpoint(client):
    """Test readiness check"""
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.json['status'] == 'ready'

def test_version_endpoint(client):
    """Test version endpoint"""
    response = client.get('/version')
    assert response.status_code == 200
    assert 'version' in response.json

def test_404_error(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    assert 'error' in response.json
```

### Running Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all unit tests
pytest tests/unit/

# Run with coverage report
pytest tests/unit/ --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_app.py::test_hello_endpoint -v
```

## Integration Tests

### Kubernetes Integration (`tests/integration/test_kubernetes.py`)

```python
import pytest
import subprocess
from kubernetes import client, config, watch

@pytest.fixture(scope="session")
def k8s_client():
    """Load kubeconfig and return client"""
    config.load_kube_config()
    return client.CoreV1Api()

def test_pod_exists(k8s_client):
    """Test if deployment pods exist"""
    pods = k8s_client.list_namespaced_pod(namespace="default")
    pod_names = [p.metadata.name for p in pods.items]
    assert any("cicd-app" in name for name in pod_names)

def test_deployment_status(k8s_client):
    """Test deployment readiness"""
    apps_api = client.AppsV1Api()
    deployments = apps_api.list_namespaced_deployment(namespace="default")
    
    for dep in deployments.items:
        if "cicd-app" in dep.metadata.name:
            assert dep.status.ready_replicas == dep.spec.replicas

def test_service_exists(k8s_client):
    """Test if service exists and has endpoints"""
    services = k8s_client.list_namespaced_service(namespace="default")
    service_names = [s.metadata.name for s in services.items]
    assert any("cicd-app" in name for name in service_names)

def test_secret_exists(k8s_client):
    """Test if secrets are deployed"""
    secrets = k8s_client.list_namespaced_secret(namespace="default")
    secret_names = [s.metadata.name for s in secrets.items]
    assert "app-secret" in secret_names
```

### Running Integration Tests

```bash
# Ensure kubeconfig is configured
export KUBECONFIG=~/.kube/config

# Run integration tests
pytest tests/integration/ -v

# Run with pytest-testinfra for host testing
pytest tests/integration/test_kubernetes.py --testinfra-hosts=localhost
```

## End-to-End Tests

### Pipeline Tests (`tests/e2e/test_pipeline.py`)

```python
import pytest
import requests
import time
from kubernetes import client, config

class TestPipeline:
    """Test complete CI/CD pipeline flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        
    def test_deployment_ready(self):
        """Test deployment reaches ready state"""
        deployment = self.apps_v1.read_namespaced_deployment(
            name="cicd-app",
            namespace="default"
        )
        
        # Wait for deployment to be ready
        timeout = 300
        start = time.time()
        while time.time() - start < timeout:
            if deployment.status.ready_replicas == deployment.spec.replicas:
                break
            time.sleep(5)
            deployment = self.apps_v1.read_namespaced_deployment(
                name="cicd-app",
                namespace="default"
            )
        
        assert deployment.status.ready_replicas == deployment.spec.replicas
    
    def test_application_responds(self):
        """Test application responds to requests"""
        # Get service endpoint
        service = self.v1.read_namespaced_service(
            name="cicd-app",
            namespace="default"
        )
        
        # Get external IP (or port-forward if not available)
        external_ip = service.status.load_balancer.ingress[0].ip if \
            service.status.load_balancer.ingress else "localhost"
        
        port = service.spec.ports[0].port
        url = f"http://{external_ip}:{port}/"
        
        # Wait for application to respond
        timeout = 60
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(url)
                assert response.status_code == 200
                break
            except requests.exceptions.RequestException:
                time.sleep(5)
    
    def test_metrics_available(self):
        """Test Prometheus metrics are available"""
        # This assumes you added metrics to the Flask app
        # See MONITORING.md for details
        pass
```

### Canary Deployment Tests

```python
def test_canary_deployment():
    """Test canary deployment process"""
    apps_v1 = client.AppsV1Api()
    
    # Deploy canary version
    subprocess.run([
        "kubectl", "set", "image",
        "deployment/cicd-app-canary",
        f"cicd-app=your-dockerhub-username/cicd-app:canary",
        "--record=true"
    ], check=True)
    
    # Wait for canary to be ready
    deployment = apps_v1.read_namespaced_deployment(
        name="cicd-app-canary",
        namespace="default"
    )
    
    # Verify canary is running
    assert deployment.status.ready_replicas > 0
    
    # Test canary endpoint
    response = requests.get("http://canary-service/")
    assert response.status_code == 200
```

## Local Testing with Docker Compose

### Run All Services

```bash
# Start all services including app, database, monitoring
docker-compose up -d

# Wait for services to be ready
docker-compose exec app curl http://localhost:5000/health

# View logs
docker-compose logs -f app
```

### Test Local Deployment

```bash
# Build image
docker build -t your-dockerhub-username/cicd-app:latest .

# Run image
docker run -p 5000:5000 -e MY_SECRET=local-secret your-dockerhub-username/cicd-app:latest

# Test endpoints
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/version
```

## CI/CD Pipeline Testing

### Jenkins Pipeline Tests

The pipeline automatically runs tests in stages:

1. **Build Stage** - Builds Docker image
2. **Push Stage** - Pushes to registry
3. **Canary Stage** - Deploys to canary
4. **Test Stage** - Runs smoke tests

### Smoke Tests (in Jenkinsfile)

```groovy
stage('Run Tests') {
    steps {
        script {
            sh '''
                # Wait for canary to be ready
                kubectl rollout status deployment/cicd-app-canary --timeout=3m
                
                # Test endpoints
                curl -f http://localhost:5000/ || exit 1
                curl -f http://localhost:5000/health || exit 1
                curl -f http://localhost:5000/ready || exit 1
            '''
        }
    }
}
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install Apache Bench
# macOS: brew install httpd
# Ubuntu: sudo apt-get install apache2-utils

# Get service URL
kubectl port-forward svc/cicd-app 8000:80

# Run load test
ab -n 1000 -c 10 http://localhost:8000/

# Results show:
# - Requests per second
# - Average response time
# - Failed requests
```

### Load Testing with k6

```bash
# Install k6
curl https://dl.k6.io/add-repo.sh | sudo bash
sudo apt-get install k6

# Create test script (k6-test.js)
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  let response = http.get('http://localhost:5000/');
  check(response, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}

# Run test
k6 run k6-test.js
```

## Security Testing

### Container Security Scanning

```bash
# Scan Docker image with Trivy
trivy image your-dockerhub-username/cicd-app:latest

# Scan with Grype
grype your-dockerhub-username/cicd-app:latest

# Scan Kubernetes manifests
trivy k8s --report json > k8s-security-report.json
```

### Network Policy Testing

```bash
# Test network policies (if deployed)
kubectl get networkpolicies
kubectl describe networkpolicy app-policy
```

## Test Reporting

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Open report
open htmlcov/index.html
```

### JUnit XML Report

```bash
# Generate JUnit report for Jenkins
pytest tests/ --junit-xml=test-results.xml

# Upload to Jenkins (configured in Jenkinsfile)
```

## Troubleshooting Tests

### Pod not ready

```bash
# Check pod status
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Service not accessible

```bash
# Check service
kubectl get svc
kubectl describe svc cicd-app

# Port forward if needed
kubectl port-forward svc/cicd-app 8000:80
```

### Tests timing out

```bash
# Increase timeout values
# In test code: timeout = 300  # 5 minutes

# Check resource limits
kubectl top pods
kubectl top nodes
```

## Best Practices

1. **Unit Tests First** - Test business logic independently
2. **Isolate Tests** - Use fixtures and mocks
3. **Integration Tests** - Test with real Kubernetes
4. **End-to-End Tests** - Test complete workflows
5. **Automated Reporting** - Generate reports in CI/CD
6. **Performance Baseline** - Establish performance standards
7. **Security Testing** - Regular vulnerability scans

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [k6 Load Testing](https://k6.io/)
- [OWASP Security Testing](https://owasp.org/www-project-web-security-testing-guide/)

---

**Last Updated**: March 28, 2026
**Version**: 1.0.0
