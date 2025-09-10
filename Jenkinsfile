pipeline {
    
    agent any

    // ==============================
    // Global Options & Triggers
    // ==============================
    tools{
        maven 'maven-3.9'
        jdk 'jdk-21'
    }
    options {
        ansiColor('xterm')
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 60, unit: 'MINUTES')
    }

    triggers {
        cron('H 2 * * 1-5') // Run Mon–Fri at ~2AM
    }

    // ==============================
    // Parameters
    // ==============================
    parameters {
        choice(name: 'DEPLOY_ENV', choices: ['dev', 'qa', 'stg', 'prd'], description: 'Target environment')
        booleanParam(name: 'RUN_SECURITY_SCANS', defaultValue: true, description: 'Enable SAST/SCA checks?')
        string(name: 'APP_NAME', defaultValue: 'complex-java-app', description: 'Application name')
        string(name: 'DOCKER_TAG', defaultValue: 'latest', description: 'Docker tag for build')
    }

    // ==============================
    // Global Environment Variables
    // ==============================
    environment {
        REGISTRY         = 'ghcr.io/your-org'
        IMAGE            = "${env.REGISTRY}/${params.APP_NAME}"
        SONARQUBE_SERVER = 'sonarqube-prod'
        REGISTRY_CRED    = credentials('registry-writer')
        // SLACK_CRED       = credentials('slack-webhook')
        // KUBE_CONFIG_DEV  = credentials('kubeconfig-dev')
        // KUBE_CONFIG_PRD  = credentials('kubeconfig-prd')
        MAVEN_OPTS       = '-Dmaven.test.failure.ignore=false -DskipTests'
    }

    // ==============================
    // Stages
    // ==============================
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.BUILD_TAG = "${env.GIT_COMMIT_SHORT}-${env.BUILD_NUMBER}"
                }
            }
        }

        stage('Set Java & Maven') {
            tools {
                jdk 'jdk-21'
                maven 'maven-3.9'
            }
            steps {
                sh 'java -version && mvn -v'
            }
        }

        stage('Build & Unit Test') {
            steps {
                sh 'mvn clean package -DskipITs=false'
            }
            post {
                always {
                    junit '**/target/surefire-reports/*.xml'
                    archiveArtifacts artifacts: 'target/*.jar', onlyIfSuccessful: true
                }
            }
        }

        stage('Static Code Analysis (SonarQube)') {
            steps {
                withSonarQubeEnv(env.SONARQUBE_SERVER) {
                    sh """
                        mvn sonar:sonar \
                          -Dsonar.projectKey=${params.APP_NAME} \
                          -Dsonar.projectName=${params.APP_NAME} \
                          -Dsonar.projectVersion=${BUILD_TAG}
                    """
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Security Scans') {
            when { expression { return params.RUN_SECURITY_SCANS } }
            steps {
                sh '''
                    echo "Running dependency and container scans..."
                    mvn org.owasp:dependency-check-maven:check -DfailOnError=false || true
                '''
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                sh '''
                    echo "$REGISTRY_CRED_PSW" | docker login ${REGISTRY} -u "$REGISTRY_CRED_USR" --password-stdin
                    docker build -t ${IMAGE}:${BUILD_TAG} .
                    docker push ${IMAGE}:${BUILD_TAG}
                '''
            }
        }

        stage('Manual Approval for Deploy') {
            when { expression { return params.DEPLOY_ENV in ['stg', 'prd'] } }
            steps {
                input message: "Deploy ${BUILD_TAG} to ${params.DEPLOY_ENV}?", ok: "Deploy"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script {
                    def kubeConfig = params.DEPLOY_ENV == 'prd' ? env.KUBE_CONFIG_PRD : env.KUBE_CONFIG_DEV
                    withCredentials([file(credentialsId: kubeConfig, variable: 'KCONFIG')]) {
                        sh """
                            export KUBECONFIG=$KCONFIG
                            kubectl set image deployment/${params.APP_NAME} ${params.APP_NAME}=${IMAGE}:${BUILD_TAG} -n ${params.DEPLOY_ENV}
                            kubectl rollout status deployment/${params.APP_NAME} -n ${params.DEPLOY_ENV} --timeout=5m
                        """
                    }
                }
            }
        }

        stage('Smoke Test') {
            steps {
                sh """
                    echo "Running smoke test against ${params.DEPLOY_ENV}..."
                    curl -s http://${params.APP_NAME}.${params.DEPLOY_ENV}.example.com/actuator/health | grep UP
                """
            }
        }
    }

    // ==============================
    // Post Actions
    // ==============================
    post {
        always {
            echo "Cleaning up Docker images from workspace..."
            sh 'docker system prune -f || true'
        }
        success {
            echo "Pipeline succeeded ✅"
            //slackSend(channel: '#deployments', message: "SUCCESS: ${params.APP_NAME} build ${BUILD_TAG}", webhookUrl: "${SLACK_CRED}")
        }
        failure {
            echo "Pipeline failed ❌"
            //slackSend(channel: '#deployments', message: "FAILURE: ${params.APP_NAME} build ${BUILD_TAG}", webhookUrl: "${SLACK_CRED}")
        }
        unstable {
            echo "Pipeline unstable ⚠️"
            //slackSend(channel: '#deployments', message: "UNSTABLE: ${params.APP_NAME} build ${BUILD_TAG}", webhookUrl: "${SLACK_CRED}")
        }
    }
}
