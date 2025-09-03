
"""
Enhanced conversion report generation with dashboard-style output
"""

import re
from typing import List, Dict, Any
from datetime import datetime
from utils import (
    extract_unsupported_features, analyze_pipeline_complexity, 
    validate_conversion_feasibility, detect_languages, detect_tools,
    extract_all_credentials
)


def generate_conversion_report(action_paths: List[Dict[str, Any]], pipeline_text: str) -> str:
    """Generate a comprehensive dashboard-style conversion report"""
    
    # Generate report timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Analyze the pipeline
    complexity_analysis = analyze_pipeline_complexity(pipeline_text)
    feasibility_analysis = validate_conversion_feasibility(pipeline_text)
    unsupported_features = extract_unsupported_features(pipeline_text)
    languages = detect_languages(pipeline_text)
    tools = detect_tools(pipeline_text)
    all_credentials = extract_all_credentials(pipeline_text)
    
    report = [
        "# 🚀 Jenkins to GitHub Actions Conversion Dashboard",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Pipeline Complexity:** {complexity_analysis['complexity_level']} ({complexity_analysis['complexity_score']} points)  ",
        f"**Conversion Feasibility:** {feasibility_analysis['confidence']}  ",
        ""
    ]
    
    # Overall status badges
    report.extend([
        "## 📊 Conversion Status Overview",
        "",
        generate_status_badges(action_paths, feasibility_analysis, complexity_analysis),
        ""
    ])
    
    # Quick stats dashboard
    report.extend([
        "## 📈 Quick Statistics",
        "",
        generate_stats_table(action_paths, pipeline_text, complexity_analysis),
        ""
    ])
    
    # Feasibility analysis
    if not feasibility_analysis['can_convert'] or feasibility_analysis['warnings']:
        report.extend([
            "## ⚠️ Conversion Feasibility Analysis",
            ""
        ])
        
        if not feasibility_analysis['can_convert']:
            report.extend([
                "### 🔴 Conversion Blockers",
                "*These issues must be resolved before conversion can succeed:*",
                ""
            ])
            for blocker in feasibility_analysis['blockers']:
                report.append(f"- ❌ {blocker}")
            report.append("")
        
        if feasibility_analysis['warnings']:
            report.extend([
                "### 🟡 Warnings & Considerations",
                "*These issues may require additional attention:*",
                ""
            ])
            for warning in feasibility_analysis['warnings']:
                report.append(f"- ⚠️ {warning}")
            report.append("")
    
    # Technology stack summary
    if languages or tools:
        report.extend([
            "## 🛠️ Technology Stack Detected",
            ""
        ])
        
        if languages:
            report.append("**Languages/Frameworks:**  ")
            report.append(" | ".join([f"`{lang}`" for lang in languages]))
            report.append("")
        
        if tools:
            report.append("**Tools & Technologies:**  ")
            report.append(" | ".join([f"`{tool}`" for tool in tools]))
            report.append("")
    
    # Secrets and credentials setup
    if all_credentials:
        report.extend([
            "## 🔐 Required GitHub Secrets Configuration",
            "",
            generate_secrets_table(all_credentials, action_paths),
            ""
        ])
    
    # Additional service setup
    additional_setup = generate_additional_setup_requirements(action_paths)
    if additional_setup:
        report.extend([
            "## 🔧 Additional Setup Requirements",
            "",
            additional_setup,
            ""
        ])
    
    # Stage-by-stage conversion details
    if action_paths:
        report.extend([
            "## 📋 Stage Conversion Details",
            "",
            generate_stage_details_table(action_paths),
            ""
        ])
    
    # Manual conversion requirements
    manual_items = get_manual_conversion_items(action_paths, unsupported_features)
    if manual_items:
        report.extend([
            "## 🔧 Manual Conversion Required",
            "*The following items need manual attention:*",
            "",
            generate_manual_conversion_table(manual_items),
            ""
        ])
    
    # Post-action handling summary
    post_actions = get_post_action_summary(action_paths)
    if post_actions:
        report.extend([
            "## 📤 Post-Action Handling",
            "",
            generate_post_actions_table(post_actions),
            ""
        ])
    
    # Approval gates and environments
    approval_envs = [a for a in action_paths if a.get("approval_environment")]
    if approval_envs:
        report.extend([
            "## 🚦 Manual Approval Gates",
            "*Configure these environments in GitHub repository settings:*",
            "",
            generate_approval_environments_table(approval_envs),
            ""
        ])
    
    # Implementation roadmap
    report.extend([
        "## 🗺️ Implementation Roadmap",
        "",
        generate_implementation_roadmap(action_paths, feasibility_analysis, complexity_analysis),
        ""
    ])
    
    # File structure overview
    report.extend([
        "## 📁 Generated Files Structure",
        "",
        generate_file_structure_diagram(action_paths),
        ""
    ])
    
    # Next steps and best practices
    report.extend([
        "## ✅ Next Steps Checklist",
        "",
        generate_next_steps_checklist(action_paths, all_credentials, feasibility_analysis),
        ""
    ])
    
    # Tips and best practices
    report.extend([
        "## 💡 Tips for Success",
        "",
        generate_tips_and_best_practices(complexity_analysis, action_paths),
        ""
    ])
    
    # Troubleshooting section
    report.extend([
        "## 🔍 Common Issues & Troubleshooting",
        "",
        generate_troubleshooting_guide(action_paths),
        ""
    ])
    
    return "\n".join(report)


def generate_status_badges(action_paths: List[Dict[str, Any]], feasibility: Dict[str, Any], complexity: Dict[str, Any]) -> str:
    """Generate status badges for the dashboard"""
    total_stages = len(action_paths)
    manual_stages = len([a for a in action_paths if a.get("manual_conversion_needed")])
    
    feasibility_color = {"High": "green", "Medium": "yellow", "Low": "red"}.get(feasibility["confidence"], "red")
    complexity_color = {"Low": "green", "Medium": "yellow", "High": "orange", "Very High": "red"}.get(complexity["complexity_level"], "red")
    
    badges = [
        f"![Stages Converted](https://img.shields.io/badge/Stages_Converted-{total_stages}-blue)",
        f"![Manual Required](https://img.shields.io/badge/Manual_Required-{manual_stages}-orange)",
        f"![Feasibility](https://img.shields.io/badge/Feasibility-{feasibility['confidence']}-{feasibility_color})",
        f"![Complexity](https://img.shields.io/badge/Complexity-{complexity['complexity_level'].replace(' ', '_')}-{complexity_color})"
    ]
    
    return " ".join(badges)


def generate_stats_table(action_paths: List[Dict[str, Any]], pipeline_text: str, complexity: Dict[str, Any]) -> str:
    """Generate quick statistics table"""
    stats = [
        "| Metric | Value | Details |",
        "|--------|-------|---------|"
    ]
    
    total_stages = len(action_paths)
    docker_stages = len([a for a in action_paths if a.get("has_docker")])
    k8s_stages = len([a for a in action_paths if a.get("has_kubectl")])
    sonar_stages = len([a for a in action_paths if a.get("has_sonarqube")])
    approval_stages = len([a for a in action_paths if a.get("approval_environment")])
    post_action_stages = len([a for a in action_paths if a.get("has_post_actions")])
    manual_stages = len([a for a in action_paths if a.get("manual_conversion_needed")])
    
    stats.extend([
        f"| Total Stages | **{total_stages}** | Number of pipeline stages converted |",
        f"| Docker Operations | **{docker_stages}** | Stages with Docker build/push operations |",
        f"| Kubernetes Stages | **{k8s_stages}** | Stages with kubectl/helm commands |",
        f"| SonarQube Integration | **{sonar_stages}** | Stages with code quality scanning |",
        f"| Approval Gates | **{approval_stages}** | Stages requiring manual approval |",
        f"| Post-Action Handling | **{post_action_stages}** | Stages with post-execution actions |",
        f"| Manual Conversion | **{manual_stages}** | Stages needing manual attention |",
        f"| Complexity Score | **{complexity['complexity_score']}** | Overall pipeline complexity rating |"
    ])
    
    return "\n".join(stats)


def generate_secrets_table(all_credentials: set, action_paths: List[Dict[str, Any]]) -> str:
    """Generate secrets configuration table"""
    table = [
        "| Secret Name | Purpose | Required For | Type |",
        "|-------------|---------|--------------|------|"
    ]
    
    # Process credential requirements
    credential_map = {}
    for cred in all_credentials:
        secret_name = cred.upper().replace("-", "_").replace(".", "_")
        stages_using = [a["name"] for a in action_paths if cred in a.get("credentials", [])]
        credential_map[secret_name] = {
            "original": cred,
            "stages": stages_using,
            "type": detect_credential_type(cred)
        }
    
    # Add common Docker/SonarQube secrets
    if any(a.get("has_docker") for a in action_paths):
        credential_map["DOCKER_USERNAME"] = {"original": "docker-login", "stages": ["Docker operations"], "type": "Username"}
        credential_map["DOCKER_PASSWORD"] = {"original": "docker-login", "stages": ["Docker operations"], "type": "Password/Token"}
    
    if any(a.get("has_sonarqube") for a in action_paths):
        credential_map["SONAR_TOKEN"] = {"original": "sonarqube-token", "stages": ["SonarQube analysis"], "type": "Token"}
        credential_map["SONAR_HOST_URL"] = {"original": "sonarqube-server", "stages": ["SonarQube analysis"], "type": "URL"}
    
    for secret_name, info in sorted(credential_map.items()):
        purpose = get_credential_purpose(info["original"])
        stages_list = ", ".join(info["stages"][:3]) + ("..." if len(info["stages"]) > 3 else "")
        table.append(f"| `{secret_name}` | {purpose} | {stages_list} | {info['type']} |")
    
    return "\n".join(table)


def detect_credential_type(cred_id: str) -> str:
    """Detect the type of credential based on its ID"""
    cred_lower = cred_id.lower()
    if "ssh" in cred_lower:
        return "SSH Key"
    elif any(x in cred_lower for x in ["token", "api", "key"]):
        return "Token/API Key"
    elif any(x in cred_lower for x in ["password", "pwd"]):
        return "Password"
    elif any(x in cred_lower for x in ["username", "user"]):
        return "Username"
    elif "kubeconfig" in cred_lower:
        return "File (Kubeconfig)"
    elif any(x in cred_lower for x in ["cert", "certificate", "pem"]):
        return "Certificate"
    else:
        return "Credential"


def get_credential_purpose(cred_id: str) -> str:
    """Get the purpose description for a credential"""
    cred_lower = cred_id.lower()
    if "docker" in cred_lower:
        return "Docker registry authentication"
    elif "git" in cred_lower or "github" in cred_lower:
        return "Git repository access"
    elif "sonar" in cred_lower:
        return "SonarQube server authentication"
    elif "kubeconfig" in cred_lower or "k8s" in cred_lower:
        return "Kubernetes cluster access"
    elif "aws" in cred_lower:
        return "AWS service authentication"
    elif "ssh" in cred_lower:
        return "SSH server access"
    else:
        return f"Authentication for {cred_id}"


def generate_additional_setup_requirements(action_paths: List[Dict[str, Any]]) -> str:
    """Generate additional setup requirements"""
    requirements = []
    
    # Check for specific service requirements
    has_sonar = any(a.get("has_sonarqube") for a in action_paths)
    has_docker = any(a.get("has_docker") for a in action_paths)
    has_k8s = any(a.get("has_kubectl") for a in action_paths)
    has_approvals = any(a.get("approval_environment") for a in action_paths)
    
    if has_sonar:
        requirements.append("### SonarQube Integration")
        requirements.extend([
            "- Configure SonarQube server URL in secrets",
            "- Generate SonarQube authentication token",
            "- Set up project key and quality gates",
            ""
        ])
    
    if has_docker:
        requirements.append("### Docker Registry Setup")
        requirements.extend([
            "- Configure Docker Hub or alternative registry credentials",
            "- Ensure repository has appropriate registry permissions",
            "- Consider using GitHub Container Registry (ghcr.io) for better integration",
            ""
        ])
    
    if has_k8s:
        requirements.append("### Kubernetes Configuration")
        requirements.extend([
            "- Configure kubeconfig file as repository secret",
            "- Ensure cluster access from GitHub Actions runners",
            "- Set up appropriate RBAC permissions",
            "- Consider using OIDC for secure authentication",
            ""
        ])
    
    if has_approvals:
        requirements.append("### Environment Protection Rules")
        requirements.extend([
            "- Create environments in repository settings",
            "- Configure required reviewers for approval gates",
            "- Set up environment-specific secrets if needed",
            ""
        ])
    
    return "\n".join(requirements) if requirements else "*No additional setup required*"


def generate_stage_details_table(action_paths: List[Dict[str, Any]]) -> str:
    """Generate detailed stage conversion table"""
    table = [
        "| Stage | Complexity | Features | Manual Items | Status |",
        "|-------|------------|----------|--------------|--------|"
    ]
    
    for action in action_paths:
        stage_name = action["name"]
        complexity = action.get("complexity_score", 0)
        complexity_level = "Low" if complexity < 10 else "Medium" if complexity < 25 else "High"
        
        features = []
        if action.get("has_docker"):
            features.append("Docker")
        if action.get("has_kubectl"):
            features.append("K8s")
        if action.get("has_sonarqube"):
            features.append("SonarQube")
        if action.get("approval_environment"):
            features.append("Approval")
        if action.get("has_post_actions"):
            features.append("Post-Actions")
        
        features_str = ", ".join(features) if features else "Basic"
        manual_items = len(action.get("manual_conversion_needed", []))
        manual_str = f"{manual_items} items" if manual_items > 0 else "None"
        
        status = "⚠️ Manual" if manual_items > 0 else "✅ Ready"
        
        table.append(f"| {stage_name} | {complexity_level} ({complexity}) | {features_str} | {manual_str} | {status} |")
    
    return "\n".join(table)


def get_manual_conversion_items(action_paths: List[Dict[str, Any]], unsupported_features: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Collect all manual conversion items"""
    manual_items = []
    
    # From stage-level analysis
    for action in action_paths:
        for item in action.get("manual_conversion_needed", []):
            manual_items.append({
                "stage": action["name"],
                "item": item,
                "type": "Stage Feature",
                "priority": "Medium"
            })
    
    # From unsupported features analysis
    for feature in unsupported_features:
        manual_items.append({
            "stage": "Pipeline Level",
            "item": feature["feature"],
            "type": "Pipeline Feature", 
            "priority": "High" if "blocker" in feature.get("manual_action", "").lower() else "Medium"
        })
    
    return manual_items


def generate_manual_conversion_table(manual_items: List[Dict[str, Any]]) -> str:
    """Generate manual conversion requirements table"""
    table = [
        "| Priority | Stage | Item | Action Required |",
        "|----------|-------|------|------------------|"
    ]
    
    # Sort by priority (High first)
    sorted_items = sorted(manual_items, key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x["priority"], 2))
    
    for item in sorted_items:
        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(item["priority"], "⚪")
        table.append(f"| {priority_emoji} {item['priority']} | {item['stage']} | {item['item']} | Manual implementation required |")
    
    return "\n".join(table)


def get_post_action_summary(action_paths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get summary of post-action handling"""
    post_summary = {}
    
    for action in action_paths:
        if action.get("has_post_actions"):
            stage_name = action["name"]
            post_types = action.get("post_action_types", [])
            post_summary[stage_name] = post_types
    
    return post_summary


def generate_post_actions_table(post_actions: Dict[str, Any]) -> str:
    """Generate post-actions handling table"""
    table = [
        "| Stage | Post Conditions | GitHub Actions Equivalent |",
        "|-------|-----------------|---------------------------|"
    ]
    
    condition_map = {
        "always": "always() - Runs regardless of job result",
        "success": "success() - Runs only on successful completion",
        "failure": "failure() - Runs only on job failure",
        "unstable": "success() \\|\\| failure() - Runs on completion (no direct equivalent)",
        "cleanup": "always() - Used for cleanup operations"
    }
    
    for stage, conditions in post_actions.items():
        conditions_str = ", ".join(conditions)
        gha_equivalent = "; ".join([condition_map.get(c, f"{c}() - Custom condition") for c in conditions])
        table.append(f"| {stage} | {conditions_str} | {gha_equivalent} |")
    
    return "\n".join(table)


def generate_approval_environments_table(approval_envs: List[Dict[str, Any]]) -> str:
    """Generate approval environments configuration table"""
    table = [
        "| Environment Name | Stage | Configuration Steps |",
        "|------------------|-------|---------------------|"
    ]
    
    for env_action in approval_envs:
        env_name = env_action["approval_environment"]
        stage_name = env_action["name"]
        config_steps = "Go to Settings → Environments → Create environment → Add required reviewers"
        table.append(f"| `{env_name}` | {stage_name} | {config_steps} |")
    
    return "\n".join(table)


def generate_implementation_roadmap(action_paths: List[Dict[str, Any]], feasibility: Dict[str, Any], complexity: Dict[str, Any]) -> str:
    """Generate implementation roadmap based on analysis"""
    roadmap = []
    
    if not feasibility["can_convert"]:
        roadmap.extend([
            "### Phase 1: Resolve Conversion Blockers ❌",
            "- Address pipeline-level issues that prevent conversion",
            "- Refactor unsupported Jenkins features",
            "- Test individual components",
            ""
        ])
    
    roadmap.extend([
        "### Phase 1: Initial Setup 🔧",
        "1. Configure GitHub repository secrets and environments",
        "2. Set up external service integrations (SonarQube, Docker registry, etc.)",
        "3. Create the main workflow file (`.github/workflows/ci.yml`)",
        ""
    ])
    
    # Determine implementation phases based on complexity
    simple_stages = [a for a in action_paths if a.get("complexity_score", 0) < 10]
    complex_stages = [a for a in action_paths if a.get("complexity_score", 0) >= 10]
    
    if simple_stages:
        roadmap.extend([
            "### Phase 2: Deploy Simple Stages ✅",
            f"*{len(simple_stages)} stages with basic functionality*",
            ""
        ])
        for stage in simple_stages[:5]:  # Show first 5
            roadmap.append(f"- {stage['name']}")
        if len(simple_stages) > 5:
            roadmap.append(f"- ... and {len(simple_stages) - 5} more")
        roadmap.append("")
    
    if complex_stages:
        roadmap.extend([
            "### Phase 3: Implement Complex Stages ⚠️",
            f"*{len(complex_stages)} stages requiring additional attention*",
            ""
        ])
        for stage in complex_stages[:5]:  # Show first 5
            manual_count = len(stage.get("manual_conversion_needed", []))
            status = f" ({manual_count} manual items)" if manual_count > 0 else ""
            roadmap.append(f"- {stage['name']}{status}")
        if len(complex_stages) > 5:
            roadmap.append(f"- ... and {len(complex_stages) - 5} more")
        roadmap.append("")
    
    roadmap.extend([
        "### Phase 4: Testing & Validation 🧪",
        "1. Test workflow with sample commits",
        "2. Validate all secrets and environment configurations",
        "3. Test approval processes and post-action handling",
        "4. Performance comparison with original Jenkins pipeline",
        "",
        "### Phase 5: Production Deployment 🚀",
        "1. Gradually migrate from Jenkins to GitHub Actions",
        "2. Monitor workflow performance and reliability",
        "3. Train team on new workflow processes",
        "4. Decommission Jenkins pipeline once stable",
        ""
    ])
    
    return "\n".join(roadmap)


def generate_file_structure_diagram(action_paths: List[Dict[str, Any]]) -> str:
    """Generate file structure diagram"""
    structure = [
        "```",
        ".github/",
        "├── workflows/",
        "│   └── ci.yml                 # Main workflow file",
        "└── actions/"
    ]
    
    # Add composite actions
    for i, action in enumerate(action_paths):
        action_name = action["name"].lower().replace(" ", "-").replace("/", "-")
        is_last_action = i == len(action_paths) - 1
        prefix = "    └──" if is_last_action else "    ├──"
        
        structure.append(f"{prefix} {action_name}/")
        structure.append(f"    {'    ' if is_last_action else '│   '}└── action.yml")
    
    structure.extend([
        "",
        "CONVERSION_REPORT.md           # This report",
        "```"
    ])
    
    return "\n".join(structure)


def generate_next_steps_checklist(action_paths: List[Dict[str, Any]], all_credentials: set, feasibility: Dict[str, Any]) -> str:
    """Generate next steps checklist"""
    checklist = []
    
    # Pre-conversion steps
    if not feasibility["can_convert"]:
        checklist.extend([
            "### Pre-Conversion Requirements",
            "- [ ] Resolve conversion blockers identified above",
            "- [ ] Test Jenkins pipeline modifications",
            ""
        ])
    
    # Basic setup
    checklist.extend([
        "### Repository Setup",
        "- [ ] Review generated workflow file (`.github/workflows/ci.yml`)",
        "- [ ] Configure repository secrets in GitHub Settings",
        f"- [ ] Set up {len(all_credentials)} required secrets (see table above)",
        ""
    ])
    
    # Service-specific setup
    if any(a.get("has_sonarqube") for a in action_paths):
        checklist.append("- [ ] Configure SonarQube integration")
    if any(a.get("has_docker") for a in action_paths):
        checklist.append("- [ ] Set up Docker registry authentication")
    if any(a.get("has_kubectl") for a in action_paths):
        checklist.append("- [ ] Configure Kubernetes cluster access")
    if any(a.get("approval_environment") for a in action_paths):
        checklist.append("- [ ] Create approval environments with required reviewers")
    
    if any([a.get("has_sonarqube") or a.get("has_docker") or a.get("has_kubectl") or a.get("approval_environment") for a in action_paths]):
        checklist.append("")
    
    # Manual conversion items
    manual_items = sum(len(a.get("manual_conversion_needed", [])) for a in action_paths)
    if manual_items > 0:
        checklist.extend([
            "### Manual Conversion Tasks",
            f"- [ ] Address {manual_items} manual conversion items (see table above)",
            "- [ ] Test complex script blocks and plugin replacements",
            ""
        ])
    
    # Testing and validation
    checklist.extend([
        "### Testing & Validation",
        "- [ ] Create test branch and trigger workflow",
        "- [ ] Verify all secrets are properly configured",
        "- [ ] Test approval processes (if applicable)",
        "- [ ] Validate artifact uploads and post-action handling",
        "- [ ] Compare results with original Jenkins pipeline",
        "",
        "### Production Deployment",
        "- [ ] Update team documentation and runbooks",
        "- [ ] Train team members on GitHub Actions workflow",
        "- [ ] Set up monitoring and alerting for workflow failures",
        "- [ ] Plan migration timeline from Jenkins",
        ""
    ])
    
    return "\n".join(checklist)


def generate_tips_and_best_practices(complexity: Dict[str, Any], action_paths: List[Dict[str, Any]]) -> str:
    """Generate tips and best practices"""
    tips = [
        "### General Best Practices",
        "- **Start Small**: Begin with the simplest stages and gradually add complexity",
        "- **Test Frequently**: Run the workflow on feature branches before merging",
        "- **Use Environments**: Leverage GitHub environments for deployment approvals and protection",
        "- **Cache Dependencies**: Implement caching for build dependencies to improve performance",
        ""
    ]
    
    if complexity["complexity_level"] in ["High", "Very High"]:
        tips.extend([
            "### High Complexity Pipeline Tips",
            "- **Break Down Complex Stages**: Consider splitting large stages into smaller, focused jobs",
            "- **Use Matrix Strategies**: Leverage GitHub Actions matrix builds for parallel execution",
            "- **Monitor Resource Usage**: GitHub Actions has different resource limits than Jenkins",
            ""
        ])
    
    if any(a.get("has_docker") for a in action_paths):
        tips.extend([
            "### Docker Best Practices",
            "- **Use Multi-stage Builds**: Optimize Docker images for faster builds and smaller sizes",
            "- **Implement Layer Caching**: Use Docker layer caching actions for better performance",
            "- **Consider GitHub Container Registry**: Use ghcr.io for better integration and security",
            ""
        ])
    
    if any(a.get("has_kubectl") for a in action_paths):
        tips.extend([
            "### Kubernetes Deployment Tips",
            "- **Use OIDC Authentication**: Implement OpenID Connect for secure, keyless authentication",
            "- **Implement Rollback Strategies**: Plan for deployment failures and rollback procedures",
            "- **Monitor Deployments**: Set up proper health checks and monitoring",
            ""
        ])
    
    tips.extend([
        "### Performance Optimization",
        "- **Concurrent Jobs**: Use job dependencies (`needs`) to run independent stages in parallel",
        "- **Conditional Execution**: Use `if` conditions to skip unnecessary steps",
        "- **Artifact Management**: Only upload necessary artifacts and clean up old ones",
        "- **Runner Selection**: Choose appropriate runner types for your workload",
        ""
    ])
    
    return "\n".join(tips)


def generate_troubleshooting_guide(action_paths: List[Dict[str, Any]]) -> str:
    """Generate troubleshooting guide"""
    guide = [
        "### Common Issues",
        "",
        "**Secrets Not Found**",
        "- Verify secret names match exactly (case-sensitive)",
        "- Check secret availability in the correct repository/environment scope",
        "- Ensure secrets are not exposed in logs",
        "",
        "**Permission Denied Errors**",
        "- Verify GITHUB_TOKEN has necessary permissions",
        "- Check repository and organization settings for Actions permissions",
        "- Ensure external services (Docker registry, K8s cluster) allow access",
        "",
        "**Workflow Timeouts**",
        "- GitHub Actions has a 6-hour maximum job runtime",
        "- Split long-running jobs into smaller, parallel jobs",
        "- Optimize build processes and use caching",
        ""
    ]
    
    if any(a.get("has_docker") for a in action_paths):
        guide.extend([
            "**Docker Issues**",
            "- Ensure Docker registry credentials are correct",
            "- Check image names and tags for typos",
            "- Verify registry permissions for push operations",
            ""
        ])
    
    if any(a.get("has_kubectl") for a in action_paths):
        guide.extend([
            "**Kubernetes Issues**",
            "- Validate kubeconfig file format and cluster connectivity",
            "- Check RBAC permissions for deployment operations",
            "- Verify namespace existence and access rights",
            ""
        ])
    
    if any(a.get("approval_environment") for a in action_paths):
        guide.extend([
            "**Approval Environment Issues**",
            "- Ensure environments are created in repository settings",
            "- Verify required reviewers are configured correctly",
            "- Check that approvers have repository access",
            ""
        ])
    
    guide.extend([
        "### Getting Help",
        "- Check [GitHub Actions documentation](https://docs.github.com/en/actions)",
        "- Review workflow run logs for detailed error messages",
        "- Use GitHub Community discussions for complex issues",
        "- Consider GitHub Support for enterprise-specific problems"
    ])
    
    return "\n".join(guide)