pipeline {
    agent none
    
    environment {
        HOME = "${env.WORKSPACE}"
    }
    
    stages {
        stage('Clone') {
            agent {
                label "BuiltIn-Agent"
            }
            
            steps {
                git branch: 'main',
                    url: 'https://github.com/ncstate-sat/auth-service.git'
            }
        }
        
        stage('Test') {
            agent {
                dockerfile true
            }
            
            steps {
                sh 'pytest'
            }
        }
        
        stage('Build') {
            agent {
                label "BuiltIn-Agent"
            }
            
            steps {
                sh 'docker build -t auth-service:latest .'
            }
        }
        
        stage('Push') {
            agent {
                label "BuiltIn-Agent"
            }
            
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'jenkins-harbor',
                    usernameVariable: 'HARBOR_USERNAME',
                    passwordVariable: 'HARBOR_PASSWORD'
                )]) {
                    sh 'docker login -u $HARBOR_USERNAME -p $HARBOR_PASSWORD $REGISTRY_URL'
                    sh 'docker tag auth-service:latest $REGISTRY_URL/jenkins-test-2/auth-service:latest'
                    sh 'docker push $REGISTRY_URL/jenkins-test-2/auth-service:latest'
                }
            }
        }
    }
}