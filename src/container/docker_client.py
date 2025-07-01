"""Docker container management for DevOpsZealot"""
import asyncio
import docker
import os
import tempfile
import shutil
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

class Container:
    """Represents a Docker container workspace"""
    
    def __init__(self, docker_container, task_id: str, workspace_path: str):
        self.container = docker_container
        self.task_id = task_id
        self.workspace_path = workspace_path
        self.id = docker_container.id[:12]
        self._start_time = datetime.utcnow()
        
    async def exec_command(self, command: str, workdir: str = "/workspace") -> Dict[str, Any]:
        """Execute command in container"""
        logger.debug("Executing command", container_id=self.id, command=command)
        
        exec_result = await asyncio.to_thread(
            self.container.exec_run,
            command,
            workdir=workdir,
            demux=True
        )
        
        stdout, stderr = exec_result.output
        
        result = {
            "exit_code": exec_result.exit_code,
            "stdout": stdout.decode('utf-8') if stdout else "",
            "stderr": stderr.decode('utf-8') if stderr else "",
            "command": command
        }
        
        if exec_result.exit_code != 0:
            logger.warning("Command failed", 
                         container_id=self.id, 
                         command=command,
                         exit_code=exec_result.exit_code,
                         stderr=result["stderr"])
        
        return result
    
    async def write_file(self, container_path: str, content: str) -> None:
        """Write file to container"""
        # Write to host workspace first
        host_path = os.path.join(self.workspace_path, container_path.lstrip('/workspace/'))
        os.makedirs(os.path.dirname(host_path), exist_ok=True)
        
        with open(host_path, 'w') as f:
            f.write(content)
            
        logger.debug("File written", container_id=self.id, path=container_path)
    
    async def read_file(self, container_path: str) -> str:
        """Read file from container"""
        host_path = os.path.join(self.workspace_path, container_path.lstrip('/workspace/'))
        
        with open(host_path, 'r') as f:
            return f.read()
    
    def is_running(self) -> bool:
        """Check if container is running"""
        self.container.reload()
        return self.container.status == 'running'
    
    async def cleanup(self) -> None:
        """Clean up container and workspace"""
        try:
            # Stop container
            await asyncio.to_thread(self.container.stop, timeout=10)
            await asyncio.to_thread(self.container.remove, force=True)
            logger.info("Container removed", container_id=self.id)
            
            # Clean up workspace
            if os.path.exists(self.workspace_path):
                shutil.rmtree(self.workspace_path)
                logger.info("Workspace cleaned", path=self.workspace_path)
                
        except Exception as e:
            logger.error("Cleanup failed", container_id=self.id, error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get container statistics"""
        stats = self.container.stats(stream=False)
        
        return {
            "cpu_usage": self._calculate_cpu_percent(stats),
            "memory_usage": stats['memory_stats'].get('usage', 0),
            "memory_limit": stats['memory_stats'].get('limit', 0),
            "runtime_seconds": (datetime.utcnow() - self._start_time).total_seconds()
        }
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage"""
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        
        if system_delta > 0 and cpu_delta > 0:
            return (cpu_delta / system_delta) * 100.0
        return 0.0


class ContainerManager:
    """Manages Docker containers for task execution"""
    
    def __init__(self, config):
        self.config = config
        self.client = docker.DockerClient(base_url=f"unix://{config.docker_socket}")
        self.base_image = "zealot/base:latest"
        self._containers: Dict[str, Container] = {}
        
        logger.info("ContainerManager initialized", base_image=self.base_image)
        
    async def create_workspace(self, task_id: str) -> Container:
        """Create isolated container workspace for task"""
        # Create temporary directory for workspace
        workspace_path = tempfile.mkdtemp(prefix=f"zealot-{task_id[:8]}-")
        logger.info("Creating workspace", task_id=task_id, path=workspace_path)
        
        try:
            # Create container
            container = await asyncio.to_thread(
                self.client.containers.run,
                self.base_image,
                detach=True,
                volumes={
                    workspace_path: {
                        "bind": "/workspace",
                        "mode": "rw"
                    }
                },
                environment={
                    "TASK_ID": task_id,
                    "ZEALOT_MODE": "autonomous"
                },
                working_dir="/workspace",
                network_mode="bridge",
                mem_limit=self.config.container_memory_limit,
                cpu_quota=self.config.container_cpu_quota,
                labels={
                    "zealot.task_id": task_id,
                    "zealot.created_at": datetime.utcnow().isoformat()
                },
                command="sleep infinity"  # Keep container running
            )
            
            # Wait for container to be ready
            await asyncio.sleep(1)
            
            # Create Container wrapper
            container_obj = Container(container, task_id, workspace_path)
            self._containers[task_id] = container_obj
            
            logger.info("Container created", 
                       task_id=task_id, 
                       container_id=container_obj.id)
            
            return container_obj
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)
            logger.error("Failed to create container", task_id=task_id, error=str(e))
            raise
    
    async def get_container(self, task_id: str) -> Optional[Container]:
        """Get container by task ID"""
        return self._containers.get(task_id)
    
    async def list_containers(self) -> Dict[str, Dict[str, Any]]:
        """List all managed containers"""
        containers = {}
        
        for task_id, container in self._containers.items():
            if container.is_running():
                containers[task_id] = {
                    "container_id": container.id,
                    "status": "running",
                    "stats": container.get_stats()
                }
        
        return containers
    
    async def cleanup_stale_containers(self, max_age_seconds: int = 3600) -> int:
        """Clean up containers older than max_age"""
        cleaned = 0
        current_time = datetime.utcnow()
        
        # Find Zealot containers
        filters = {"label": "zealot.task_id"}
        containers = await asyncio.to_thread(self.client.containers.list, 
                                           all=True, 
                                           filters=filters)
        
        for container in containers:
            created_at = container.labels.get("zealot.created_at")
            if created_at:
                created_time = datetime.fromisoformat(created_at)
                age = (current_time - created_time).total_seconds()
                
                if age > max_age_seconds:
                    task_id = container.labels.get("zealot.task_id")
                    logger.info("Cleaning stale container", 
                              container_id=container.id[:12],
                              task_id=task_id,
                              age_seconds=age)
                    
                    try:
                        await asyncio.to_thread(container.stop, timeout=10)
                        await asyncio.to_thread(container.remove, force=True)
                        cleaned += 1
                    except Exception as e:
                        logger.error("Failed to clean container", 
                                   container_id=container.id[:12],
                                   error=str(e))
        
        return cleaned
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Docker daemon health"""
        try:
            info = await asyncio.to_thread(self.client.info)
            
            return {
                "status": "healthy",
                "docker_version": info.get("ServerVersion"),
                "containers_running": info.get("ContainersRunning", 0),
                "images": info.get("Images", 0)
            }
        except Exception as e:
            logger.error("Docker health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def build_base_image(self, dockerfile_path: str) -> None:
        """Build the base Docker image"""
        logger.info("Building base image", path=dockerfile_path)
        
        try:
            image, build_logs = await asyncio.to_thread(
                self.client.images.build,
                path=os.path.dirname(dockerfile_path),
                dockerfile=os.path.basename(dockerfile_path),
                tag=self.base_image,
                rm=True,
                forcerm=True
            )
            
            for log in build_logs:
                if 'stream' in log:
                    logger.debug("Build output", message=log['stream'].strip())
                    
            logger.info("Base image built successfully", image=self.base_image)
            
        except Exception as e:
            logger.error("Failed to build base image", error=str(e))
            raise
