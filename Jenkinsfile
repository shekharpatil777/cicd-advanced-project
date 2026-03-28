pipeline {
    agent any
    environment {
        DOCKER_IMAGE = "your-dockerhub-username/cicd-app"
    }
    stages {
        stage('Build') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:${BUILD_NUMBER}")
                }
            }
        }
        stage('Push') {
            steps {
                script {
                    docker.withRegistry('', 'dockerhub-credentials-id') {
                        docker.image("${DOCKER_IMAGE}:${BUILD_NUMBER}").push()
                    }
                }
            }
        }
    }
}
