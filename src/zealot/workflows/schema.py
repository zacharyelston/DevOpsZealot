"""
Workflow configuration schema for DevOpsZealot Universal Architecture
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import yaml
import json
import re


@dataclass
class WorkflowMatch:
    """Criteria for matching workflows to tasks"""
    labels: List[str] = field(default_factory=list)
    repository_pattern: Optional[str] = None
    file_patterns: List[str] = field(default_factory=list)
    metadata_filters: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, task: Any) -> bool:
        """Check if task matches workflow criteria"""
        # Check labels
        if self.labels:
            task_labels = getattr(task, 'labels', [])
            if not any(label in task_labels for label in self.labels):
                return False
        
        # Check repository pattern
        if self.repository_pattern:
            if not re.match(self.repository_pattern, task.repository):
                return False
        
        # Check file patterns
        if self.file_patterns:
            task_files = getattr(task, 'files', [])
            if not any(
                any(re.match(pattern, file) for pattern in self.file_patterns)
                for file in task_files
            ):
                return False
        
        # Check metadata filters
        if self.metadata_filters:
            task_metadata = getattr(task, 'metadata', {})
            for key, value in self.metadata_filters.items():
                if task_metadata.get(key) != value:
                    return False
        
        return True


@dataclass
class HookCommand:
    """Command to execute as part of workflow"""
    name: str
    command: str
    timeout: int = 300
    continue_on_failure: bool = False
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowStage:
    """Stage in workflow execution"""
    name: str
    hooks: List[HookCommand] = field(default_factory=list)
    parallel: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStage':
        """Create stage from dictionary"""
        hooks = []
        for hook_data in data.get('hooks', []):
            if isinstance(hook_data, str):
                hooks.append(HookCommand(name=hook_data, command=hook_data))
            else:
                hooks.append(HookCommand(**hook_data))
        
        return cls(
            name=data['name'],
            hooks=hooks,
            parallel=data.get('parallel', False)
        )


@dataclass
class Workflow:
    """Complete workflow definition"""
    name: str
    description: Optional[str] = None
    match: Optional[WorkflowMatch] = None
    pre_edit: List[WorkflowStage] = field(default_factory=list)
    post_edit: List[WorkflowStage] = field(default_factory=list)
    validation: List[WorkflowStage] = field(default_factory=list)
    context_template: str = ""
    llm_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create workflow from dictionary"""
        match_data = data.get('match', {})
        match = WorkflowMatch(**match_data) if match_data else None
        
        pre_edit = [
            WorkflowStage.from_dict({'name': f'pre_{i}', 'hooks': [h]})
            if isinstance(h, (str, dict)) else WorkflowStage.from_dict(h)
            for i, h in enumerate(data.get('pre_edit', []))
        ]
        
        post_edit = [
            WorkflowStage.from_dict({'name': f'post_{i}', 'hooks': [h]})
            if isinstance(h, (str, dict)) else WorkflowStage.from_dict(h)
            for i, h in enumerate(data.get('post_edit', []))
        ]
        
        validation = [
            WorkflowStage.from_dict({'name': f'val_{i}', 'hooks': [h]})
            if isinstance(h, (str, dict)) else WorkflowStage.from_dict(h)
            for i, h in enumerate(data.get('validation', []))
        ]
        
        return cls(
            name=data['name'],
            description=data.get('description'),
            match=match,
            pre_edit=pre_edit,
            post_edit=post_edit,
            validation=validation,
            context_template=data.get('context_template', ''),
            llm_config=data.get('llm_config', {})
        )


class WorkflowLoader:
    """Load workflows from configuration files"""
    
    @staticmethod
    def load_from_file(filepath: str) -> List[Workflow]:
        """Load workflows from YAML or JSON file"""
        with open(filepath, 'r') as f:
            if filepath.endswith('.yaml') or filepath.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        workflows = []
        for workflow_data in data.get('workflows', []):
            workflows.append(Workflow.from_dict(workflow_data))
        
        return workflows
    
    @staticmethod
    def load_from_directory(directory: str) -> List[Workflow]:
        """Load all workflow files from directory"""
        import os
        workflows = []
        
        for filename in os.listdir(directory):
            if filename.endswith(('.yaml', '.yml', '.json')):
                filepath = os.path.join(directory, filename)
                workflows.extend(WorkflowLoader.load_from_file(filepath))
        
        return workflows


class WorkflowMatcher:
    """Match tasks to appropriate workflows"""
    
    def __init__(self, workflows: List[Workflow]):
        self.workflows = workflows
    
    def find_workflow(self, task: Any) -> Optional[Workflow]:
        """Find the best matching workflow for a task"""
        for workflow in self.workflows:
            if workflow.match and workflow.match.matches(task):
                return workflow
        
        # Return default workflow if exists
        for workflow in self.workflows:
            if workflow.name == 'default':
                return workflow
        
        return None
