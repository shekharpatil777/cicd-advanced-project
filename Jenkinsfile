pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = "chandrashekharpatil/cicd-app"
        DOCKER_REGISTRY = "https://index.docker.io/v1/"
        KUBECONFIG = credentials('kubeconfig-credential-id')
        AWS_REGION = "us-east-1"
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 1, unit: 'HOURS')
        timestamps()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    echo "Repository checked out"
                    echo "Git commit: ${GIT_COMMIT_SHORT}"
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building Docker image: ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    docker.build("${DOCKER_IMAGE}:${BUILD_NUMBER}")
                    docker.build("${DOCKER_IMAGE}:${GIT_COMMIT_SHORT}")
                    docker.build("${DOCKER_IMAGE}:latest")
                }
            }
        }
        
        stage('Push to Registry') {
            steps {
                script {
                    docker.withRegistry("${DOCKER_REGISTRY}", 'dockerhub-credentials-id') {
                        echo "Pushing Docker images to registry"
                        docker.image("${DOCKER_IMAGE}:${BUILD_NUMBER}").push()
                        docker.image("${DOCKER_IMAGE}:${GIT_COMMIT_SHORT}").push()
                        docker.image("${DOCKER_IMAGE}:latest").push()
                    }
                }
            }
        }
        
        stage('Deploy to Canary') {
            steps {
                script {
                    echo "Deploying to Canary environment"
                    sh '''
                        kubectl set image deployment/cicd-app-canary \
                            cicd-app=${DOCKER_IMAGE}:${BUILD_NUMBER} \
                            --record=true
                        kubectl rollout status deployment/cicd-app-canary --timeout=5m
                    '''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo "Running tests"
                    sh '''
                        # Wait for canary deployment to be ready
                        kubectl rollout status deployment/cicd-app-canary --timeout=3m
                        
                        # Get the service IP/Port
                        export SERVICE_IP=$(kubectl get svc cicd-app-canary -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
                        export SERVICE_PORT=$(kubectl get svc cicd-app-canary -o jsonpath='{.spec.ports[0].port}')
                        
                        # Run basic smoke test
                        curl -f http://${SERVICE_IP}:${SERVICE_PORT}/ || exit 1
                    '''
                }
            }
        }
        
        stage('Approve Production') {
            steps {
                input(message: 'Approve deployment to production?', ok: 'Deploy')
            }
        }
        
        stage('Deploy to Production') {
            steps {
                script {
                    echo "Deploying to Production via ArgoCD"
                    sh '''
                        # Update deployment manifest
                        sed -i "s|your-dockerhub-username/cicd-app:.*|${DOCKER_IMAGE}:${BUILD_NUMBER}|g" k8s/deployment.yaml
                        
                        # Commit changes to git (trigger ArgoCD sync)
                        git config user.name "Jenkins CI"
                        git config user.email "jenkins@example.com"
                        git add k8s/deployment.yaml
                        git commit -m "Update deployment to ${DOCKER_IMAGE}:${BUILD_NUMBER}" || true
                        git push origin main || true
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo "Pipeline execution completed"
            cleanWs()
        }
        success {
            echo "Pipeline succeeded! Deployment complete."
        }
        failure {
            echo "Pipeline failed! Check logs for details."
        }
    }
}
