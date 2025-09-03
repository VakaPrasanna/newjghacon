# My Java App

A Spring Boot application with Jenkins CI/CD pipeline support.

## Project Structure

```
├── src/
│ ├── main/
│ │ ├── java/com/example/myapp/
│ │ │ └── MyJavaAppApplication.java
│ │ └── resources/
│ │ └── application.properties
│ └── test/
│ └── java/com/example/myapp/
│ └── MyJavaAppApplicationTests.java
├── helm/
│ └── my-java-app/
│ ├── Chart.yaml
│ ├── values.yaml
│ ├── values-dev.yaml
│ ├── values-stg.yaml
│ └── templates/
│ ├── deployment.yaml
│ ├── service.yaml
│ ├── _helpers.tpl
│ └── tests/
│ └── test-connection.yaml
├── Dockerfile
├── pom.xml
└── README.md
```

## Building the Application

```bash
# Compile and run tests
mvn clean verify

# Build Docker image
docker build -t my-java-app:latest .

# Run application
mvn spring-boot:run
```

## Endpoints

- `/` - Hello message
- `/health` - Health check
- `/api/status` - Status endpoint
- `/api/info` - Application info
- `/actuator/health` - Spring Boot Actuator health

## Helm Deployment

```bash
# Deploy to dev
helm upgrade --install my-java-app helm/my-java-app \
  -n my-java-app-dev --create-namespace \
  -f helm/my-java-app/values-dev.yaml

# Run Helm tests
helm test my-java-app -n my-java-app-dev
```

## Jenkins Pipeline

This project is designed to work with the provided Jenkinsfile which includes:

- Maven build and test
- SonarQube static analysis
- Security scans (OWASP, SBOM)
- Docker image build and push
- Helm chart packaging
- Multi-environment deployment (dev/stg/prd)
- Blue/Green deployment strategy
- Post-deployment validation

## Requirements

- Java 17
- Maven 3.6+
- Docker
- Kubernetes cluster
- Helm 3.x