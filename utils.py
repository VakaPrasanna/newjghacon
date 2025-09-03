
"""
Enhanced utility functions for Jenkins to GitHub Actions conversion
"""

import re
from typing import List, Dict, Any, Optional, Set


def strip_comments(text: str) -> str:
    """Remove /* */ and // comments from text"""
    # Remove /* */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove // comments but preserve URLs
    lines = text.split('\n')
    result_lines = []
    for line in lines:
        # Don't remove // if it's part of a URL
        if 'http://' in line or 'https://' in line:
            result_lines.append(line)
        else:
            # Remove // comments
            comment_pos = line.find('//')
            if comment_pos != -1:
                line = line[:comment_pos]
            result_lines.append(line)
    return '\n'.join(result_lines)


def find_block(text: str, pattern: str) -> tuple[int, int]:
    """Find { ... } block starting with pattern"""
    match = re.search(pattern + r'\s*\{', text)
    if not match:
        return -1, -1
    
    start = match.end() - 1  # Position of opening {
    depth = 0
    i = start
    
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return start + 1, i  # Content between { }
        i += 1
    
    return -1, -1


def multiline_to_commands(text: str) -> List[str]:
    """Convert multiline shell script to individual commands"""
    commands = []
    lines = text.strip().split('\n')
    current_command = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Handle line continuations
        if line.endswith('\\'):
            current_command += line[:-1] + " "
        else:
            current_command += line
            if current_command.strip():
                commands.append(current_command.strip())
            current_command = ""
    
    if current_command.strip():
        commands.append(current_command.strip())
    
    return commands


def sanitize_name(name: str) -> str:
    """Sanitize stage name for use as action/job name"""
    # Replace special characters with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '-', name)
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized.lower()


def gha_job_id(stage_name: str) -> str:
    """Convert stage name to valid GitHub Actions job ID"""
    return sanitize_name(stage_name)


def extract_unsupported_features(pipeline_text: str) -> List[Dict[str, str]]:
    """Detect unsupported Jenkins features that need manual conversion"""
    unsupported = []
    
    # Complex pipeline features
    patterns = {
        'Build triggers': r'triggers\s*\{[^}]+\}',
        'Options block': r'options\s*\{[^}]+\}',
        'Libraries': r'@Library\s*\([^)]+\)',
        'Shared libraries': r'library\s+[\'"][^\'"]+[\'"]',
        'Matrix builds': r'matrix\s*\{[^}]+\}',
        'When expressions (complex)': r'when\s*\{\s*expression\s*\{[^}]+\}\s*\}',
        'Pipeline functions': r'pipeline\s*\.\s*\w+\s*\(',
        'Build parameters in steps': r'build\s+job\s*:',
        'Parallel nested stages': r'parallel\s*\{[^}]*stage[^}]*stage[^}]*\}',
        'Custom functions': r'def\s+\w+\s*\([^)]*\)\s*\{',
        'Script blocks (complex)': r'script\s*\{[^}]{100,}\}',  # Large script blocks
        'Node allocation': r'node\s*\([^)]+\)\s*\{',
        'Milestone steps': r'milestone\s*\([^)]+\)',
        'Lock resources': r'lock\s*\([^)]+\)',
        'Timeout (complex)': r'timeout\s*\([^)]+\)\s*\{[^}]+\}',
        'Retry blocks': r'retry\s*\([^)]+\)\s*\{',
        'Archive on failure only': r'archiveArtifacts.*onlyIfSuccessful\s*:\s*false',
        'Custom workspace': r'ws\s*\([^)]+\)',
        'Jenkins CLI calls': r'jenkins\s+[\'"][^\'"]+[\'"]',
        'Plugin-specific steps': r'(publishHTML|publishTestResults|step\s*\[\s*\$class)',
    }
    
    for feature_name, pattern in patterns.items():
        matches = re.findall(pattern, pipeline_text, re.DOTALL | re.IGNORECASE)
        if matches:
            for match in matches:
                unsupported.append({
                    'feature': feature_name,
                    'code_snippet': match[:200] + '...' if len(match) > 200 else match,
                    'manual_action': get_manual_action_for_feature(feature_name)
                })
    
    return unsupported


def get_manual_action_for_feature(feature_name: str) -> str:
    """Get manual conversion instructions for unsupported features"""
    manual_actions = {
        'Build triggers': 'Configure GitHub webhook triggers or scheduled workflows manually',
        'Options block': 'Review Jenkins options and configure equivalent GitHub Actions settings',
        'Libraries': 'Replace with GitHub Actions marketplace actions or custom scripts',
        'Shared libraries': 'Convert shared library functions to reusable composite actions',
        'Matrix builds': 'Use GitHub Actions matrix strategy in workflow file',
        'When expressions (complex)': 'Simplify conditions or use GitHub Actions expressions',
        'Pipeline functions': 'Replace with GitHub Actions workflow commands or API calls',
        'Build parameters in steps': 'Use workflow_call or repository_dispatch events',
        'Parallel nested stages': 'Flatten parallel structure or use job dependencies',
        'Custom functions': 'Convert to shell scripts or composite actions',
        'Script blocks (complex)': 'Break down into smaller steps or external scripts',
        'Node allocation': 'Use GitHub Actions job concurrency controls',
        'Milestone steps': 'Use GitHub deployment environments and protection rules',
        'Lock resources': 'Use GitHub Actions concurrency groups',
        'Timeout (complex)': 'Use GitHub Actions timeout-minutes at job or step level',
        'Retry blocks': 'Use third-party retry actions or implement retry logic',
        'Archive on failure only': 'Use conditional artifact upload with if: failure()',
        'Custom workspace': 'Use GitHub Actions runner file system or custom actions',
        'Jenkins CLI calls': 'Replace with GitHub API calls or GitHub CLI commands',
        'Plugin-specific steps': 'Find equivalent GitHub Actions marketplace actions'
    }
    
    return manual_actions.get(feature_name, 'Manual review required - no direct equivalent')


def analyze_pipeline_complexity(pipeline_text: str) -> Dict[str, Any]:
    """Analyze pipeline complexity and provide conversion recommendations"""
    analysis = {
        'total_stages': len(re.findall(r'stage\s*\([^)]+\)', pipeline_text)),
        'has_parallel': bool(re.search(r'parallel\s*\{', pipeline_text)),
        'has_matrix': bool(re.search(r'matrix\s*\{', pipeline_text)),
        'has_conditional_stages': len(re.findall(r'when\s*\{', pipeline_text)),
        'has_post_actions': bool(re.search(r'post\s*\{', pipeline_text)),
        'script_blocks': len(re.findall(r'script\s*\{', pipeline_text)),
        'credential_usage': len(re.findall(r'credentials?\s*\(', pipeline_text)),
        'complexity_score': 0
    }
    
    # Calculate complexity score
    score = 0
    score += analysis['total_stages'] * 2
    score += 10 if analysis['has_parallel'] else 0
    score += 15 if analysis['has_matrix'] else 0
    score += analysis['has_conditional_stages'] * 3
    score += analysis['script_blocks'] * 5
    score += analysis['credential_usage'] * 2
    
    analysis['complexity_score'] = score
    analysis['complexity_level'] = (
        'Low' if score < 20 else
        'Medium' if score < 50 else
        'High' if score < 100 else
        'Very High'
    )
    
    return analysis


def validate_conversion_feasibility(pipeline_text: str) -> Dict[str, Any]:
    """Validate if pipeline can be fully converted and identify limitations"""
    feasibility = {
        'can_convert': True,
        'confidence': 'High',
        'warnings': [],
        'blockers': [],
        'manual_steps_required': []
    }
    
    # Check for absolute blockers
    blockers = [
        (r'@NonCPS', 'Non-CPS functions require complete rewrite'),
        (r'@Library.*vars/', 'Global variable libraries need manual conversion'),
        (r'properties\s*\([^)]*pipeline', 'Pipeline properties need workflow-level configuration'),
        (r'currentBuild\.\w+\s*=', 'Build property modifications not directly supported'),
    ]
    
    for pattern, message in blockers:
        if re.search(pattern, pipeline_text, re.IGNORECASE):
            feasibility['blockers'].append(message)
            feasibility['can_convert'] = False
    
    # Check for warning conditions
    warnings = [
        (r'build\s+job\s*:', 'Triggering other Jenkins jobs requires workflow redesign'),
        (r'milestone\s*\(', 'Milestone steps need GitHub deployment protection rules'),
        (r'input\s*\([^)]*parameters', 'Complex input parameters may need simplification'),
        (r'timeout\s*\([^)]*HOURS', 'Long timeouts may exceed GitHub Actions limits'),
        (r'publishHTML', 'HTML publishing requires GitHub Pages or artifact handling'),
    ]
    
    for pattern, message in warnings:
        if re.search(pattern, pipeline_text, re.IGNORECASE):
            feasibility['warnings'].append(message)
    
    # Adjust confidence based on findings
    if feasibility['blockers']:
        feasibility['confidence'] = 'Low'
    elif len(feasibility['warnings']) > 3:
        feasibility['confidence'] = 'Medium'
    elif len(feasibility['warnings']) > 1:
        feasibility['confidence'] = 'High'
    
    return feasibility


def extract_pipeline_metadata(pipeline_text: str) -> Dict[str, Any]:
    """Extract metadata about the pipeline for reporting"""
    metadata = {
        'pipeline_type': 'Declarative',
        'has_parameters': bool(re.search(r'parameters\s*\{', pipeline_text)),
        'has_global_env': bool(re.search(r'environment\s*\{', pipeline_text)),
        'has_global_agent': bool(re.search(r'agent\s+', pipeline_text)),
        'has_tools': bool(re.search(r'tools\s*\{', pipeline_text)),
        'has_options': bool(re.search(r'options\s*\{', pipeline_text)),
        'has_triggers': bool(re.search(r'triggers\s*\{', pipeline_text)),
        'has_libraries': bool(re.search(r'@Library', pipeline_text)),
        'total_post_blocks': len(re.findall(r'post\s*\{', pipeline_text)),
        'languages_detected': detect_languages(pipeline_text),
        'tools_detected': detect_tools(pipeline_text)
    }
    
    return metadata


def detect_languages(pipeline_text: str) -> List[str]:
    """Detect programming languages/technologies used in pipeline"""
    languages = set()
    
    patterns = {
        'Java': [r'mvn\s+', r'\.jar\b', r'pom\.xml', r'jdk\s+'],
        'Python': [r'pip\s+', r'python\s+', r'\.py\b', r'requirements\.txt'],
        'Node.js': [r'npm\s+', r'yarn\s+', r'package\.json', r'node\s+'],
        'Go': [r'go\s+build', r'go\s+test', r'go\.mod'],
        'Docker': [r'docker\s+', r'Dockerfile', r'docker-compose'],
        'Kubernetes': [r'kubectl\s+', r'helm\s+', r'kubeconfig'],
        'Terraform': [r'terraform\s+', r'\.tf\b'],
        'Ansible': [r'ansible\s+', r'playbook'],
        'Shell': [r'sh\s+[\'"]', r'bash\s+', r'#!/bin/'],
    }
    
    for lang, lang_patterns in patterns.items():
        if any(re.search(pattern, pipeline_text, re.IGNORECASE) for pattern in lang_patterns):
            languages.add(lang)
    
    return sorted(list(languages))


def detect_tools(pipeline_text: str) -> List[str]:
    """Detect tools and technologies used in pipeline"""
    tools = set()
    
    # Tool patterns
    tool_patterns = {
        'SonarQube': r'sonar:|withSonarQubeEnv',
        'Docker': r'docker\s+',
        'Kubernetes': r'kubectl|helm\s+',
        'Maven': r'mvn\s+',
        'Gradle': r'gradle\s+|gradlew',
        'npm': r'npm\s+',
        'yarn': r'yarn\s+',
        'pip': r'pip\s+',
        'Git': r'git\s+',
        'SSH': r'ssh\s+|sshagent',
        'AWS CLI': r'aws\s+',
        'Azure CLI': r'az\s+',
        'Google Cloud': r'gcloud\s+',
        'Terraform': r'terraform\s+',
        'Ansible': r'ansible',
        'Cosign': r'cosign\s+',
        'Trivy': r'trivy\s+',
        'OWASP': r'dependency-check',
    }
    
    for tool, pattern in tool_patterns.items():
        if re.search(pattern, pipeline_text, re.IGNORECASE):
            tools.add(tool)
    
    return sorted(list(tools))


def extract_all_credentials(pipeline_text: str) -> Set[str]:
    """Extract all credential references from pipeline"""
    credentials = set()
    
    # Various credential patterns
    patterns = [
        r'credentials\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        r'credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'usernamePassword\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'string\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'file\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'sshUserPrivateKey\s*\([^)]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
        r'withCredentials\s*\[[^\]]*credentialsId\s*:\s*[\'"]([^\'"]+)[\'"]',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, pipeline_text, re.IGNORECASE)
        credentials.update(matches)
    
    return credentials


def generate_limitations_comment(feature: str, details: str) -> str:
    """Generate a comment block for manual conversion requirements"""
    return f"""
# MANUAL CONVERSION REQUIRED: {feature}
# Original Jenkins feature: {details}
# Action needed: {get_manual_action_for_feature(feature)}
# TODO: Implement this functionality manually
"""


def get_manual_action_for_feature(feature_name: str) -> str:
    """Get detailed manual conversion instructions"""
    manual_actions = {
        'Build triggers': 'Configure repository webhooks or use scheduled workflows',
        'Options block': 'Set workflow-level timeouts, concurrency, and retention policies',
        'Libraries': 'Replace with marketplace actions or create custom composite actions',
        'Matrix builds': 'Use GitHub Actions strategy.matrix configuration',
        'Complex when expressions': 'Simplify to basic GitHub Actions if conditions',
        'Pipeline functions': 'Use GitHub Actions contexts and expressions',
        'Nested parallel stages': 'Flatten structure or use job dependencies with needs',
        'Custom functions': 'Create shell scripts or composite actions',
        'Script blocks (large)': 'Break into smaller steps or external scripts',
        'Milestone steps': 'Use deployment environments with protection rules',
        'Lock resources': 'Use concurrency groups at workflow or job level',
        'HTML publishing': 'Use GitHub Pages action or artifact uploads',
        'Jenkins-specific plugins': 'Find equivalent marketplace actions or implement custom logic'
    }
    
    return manual_actions.get(feature_name, 'Review Jenkins documentation and implement equivalent logic')


def create_conversion_metadata(pipeline_text: str, action_paths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create comprehensive metadata about the conversion"""
    return {
        'source_analysis': extract_pipeline_metadata(pipeline_text),
        'complexity_analysis': analyze_pipeline_complexity(pipeline_text),
        'feasibility_analysis': validate_conversion_feasibility(pipeline_text),
        'unsupported_features': extract_unsupported_features(pipeline_text),
        'all_credentials': list(extract_all_credentials(pipeline_text)),
        'generated_actions': len(action_paths),
        'total_jobs': len([a for a in action_paths if not a.get('is_parallel_child', False)])
    }