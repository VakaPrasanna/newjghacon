
"""
Enhanced composite action generation for GitHub Actions with comprehensive post-action support
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Any

from utils import sanitize_name, generate_limitations_comment
from jenkins_extractors import (
    extract_tools, extract_git_steps, extract_sonarqube_steps, 
    extract_docker_steps, extract_kubectl_steps, extract_input_steps,
    extract_credentials_usage, extract_steps_commands, extract_stage_post,
    extract_withCredentials_blocks, extract_script_blocks, extract_plugin_steps
)


def generate_tool_setup_steps(tools: Dict[str, str]) -> List[Dict[str, Any]]:
    """Generate setup steps for tools"""
    setup_steps = []
    
    # Java/JDK setup
    if "jdk" in tools or "maven" in tools:
        java_version = "17"  # Default to 17 for modern setups
        if "jdk" in tools:
            jdk_name = tools["jdk"].lower()
            if "8" in jdk_name:
                java_version = "8"
            elif "11" in jdk_name:
                java_version = "11"
            elif "17" in jdk_name:
                java_version = "17"
            elif "21" in jdk_name:
                java_version = "21"
        
        setup_steps.append({
            "name": "Set up JDK",
            "uses": "actions/setup-java@v4",
            "with": {
                "java-version": java_version,
                "distribution": "temurin"
            }
        })
    
    # Maven cache
    if "maven" in tools:
        setup_steps.append({
            "name": "Cache Maven packages",
            "uses": "actions/cache@v4",
            "with": {
                "path": "~/.m2",
                "key": "${{ runner.os }}-m2-${{ hashFiles('**/pom.xml') }}",
                "restore-keys": "${{ runner.os }}-m2"
            }
        })
    
    # Node.js setup
    if "nodejs" in tools:
        node_version = "18"  # Default
        if "nodejs" in tools:
            nodejs_name = tools["nodejs"].lower()
            if "16" in nodejs_name:
                node_version = "16"
            elif "18" in nodejs_name:
                node_version = "18"
            elif "20" in nodejs_name:
                node_version = "20"
        
        setup_steps.append({
            "name": "Set up Node.js",
            "uses": "actions/setup-node@v4",
            "with": {
                "node-version": node_version,
                "cache": "npm"
            }
        })
    
    return setup_steps


def convert_git_steps_to_actions(git_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Jenkins git steps to GitHub Actions checkout steps"""
    checkout_steps = []
    
    for git_step in git_steps:
        step = {
            "name": "Checkout code",
            "uses": "actions/checkout@v4"
        }
        
        with_params = {}
        
        # Handle different git step types
        if git_step.get("type") == "scm":
            # checkout scm - use default checkout
            checkout_steps.append(step)
            continue
        elif git_step.get("type") == "clone":
            step["name"] = "Clone repository"
            if git_step["url"]:
                with_params["repository"] = extract_repo_from_url(git_step["url"])
            if git_step["branch"]:
                with_params["ref"] = git_step["branch"]
        else:
            # Standard git checkout
            if git_step["url"]:
                with_params["repository"] = extract_repo_from_url(git_step["url"])
            
            if git_step["branch"]:
                branch = git_step["branch"]
                # Handle parameter references
                if "${params." in branch:
                    param_name = re.search(r"\$\{params\.([^}]+)\}", branch)
                    if param_name:
                        with_params["ref"] = f"${{{{ inputs.{param_name.group(1)} }}}}"
                else:
                    with_params["ref"] = branch
        
        if git_step["credentialsId"]:
            # Convert credential ID to secret reference
            cred_id = sanitize_credential_name(git_step["credentialsId"])
            with_params["token"] = f"${{{{ secrets.{cred_id} }}}}"
        
        if with_params:
            step["with"] = with_params
        
        checkout_steps.append(step)
    
    return checkout_steps


def extract_repo_from_url(url: str) -> str:
    """Extract repository name from git URL"""
    if url.startswith("https://github.com/"):
        return url.replace("https://github.com/", "").replace(".git", "")
    elif url.startswith("git@github.com:"):
        return url.replace("git@github.com:", "").replace(".git", "")
    elif "/" in url and not url.startswith("http"):
        # Assume it's already in owner/repo format
        return url
    return url


def sanitize_credential_name(cred_id: str) -> str:
    """Convert credential ID to valid secret name"""
    return cred_id.upper().replace("-", "_").replace(".", "_")


def convert_sonarqube_steps(sonar_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert SonarQube steps to GitHub Actions"""
    sonar_actions = []
    
    for sonar_step in sonar_steps:
        # Add SonarQube scan action
        action = {
            "name": "SonarQube Scan",
            "uses": "sonarqube-scan-action@master",
            "env": {
                "SONAR_TOKEN": "${{ secrets.SONAR_TOKEN }}",
                "SONAR_HOST_URL": "${{ secrets.SONAR_HOST_URL }}"
            }
        }
        
        # Extract sonar properties from commands
        with_params = {}
        for cmd in sonar_step["commands"]:
            if "-Dsonar.projectKey=" in cmd:
                key_match = re.search(r"-Dsonar\.projectKey=([^\s]+)", cmd)
                if key_match:
                    with_params["projectKey"] = key_match.group(1)
            
            if "-Dsonar.projectName=" in cmd:
                name_match = re.search(r"-Dsonar\.projectName=([^\s'\"]+)", cmd)
                if name_match:
                    with_params["projectName"] = name_match.group(1).strip("'\"")
        
        if with_params:
            action["with"] = with_params
        
        sonar_actions.append(action)
        
        # Add original commands as fallback for complex scenarios
        for cmd in sonar_step["commands"]:
            sonar_actions.append({
                "name": "Run SonarQube analysis",
                "run": cmd,
                "shell": "bash",
                "env": {
                    "SONAR_TOKEN": "${{ secrets.SONAR_TOKEN }}",
                    "SONAR_HOST_URL": "${{ secrets.SONAR_HOST_URL }}"
                }
            })
    
    return sonar_actions


def convert_docker_steps(docker_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Docker steps to GitHub Actions"""
    docker_actions = []
    needs_login = False
    
    for docker_step in docker_steps:
        if docker_step["type"] == "build":
            build_cmd = f"docker build -t {docker_step['tag']} {docker_step['context']}"
            if docker_step.get("dockerfile"):
                build_cmd = f"docker build -f {docker_step['dockerfile']} -t {docker_step['tag']} {docker_step['context']}"
            
            docker_actions.append({
                "name": "Build Docker image",
                "run": build_cmd,
                "shell": "bash"
            })
        elif docker_step["type"] == "push":
            needs_login = True
            docker_actions.append({
                "name": "Push Docker image",
                "run": f"docker push {docker_step['tag']}",
                "shell": "bash"
            })
        elif docker_step["type"] == "login":
            needs_login = True
    
    # Add Docker login if needed
    if needs_login:
        login_step = {
            "name": "Login to DockerHub",
            "uses": "docker/login-action@v3",
            "with": {
                "username": "${{ secrets.DOCKER_USERNAME }}",
                "password": "${{ secrets.DOCKER_PASSWORD }}"
            }
        }
        docker_actions.insert(0, login_step)
    
    return docker_actions


def convert_input_steps_to_environment(input_steps: List[Dict[str, Any]], stage_name: str) -> str:
    """Convert input steps to environment requirement"""
    if input_steps:
        # Return environment name for manual approval
        return f"approval-{sanitize_name(stage_name.lower())}"
    return ""


def convert_post_actions_to_steps(post_info: Dict[str, Any], stage_name: str) -> List[Dict[str, Any]]:
    """Convert Jenkins post actions to GitHub Actions steps with proper conditions"""
    post_steps = []
    
    # Map Jenkins post conditions to GitHub Actions conditions
    condition_map = {
        "always": "always()",
        "success": "success()",
        "failure": "failure()",
        "unstable": "success() || failure()",  # GitHub doesn't have unstable, treat as always
        "cleanup": "always()",
        "aborted": "cancelled()"
    }
    
    for condition, actions in post_info.items():
        gha_condition = condition_map.get(condition, "always()")
        
        # Handle archiveArtifacts
        if "archive" in actions:
            step = {
                "name": f"Upload artifacts ({condition})",
                "if": gha_condition,
                "uses": "actions/upload-artifact@v4",
                "with": {
                    "name": f"{sanitize_name(stage_name)}-{condition}-artifacts",
                    "path": actions["archive"]
                }
            }
            
            # Add additional options
            if actions.get("allowEmptyArchive"):
                step["continue-on-error"] = True
            
            post_steps.append(step)
        
        # Handle junit test results
        if "junit" in actions:
            junit_info = actions["junit"]
            step = {
                "name": f"Publish test results ({condition})",
                "if": gha_condition,
                "uses": "dorny/test-reporter@v1",
                "with": {
                    "name": f"{stage_name} Test Results",
                    "path": junit_info["testResults"],
                    "reporter": "java-junit"
                }
            }
            
            if junit_info.get("allowEmptyResults"):
                step["continue-on-error"] = True
            
            post_steps.append(step)
        
        # Handle coverage reports
        if "coverage" in actions:
            coverage_info = actions["coverage"]
            if coverage_info["type"] == "jacoco":
                post_steps.append({
                    "name": f"Upload coverage reports ({condition})",
                    "if": gha_condition,
                    "uses": "codecov/codecov-action@v3",
                    "with": {
                        "file": coverage_info["path"],
                        "fail_ci_if_error": "false"
                    }
                })
        
        # Handle mail notifications
        if "mail" in actions:
            mail_info = actions["mail"]
            post_steps.append({
                "name": f"Send email notification ({condition})",
                "if": gha_condition,
                "uses": "dawidd6/action-send-mail@v3",
                "with": {
                    "server_address": "smtp.gmail.com",
                    "server_port": "587",
                    "username": "${{ secrets.EMAIL_USERNAME }}",
                    "password": "${{ secrets.EMAIL_PASSWORD }}",
                    "subject": mail_info.get("subject", f"Pipeline {condition}: ${{ github.workflow }}"),
                    "to": mail_info["to"],
                    "from": "${{ secrets.EMAIL_USERNAME }}",
                    "body": mail_info.get("body", f"Pipeline {condition} for ${{ github.repository }} - ${{ github.sha }}")
                }
            })
        
        # Handle Slack notifications
        if "slack" in actions:
            post_steps.append({
                "name": f"Slack notification ({condition})",
                "if": gha_condition,
                "uses": "8398a7/action-slack@v3",
                "with": {
                    "status": condition,
                    "channel": "${{ secrets.SLACK_CHANNEL }}",
                    "webhook_url": "${{ secrets.SLACK_WEBHOOK_URL }}"
                }
            })
        
        # Handle cleanup actions
        if actions.get("deleteDir") or actions.get("cleanWs"):
            post_steps.append({
                "name": f"Cleanup workspace ({condition})",
                "if": gha_condition,
                "run": "rm -rf ${{ github.workspace }}/*",
                "shell": "bash"
            })
        
        # Handle custom commands
        if "commands" in actions:
            for i, cmd in enumerate(actions["commands"]):
                post_steps.append({
                    "name": f"Post {condition} command {i+1}",
                    "if": gha_condition,
                    "run": cmd,
                    "shell": "bash"
                })
        
        # Handle script blocks (require manual conversion)
        if "script_block" in actions:
            post_steps.append({
                "name": f"Post {condition} script (MANUAL CONVERSION REQUIRED)",
                "if": gha_condition,
                "run": generate_limitations_comment("Script block", actions["script_block"][:100] + "..."),
                "shell": "bash"
            })
    
    return post_steps


def convert_credentials_to_env_setup(cred_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert withCredentials blocks to GitHub Actions environment setup"""
    env_steps = []
    
    for cred_block in cred_blocks:
        # Create environment setup based on credential types
        env_vars = {}
        secrets_needed = []
        
        for cred in cred_block["credentials"]:
            cred_name = sanitize_credential_name(cred["credentialsId"])
            
            if cred["type"] == "usernamePassword":
                env_vars[cred["usernameVariable"]] = f"${{{{ secrets.{cred_name}_USERNAME }}}}"
                env_vars[cred["passwordVariable"]] = f"${{{{ secrets.{cred_name}_PASSWORD }}}}"
                secrets_needed.extend([f"{cred_name}_USERNAME", f"{cred_name}_PASSWORD"])
            elif cred["type"] == "string":
                env_vars[cred["variable"]] = f"${{{{ secrets.{cred_name} }}}}"
                secrets_needed.append(cred_name)
            elif cred["type"] == "file":
                # File credentials need special handling
                env_steps.append({
                    "name": f"Setup {cred['variable']} file credential",
                    "run": f"echo '${{{{ secrets.{cred_name} }}}}' > {cred['variable']}",
                    "shell": "bash"
                })
                env_vars[cred["variable"]] = cred["variable"]
                secrets_needed.append(cred_name)
        
        # Add the actual commands with environment variables
        if cred_block["content"]:
            commands = extract_steps_commands(cred_block["content"])
            for i, cmd in enumerate(commands):
                step = {
                    "name": f"Run with credentials {i+1}",
                    "run": cmd,
                    "shell": "bash"
                }
                if env_vars:
                    step["env"] = env_vars
                env_steps.append(step)
    
    return env_steps


def generate_enhanced_composite_action(stage_name: str, stage_body: str, stage_env: Dict[str, str], 
                                     stage_agent: Dict[str, Any], post_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate enhanced composite action with comprehensive Jenkins feature support"""
    
    # Extract all Jenkins features
    tools = extract_tools(stage_body)
    git_steps = extract_git_steps(stage_body)
    sonar_steps = extract_sonarqube_steps(stage_body)
    docker_steps = extract_docker_steps(stage_body)
    kubectl_commands = extract_kubectl_steps(stage_body)
    input_steps = extract_input_steps(stage_body)
    credentials = extract_credentials_usage(stage_body)
    basic_commands = extract_steps_commands(stage_body)
    cred_blocks = extract_withCredentials_blocks(stage_body)
    script_blocks = extract_script_blocks(stage_body)
    plugin_steps = extract_plugin_steps(stage_body)
    
    action_def = {
        "name": f"{stage_name} Action",
        "description": f"Enhanced composite action for {stage_name} stage with comprehensive Jenkins feature support",
        "inputs": {},
        "runs": {
            "using": "composite",
            "steps": []
        }
    }
    
    # Add environment variables as inputs
    for env_key, env_val in stage_env.items():
        input_key = env_key.lower().replace('_', '-')
        action_def["inputs"][input_key] = {
            "description": f"Environment variable {env_key}",
            "required": False,
            "default": env_val
        }
    
    steps = []
    
    # Add tool setup steps
    tool_steps = generate_tool_setup_steps(tools)
    steps.extend(tool_steps)
    
    # Add git checkout steps (if any custom git operations)
    if git_steps:
        git_actions = convert_git_steps_to_actions(git_steps)
        steps.extend(git_actions)
    
    # Add credential-based steps
    if cred_blocks:
        cred_steps = convert_credentials_to_env_setup(cred_blocks)
        steps.extend(cred_steps)
    
    # Add SonarQube steps
    if sonar_steps:
        sonar_actions = convert_sonarqube_steps(sonar_steps)
        steps.extend(sonar_actions)
    
    # Add Docker steps
    if docker_steps:
        docker_actions = convert_docker_steps(docker_steps)
        steps.extend(docker_actions)
    
    # Add basic shell commands (filtered to avoid duplicates)
    filtered_commands = []
    for cmd in basic_commands:
        # Skip commands that are handled by specialized steps
        if not any([
            cmd.startswith("git ") and git_steps,
            "withSonarQubeEnv" in cmd and sonar_steps,
            cmd.startswith("docker build") and docker_steps,
            cmd.startswith("docker push") and docker_steps,
            "mvn sonar:sonar" in cmd and sonar_steps
        ]):
            filtered_commands.append(cmd)
    
    for i, cmd in enumerate(filtered_commands):
        step = {
            "name": f"Run command {i+1}",
            "run": cmd,
            "shell": "bash"
        }
        if stage_env:
            step["env"] = {k: f"${{{{ inputs.{k.lower().replace('_', '-')} }}}}" for k in stage_env.keys()}
        steps.append(step)
    
    # Add kubectl/helm commands
    for i, kubectl_cmd in enumerate(kubectl_commands):
        steps.append({
            "name": f"Run Kubernetes command {i+1}",
            "run": kubectl_cmd,
            "shell": "bash"
        })
    
    # Add manual conversion comments for complex features
    if script_blocks:
        for i, script_block in enumerate(script_blocks):
            if script_block["complexity"]["requires_manual_conversion"]:
                steps.append({
                    "name": f"Script block {i+1} (REQUIRES MANUAL CONVERSION)",
                    "run": generate_limitations_comment("Complex script block", script_block["content"][:200]),
                    "shell": "bash"
                })
    
    # Add manual conversion comments for plugin steps
    if plugin_steps:
        for plugin_step in plugin_steps:
            steps.append({
                "name": f"{plugin_step['plugin']} (REQUIRES MANUAL CONVERSION)",
                "run": generate_limitations_comment(plugin_step['plugin'], plugin_step['full_match'][:100]),
                "shell": "bash"
            })
    
    # Add post-action steps
    if post_info:
        post_steps = convert_post_actions_to_steps(post_info, stage_name)
        steps.extend(post_steps)
    
    action_def["runs"]["steps"] = steps
    return action_def


def save_enhanced_composite_actions(stages_info: List[Dict[str, Any]], output_dir: Path) -> List[Dict[str, Any]]:
    """Save enhanced composite actions and return comprehensive metadata"""
    actions_dir = output_dir / ".github" / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)
    
    action_paths = []
    
    for stage_info in stages_info:
        stage_name = stage_info["name"]
        stage_body = stage_info.get("body", "")
        action_name = sanitize_name(stage_name.lower())
        action_dir = actions_dir / action_name
        action_dir.mkdir(exist_ok=True)
        
        # Extract post information
        post_info = extract_stage_post(stage_body)
        
        # Generate the enhanced composite action
        action_def = generate_enhanced_composite_action(
            stage_name,
            stage_body,
            stage_info.get("env", {}),
            stage_info.get("agent", {}),
            post_info
        )
        
        # Save action definition
        action_file = action_dir / "action.yml"
        with action_file.open("w", encoding="utf-8") as f:
            yaml.dump(action_def, f, sort_keys=False, width=1000, default_flow_style=False)
        
        relative_path = f"./.github/actions/{action_name}"
        
        # Extract comprehensive metadata for job creation and reporting
        input_steps = extract_input_steps(stage_body)
        approval_env = convert_input_steps_to_environment(input_steps, stage_name)
        credentials = extract_credentials_usage(stage_body)
        plugin_steps = extract_plugin_steps(stage_body)
        script_blocks = extract_script_blocks(stage_body)
        
        # Analyze manual conversion requirements
        manual_conversion_needed = []
        if plugin_steps:
            manual_conversion_needed.extend([f"Jenkins plugin: {p['plugin']}" for p in plugin_steps])
        if any(s["complexity"]["requires_manual_conversion"] for s in script_blocks):
            manual_conversion_needed.append("Complex script blocks")
        if post_info and any("script_block" in actions for actions in post_info.values()):
            manual_conversion_needed.append("Post-action script blocks")
        
        action_metadata = {
            "name": stage_name,
            "path": relative_path,
            "env": stage_info.get("env", {}),
            "approval_environment": approval_env,
            "credentials": list(credentials),
            "has_docker": bool(extract_docker_steps(stage_body)),
            "has_kubectl": bool(extract_kubectl_steps(stage_body)),
            "has_sonarqube": bool(extract_sonarqube_steps(stage_body)),
            "has_post_actions": bool(post_info),
            "post_action_types": list(post_info.keys()) if post_info else [],
            "manual_conversion_needed": manual_conversion_needed,
            "complexity_score": calculate_complexity_score(stage_body),
            "plugin_dependencies": [p['plugin'] for p in plugin_steps]
        }
        
        action_paths.append(action_metadata)

    return action_paths


def calculate_complexity_score(stage_body: str) -> int:
    """Calculate complexity score for a stage"""
    score = 0
    
    # Basic features
    score += len(extract_steps_commands(stage_body))
    score += len(extract_credentials_usage(stage_body)) * 2
    score += len(extract_docker_steps(stage_body)) * 3
    score += len(extract_kubectl_steps(stage_body)) * 3
    score += len(extract_sonarqube_steps(stage_body)) * 4
    
    # Complex features
    script_blocks = extract_script_blocks(stage_body)
    score += sum(5 if s["complexity"]["requires_manual_conversion"] else 2 for s in script_blocks)
    
    plugin_steps = extract_plugin_steps(stage_body)
    score += len(plugin_steps) * 4
    
    post_info = extract_stage_post(stage_body)
    score += len(post_info) * 2
    
    return score
