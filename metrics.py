import yaml
import json
import csv
from datetime import datetime, timedelta
import random
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class StepMetrics:
    step_name: str
    step_id: Optional[str]
    uses_action: Optional[str]
    run_command: Optional[str]
    commands: List[str]
    start_time: str
    end_time: str
    duration_seconds: int
    status: str
    exit_code: int
    output_lines: List[str]
    error_lines: List[str]
    shell: str
    with_parameters: Dict[str, Any]

@dataclass
class JobMetrics:
    job_name: str
    display_name: Optional[str]
    runs_on: str
    timeout_minutes: int
    needs: List[str]
    job_url: str
    start_time: str
    end_time: str
    duration_seconds: int
    duration_formatted: str
    status: str
    steps: List[StepMetrics]
    # Job-level aggregated metrics
    total_steps: int
    successful_steps: int
    failed_steps: int
    total_commands: int
    avg_step_duration: float
    resource_usage_cpu_percent: float
    resource_usage_memory_mb: float
    cost_estimate_usd: float

class WorkflowMetricsGenerator:
    def __init__(self, workflow_yaml_path: str = None, workflow_yaml_content: str = None):
        if workflow_yaml_content:
            self.workflow_data = yaml.safe_load(workflow_yaml_content)
        elif workflow_yaml_path:
            with open(workflow_yaml_path, 'r') as file:
                self.workflow_data = yaml.safe_load(file)
        else:
            raise ValueError("Either workflow_yaml_path or workflow_yaml_content must be provided")
        
        self.base_timestamp = datetime.now()
    
    def parse_jobs(self) -> Dict[str, Dict]:
        """Parse jobs from the workflow YAML"""
        jobs = self.workflow_data.get('jobs', {})
        parsed_jobs = {}
        
        for job_name, job_config in jobs.items():
            parsed_jobs[job_name] = {
                'name': job_name,
                'display_name': job_config.get('name', job_name),
                'runs_on': job_config.get('runs-on', 'ubuntu-latest'),
                'timeout_minutes': job_config.get('timeout-minutes', 30),
                'needs': self._normalize_needs(job_config.get('needs', [])),
                'steps': job_config.get('steps', []),
                'if': job_config.get('if', ''),
                'continue_on_error': job_config.get('continue-on-error', False),
                'concurrency': job_config.get('concurrency', {}),
                'environment': job_config.get('environment', '')
            }
        
        return parsed_jobs
    
    def _normalize_needs(self, needs) -> List[str]:
        """Normalize the needs field to always be a list"""
        if not needs:
            return []
        elif isinstance(needs, str):
            return [needs]
        elif isinstance(needs, list):
            return needs
        else:
            return []
    
    def _extract_commands_from_step(self, step: Dict) -> List[str]:
        """Extract commands from a step"""
        commands = []
        
        if 'run' in step:
            run_script = step['run'].strip()
            # Split multi-line scripts into individual commands
            lines = run_script.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
        elif 'uses' in step:
            commands.append(f"uses: {step['uses']}")
            if 'with' in step:
                for key, value in step['with'].items():
                    commands.append(f"  {key}: {value}")
        
        return commands
    
    def _generate_step_output(self, step_name: str, commands: List[str], status: str) -> tuple:
        """Generate realistic step output and error logs"""
        timestamp_base = self.base_timestamp + timedelta(seconds=random.randint(0, 300))
        output_lines = []
        error_lines = []
        
        # Add timestamp and shell info
        ts1 = timestamp_base.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        ts2 = (timestamp_base + timedelta(milliseconds=50)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        # Add command echo
        for cmd in commands:
            output_lines.append(f"{ts1} {cmd}")
        
        output_lines.append(f"{ts2} shell: /usr/bin/bash -e {{0}}")
        
        # Add command outputs based on step type
        if any('echo' in cmd for cmd in commands):
            for cmd in commands:
                if 'echo' in cmd:
                    # Extract echo content
                    match = re.search(r'echo\s+["\']?([^"\']+)["\']?', cmd)
                    if match:
                        output_lines.append(f"{ts2} {match.group(1)}")
        
        elif any('build' in cmd.lower() or 'mvn' in cmd.lower() for cmd in commands):
            output_lines.extend([
                f"{ts2} [INFO] Scanning for projects...",
                f"{ts2} [INFO] Building {step_name}",
                f"{ts2} [INFO] BUILD SUCCESS" if status == 'success' else f"{ts2} [ERROR] BUILD FAILED"
            ])
        
        elif any('test' in cmd.lower() for cmd in commands):
            output_lines.extend([
                f"{ts2} Running tests...",
                f"{ts2} Tests run: {random.randint(10, 50)}, Failures: {0 if status == 'success' else random.randint(1, 3)}, Errors: 0, Skipped: 0"
            ])
        
        elif any('docker' in cmd.lower() for cmd in commands):
            if 'push' in str(commands).lower():
                output_lines.extend([
                    f"{ts2} The push refers to repository [docker.io/prasannavaka81/githubactions1]",
                    f"{ts2} latest: digest: sha256:abc123... size: 1234" if status == 'success' else f"{ts2} Error pushing image"
                ])
            else:
                output_lines.extend([
                    f"{ts2} Successfully built abc123def456",
                    f"{ts2} Successfully tagged prasannavaka81/githubactions1:latest" if status == 'success' else f"{ts2} Error building image"
                ])
        
        elif any('deploy' in cmd.lower() or 'kubectl' in cmd.lower() for cmd in commands):
            output_lines.extend([
                f"{ts2} deployment.apps/complex-java-app {'created' if status == 'success' else 'failed'}",
                f"{ts2} service/complex-java-app {'unchanged' if status == 'success' else 'error'}"
            ])
        
        else:
            # Generic output
            output_lines.append(f"{ts2} Step completed")
        
        # Add errors for failed steps
        if status == 'failure':
            error_ts = (timestamp_base + timedelta(seconds=random.randint(5, 30))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            error_lines.append(f"{error_ts} ##[error]Process completed with exit code 1.")
        
        return output_lines, error_lines
    
    def _generate_step_metrics(self, step_config: Dict, step_index: int, job_start_time: datetime) -> StepMetrics:
        """Generate metrics for a single step"""
        
        # Extract step information
        step_name = step_config.get('name', f'Step {step_index + 1}')
        step_id = step_config.get('id', '')
        uses_action = step_config.get('uses', '')
        run_command = step_config.get('run', '')
        with_params = step_config.get('with', {})
        
        # Extract commands
        commands = self._extract_commands_from_step(step_config)
        
        # Generate timing
        step_start = job_start_time + timedelta(seconds=step_index * random.randint(10, 30))
        duration = random.randint(5, 120)  # 5 seconds to 2 minutes
        step_end = step_start + timedelta(seconds=duration)
        
        # Determine status (most steps succeed, some fail)
        status = 'success' if random.random() > 0.15 else 'failure'  # 85% success rate
        exit_code = 0 if status == 'success' else 1
        
        # Generate output
        output_lines, error_lines = self._generate_step_output(step_name, commands, status)
        
        return StepMetrics(
            step_name=step_name,
            step_id=step_id,
            uses_action=uses_action,
            run_command=run_command,
            commands=commands,
            start_time=step_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_time=step_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_seconds=duration,
            status=status,
            exit_code=exit_code,
            output_lines=output_lines,
            error_lines=error_lines,
            shell='/usr/bin/bash -e {0}' if run_command else '',
            with_parameters=with_params
        )
    
    def _generate_job_metrics(self, job_name: str, job_config: Dict) -> JobMetrics:
        """Generate comprehensive metrics for a job"""
        
        # Basic job info
        steps_config = job_config['steps']
        runs_on = job_config['runs_on']
        timeout_minutes = job_config['timeout_minutes']
        
        # Generate timing
        job_start = self.base_timestamp + timedelta(minutes=random.randint(0, 10))
        
        # Generate step metrics
        step_metrics = []
        for i, step_config in enumerate(steps_config):
            step_metric = self._generate_step_metrics(step_config, i, job_start)
            step_metrics.append(step_metric)
        
        # Calculate job-level metrics
        if step_metrics:
            job_end_time = max(datetime.strptime(step.end_time, "%Y-%m-%dT%H:%M:%SZ") for step in step_metrics)
            job_duration = int((job_end_time - job_start).total_seconds())
        else:
            job_duration = random.randint(30, 300)
            job_end_time = job_start + timedelta(seconds=job_duration)
        
        # Determine job status
        failed_steps = [s for s in step_metrics if s.status == 'failure']
        job_status = 'failure' if failed_steps else 'success'
        
        # Calculate aggregated metrics
        total_steps = len(step_metrics)
        successful_steps = len([s for s in step_metrics if s.status == 'success'])
        failed_steps_count = total_steps - successful_steps
        total_commands = sum(len(s.commands) for s in step_metrics)
        avg_step_duration = sum(s.duration_seconds for s in step_metrics) / total_steps if total_steps > 0 else 0
        
        # Resource usage (based on runner type and job characteristics)
        if 'ubuntu' in runs_on:
            cpu_usage = random.uniform(20, 80)
            memory_usage = random.uniform(512, 2048)
            cost_per_minute = 0.008
        else:
            cpu_usage = random.uniform(15, 70)
            memory_usage = random.uniform(1024, 4096)
            cost_per_minute = 0.016
        
        # Generate job URL
        job_url = f"http://gh.asml.com/repos/asml-gh/jc09-obi-actions-common/actions/runs/{random.randint(1000000, 9999999)}"
        
        return JobMetrics(
            job_name=job_name,
            display_name=job_config['display_name'],
            runs_on=runs_on,
            timeout_minutes=timeout_minutes,
            needs=job_config['needs'],
            job_url=job_url,
            start_time=job_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_time=job_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_seconds=job_duration,
            duration_formatted=f"{job_duration}s",
            status=job_status,
            steps=step_metrics,
            total_steps=total_steps,
            successful_steps=successful_steps,
            failed_steps=failed_steps_count,
            total_commands=total_commands,
            avg_step_duration=round(avg_step_duration, 2),
            resource_usage_cpu_percent=round(cpu_usage, 2),
            resource_usage_memory_mb=round(memory_usage, 2),
            cost_estimate_usd=round((job_duration / 60) * cost_per_minute, 4)
        )
    
    def generate_all_metrics(self) -> List[JobMetrics]:
        """Generate metrics for all jobs in the workflow"""
        jobs = self.parse_jobs()
        metrics = []
        
        for job_name, job_config in jobs.items():
            job_metrics = self._generate_job_metrics(job_name, job_config)
            metrics.append(job_metrics)
        
        return metrics
    
    def export_to_json(self, metrics: List[JobMetrics], filename: str = None, detailed: bool = True) -> str:
        """Export metrics to JSON format with structure similar to your reference"""
        if filename is None:
            filename = f"workflow_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if detailed:
            # Structure similar to your reference format
            export_data = {}
            
            for job_metric in metrics:
                job_data = {
                    "data": {
                        "Job URL": job_metric.job_url,
                        "Start Time": job_metric.start_time,
                        "End Time": job_metric.end_time,
                        "Duration": job_metric.duration_formatted,
                        "Status": job_metric.status,
                        "Runs On": job_metric.runs_on,
                        "Timeout Minutes": job_metric.timeout_minutes,
                        "Needs": job_metric.needs,
                        "Total Steps": job_metric.total_steps,
                        "Successful Steps": job_metric.successful_steps,
                        "Failed Steps": job_metric.failed_steps,
                        "Resource Usage": {
                            "CPU": f"{job_metric.resource_usage_cpu_percent}%",
                            "Memory": f"{job_metric.resource_usage_memory_mb} MB"
                        },
                        "Cost Estimate": f"${job_metric.cost_estimate_usd}"
                    },
                    "stderr": {
                        "file": f"logs/{job_metric.job_name}.txt",
                        "errors": []
                    },
                    "stdout": {}
                }
                
                # Add error logs from failed steps
                for step in job_metric.steps:
                    if step.error_lines:
                        job_data["stderr"]["errors"].extend(step.error_lines)
                
                # Add step details to stdout
                for step in job_metric.steps:
                    step_key = step.step_name.replace(' ', '_').lower()
                    job_data["stdout"][step_key] = {
                        "steps": [
                            {
                                "cmds": step.commands,
                                "uses": step.uses_action,
                                "with": step.with_parameters,
                                "duration": f"{step.duration_seconds}s",
                                "status": step.status,
                                "exit_code": step.exit_code
                            }
                        ],
                        "output": step.output_lines
                    }
                
                export_data[job_metric.job_name] = job_data
        else:
            # Simple format
            export_data = [asdict(metric) for metric in metrics]
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename
    
    def export_to_csv(self, metrics: List[JobMetrics], filename: str = None, include_steps: bool = True) -> str:
        """Export metrics to CSV format"""
        if filename is None:
            filename = f"workflow_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if include_steps:
            # Flatten the data to include step details
            flattened_data = []
            for job_metric in metrics:
                for step in job_metric.steps:
                    flattened_data.append({
                        'job_name': job_metric.job_name,
                        'job_status': job_metric.status,
                        'job_duration_seconds': job_metric.duration_seconds,
                        'job_start_time': job_metric.start_time,
                        'job_end_time': job_metric.end_time,
                        'job_url': job_metric.job_url,
                        'runs_on': job_metric.runs_on,
                        'step_name': step.step_name,
                        'step_status': step.status,
                        'step_duration_seconds': step.duration_seconds,
                        'step_start_time': step.start_time,
                        'step_end_time': step.end_time,
                        'step_exit_code': step.exit_code,
                        'uses_action': step.uses_action,
                        'commands_count': len(step.commands),
                        'output_lines_count': len(step.output_lines),
                        'error_lines_count': len(step.error_lines),
                        'cpu_usage_percent': job_metric.resource_usage_cpu_percent,
                        'memory_usage_mb': job_metric.resource_usage_memory_mb,
                        'cost_estimate_usd': job_metric.cost_estimate_usd
                    })
        else:
            # Job-level data only
            flattened_data = []
            for job_metric in metrics:
                job_dict = asdict(job_metric)
                job_dict.pop('steps', None)  # Remove nested steps data
                flattened_data.append(job_dict)
        
        if not flattened_data:
            return filename
        
        fieldnames = flattened_data[0].keys()
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_data)
        
        return filename
    
    def print_metrics_summary(self, metrics: List[JobMetrics]):
        """Print a detailed summary of job and step metrics"""
        print("=" * 100)
        print(f"GITHUB ACTIONS WORKFLOW METRICS - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        
        for job_metric in metrics:
            print(f"\n🔧 JOB: {job_metric.job_name.upper()}")
            if job_metric.display_name != job_metric.job_name:
                print(f"   Display Name: {job_metric.display_name}")
            print("-" * 80)
            
            # Job-level info
            print(f"  📊 Job Overview:")
            print(f"    • URL: {job_metric.job_url}")
            print(f"    • Status: {'✅' if job_metric.status == 'success' else '❌'} {job_metric.status.upper()}")
            print(f"    • Duration: {job_metric.duration_formatted} ({job_metric.start_time} - {job_metric.end_time})")
            print(f"    • Runner: {job_metric.runs_on}")
            print(f"    • Dependencies: {', '.join(job_metric.needs) if job_metric.needs else 'None'}")
            
            print(f"  📈 Step Summary:")
            print(f"    • Total Steps: {job_metric.total_steps}")
            print(f"    • Successful: {job_metric.successful_steps}")
            print(f"    • Failed: {job_metric.failed_steps}")
            print(f"    • Total Commands: {job_metric.total_commands}")
            print(f"    • Avg Step Duration: {job_metric.avg_step_duration}s")
            
            print(f"  💻 Resource Usage:")
            print(f"    • CPU: {job_metric.resource_usage_cpu_percent}%")
            print(f"    • Memory: {job_metric.resource_usage_memory_mb} MB")
            print(f"    • Estimated Cost: ${job_metric.cost_estimate_usd}")
            
            # Step details
            print(f"\n  🔍 Step Details:")
            for i, step in enumerate(job_metric.steps, 1):
                status_icon = "✅" if step.status == "success" else "❌"
                print(f"    {i}. {status_icon} {step.step_name}")
                print(f"       Duration: {step.duration_seconds}s | Exit Code: {step.exit_code}")
                if step.uses_action:
                    print(f"       Uses: {step.uses_action}")
                if step.commands:
                    print(f"       Commands: {len(step.commands)} cmd(s)")
                    for cmd in step.commands[:2]:  # Show first 2 commands
                        print(f"         - {cmd}")
                    if len(step.commands) > 2:
                        print(f"         ... and {len(step.commands) - 2} more")
                
                # Show some output lines
                if step.output_lines:
                    print(f"       Output: {len(step.output_lines)} lines")
                    for line in step.output_lines[:2]:  # Show first 2 output lines
                        print(f"         > {line}")
                    if len(step.output_lines) > 2:
                        print(f"         ... and {len(step.output_lines) - 2} more lines")
                
                # Show errors if any
                if step.error_lines:
                    print(f"       ❌ Errors: {len(step.error_lines)} error(s)")
                    for error in step.error_lines:
                        print(f"         > {error}")
                print()
        
        # Workflow summary
        total_jobs = len(metrics)
        successful_jobs = len([m for m in metrics if m.status == 'success'])
        failed_jobs = total_jobs - successful_jobs
        total_duration = sum(m.duration_seconds for m in metrics)
        total_cost = sum(m.cost_estimate_usd for m in metrics)
        total_steps = sum(m.total_steps for m in metrics)
        
        print("\n" + "=" * 100)
        print("WORKFLOW SUMMARY")
        print("=" * 100)
        print(f"  📊 Overall Stats:")
        print(f"    • Total Jobs: {total_jobs}")
        print(f"    • Successful Jobs: {successful_jobs}")
        print(f"    • Failed Jobs: {failed_jobs}")
        print(f"    • Success Rate: {(successful_jobs/total_jobs*100):.1f}%")
        print(f"    • Total Steps: {total_steps}")
        print(f"    • Total Duration: {total_duration}s ({total_duration//60}m {total_duration%60}s)")
        print(f"    • Estimated Total Cost: ${total_cost:.4f}")
        print("=" * 100)

# Usage functions
def quick_start(workflow_file_path: str):
    """Quick start function - just provide your workflow file path"""
    try:
        generator = WorkflowMetricsGenerator(workflow_yaml_path=workflow_file_path)
        metrics = generator.generate_all_metrics()
        
        # Print detailed summary
        generator.print_metrics_summary(metrics)
        
        # Export files
        json_file = generator.export_to_json(metrics, detailed=True)
        csv_file = generator.export_to_csv(metrics, include_steps=True)
        
        print(f"\n✅ Files generated:")
        print(f"   📄 Detailed JSON: {json_file}")
        print(f"   📊 Step-level CSV: {csv_file}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def quick_start_with_yaml(yaml_content: str):
    """Quick start with YAML content directly"""
    try:
        generator = WorkflowMetricsGenerator(workflow_yaml_content=yaml_content)
        metrics = generator.generate_all_metrics()
        
        generator.print_metrics_summary(metrics)
        
        json_file = generator.export_to_json(metrics, detailed=True)
        csv_file = generator.export_to_csv(metrics, include_steps=True)
        
        print(f"\n✅ Files generated:")
        print(f"   📄 Detailed JSON: {json_file}")
        print(f"   📊 Step-level CSV: {csv_file}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    # METHOD 1: Using file path (RECOMMENDED)
    print("🚀 Generating workflow metrics from file...")
    
    # UPDATE THIS PATH TO YOUR WORKFLOW FILE
    workflow_file_path = ".github/workflows/ci.yml"
    
    # Generate metrics from file
    metrics = quick_start(workflow_file_path)
    
    if metrics:
        print(f"\n🎉 Successfully generated metrics for {len(metrics)} jobs!")
    else:
        print("\n💡 If file not found, make sure the path is correct relative to where you run the script.")
        print("   Alternative paths to try:")
        print("   - './ci.yml' (if file is in same directory)")
        print("   - 'workflows/ci.yml' (if in workflows folder)")
        print("   - '../.github/workflows/ci.yml' (if script is in subfolder)")
    
    # print("🚀 Generating workflow metrics from YAML content...")
    # quick_start_with_yaml(yaml_content)
