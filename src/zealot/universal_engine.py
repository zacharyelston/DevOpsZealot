"""
Universal Zealot Engine - A pure code editing engine
Handles: issue lookup, branch creation, LLM context management, and code editing
All specific behaviors are driven by external configuration
"""
import asyncio
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import structlog

from .workflows.schema import Workflow, WorkflowMatcher, WorkflowLoader
from .plugins.interface import PluginManager, PluginContext, PluginResult
from .adapters.base import (
    IssueAdapter,
    VCSAdapter, 
    LLMAdapter,
    ContainerAdapter
)
# TaskQueue is optional - only imported if redis_url is provided
TaskQueue = None
from .universal_config import UniversalConfig

logger = structlog.get_logger()


@dataclass
class UniversalTask:
    """Universal task representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    issue_id: Optional[str] = None
    issue_source: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    files: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    workflow_override: Optional[str] = None


@dataclass
class UniversalResult:
    """Result of universal task execution"""
    task_id: str
    success: bool
    changes: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: List[PluginResult] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    branch_name: Optional[str] = None
    commit_sha: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversalZealotEngine:
    """Universal orchestration engine for Zealot"""
    
    def __init__(self, config: UniversalConfig):
        self.config = config
        
        # Load adapters based on configuration
        self.issue_adapter = self._load_adapter('issue', config.issue_source)
        self.vcs_adapter = self._load_adapter('vcs', config.vcs)
        self.llm_adapter = self._load_adapter('llm', config.llm)
        self.container_adapter = self._load_adapter('container', config.container)
        
        # Load workflows and plugins
        self.workflows = WorkflowLoader.load_from_directory(config.workflows_dir)
        self.workflow_matcher = WorkflowMatcher(self.workflows)
        self.plugin_manager = PluginManager()
        
        # Task queue - only available if Redis is configured
        self.task_queue = None
        if config.redis_url:
            try:
                from .task_queue import TaskQueue
                self.task_queue = TaskQueue(config.redis_url)
            except ImportError:
                logger.warning("Redis not available, task queue disabled")
        
        self._running = False
        
        logger.info("UniversalZealotEngine initialized",
                   issue_source=config.issue_source.get('type'),
                   vcs_type=config.vcs.get('type'),
                   llm_provider=config.llm.get('provider'),
                   workflows_loaded=len(self.workflows))
    
    def _load_adapter(self, adapter_type: str, config: Dict[str, Any]) -> Any:
        """Dynamically load adapter based on configuration"""
        adapter_name = config.get('type', 'mock')
        
        # Special handling for different adapter types
        if adapter_type == 'issue':
            if adapter_name == 'redmine':
                from .adapters.issue import RedmineIssueAdapter
                return RedmineIssueAdapter(config)
            elif adapter_name == 'mock':
                from .adapters.mock import MockIssueAdapter
                return MockIssueAdapter(config)
        elif adapter_type == 'vcs':
            if adapter_name == 'git':
                from .adapters.vcs import GitVcsAdapter
                return GitVcsAdapter(config)
            elif adapter_name == 'mock':
                from .adapters.mock import MockVCSAdapter
                return MockVCSAdapter(config)
        elif adapter_type == 'llm':
            if adapter_name == 'mock':
                from .adapters.mock import MockLLMAdapter
                return MockLLMAdapter(config)
            # Add other LLM adapters here (openai, anthropic, etc.)
        elif adapter_type == 'container':
            if adapter_name == 'mock':
                from .adapters.mock import MockContainerAdapter
                return MockContainerAdapter(config)
            # Add other container adapters here (docker, kubernetes, etc.)
        
        # Default to mock adapter if not found
        logger.warning(f"Unknown adapter type '{adapter_name}' for {adapter_type}, using mock")
        from .adapters.mock import (
            MockIssueAdapter, MockVCSAdapter, 
            MockLLMAdapter, MockContainerAdapter
        )
        
        mock_classes = {
            'issue': MockIssueAdapter,
            'vcs': MockVCSAdapter,
            'llm': MockLLMAdapter,
            'container': MockContainerAdapter
        }
        
        return mock_classes[adapter_type](config)
    
    async def execute(self, task: UniversalTask) -> UniversalResult:
        """Execute a universal task"""
        start_time = datetime.utcnow()
        workspace = None
        
        logger.info("Executing universal task", task_id=task.id)
        
        try:
            # 1. Get issue data if provided
            issue_data = {}
            if task.issue_id and self.issue_adapter:
                issue_data = await self.issue_adapter.get_issue(task.issue_id)
                logger.info("Issue retrieved", task_id=task.id, issue_id=task.issue_id)
            
            # 2. Find matching workflow
            workflow = None
            if task.workflow_override:
                # Find workflow by name
                workflow = next((w for w in self.workflows if w.name == task.workflow_override), None)
            else:
                workflow = self.workflow_matcher.find_workflow(task)
            
            if not workflow:
                raise ValueError("No matching workflow found for task")
            
            logger.info("Workflow selected", task_id=task.id, workflow=workflow.name)
            
            # 3. Create workspace
            workspace = await self.container_adapter.create_workspace(task.id)
            
            # 4. Setup VCS
            if task.repository:
                await self.vcs_adapter.clone(workspace.path, task.repository, task.branch)
                branch_name = await self.vcs_adapter.create_branch(
                    workspace.path,
                    self._generate_branch_name(task, issue_data)
                )
            else:
                branch_name = None
            
            # 5. Create plugin context
            context = PluginContext(
                task_id=task.id,
                workspace_path=workspace.path,
                issue_data=issue_data,
                files=task.files,
                metadata=task.metadata,
                environment=self._build_environment(task, issue_data, workflow)
            )
            
            # 6. Execute pre-edit hooks
            pre_results = await self._execute_workflow_stage(workflow.pre_edit, context)
            if not all(r.success for r in pre_results):
                raise ValueError(f"Pre-edit hooks failed: {[r.error for r in pre_results if not r.success]}")
            
            # 7. Process files with LLM
            changes = []
            for file_path in task.files:
                change = await self._process_file_with_llm(
                    workspace.path,
                    file_path,
                    issue_data,
                    workflow,
                    context
                )
                changes.append(change)
            
            # 8. Execute post-edit hooks
            post_results = await self._execute_workflow_stage(workflow.post_edit, context)
            if not all(r.success for r in post_results):
                raise ValueError(f"Post-edit hooks failed: {[r.error for r in post_results if not r.success]}")
            
            # 9. Execute validation
            validation_results = await self._execute_workflow_stage(workflow.validation, context)
            
            # 10. Commit and push if validation passed
            commit_sha = None
            if all(r.success for r in validation_results) and branch_name:
                commit_message = self._generate_commit_message(task, issue_data, changes)
                commit_sha = await self.vcs_adapter.commit(workspace.path, commit_message)
                await self.vcs_adapter.push(workspace.path, branch_name)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return UniversalResult(
                task_id=task.id,
                success=True,
                changes=changes,
                validation_results=validation_results,
                duration_seconds=duration,
                branch_name=branch_name,
                commit_sha=commit_sha,
                metadata={
                    'workflow': workflow.name,
                    'issue_id': task.issue_id,
                    'pre_edit_results': len(pre_results),
                    'post_edit_results': len(post_results)
                }
            )
            
        except Exception as e:
            logger.error("Task execution failed",
                        task_id=task.id,
                        error=str(e),
                        exc_info=True)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return UniversalResult(
                task_id=task.id,
                success=False,
                error=str(e),
                duration_seconds=duration
            )
            
        finally:
            if workspace:
                await workspace.cleanup()
    
    async def _execute_workflow_stage(self, stages: List[Any], context: PluginContext) -> List[PluginResult]:
        """Execute a workflow stage with its hooks"""
        results = []
        
        for stage in stages:
            for hook in stage.hooks:
                # Create plugin for hook
                plugin_config = {
                    'command': hook.command,
                    'timeout': hook.timeout,
                    'environment': hook.environment
                }
                
                plugin = self.plugin_manager.create_plugin('command', plugin_config)
                
                # Execute based on stage name
                if 'pre' in stage.name:
                    result = await plugin.pre_edit(context)
                elif 'post' in stage.name:
                    result = await plugin.post_edit(context)
                else:
                    result = await plugin.validate(context)
                
                results.append(result)
                
                if not result.success and not hook.continue_on_failure:
                    break
        
        return results
    
    async def _process_file_with_llm(self, workspace_path: str, file_path: str, 
                                     issue_data: Dict[str, Any], workflow: Workflow,
                                     context: PluginContext) -> Dict[str, Any]:
        """Process a single file with LLM"""
        # Read current content
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                current_content = f.read()
        else:
            current_content = ""
        
        # Build context from template
        llm_context = workflow.context_template.format(
            issue_description=issue_data.get('description', ''),
            issue_title=issue_data.get('title', ''),
            current_content=current_content,
            file_path=file_path,
            **context.metadata
        )
        
        # Get LLM response
        llm_config = workflow.llm_config.copy()
        llm_config.update({
            'context': llm_context,
            'file_type': self._get_file_extension(file_path)
        })
        
        response = await self.llm_adapter.generate_edit(llm_config)
        
        # Write new content
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(response['content'])
        
        return {
            'file': file_path,
            'original': current_content,
            'modified': response['content'],
            'summary': response.get('summary', 'File modified'),
            'metadata': response.get('metadata', {})
        }
    
    def _generate_branch_name(self, task: UniversalTask, issue_data: Dict[str, Any]) -> str:
        """Generate branch name based on configuration"""
        pattern = self.config.vcs.get('branch_pattern', 'zealot/{task_id}')
        
        # Replace placeholders
        replacements = {
            '{task_id}': task.id[:8],
            '{issue_id}': str(task.issue_id or 'no-issue'),
            '{timestamp}': datetime.utcnow().strftime('%Y%m%d-%H%M%S'),
            '{slug}': self._slugify(issue_data.get('title', 'task'))
        }
        
        branch_name = pattern
        for key, value in replacements.items():
            branch_name = branch_name.replace(key, value)
        
        return branch_name
    
    def _generate_commit_message(self, task: UniversalTask, issue_data: Dict[str, Any], 
                                changes: List[Dict[str, Any]]) -> str:
        """Generate commit message"""
        files_changed = [c['file'] for c in changes]
        
        message_parts = []
        
        if issue_data.get('title'):
            message_parts.append(f"feat: {issue_data['title']}")
        else:
            message_parts.append(f"feat: Automated changes by Zealot")
        
        message_parts.append("")
        message_parts.append(f"Task ID: {task.id}")
        
        if task.issue_id:
            message_parts.append(f"Issue: {task.issue_id}")
        
        message_parts.append(f"Files changed: {len(files_changed)}")
        for file in files_changed[:5]:
            message_parts.append(f"  - {file}")
        
        if len(files_changed) > 5:
            message_parts.append(f"  ... and {len(files_changed) - 5} more")
        
        return "\n".join(message_parts)
    
    def _build_environment(self, task: UniversalTask, issue_data: Dict[str, Any], 
                          workflow: Workflow) -> Dict[str, str]:
        """Build environment variables for plugins"""
        env = os.environ.copy()
        
        # Add task-specific variables
        env.update({
            'ZEALOT_TASK_ID': task.id,
            'ZEALOT_WORKFLOW': workflow.name,
            'ZEALOT_ISSUE_ID': str(task.issue_id or ''),
            'ZEALOT_REPOSITORY': task.repository or '',
            'ZEALOT_BRANCH': task.branch or 'main'
        })
        
        # Add issue data as environment variables
        for key, value in issue_data.items():
            if isinstance(value, (str, int, float, bool)):
                env[f'ZEALOT_ISSUE_{key.upper()}'] = str(value)
        
        return env
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension"""
        return os.path.splitext(file_path)[1].lstrip('.')
    
    def _slugify(self, text: str) -> str:
        """Convert text to slug"""
        import re
        text = re.sub(r'[^\w\s-]', '', text.lower())
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]
