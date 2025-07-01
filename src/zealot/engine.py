"""
DevOpsZealot Core Engine
Orchestrates autonomous AI-powered infrastructure edits
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import structlog

from ..container.docker_client import ContainerManager
from ..ai.openai_client import OpenAIClient
from ..git.operations import GitManager
from ..validation.validator import ValidationPipeline
from .task_queue import TaskQueue
from .config import Config

logger = structlog.get_logger()

@dataclass
class Task:
    """Represents an infrastructure editing task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "infrastructure_edit"
    repository: str = ""
    branch: str = "main"
    files: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    success: bool
    changes: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    pr_url: Optional[str] = None
    commit_sha: Optional[str] = None

class ZealotEngine:
    """Main orchestration engine for DevOpsZealot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.container_manager = ContainerManager(config)
        self.ai_client = OpenAIClient(config.openai_api_key, config.ai_model)
        self.task_queue = TaskQueue(config.redis_url)
        self.validation_pipeline = ValidationPipeline(config)
        self._running = False
        
        logger.info("ZealotEngine initialized", 
                   ai_model=config.ai_model,
                   redis_url=config.redis_url)
        
    async def start(self):
        """Start the engine"""
        self._running = True
        logger.info("ZealotEngine starting")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._process_queue()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._metrics_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("ZealotEngine shutting down")
            
    async def stop(self):
        """Stop the engine gracefully"""
        logger.info("Stopping ZealotEngine")
        self._running = False
        await self.task_queue.close()
        
    async def submit_task(self, task: Task) -> str:
        """Submit a task for processing"""
        logger.info("Task submitted", task_id=task.id, type=task.type)
        await self.task_queue.enqueue(task)
        return task.id
        
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get the status of a task"""
        return await self.task_queue.get_result(task_id)
        
    async def process_task(self, task: Task) -> TaskResult:
        """Process a single task"""
        start_time = datetime.utcnow()
        container = None
        
        logger.info("Processing task", task_id=task.id, repository=task.repository)
        
        try:
            # 1. Create container workspace
            container = await self.container_manager.create_workspace(task.id)
            logger.info("Container created", task_id=task.id, container_id=container.id)
            
            # 2. Clone repository
            git_manager = GitManager(container.workspace_path)
            await asyncio.to_thread(git_manager.clone_repository, task.repository, task.branch)
            logger.info("Repository cloned", task_id=task.id)
            
            # 3. Create feature branch
            branch_name = f"zealot/{task.id[:8]}"
            await asyncio.to_thread(git_manager.create_feature_branch, branch_name)
            
            # 4. Process each file
            changes = []
            for file_path in task.files:
                logger.info("Processing file", task_id=task.id, file=file_path)
                change = await self._process_file(container, task, file_path, git_manager)
                changes.append(change)
            
            # 5. Validate changes
            validation_result = await self._validate_changes(container, task, changes)
            
            if not validation_result['passed']:
                raise ValueError(f"Validation failed: {validation_result['errors']}")
            
            # 6. Commit and push changes
            commit_message = self._generate_commit_message(task, changes)
            commit_sha = await asyncio.to_thread(
                git_manager.commit_changes, 
                commit_message
            )
            
            await asyncio.to_thread(git_manager.push_changes, branch_name)
            
            # 7. Create pull request
            pr_url = await self._create_pull_request(task, branch_name, commit_message)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = TaskResult(
                task_id=task.id,
                success=True,
                changes=changes,
                validation_results=validation_result,
                duration_seconds=duration,
                pr_url=pr_url,
                commit_sha=commit_sha
            )
            
            logger.info("Task completed successfully", 
                       task_id=task.id, 
                       duration=duration,
                       pr_url=pr_url)
            
            return result
            
        except Exception as e:
            logger.error("Task failed", 
                        task_id=task.id, 
                        error=str(e),
                        exc_info=True)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                duration_seconds=duration
            )
            
        finally:
            if container:
                await container.cleanup()
                logger.info("Container cleaned up", task_id=task.id)
    
    async def _process_queue(self):
        """Process tasks from the queue"""
        while self._running:
            try:
                task = await self.task_queue.dequeue()
                if task:
                    result = await self.process_task(task)
                    await self.task_queue.set_result(task.id, result)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error("Queue processing error", error=str(e), exc_info=True)
                await asyncio.sleep(5)
    
    async def _process_file(self, container, task: Task, file_path: str, git_manager: GitManager) -> Dict[str, Any]:
        """Process a single file"""
        # Read current content
        current_content = await asyncio.to_thread(git_manager.read_file, file_path)
        
        # Generate AI edit
        ai_response = await self.ai_client.generate_edit(
            current_content=current_content,
            requirements=task.requirements,
            file_type=self._get_file_type(file_path),
            context={
                "repository": task.repository,
                "file_path": file_path,
                "metadata": task.metadata
            }
        )
        
        # Apply changes
        await asyncio.to_thread(git_manager.write_file, file_path, ai_response['content'])
        
        return {
            "file": file_path,
            "original": current_content,
            "modified": ai_response['content'],
            "summary": ai_response.get('summary', 'Changes applied'),
            "tokens_used": ai_response.get('tokens_used', 0)
        }
    
    async def _validate_changes(self, container, task: Task, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate all changes"""
        validation_results = []
        
        for change in changes:
            file_type = self._get_file_type(change['file'])
            result = await self.validation_pipeline.validate(
                file_type=file_type,
                content=change['modified'],
                original=change['original'],
                container=container,
                rules=task.validation_rules
            )
            validation_results.append(result)
        
        return {
            "passed": all(r['passed'] for r in validation_results),
            "results": validation_results,
            "errors": [r['error'] for r in validation_results if not r['passed']]
        }
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path"""
        if file_path.endswith('.tf'):
            return 'terraform'
        elif file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith(('.yml', '.yaml')):
            return 'yaml'
        elif file_path.endswith('Dockerfile'):
            return 'dockerfile'
        else:
            return 'text'
    
    def _generate_commit_message(self, task: Task, changes: List[Dict[str, Any]]) -> str:
        """Generate commit message from changes"""
        requirements_summary = "; ".join(task.requirements[:3])
        if len(task.requirements) > 3:
            requirements_summary += f" (+{len(task.requirements) - 3} more)"
        
        files_changed = [c['file'] for c in changes]
        
        return f"AI: {requirements_summary}\n\n" \
               f"Task ID: {task.id}\n" \
               f"Files changed: {', '.join(files_changed)}\n\n" \
               f"This change was automatically generated by DevOpsZealot"
    
    async def _create_pull_request(self, task: Task, branch_name: str, commit_message: str) -> str:
        """Create a pull request (placeholder - implement with GitHub API)"""
        # TODO: Implement actual PR creation using GitHub API
        logger.info("Creating pull request", task_id=task.id, branch=branch_name)
        return f"https://github.com/example/repo/pull/123"
    
    async def _health_check_loop(self):
        """Periodic health checks"""
        while self._running:
            try:
                await self.container_manager.health_check()
                await self.task_queue.health_check()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error("Health check failed", error=str(e))
    
    async def _metrics_loop(self):
        """Collect and export metrics"""
        while self._running:
            try:
                # TODO: Implement metrics collection
                await asyncio.sleep(60)
            except Exception as e:
                logger.error("Metrics collection failed", error=str(e))
