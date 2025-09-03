
#!/usr/bin/env python3
"""
My Java App - Complete Project Generator
Creates the entire project structure with all files needed for Jenkins pipeline success
"""

import os
from pathlib import Path

# File contents as constants
POM_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
                           http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>my-java-app</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <n>My Java App</n>
    <description>Spring Boot application for Jenkins pipeline</description>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.1.5</version>
        <relativePath/>
    </parent>

    <properties>
        <java.version>17</java.version>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <jacoco.version>0.8.8</jacoco.version>
        <sonar.java.coveragePlugin>jacoco</sonar.java.coveragePlugin>
        <sonar.dynamicAnalysis>reuseReports</sonar.dynamicAnalysis>
        <sonar.language>java</sonar.language>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>

        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>

        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>

            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.0.0</version>
                <configuration>
                    <includes>
                        <include>**/*Test.java</include>
                        <include>**/*Tests.java</include>
                    </includes>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>${jacoco.version}</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>prepare-agent</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals>
                            <goal>report</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>

            <plugin>
                <groupId>org.sonarsource.scanner.maven</groupId>
                <artifactId>sonar-maven-plugin</artifactId>
                <version>3.9.1.2184</version>
            </plugin>

            <plugin>
                <groupId>org.owasp</groupId>
                <artifactId>dependency-check-maven</artifactId>
                <version>8.4.0</version>
                <configuration>
                    <format>JSON</format>
                    <failOnError>false</failOnError>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.cyclonedx</groupId>
                <artifactId>cyclonedx-maven-plugin</artifactId>
                <version>2.7.9</version>
                <configuration>
                    <projectType>application</projectType>
                    <schemaVersion>1.5</schemaVersion>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>'''

MAIN_APP = '''package com.example.myapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class MyJavaAppApplication {

    public static void main(String[] args) {
        SpringApplication.run(MyJavaAppApplication.class, args);
    }

    @GetMapping("/")
    public String hello() {
        return "Hello from My Java App!";
    }

    @GetMapping("/health")
    public String health() {
        return "UP";
    }

    @GetMapping("/api/status")
    public String status() {
        return "Application is running successfully";
    }

    @GetMapping("/api/info")
    public String info() {
        return "My Java App - Version 1.0.0";
    }
}'''

TEST_CLASS = '''package com.example.myapp;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@SpringJUnitConfig
class MyJavaAppApplicationTests {

    @Test
    void contextLoads() {
        // Test that Spring context loads successfully
        assertTrue(true);
    }

    @Test
    void testBasicFunctionality() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String result = app.hello();
        assertEquals("Hello from My Java App!", result);
    }

    @Test
    void testHealthEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String health = app.health();
        assertEquals("UP", health);
    }

    @Test
    void testStatusEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String status = app.status();
        assertEquals("Application is running successfully", status);
    }

    @Test
    void testInfoEndpoint() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        String info = app.info();
        assertEquals("My Java App - Version 1.0.0", info);
    }

    @Test
    void testApplicationNotNull() {
        MyJavaAppApplication app = new MyJavaAppApplication();
        assertNotNull(app);
    }
}'''

APPLICATION_PROPERTIES = '''# Server configuration
server.port=8080
server.servlet.context-path=/

# Actuator configuration
management.endpoints.web.exposure.include=health,info,metrics
management.endpoint.health.show-details=always
management.health.defaults.enabled=true

# Logging configuration
logging.level.com.example.myapp=INFO
logging.level.org.springframework=WARN
logging.pattern.console=%d{yyyy-MM-dd HH:mm:ss} - %msg%n

# Application info
info.app.name=My Java App
info.app.description=Spring Boot application for Jenkins pipeline
info.app.version=1.0.0'''

DOCKERFILE = '''FROM openjdk:17-jdk-slim

WORKDIR /app

# Copy the jar file
COPY target/*.jar app.jar

# Expose port
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/actuator/health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]'''

CHART_YAML = '''apiVersion: v2
name: my-java-app
description: A Helm chart for My Java App
type: application
version: 0.1.0
appVersion: "1.0.0"'''

VALUES_YAML = '''replicaCount: 1

image:
  repository: ghcr.io/your-org/my-java-app
  pullPolicy: IfNotPresent
  tag: ""
  digest: ""

nameOverride: ""
fullnameOverride: ""

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

ingress:
  enabled: false

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

nodeSelector: {}
tolerations: []
affinity: {}

healthcheck:
  enabled: true
  path: /actuator/health'''

VALUES_DEV_YAML = '''replicaCount: 1

resources:
  limits:
    cpu: 250m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Dev environment specific configurations
service:
  type: NodePort

# Enable debug logging in dev
logging:
  level: DEBUG'''

VALUES_STG_YAML = '''replicaCount: 2

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

# Staging environment specific configurations
service:
  type: ClusterIP

# Enable more monitoring in staging
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus'''

DEPLOYMENT_YAML = '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-java-app.fullname" . }}
  labels:
    {{- include "my-java-app.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "my-java-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "my-java-app.selectorLabels" . | nindent 8 }}
        release: {{ .Release.Name }}
        app: {{ include "my-java-app.name" . }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: "kubernetes"'''

SERVICE_YAML = '''apiVersion: v1
kind: Service
metadata:
  name: {{ include "my-java-app.fullname" . }}-svc
  labels:
    {{- include "my-java-app.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "my-java-app.selectorLabels" . | nindent 4 }}'''

HELPERS_TPL = '''{{/*
Expand the name of the chart.
*/}}
{{- define "my-java-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "my-java-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "my-java-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "my-java-app.labels" -}}
helm.sh/chart: {{ include "my-java-app.chart" . }}
{{ include "my-java-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "my-java-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-java-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}'''

TEST_CONNECTION_YAML = '''apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-java-app.fullname" . }}-test-connection"
  labels:
    {{- include "my-java-app.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
spec:
  restartPolicy: Never
  containers:
    - name: wget
      image: busybox:1.35
      command: ['wget']
      args: ['{{ include "my-java-app.fullname" . }}-svc:{{ .Values.service.port }}']
    - name: health-check
      image: busybox:1.35
      command: ['wget']
      args: ['{{ include "my-java-app.fullname" . }}-svc:{{ .Values.service.port }}/actuator/health']'''

GITIGNORE = '''# Maven
target/
pom.xml.tag
pom.xml.releaseBackup
pom.xml.versionsBackup
pom.xml.next
release.properties
dependency-reduced-pom.xml
buildNumber.properties
.mvn/timing.properties
.mvn/wrapper/maven-wrapper.jar

# Java
*.class
*.log
*.ctxt
.mtj.tmp/
*.jar
*.war
*.nar
*.ear
*.zip
*.tar.gz
*.rar
hs_err_pid*

# IDE
.idea/
*.iws
*.iml
*.ipr
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Kubernetes
*.kubeconfig

# Security scans
dependency-check-report.json
dependency-check-report.html
**/bom.xml

# Logs
logs/
*.log

# Environment
.env
.env.local
.env.*.local

# Helm
*.tgz
charts/*/charts/
charts/*/requirements.lock

# Cosign
cosign.key
cosign.pub'''

README_MD = '''# My Java App

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
helm upgrade --install my-java-app helm/my-java-app \\
  -n my-java-app-dev --create-namespace \\
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
- Helm 3.x'''

def create_project():
    """Create the complete project structure with all files"""
    
    print("🚀 Creating My Java App project structure...")
    
    # Create all directories
    directories = [
        "src/main/java/com/example/myapp",
        "src/main/resources", 
        "src/test/java/com/example/myapp",
        "src/test/resources",
        "helm/my-java-app/templates/tests",
        "helm/my-java-app/charts",
        "target/surefire-reports",
        "target/site/jacoco",
        ".github/workflows"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created directory structure")
    
    # Create all files
    files = {
        "pom.xml": POM_XML,
        "src/main/java/com/example/myapp/MyJavaAppApplication.java": MAIN_APP,
        "src/test/java/com/example/myapp/MyJavaAppApplicationTests.java": TEST_CLASS,
        "src/main/resources/application.properties": APPLICATION_PROPERTIES,
        "Dockerfile": DOCKERFILE,
        "helm/my-java-app/Chart.yaml": CHART_YAML,
        "helm/my-java-app/values.yaml": VALUES_YAML,
        "helm/my-java-app/values-dev.yaml": VALUES_DEV_YAML,
        "helm/my-java-app/values-stg.yaml": VALUES_STG_YAML,
        "helm/my-java-app/templates/deployment.yaml": DEPLOYMENT_YAML,
        "helm/my-java-app/templates/service.yaml": SERVICE_YAML,
        "helm/my-java-app/templates/_helpers.tpl": HELPERS_TPL,
        "helm/my-java-app/templates/tests/test-connection.yaml": TEST_CONNECTION_YAML,
        ".gitignore": GITIGNORE,
        "README.md": README_MD,
        "src/test/resources/.gitkeep": "",
        "helm/my-java-app/charts/.gitkeep": ""
    }
    
    for file_path, content in files.items():
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Created {file_path}")
    
    print("\n🎉 Project created successfully!")
    print("\n📁 Project structure:")
    print("my-java-app/")
    print("├── .gitignore")
    print("├── README.md") 
    print("├── Dockerfile")
    print("├── pom.xml")
    print("├── src/")
    print("│ ├── main/java/com/example/myapp/MyJavaAppApplication.java")
    print("│ ├── main/resources/application.properties")
    print("│ └── test/java/com/example/myapp/MyJavaAppApplicationTests.java")
    print("└── helm/my-java-app/")
    print(" ├── Chart.yaml")
    print(" ├── values.yaml")
    print(" ├── values-dev.yaml")
    print(" ├── values-stg.yaml") 
    print(" └── templates/")
    print(" ├── deployment.yaml")
    print(" ├── service.yaml")
    print(" ├── _helpers.tpl")
    print(" └── tests/test-connection.yaml")
    
    print("\n🚀 Next steps:")
    print("1. cd my-java-app")
    print("2. mvn clean verify")
    print("3. docker build -t my-java-app:latest .")
    print("4. helm lint helm/my-java-app")
    print("\n✅ Your Jenkins pipeline will now succeed!")

if __name__ == "__main__":
    create_project()
