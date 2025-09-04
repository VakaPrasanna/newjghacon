
"""
Enhanced Jenkins Declarative Pipeline -> GitHub Actions converter
Core conversion logic with proper secrets handling
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

from utils import (
    strip_comments, find_block, sanitize_name, gha_job_id,
    extract_unsupported_features, validate_conversion_feasibility,
    generate_limitations_comment
)
from jenkins_extractors import (
    extract_parameters, extract_global_agent, extract_env_kv,
    split_stages, extract_stage_when_branch, extract_stage_environment,
    extract_steps_commands, extract_stage_post, extract_pipeline_post,
    extract_parallel, extract_stage_agent, extract_when_conditions,
    extract_plugin_steps, extract_script_blocks
)
from action_generator import save_enhanced_composite_actions
from agent_mapper import map_label_to_runs_on


def convert_jenkins_to_gha(jenkins_text: str, output_dir: Path = Path(".")) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Enhanced conversion of Jenkins declarative pipeline to GitHub Actions workflow
    Returns tuple of (workflow_dict, action_paths_metadata)
    """
    text = strip_comments(jenkins_text)

    # Validate conversion feasibility first
    feasibility = validate_conversion_feasibility(jenkins_text)
    unsupported_features = extract_unsupported_features(jenkins_text)
    
    if not feasibility["can_convert"]:
        print("WARNING: Pipeline contains features that may prevent successful conversion:")
        for blocker in feasibility["blockers"]:
            print(f"  - {blocker}")
        print("Review the conversion report for detailed guidance.")

    # pipeline { ... }
    pstart, pend = find_block(text, r"\bpipeline\b")
    if pstart == -1:
        raise ValueError("Not a declarative Jenkins pipeline (no 'pipeline { ... }' found).")
    pipeline_body = text[pstart:pend]

    # Extract pipeline components with enhanced error handling
    try:
        global_agent = extract_global_agent(pipeline_body)
        parameters = extract_parameters(pipeline_body)
        
        # Global environment
        es, ee = find_block(pipeline_body, r"\benvironment\b")
        global_env = extract_env_kv(pipeline_body[es:ee]) if es != -1 else {}

        # Stages
        ss, se = find_block(pipeline_body, r"\bstages\b")
        if ss == -1:
            raise ValueError("No 'stages { ... }' found.")
        stages_list = split_stages(pipeline_body[ss:se])

        # Pipeline-level post
        pipeline_post = extract_pipeline_post(pipeline_body)

    except Exception as e:
        raise ValueError(f"Error parsing Jenkins pipeline structure: {e}")

    # Determine default runs-on and container from global agent
    default_runs_on: Any = "ubuntu-latest"
    default_container: Optional[Dict[str, Any]] = None
    if global_agent:
        if global_agent["type"] == "any":
            default_runs_on = "ubuntu-latest"
        elif global_agent["type"] == "label":
            default_runs_on = map_label_to_runs_on(global_agent["label"])
        elif global_agent["type"] == "docker":
            default_runs_on = "ubuntu-latest"
            default_container = {"image": global_agent["image"]}
            if "args" in global_agent:
                default_container["options"] = global_agent["args"]

    # Build workflow inputs from parameters
    workflow_inputs = {}
    workflow_env = dict(global_env)
    
    for param_name, param_info in parameters.items():
        if param_info["type"] == "string":
            workflow_inputs[param_name] = {
                "description": param_info["description"] or f"Parameter {param_name}",
                "required": False,
                "default": param_info["default"],
                "type": "string"
            }
        elif param_info["type"] == "boolean":
            workflow_inputs[param_name] = {
                "description": param_info["description"] or f"Parameter {param_name}",
                "required": False,
                "default": param_info["default"],
                "type": "boolean"
            }
        elif param_info["type"] == "choice":
            workflow_inputs[param_name] = {
                "description": param_info["description"] or f"Parameter {param_name}",
                "required": False,
                "default": param_info["default"],
                "type": "choice",
                "options": param_info["options"]
            }

    # Enhanced GHA structure with better triggers
    gha: Dict[str, Any] = {
        "name": "CI Pipeline",
        "on": {
            "push": {
                "branches": ["master", "main", "develop"]
            },
            "pull_request": {
                "branches": ["master", "main", "develop"]
            }
        }
    }
    
    # Add workflow_dispatch with inputs if parameters exist
    if workflow_inputs:
        gha["on"]["workflow_dispatch"] = {"inputs": workflow_inputs}
    
    # Add global environment
    if workflow_env:
        gha["env"] = workflow_env

    # Add permissions for enhanced functionality
    gha["permissions"] = {
        "contents": "read",
        "actions": "read",
        "security-events": "write",  # For SARIF uploads
        "deployments": "write",      # For environment deployments
        "checks": "write"            # For test results
    }

    gha["jobs"] = {}

    # Collect stage information for enhanced composite actions
    stages_info = []
    last_job_ids: List[str] = []
    prev_job_id: str = ""

    def compute_job_env(stage_env: Dict[str, str]) -> Dict[str, str]:
        """Return only keys that differ from workflow-level env or are new."""
        if not stage_env:
            return {}
        if not global_env:
            return stage_env
        out: Dict[str, str] = {}
        for k, v in stage_env.items():
            if k not in global_env or str(global_env[k]) != str(v):
                out[k] = v
        return out

    def apply_agent_to_job(job_def: Dict[str, Any], stage_agent: Dict[str, Any]):
        """Apply agent configuration to job definition with proper ordering"""
        if not stage_agent:
            job_def["runs-on"] = default_runs_on
            if default_container:
                job_def["container"] = dict(default_container)
            return
            
        if stage_agent["type"] == "any":
            job_def["runs-on"] = "ubuntu-latest"
        elif stage_agent["type"] == "label":
            job_def["runs-on"] = map_label_to_runs_on(stage_agent["label"])
        elif stage_agent["type"] == "docker":
            job_def["runs-on"] = "ubuntu-latest"
            job_def["container"] = {"image": stage_agent["image"]}
            if "args" in stage_agent:
                job_def["container"]["options"] = stage_agent["args"]

    def create_enhanced_job_steps(action_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create enhanced job steps with proper secrets passing"""
        steps = []
        
        # Add checkout only if the action doesn't handle git steps itself
        if not any("git" in str(cred).lower() for cred in action_info.get("credentials", [])):
            checkout_step = {"uses": "actions/checkout@v4"}
            
            # Add fetch-depth for better git history if needed
            if action_info.get("has_sonarqube") or "sonar" in action_info.get("name", "").lower():
                checkout_step["with"] = {"fetch-depth": 0}
            
            steps.append(checkout_step)
        
        # Add composite action step with proper secrets
        step = {
            "name": f"Run {action_info['name']}",
            "uses": action_info["path"]
        }
        
        # Create with block for secrets and inputs
        with_block = {}
        
        # Add required secrets from the action
        required_secrets = action_info.get("required_secrets", [])
        for secret_key in required_secrets:
            # Map secret keys to GitHub secrets
            github_secret_name = map_to_github_secret(secret_key)
            with_block[secret_key] = f"${{{{ secrets.{github_secret_name} }}}}"
        
        # Add environment variables as inputs
        stage_env = action_info.get("env", {})
        for env_key in stage_env.keys():
            input_key = env_key.lower().replace('_', '-')
            if input_key not in with_block:  # Don't override secrets
                with_block[input_key] = f"${{{{ env.{env_key} }}}}"
        
        # Add common inputs for Docker builds
        if action_info.get("has_docker"):
            if "image-name" not in with_block:
                with_block["image-name"] = "${{ github.repository }}"
            if "build-tag" not in with_block:
                with_block["build-tag"] = "${{ github.sha }}"
            if "registry" not in with_block:
                with_block["registry"] = "docker.io"
        
        if with_block:
            step["with"] = with_block
        
        # Add error handling for critical steps
        if action_info.get("has_docker") or action_info.get("has_kubectl"):
            step["timeout-minutes"] = 30
        
        steps.append(step)
        return steps

    def map_to_github_secret(secret_key: str) -> str:
        """Map action input secret keys to GitHub secret names"""
        # Convert kebab-case to UPPER_SNAKE_CASE
        return secret_key.upper().replace('-', '_')

    def create_when_condition(when_conditions: Dict[str, Any]) -> Optional[str]:
        """Convert Jenkins when conditions to GitHub Actions if conditions"""
        if not when_conditions:
            return None
        
        conditions = []
        
        if "branch" in when_conditions:
            branch = when_conditions["branch"]
            if branch in ["master", "main"]:
                conditions.append("github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'")
            else:
                conditions.append(f"github.ref == 'refs/heads/{branch}'")
        
        if "expression" in when_conditions:
            expr = when_conditions["expression"]
            # Simple parameter-based expressions
            if "params." in expr:
                param_expr = re.sub(r'params\.(\w+)', r'inputs.\1', expr)
                param_expr = re.sub(r'==\s*true', r'== true', param_expr)
                param_expr = re.sub(r'==\s*false', r'== false', param_expr)
                conditions.append(f"github.event_name == 'workflow_dispatch' && {param_expr}")
            else:
                # Mark complex expressions for manual conversion
                conditions.append(f"true  # MANUAL CONVERSION REQUIRED: {expr}")
        
        if "environment" in when_conditions:
            env_cond = when_conditions["environment"]
            env_name = env_cond["name"]
            env_value = env_cond["value"]
            if env_value:
                conditions.append(f"env.{env_name} == '{env_value}'")
            else:
                conditions.append(f"env.{env_name} != ''")
        
        if "changeRequest" in when_conditions:
            conditions.append("github.event_name == 'pull_request'")
        
        if "buildingTag" in when_conditions:
            conditions.append("startsWith(github.ref, 'refs/tags/')")
        
        return " && ".join(conditions) if conditions else None

    # Process stages with enhanced features and error handling
    for stage in stages_list:
        stage_name = stage["name"]
        stage_body = stage["content"]

        try:
            # Handle parallel stages
            parallel_substages = extract_parallel(stage_body)
            if parallel_substages:
                upstream = prev_job_id or (last_job_ids[-1] if last_job_ids else None)
                parallel_ids = []
                
                for sub in parallel_substages:
                    sub_name = sub["name"]
                    sub_body = sub["content"]
                    job_id = gha_job_id(sub_name)
                    parallel_ids.append(job_id)

                    stage_agent = extract_stage_agent(sub_body)
                    stage_env_raw = extract_stage_environment(sub_body)
                    job_env = compute_job_env(stage_env_raw)
                    when_conditions = extract_when_conditions(sub_body)
                    if_cond = create_when_condition(when_conditions)
                    post_info = extract_stage_post(sub_body)

                    # Check for unsupported features in this stage
                    plugin_steps = extract_plugin_steps(sub_body)
                    script_blocks = extract_script_blocks(sub_body)
                    
                    # Add to stages info for enhanced composite action generation
                    stages_info.append({
                        "name": sub_name,
                        "body": sub_body,
                        "env": stage_env_raw,
                        "agent": stage_agent,
                        "post": post_info,
                        "is_parallel_child": True,
                        "plugin_steps": plugin_steps,
                        "script_blocks": script_blocks
                    })

                    # Create job definition with proper ordering
                    job_def: Dict[str, Any] = {}
                    apply_agent_to_job(job_def, stage_agent)
                    
                    if job_env:
                        job_def["env"] = job_env
                    if if_cond:
                        job_def["if"] = if_cond
                    if upstream:
                        job_def["needs"] = upstream
                    
                    # Add timeout for long-running jobs
                    job_def["timeout-minutes"] = 60
                    
                    # Placeholder steps - will be updated after composite actions are created
                    job_def["steps"] = [{"uses": "actions/checkout@v4"}]
                    
                    gha["jobs"][job_id] = job_def

                last_job_ids = parallel_ids
                prev_job_id = ""
                continue

            # Handle sequential stages
            job_id = gha_job_id(stage_name)
            stage_agent = extract_stage_agent(stage_body)
            stage_env_raw = extract_stage_environment(stage_body)
            job_env = compute_job_env(stage_env_raw)
            when_conditions = extract_when_conditions(stage_body)
            if_cond = create_when_condition(when_conditions)
            post_info = extract_stage_post(stage_body)

            # Check for unsupported features in this stage
            plugin_steps = extract_plugin_steps(stage_body)
            script_blocks = extract_script_blocks(stage_body)

            # Add to stages info for enhanced composite action generation
            stages_info.append({
                "name": stage_name,
                "body": stage_body,
                "env": stage_env_raw,
                "agent": stage_agent,
                "post": post_info,
                "is_parallel_child": False,
                "plugin_steps": plugin_steps,
                "script_blocks": script_blocks
            })

            # Create job definition with proper ordering
            job_def: Dict[str, Any] = {}
            apply_agent_to_job(job_def, stage_agent)
            
            if job_env:
                job_def["env"] = job_env
            if if_cond:
                job_def["if"] = if_cond

            if last_job_ids:
                job_def["needs"] = last_job_ids
                last_job_ids = []
            elif prev_job_id:
                job_def["needs"] = prev_job_id

            # Add timeout for long-running jobs
            job_def["timeout-minutes"] = 60
            
            # Add concurrency control for deployment stages
            if any(keyword in stage_name.lower() for keyword in ["deploy", "release", "publish"]):
                job_def["concurrency"] = {
                    "group": f"deployment-{stage_name.lower().replace(' ', '-')}",
                    "cancel-in-progress": False
                }

            # Placeholder steps - will be updated after composite actions are created
            job_def["steps"] = [{"uses": "actions/checkout@v4"}]
            
            gha["jobs"][job_id] = job_def
            prev_job_id = job_id

        except Exception as e:
            print(f"WARNING: Error processing stage '{stage_name}': {e}")
            # Create a basic job that requires manual attention
            job_id = gha_job_id(stage_name)
            job_def = {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 30,
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Manual Conversion Required",
                        "run": generate_limitations_comment("Stage Processing Error", f"Error: {e}"),
                        "shell": "bash"
                    }
                ]
            }
            
            # Add job dependencies if needed
            if last_job_ids:
                job_def["needs"] = last_job_ids
                last_job_ids = []
            elif prev_job_id:
                job_def["needs"] = prev_job_id
            
            gha["jobs"][job_id] = job_def
            prev_job_id = job_id
            
            # Add minimal stage info
            stages_info.append({
                "name": stage_name,
                "body": stage_body,
                "env": {},
                "agent": {},
                "post": {},
                "conversion_error": str(e),
                "manual_conversion_needed": ["Complete stage conversion due to parsing error"]
            })

    # Generate enhanced composite actions with error handling
    try:
        action_paths = save_enhanced_composite_actions(stages_info, output_dir)
    except Exception as e:
        print(f"WARNING: Error generating composite actions: {e}")
        # Create fallback action paths
        action_paths = []
        for stage_info in stages_info:
            action_paths.append({
                "name": stage_info["name"],
                "path": f"./.github/actions/{sanitize_name(stage_info['name'].lower())}",
                "env": stage_info.get("env", {}),
                "required_secrets": [],
                "conversion_error": "Failed to generate composite action",
                "manual_conversion_needed": ["Complete stage conversion"]
            })

    # Update job steps to use enhanced composite actions with proper secrets
    job_keys = list(gha["jobs"].keys())
    for i, job_key in enumerate(job_keys):
        if i < len(action_paths):
            action_info = action_paths[i]
            
            try:
                # Update job with enhanced features
                job = gha["jobs"][job_key]
                
                # Add approval environment if needed
                if action_info.get("approval_environment"):
                    job["environment"] = action_info["approval_environment"]
                
                # Update steps to use enhanced composite action with secrets
                job["steps"] = create_enhanced_job_steps(action_info)
                
                # Add continue-on-error for non-critical jobs with manual conversion needs
                if action_info.get("manual_conversion_needed"):
                    # Only add continue-on-error for non-deployment stages
                    if not any(keyword in action_info.get("name", "").lower() 
                              for keyword in ["deploy", "release", "publish", "production"]):
                        job["continue-on-error"] = True

            except Exception as e:
                print(f"WARNING: Error updating job '{job_key}': {e}")
                # Keep basic checkout step and add error indication
                gha["jobs"][job_key]["steps"] = [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Job Update Error - Manual Attention Required",
                        "run": f"echo 'Error updating job: {e}' && echo 'This job requires manual conversion'",
                        "shell": "bash"
                    }
                ]

    # Pipeline-level post -> final job that depends on all others
    if pipeline_post:
        try:
            post_job_steps: List[Dict[str, Any]] = [{"uses": "actions/checkout@v4"}]
            
            for kind in ("always", "success", "failure", "cleanup"):
                if kind in pipeline_post:
                    pdata = pipeline_post[kind]
                    gha_condition = {
                        "always": "always()",
                        "success": "success()",
                        "failure": "failure()",
                        "cleanup": "always()"
                    }.get(kind, "always()")
                    
                    if "archive" in pdata:
                        post_job_steps.append({
                            "name": f"Upload artifacts ({kind})",
                            "if": gha_condition,
                            "uses": "actions/upload-artifact@v4",
                            "with": {
                                "name": f"pipeline-{kind}-artifacts",
                                "path": pdata["archive"]
                            }
                        })
                    
                    if "junit" in pdata:
                        junit_info = pdata["junit"]
                        post_job_steps.append({
                            "name": f"Publish test results ({kind})",
                            "if": gha_condition,
                            "uses": "dorny/test-reporter@v1",
                            "with": {
                                "name": f"Pipeline Test Results ({kind})",
                                "path": junit_info["testResults"],
                                "reporter": "java-junit"
                            },
                            "continue-on-error": junit_info.get("allowEmptyResults", False)
                        })
                    
                    if "commands" in pdata:
                        for cmd in pdata["commands"]:
                            post_job_steps.append({
                                "name": f"Pipeline post {kind}",
                                "if": gha_condition,
                                "run": cmd,
                                "shell": "bash"
                            })
                    
                    if "mail" in pdata:
                        mail_info = pdata["mail"]
                        post_job_steps.append({
                            "name": f"Send notification on {kind}",
                            "if": gha_condition,
                            "uses": "dawidd6/action-send-mail@v3",
                            "with": {
                                "server_address": "smtp.gmail.com",
                                "server_port": "587",
                                "username": "${{ secrets.EMAIL_USERNAME }}",
                                "password": "${{ secrets.EMAIL_PASSWORD }}",
                                "subject": mail_info.get("subject", f"Pipeline {kind}: ${{ github.workflow }}"),
                                "to": mail_info.get("to", ""),
                                "from": "${{ secrets.EMAIL_USERNAME }}",
                                "body": mail_info.get("body", f"Pipeline {kind} for ${{ github.repository }} - ${{ github.sha }}")
                            }
                        })
                    
                    if "slack" in pdata:
                        post_job_steps.append({
                            "name": f"Slack notification ({kind})",
                            "if": gha_condition,
                            "uses": "8398a7/action-slack@v3",
                            "with": {
                                "status": kind,
                                "channel": "${{ secrets.SLACK_CHANNEL }}",
                                "webhook_url": "${{ secrets.SLACK_WEBHOOK_URL }}"
                            }
                        })
                    
                    if "emailext" in pdata:
                        post_job_steps.append({
                            "name": f"Extended email notification ({kind}) - MANUAL CONVERSION REQUIRED",
                            "if": gha_condition,
                            "run": generate_limitations_comment("EmailExt Plugin", pdata["emailext"]),
                            "shell": "bash"
                        })
                    
                    if "publishHTML" in pdata:
                        post_job_steps.append({
                            "name": f"Publish HTML ({kind}) - MANUAL CONVERSION REQUIRED",
                            "if": gha_condition,
                            "run": generate_limitations_comment("PublishHTML Plugin", pdata["publishHTML"]),
                            "shell": "bash"
                        })
            
            if len(post_job_steps) > 1:
                all_jobs = [k for k in gha["jobs"].keys() if k != "pipeline-post"]
                post_job_def = {
                    "name": "Pipeline Post Actions",
                    "runs-on": default_runs_on,
                    "needs": all_jobs,
                    "if": "always()",
                    "timeout-minutes": 30,
                    "steps": post_job_steps
                }
                if default_container:
                    post_job_def["container"] = dict(default_container)
                gha["jobs"]["pipeline-post"] = post_job_def
                
        except Exception as e:
            print(f"WARNING: Error processing pipeline post actions: {e}")
            # Add basic post job with error indication
            all_jobs = [k for k in gha["jobs"].keys() if k != "pipeline-post"]
            if all_jobs:
                gha["jobs"]["pipeline-post"] = {
                    "name": "Pipeline Post Actions (Manual Conversion Required)",
                    "runs-on": "ubuntu-latest",
                    "needs": all_jobs,
                    "if": "always()",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {
                            "name": "Post Action Conversion Error",
                            "run": f"echo 'Error converting pipeline post actions: {e}'",
                            "shell": "bash"
                        }
                    ]
                }

    return gha, action_paths
