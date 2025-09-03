
"""
Enhanced Jenkins pipeline parsing and feature extraction functions
"""

import re
from typing import List, Dict, Any, Set, Optional
from utils import find_block, multiline_to_commands, strip_comments


def extract_tools(stage_body: str) -> Dict[str, str]:
    """Extract tools block from stage"""
    tools = {}
    s, e = find_block(stage_body, r"\btools\b")
    if s == -1:
        return tools
    
    tools_body = stage_body[s:e]
    
    # Maven tools
    m = re.search(r"maven\s+['\"]([^'\"]+)['\"]", tools_body)
    if m:
        tools["maven"] = m.group(1)
    
    # JDK tools
    m = re.search(r"jdk\s+['\"]([^'\"]+)['\"]", tools_body)
    if m:
        tools["jdk"] = m.group(1)
    
    # Node.js tools
    m = re.search(r"nodejs\s+['\"]([^'\"]+)['\"]", tools_body)
    if m:
        tools["nodejs"] = m.group(1)
    
    # Git tools
    m = re.search(r"git\s+['\"]([^'\"]+)['\"]", tools_body)
    if m:
        tools["git"] = m.group(1)
        
    return tools


def extract_git_steps(stage_body: str) -> List[Dict[str, Any]]:
    """Extract git checkout steps with enhanced pattern matching"""
    git_steps = []
    
    # Enhanced git patterns
    patterns = [
        # git branch: "...", url: "...", credentialsId: "..."
        r"git\s+(?:branch\s*:\s*['\"]([^'\"]*)['\"](?:\s*,)?)?\s*(?:url\s*:\s*['\"]([^'\"]+)['\"](?:\s*,)?)?\s*(?:credentialsId\s*:\s*['\"]([^'\"]*)['\"])?",
        # checkout scm
        r"checkout\s+scm",
        # git commands in sh blocks
        r"git\s+clone\s+([^\s]+)(?:\s+([^\s]+))?"
    ]
    
    for pattern in patterns:
        for m in re.finditer(pattern, stage_body):
            if "checkout scm" in m.group(0):
                git_steps.append({
                    "type": "scm",
                    "branch": "",
                    "url": "",
                    "credentialsId": ""
                })
            elif "git clone" in m.group(0):
                url = m.group(1) if m.group(1) else ""
                branch = m.group(2) if len(m.groups()) > 1 and m.group(2) else ""
                git_steps.append({
                    "type": "clone",
                    "branch": branch,
                    "url": url,
                    "credentialsId": ""
                })
            else:
                branch = m.group(1) or ""
                url = m.group(2) or ""
                credentials_id = m.group(3) or ""
                
                if url or branch:  # Only add if we have meaningful git info
                    git_steps.append({
                        "type": "standard",
                        "branch": branch,
                        "url": url,
                        "credentialsId": credentials_id
                    })
    
    return git_steps


def extract_sonarqube_steps(stage_body: str) -> List[Dict[str, Any]]:
    """Extract SonarQube steps with enhanced parsing"""
    sonar_steps = []
    
    # withSonarQubeEnv pattern
    pattern = r"withSonarQubeEnv\s*\(\s*(?:['\"]([^'\"]*)['\"]|([^)]+))?\s*\)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
    
    for m in re.finditer(pattern, stage_body, re.DOTALL):
        server_name = m.group(1) or m.group(2) or ""
        inner_commands = m.group(3) or ""
        
        # Extract commands from within the block
        commands = []
        
        # Multi-line sh commands
        for cmd_match in re.finditer(r"sh\s+['\"]([^'\"]+)['\"]", inner_commands):
            commands.append(cmd_match.group(1))
        
        # Triple-quoted sh commands
        for cmd_match in re.finditer(r"sh\s+([\"']{3})([\s\S]*?)\1", inner_commands):
            commands.extend(multiline_to_commands(cmd_match.group(2)))
        
        if commands or server_name:
            sonar_steps.append({
                "serverName": server_name.strip("'\"") if server_name else "",
                "commands": commands
            })
    
    # Also check for direct sonar commands outside withSonarQubeEnv
    direct_sonar_commands = []
    for m in re.finditer(r"sh\s+['\"]([^'\"]*sonar[^'\"]*)['\"]", stage_body):
        direct_sonar_commands.append(m.group(1))
    
    if direct_sonar_commands:
        sonar_steps.append({
            "serverName": "",
            "commands": direct_sonar_commands
        })
    
    return sonar_steps


def extract_input_steps(stage_body: str) -> List[Dict[str, Any]]:
    """Extract input approval steps with enhanced parameter parsing"""
    input_steps = []
    
    # Enhanced input pattern
    pattern = r"input\s*\(\s*(?:message\s*:\s*['\"]([^'\"]+)['\"])?(?:\s*,\s*ok\s*:\s*['\"]([^'\"]*)['\"])?(?:\s*,\s*parameters\s*:\s*\[([^\]]*)\])?\s*\)"
    
    for m in re.finditer(pattern, stage_body, re.DOTALL):
        message = m.group(1) or "Approval required"
        ok_button = m.group(2) or "Proceed"
        parameters_str = m.group(3) or ""
        
        # Parse parameters if present
        parameters = []
        if parameters_str:
            param_patterns = [
                r"string\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"]",
                r"choice\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"]",
                r"booleanParam\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"]"
            ]
            for pattern in param_patterns:
                for param_match in re.finditer(pattern, parameters_str):
                    parameters.append(param_match.group(1))
        
        input_steps.append({
            "message": message,
            "ok": ok_button,
            "parameters": parameters
        })
    
    return input_steps


def extract_credentials_usage(stage_body: str) -> Set[str]:
    """Extract credential IDs used in the stage with comprehensive patterns"""
    credentials = set()
    
    # All possible credential patterns
    patterns = [
        r'credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'credentials\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        r'usernamePassword\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'string\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'file\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'sshUserPrivateKey\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'withCredentials\s*\[[^\]]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'sshagent\s*\(\s*\[[\'"]([^\'"]+)[\'"]\]\s*\)',
        r'dockerCredentials\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, stage_body, re.IGNORECASE)
        credentials.update(matches)
    
    # Extract from environment variable assignments
    env_patterns = [
        r'=\s*credentials\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        r'KUBECONFIG[^=]*=\s*credentials\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ]
    
    for pattern in env_patterns:
        matches = re.findall(pattern, stage_body, re.IGNORECASE)
        credentials.update(matches)
    
    return credentials


def extract_docker_steps(stage_body: str) -> List[Dict[str, Any]]:
    """Extract Docker-related steps with enhanced parsing"""
    docker_steps = []
    
    # Docker build patterns
    build_patterns = [
        r"docker\s+build\s+(?:--pull\s+)?(?:--progress=\w+\s+)?(?:-f\s+([^\s]+)\s+)?(?:-t\s+([^\s]+)\s+)?([^\s]*)",
        r"docker\s+build\s+[^|]*-t\s+([^\s]+)",
    ]
    
    for pattern in build_patterns:
        for m in re.finditer(pattern, stage_body):
            groups = m.groups()
            dockerfile = ""
            tag = ""
            context = "."
            
            if len(groups) >= 3:
                dockerfile = groups[0] or ""
                tag = groups[1] or ""
                context = groups[2] or "."
            elif len(groups) >= 1:
                tag = groups[0] or ""
            
            if tag:
                docker_steps.append({
                    "type": "build",
                    "tag": tag,
                    "context": context,
                    "dockerfile": dockerfile
                })
    
    # Docker push patterns
    push_patterns = [
        r"docker\s+push\s+([^\s]+)",
        r"docker\s+image\s+push\s+([^\s]+)"
    ]
    
    for pattern in push_patterns:
        for m in re.finditer(pattern, stage_body):
            tag = m.group(1).strip()
            docker_steps.append({
                "type": "push",
                "tag": tag
            })
    
    # Docker login patterns
    if re.search(r"docker\s+login", stage_body):
        docker_steps.append({
            "type": "login"
        })
    
    return docker_steps


def extract_kubectl_steps(stage_body: str) -> List[str]:
    """Extract kubectl commands with enhanced parsing"""
    kubectl_commands = []
    
    # Direct kubectl commands
    for m in re.finditer(r"kubectl\s+([^\n\"']+)", stage_body):
        kubectl_commands.append(f"kubectl {m.group(1).strip()}")
    
    # kubectl in multiline sh blocks
    for m in re.finditer(r"sh\s+([\"']{3})([\s\S]*?)\1", stage_body):
        commands = multiline_to_commands(m.group(2))
        for cmd in commands:
            if cmd.strip().startswith('kubectl'):
                kubectl_commands.append(cmd.strip())
    
    # helm commands (related to k8s)
    for m in re.finditer(r"helm\s+([^\n\"']+)", stage_body):
        kubectl_commands.append(f"helm {m.group(1).strip()}")
    
    return kubectl_commands


def extract_parameters(pipeline_body: str) -> Dict[str, Any]:
    """Extract pipeline parameters with enhanced support"""
    params = {}
    s, e = find_block(pipeline_body, r"\bparameters\b")
    if s == -1:
        return params
    
    param_body = pipeline_body[s:e]
    
    # string parameters
    for m in re.finditer(r"string\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"](?:,\s*defaultValue\s*:\s*['\"]([^'\"]*)['\"])?(?:,\s*description\s*:\s*['\"]([^'\"]*)['\"])?", param_body):
        name = m.group(1)
        default = m.group(2) or ""
        description = m.group(3) or ""
        params[name] = {
            "type": "string",
            "default": default,
            "description": description
        }
    
    # boolean parameters
    for m in re.finditer(r"booleanParam\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"](?:,\s*defaultValue\s*:\s*(true|false))?(?:,\s*description\s*:\s*['\"]([^'\"]*)['\"])?", param_body):
        name = m.group(1)
        default = m.group(2) or "false"
        description = m.group(3) or ""
        params[name] = {
            "type": "boolean",
            "default": default.lower() == "true",
            "description": description
        }
    
    # choice parameters
    for m in re.finditer(r"choice\s*\(\s*name\s*:\s*['\"]([^'\"]+)['\"](?:,\s*choices\s*:\s*\[([^\]]+)\])?(?:,\s*description\s*:\s*['\"]([^'\"]*)['\"])?", param_body):
        name = m.group(1)
        choices_str = m.group(2) or ""
        description = m.group(3) or ""
        choices = [c.strip().strip('\'"') for c in choices_str.split(',') if c.strip()]
        params[name] = {
            "type": "choice",
            "options": choices,
            "default": choices[0] if choices else "",
            "description": description
        }
    
    return params


def extract_global_agent(pipeline_body: str) -> Dict[str, Any]:
    """Enhanced agent extraction with better parsing"""
    s, e = find_block(pipeline_body, r"\bagent\b")
    if s == -1:
        return {}
    agent_body = pipeline_body[s:e]
    
    # agent any
    if re.search(r"\bany\b", agent_body):
        return {"type": "any"}
    
    # agent { node { label '...' } }
    ns, ne = find_block(agent_body, r"\bnode\b")
    if ns != -1:
        node_body = agent_body[ns:ne]
        m = re.search(r"label\s+['\"]([^'\"]+)['\"]", node_body)
        if m:
            return {"type": "label", "label": m.group(1).strip()}
    
    # agent { label '...' }
    m = re.search(r"label\s+['\"]([^'\"]+)['\"]", agent_body)
    if m:
        return {"type": "label", "label": m.group(1).strip()}
    
    # agent { docker { ... } }
    ds, de = find_block(agent_body, r"\bdocker\b")
    if ds != -1:
        docker_body = agent_body[ds:de]
        img = re.search(r"image\s+['\"]([^'\"]+)['\"]", docker_body)
        args = re.search(r"args\s+['\"]([^'\"]+)['\"]", docker_body)
        reuse_node = re.search(r"reuseNode\s+(true|false)", docker_body)
        
        if img:
            out = {"type": "docker", "image": img.group(1).strip()}
            if args:
                out["args"] = args.group(1).strip()
            if reuse_node:
                out["reuseNode"] = reuse_node.group(1) == "true"
            return out
    
    return {}


def extract_stage_agent(stage_body: str) -> Dict[str, Any]:
    """Enhanced stage agent extraction"""
    s, e = find_block(stage_body, r"\bagent\b")
    if s == -1:
        return {}
    body = stage_body[s:e]
    
    if re.search(r"\bany\b", body):
        return {"type": "any"}
    
    # Handle node { label } syntax
    ns, ne = find_block(body, r"\bnode\b")
    if ns != -1:
        node_body = body[ns:ne]
        m = re.search(r"label\s+['\"]([^'\"]+)['\"]", node_body)
        if m:
            return {"type": "label", "label": m.group(1).strip()}
    
    m = re.search(r"label\s+['\"]([^'\"]+)['\"]", body)
    if m:
        return {"type": "label", "label": m.group(1).strip()}
    
    ds, de = find_block(body, r"\bdocker\b")
    if ds != -1:
        dbody = body[ds:de]
        img = re.search(r"image\s+['\"]([^'\"]+)['\"]", dbody)
        args = re.search(r"args\s+['\"]([^'\"]+)['\"]", dbody)
        reuse_node = re.search(r"reuseNode\s+(true|false)", dbody)
        
        if img:
            out = {"type": "docker", "image": img.group(1).strip()}
            if args:
                out["args"] = args.group(1).strip()
            if reuse_node:
                out["reuseNode"] = reuse_node.group(1) == "true"
            return out
    
    return {}


def extract_env_kv(env_body: str) -> Dict[str, str]:
    """Extract environment key-value pairs from environment block"""
    env: Dict[str, str] = {}
    for line in env_body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
            env[key] = val
    return env


def split_stages(stages_body: str) -> List[Dict[str, Any]]:
    """Split stages block into individual stages with enhanced parsing"""
    res = []
    i = 0
    while True:
        m = re.search(r"stage\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\{", stages_body[i:])
        if not m:
            break
        name = m.group(1)
        abs_start = i + m.start()
        block_start = abs_start + m.end() - m.start() - 1
        depth = 0
        j = block_start + 1
        content_start = j
        while j < len(stages_body):
            if stages_body[j] == '{':
                depth += 1
            elif stages_body[j] == '}':
                if depth == 0:
                    res.append({"name": name, "content": stages_body[content_start:j]})
                    i = j + 1
                    break
                depth -= 1
            j += 1
        else:
            break
    return res


def extract_stage_when_branch(stage_body: str) -> str:
    """Extract branch condition from when block"""
    s, e = find_block(stage_body, r"\bwhen\b")
    if s == -1:
        return ""
    when_body = stage_body[s:e]
    m = re.search(r"branch\s+['\"]([^'\"]+)['\"]", when_body)
    return m.group(1) if m else ""


def extract_stage_when_expression(stage_body: str) -> Optional[str]:
    """Extract expression condition from when block"""
    s, e = find_block(stage_body, r"\bwhen\b")
    if s == -1:
        return None
    when_body = stage_body[s:e]
    
    # Look for expression { ... }
    expr_match = re.search(r"expression\s*\{\s*return\s+([^}]+)\s*\}", when_body)
    if expr_match:
        return expr_match.group(1).strip()
    
    # Look for other when conditions
    if re.search(r"anyOf\s*\{", when_body):
        return "complex_anyOf_condition"
    if re.search(r"allOf\s*\{", when_body):
        return "complex_allOf_condition"
    
    return None


def extract_stage_environment(stage_body: str) -> Dict[str, str]:
    """Extract environment variables from stage"""
    s, e = find_block(stage_body, r"\benvironment\b")
    if s == -1:
        return {}
    return extract_env_kv(stage_body[s:e])


def extract_steps_commands(stage_body: str) -> List[str]:
    """Extract shell commands from steps block with enhanced parsing"""
    cmds: List[str] = []
    s, e = find_block(stage_body, r"\bsteps\b")
    search_zone = stage_body[s:e] if s != -1 else stage_body
    zone = strip_comments(search_zone)

    # Triple-quoted strings
    for m in re.finditer(r"sh\s+([\"']{3})([\s\S]*?)\1", zone):
        inner = m.group(2)
        cmds.extend(multiline_to_commands(inner))
    
    # Single/double quoted strings
    for m in re.finditer(r"sh\s+['\"]([^'\"]+)['\"]", zone):
        cmds.append(m.group(1).strip())
    
    # Echo commands
    for m in re.finditer(r"\becho\s+['\"]([^'\"]+)['\"]", zone):
        cmds.append(f"echo {m.group(1).strip()}")
    
    # Script blocks with returnStdout
    for m in re.finditer(r"sh\s*\(\s*script\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*returnStdout\s*:\s*true)?\s*\)", zone):
        cmds.append(m.group(1).strip())

    return cmds


def _extract_post_body(body: str) -> Dict[str, Any]:
    """Extract post block content with enhanced parsing for stage and pipeline level"""
    out: Dict[str, Any] = {}
    ps, pe = find_block(body, r"\bpost\b")
    if ps == -1:
        return out
    post_body = body[ps:pe]

    def _collect(kind: str) -> Dict[str, Any]:
        ks, ke = find_block(post_body, rf"\b{kind}\b")
        if ks == -1:
            return {}
        kbody = post_body[ks:ke]
        data: Dict[str, Any] = {}
        
        # archiveArtifacts with various options
        archive_patterns = [
            r"archiveArtifacts\s*\(\s*artifacts\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*onlyIfSuccessful\s*:\s*(true|false))?(?:\s*,\s*allowEmptyArchive\s*:\s*(true|false))?\s*\)",
            r"archiveArtifacts\s+['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in archive_patterns:
            m = re.search(pattern, kbody)
            if m:
                data["archive"] = m.group(1).strip()
                if len(m.groups()) > 1 and m.group(2):
                    data["onlyIfSuccessful"] = m.group(2).lower() == "true"
                if len(m.groups()) > 2 and m.group(3):
                    data["allowEmptyArchive"] = m.group(3).lower() == "true"
                break
        
        # junit test results
        junit_patterns = [
            r"junit\s*\(\s*(?:allowEmptyResults\s*:\s*(true|false)\s*,\s*)?testResults\s*:\s*['\"]([^'\"]+)['\"]",
            r"junit\s+['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in junit_patterns:
            m = re.search(pattern, kbody)
            if m:
                if len(m.groups()) > 1:
                    data["junit"] = {
                        "allowEmptyResults": m.group(1).lower() == "true" if m.group(1) else False,
                        "testResults": m.group(2)
                    }
                else:
                    data["junit"] = {
                        "allowEmptyResults": False,
                        "testResults": m.group(1)
                    }
                break
        
        # publishCoverage
        coverage_match = re.search(r"publishCoverage\s+adapters\s*:\s*\[([^\]]+)\]", kbody)
        if coverage_match:
            adapters = coverage_match.group(1)
            if "jacocoAdapter" in adapters:
                jacoco_match = re.search(r"jacocoAdapter\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", adapters)
                if jacoco_match:
                    data["coverage"] = {
                        "type": "jacoco",
                        "path": jacoco_match.group(1)
                    }
        
        # publishHTML
        html_match = re.search(r"publishHTML\s*\([^)]+\)", kbody)
        if html_match:
            data["publishHTML"] = html_match.group(0)
        
        # mail notifications
        mail_patterns = [
            r"mail\s+to\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*subject\s*:\s*['\"]([^'\"]*)['\"])?(?:\s*,\s*body\s*:\s*['\"]([^'\"]*)['\"])?",
            r"emailext\s*\([^)]+\)"
        ]
        
        for pattern in mail_patterns:
            m = re.search(pattern, kbody)
            if m:
                if "emailext" in pattern:
                    data["emailext"] = m.group(0)
                else:
                    data["mail"] = {
                        "to": m.group(1),
                        "subject": m.group(2) if len(m.groups()) > 1 and m.group(2) else "",
                        "body": m.group(3) if len(m.groups()) > 2 and m.group(3) else ""
                    }
                break
        
        # slack notifications
        slack_match = re.search(r"slackSend\s*\([^)]+\)", kbody)
        if slack_match:
            data["slack"] = slack_match.group(0)
        
        # deleteDir
        if re.search(r"deleteDir\s*\(\s*\)", kbody):
            data["deleteDir"] = True
        
        # cleanWs
        if re.search(r"cleanWs\s*\(\s*\)", kbody):
            data["cleanWs"] = True
        
        # capture shell/echo commands inside post
        cmds = []
        for mm in re.finditer(r"sh\s+['\"]([^'\"]+)['\"]", kbody):
            cmds.append(mm.group(1).strip())
        for mm in re.finditer(r"sh\s+([\"']{3})([\s\S]*?)\1", kbody):
            cmds.extend(multiline_to_commands(mm.group(2)))
        for mm in re.finditer(r"\becho\s+['\"]([^'\"]+)['\"]", kbody):
            cmds.append(f"echo {mm.group(1).strip()}")
        if cmds:
            data["commands"] = cmds
        
        # script blocks in post
        script_match = re.search(r"script\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", kbody, re.DOTALL)
        if script_match:
            script_content = script_match.group(1).strip()
            if script_content:
                data["script_block"] = script_content
        
        return data

    for kind in ("always", "success", "failure", "cleanup", "unstable", "aborted"):
        kdata = _collect(kind)
        if kdata:
            out[kind] = kdata
    
    return out


def extract_stage_post(stage_body: str) -> Dict[str, Any]:
    """Extract post block from stage"""
    return _extract_post_body(stage_body)


def extract_pipeline_post(pipeline_body: str) -> Dict[str, Any]:
    """Extract post block from pipeline"""
    return _extract_post_body(pipeline_body)


def extract_parallel(stage_body: str) -> List[Dict[str, Any]]:
    """Extract parallel stages from stage body"""
    ps, pe = find_block(stage_body, r"\bparallel\b")
    if ps == -1:
        return []
    par_body = stage_body[ps:pe]
    return split_stages(par_body)


def extract_withCredentials_blocks(stage_body: str) -> List[Dict[str, Any]]:
    """Extract withCredentials blocks with their contents"""
    cred_blocks = []
    
    # Find withCredentials blocks
    pattern = r"withCredentials\s*\[\s*([^\]]+)\s*\]\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
    
    for m in re.finditer(pattern, stage_body, re.DOTALL):
        credentials_def = m.group(1)
        block_content = m.group(2)
        
        # Parse credential definitions
        cred_types = []
        
        # file credential
        file_matches = re.finditer(r"file\s*\(\s*credentialsId\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*variable\s*:\s*['\"]([^'\"]+)['\"])?\s*\)", credentials_def)
        for fm in file_matches:
            cred_types.append({
                "type": "file",
                "credentialsId": fm.group(1),
                "variable": fm.group(2) if fm.group(2) else fm.group(1).upper()
            })
        
        # usernamePassword credential
        userpass_matches = re.finditer(r"usernamePassword\s*\(\s*credentialsId\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*usernameVariable\s*:\s*['\"]([^'\"]+)['\"])?(?:\s*,\s*passwordVariable\s*:\s*['\"]([^'\"]+)['\"])?\s*\)", credentials_def)
        for um in userpass_matches:
            cred_id = um.group(1)
            username_var = um.group(2) if um.group(2) else f"{cred_id.upper()}_USR"
            password_var = um.group(3) if um.group(3) else f"{cred_id.upper()}_PSW"
            cred_types.append({
                "type": "usernamePassword",
                "credentialsId": cred_id,
                "usernameVariable": username_var,
                "passwordVariable": password_var
            })
        
        # string/token credential
        string_matches = re.finditer(r"string\s*\(\s*credentialsId\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*variable\s*:\s*['\"]([^'\"]+)['\"])?\s*\)", credentials_def)
        for sm in string_matches:
            cred_types.append({
                "type": "string",
                "credentialsId": sm.group(1),
                "variable": sm.group(2) if sm.group(2) else sm.group(1).upper()
            })
        
        if cred_types:
            cred_blocks.append({
                "credentials": cred_types,
                "content": block_content.strip()
            })
    
    return cred_blocks


def extract_script_blocks(stage_body: str) -> List[Dict[str, Any]]:
    """Extract script blocks and their complexity"""
    script_blocks = []
    
    pattern = r"script\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
    
    for m in re.finditer(pattern, stage_body, re.DOTALL):
        script_content = m.group(1).strip()
        
        # Analyze script complexity
        complexity = {
            "has_groovy_specific": bool(re.search(r"\.each\s*\{|\.collect\s*\{|\.findAll\s*\{", script_content)),
            "has_jenkins_api": bool(re.search(r"currentBuild\.|env\.|params\.", script_content)),
            "has_conditionals": bool(re.search(r"if\s*\(|switch\s*\(", script_content)),
            "has_loops": bool(re.search(r"for\s*\(|while\s*\(", script_content)),
            "line_count": len(script_content.split('\n')),
            "requires_manual_conversion": False
        }
        
        # Mark as requiring manual conversion if complex
        if (complexity["has_groovy_specific"] or 
            complexity["line_count"] > 10 or 
            complexity["has_jenkins_api"]):
            complexity["requires_manual_conversion"] = True
        
        script_blocks.append({
            "content": script_content,
            "complexity": complexity
        })
    
    return script_blocks


def extract_plugin_steps(stage_body: str) -> List[Dict[str, Any]]:
    """Extract Jenkins plugin-specific steps that need special handling"""
    plugin_steps = []
    
    # Common Jenkins plugins and their patterns
    plugin_patterns = {
        "publishHTML": r"publishHTML\s*\([^)]+\)",
        "publishTestResults": r"publishTestResults\s*\([^)]+\)",
        "step": r"step\s*\[\s*\$class\s*:\s*['\"]([^'\"]+)['\"]",
        "build": r"build\s+job\s*:\s*['\"]([^'\"]+)['\"]",
        "emailext": r"emailext\s*\([^)]+\)",
        "slackSend": r"slackSend\s*\([^)]+\)",
        "milestone": r"milestone\s*\([^)]+\)",
        "timeout": r"timeout\s*\([^)]+\)\s*\{",
        "retry": r"retry\s*\([^)]+\)\s*\{",
        "lock": r"lock\s*\([^)]+\)\s*\{",
        "ws": r"ws\s*\([^)]+\)\s*\{",
        "node": r"node\s*\([^)]+\)\s*\{",
        "waitForQualityGate": r"waitForQualityGate\s*\(\s*\)",
        "readProperties": r"readProperties\s+file\s*:\s*['\"]([^'\"]+)['\"]"
    }
    
    for plugin_name, pattern in plugin_patterns.items():
        matches = re.finditer(pattern, stage_body, re.DOTALL)
        for match in matches:
            step_info = {
                "plugin": plugin_name,
                "full_match": match.group(0),
                "requires_manual_conversion": True
            }
            
            # Extract specific information based on plugin type
            if plugin_name == "build":
                step_info["job_name"] = match.group(1) if match.groups() else ""
            elif plugin_name == "step":
                step_info["class_name"] = match.group(1) if match.groups() else ""
            elif plugin_name == "readProperties":
                step_info["file_path"] = match.group(1) if match.groups() else ""
            
            plugin_steps.append(step_info)
    
    return plugin_steps


def extract_when_conditions(stage_body: str) -> Dict[str, Any]:
    """Extract all when conditions with enhanced parsing"""
    conditions = {}
    s, e = find_block(stage_body, r"\bwhen\b")
    if s == -1:
        return conditions
    
    when_body = stage_body[s:e]
    
    # Branch condition
    branch_match = re.search(r"branch\s+['\"]([^'\"]+)['\"]", when_body)
    if branch_match:
        conditions["branch"] = branch_match.group(1)
    
    # Expression condition
    expr_match = re.search(r"expression\s*\{\s*return\s+([^}]+)\s*\}", when_body)
    if expr_match:
        conditions["expression"] = expr_match.group(1).strip()
    
    # Environment condition
    env_match = re.search(r"environment\s+name\s*:\s*['\"]([^'\"]+)['\"](?:\s*,\s*value\s*:\s*['\"]([^'\"]+)['\"])?", when_body)
    if env_match:
        conditions["environment"] = {
            "name": env_match.group(1),
            "value": env_match.group(2) if env_match.group(2) else ""
        }
    
    # anyOf condition
    if re.search(r"anyOf\s*\{", when_body):
        conditions["anyOf"] = True
        conditions["complex"] = True
    
    # allOf condition
    if re.search(r"allOf\s*\{", when_body):
        conditions["allOf"] = True
        conditions["complex"] = True
    
    # changeRequest condition
    if re.search(r"changeRequest", when_body):
        conditions["changeRequest"] = True
    
    # buildingTag condition
    if re.search(r"buildingTag", when_body):
        conditions["buildingTag"] = True
    
    return conditions