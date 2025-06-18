import json
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

class ContainerManager:
    """Manages container lifecycle for Git repository modifications."""
    
    def __init__(self):
        self.containers = {}
        self.results_dir = Path("container_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def create_container_config(self, 
                              repo_url: str,
                              branch_name: str,
                              base_branch: str,
                              prompt: str,
                              context: str = "",
                              file_patterns: Optional[List[str]] = None,
                              auth_username: Optional[str] = None,
                              auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Create configuration for a container job."""
        
        job_id = str(uuid.uuid4())[:8]
        config = {
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "repo_url": repo_url,
            "branch_name": branch_name,
            "base_branch": base_branch,
            "prompt": prompt,
            "context": context,
            "file_patterns": file_patterns or ["*.py", "*.js", "*.ts", "*.java", "*.go"],
            "auth": {
                "username": auth_username,
                "token": auth_token
            } if auth_username and auth_token else None,
            "status": "configured",
            "container_id": None,
            "logs": [],
            "results": {}
        }
        
        self.containers[job_id] = config
        return config
    
    def launch_container(self, job_id: str) -> bool:
        """Launch a container for the specified job."""
        if job_id not in self.containers:
            raise ValueError(f"Job {job_id} not found")
        
        config = self.containers[job_id]
        
        try:
            # Create temporary directory for container communication
            temp_dir = tempfile.mkdtemp(prefix=f"git_job_{job_id}_")
            config_file = Path(temp_dir) / "job_config.json"
            
            # Write config to file for container
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Build Docker run command
            docker_cmd = [
                "docker", "run",
                "--rm",  # Remove container when done
                "-d",    # Run in background
                "-v", f"{temp_dir}:/workspace/job_data",
                "-e", f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY')}",
                "--name", f"git_modifier_{job_id}",
                "git-ai-modifier:latest",
                "/workspace/run_job.py"
            ]
            
            # Launch container
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                config["container_id"] = container_id
                config["status"] = "running"
                config["temp_dir"] = temp_dir
                self._log_message(job_id, f"Container {container_id} launched successfully")
                return True
            else:
                self._log_message(job_id, f"Failed to launch container: {result.stderr}")
                config["status"] = "failed"
                return False
                
        except Exception as e:
            self._log_message(job_id, f"Error launching container: {str(e)}")
            config["status"] = "failed"
            return False
    
    def check_container_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a running container."""
        if job_id not in self.containers:
            return {"error": "Job not found"}
        
        config = self.containers[job_id]
        container_id = config.get("container_id")
        
        if not container_id:
            return {"status": config["status"], "logs": config["logs"]}
        
        try:
            # Check if container is still running
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"id={container_id}"],
                capture_output=True, text=True
            )
            
            if result.stdout.strip():
                config["status"] = "running"
            else:
                # Container finished, get exit code
                result = subprocess.run(
                    ["docker", "ps", "-a", "-q", "-f", f"id={container_id}"],
                    capture_output=True, text=True
                )
                
                if result.stdout.strip():
                    # Get exit code
                    inspect_result = subprocess.run(
                        ["docker", "inspect", container_id, "--format={{.State.ExitCode}}"],
                        capture_output=True, text=True
                    )
                    
                    exit_code = int(inspect_result.stdout.strip())
                    config["status"] = "completed" if exit_code == 0 else "failed"
                    
                    # Load results if available
                    self._load_container_results(job_id)
                else:
                    config["status"] = "unknown"
            
            return {
                "status": config["status"],
                "logs": config["logs"],
                "results": config.get("results", {})
            }
            
        except Exception as e:
            self._log_message(job_id, f"Error checking container status: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def get_container_logs(self, job_id: str) -> List[str]:
        """Get logs from a container."""
        if job_id not in self.containers:
            return ["Job not found"]
        
        config = self.containers[job_id]
        container_id = config.get("container_id")
        
        if not container_id:
            return config["logs"]
        
        try:
            result = subprocess.run(
                ["docker", "logs", container_id],
                capture_output=True, text=True
            )
            
            logs = result.stdout.split('\n') if result.stdout else []
            if result.stderr:
                logs.extend(["--- STDERR ---"] + result.stderr.split('\n'))
            
            config["logs"] = logs
            return logs
            
        except Exception as e:
            error_msg = f"Error getting container logs: {str(e)}"
            config["logs"].append(error_msg)
            return config["logs"]
    
    def cleanup_container(self, job_id: str) -> bool:
        """Clean up container and temporary files."""
        if job_id not in self.containers:
            return False
        
        config = self.containers[job_id]
        container_id = config.get("container_id")
        
        try:
            # Stop and remove container if still running
            if container_id:
                subprocess.run(["docker", "stop", container_id], 
                             capture_output=True, text=True)
                subprocess.run(["docker", "rm", container_id], 
                             capture_output=True, text=True)
            
            # Clean up temporary directory
            temp_dir = config.get("temp_dir")
            if temp_dir and Path(temp_dir).exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Move to completed jobs
            config["status"] = "cleaned"
            return True
            
        except Exception as e:
            self._log_message(job_id, f"Error during cleanup: {str(e)}")
            return False
    
    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        """List all jobs and their status."""
        return {
            job_id: {
                "status": config["status"],
                "timestamp": config["timestamp"],
                "repo_url": config["repo_url"],
                "branch_name": config["branch_name"],
                "prompt": config["prompt"][:100] + "..." if len(config["prompt"]) > 100 else config["prompt"]
            }
            for job_id, config in self.containers.items()
        }
    
    def _log_message(self, job_id: str, message: str):
        """Add a log message to a job."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if job_id in self.containers:
            self.containers[job_id]["logs"].append(log_entry)
    
    def _load_container_results(self, job_id: str):
        """Load results from container execution."""
        config = self.containers[job_id]
        temp_dir = config.get("temp_dir")
        
        if not temp_dir:
            return
        
        results_file = Path(temp_dir) / "results.json"
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    results = json.load(f)
                config["results"] = results
                self._log_message(job_id, "Results loaded successfully")
            except Exception as e:
                self._log_message(job_id, f"Error loading results: {str(e)}")