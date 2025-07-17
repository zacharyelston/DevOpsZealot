"""
Base adapter interfaces for universal Zealot architecture
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class Workspace:
    """Represents a workspace for code editing"""
    id: str
    path: str
    metadata: Dict[str, Any] = None
    
    async def cleanup(self):
        """Cleanup workspace resources"""
        pass


class IssueAdapter(ABC):
    """Interface for issue tracking systems"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Get issue details by ID"""
        pass
    
    @abstractmethod
    async def update_issue(self, issue_id: str, updates: Dict[str, Any]) -> bool:
        """Update issue with new information"""
        pass
    
    @abstractmethod
    async def list_issues(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List issues based on filters"""
        pass


class VCSAdapter(ABC):
    """Interface for version control systems"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def clone(self, workspace_path: str, repository: str, branch: str = None) -> None:
        """Clone repository to workspace"""
        pass
    
    @abstractmethod
    async def create_branch(self, workspace_path: str, branch_name: str) -> str:
        """Create new branch"""
        pass
    
    @abstractmethod
    async def commit(self, workspace_path: str, message: str) -> str:
        """Commit changes"""
        pass
    
    @abstractmethod
    async def push(self, workspace_path: str, branch: str) -> None:
        """Push changes to remote"""
        pass
    
    @abstractmethod
    async def get_current_branch(self, workspace_path: str) -> str:
        """Get current branch name"""
        pass


class LLMAdapter(ABC):
    """Interface for language models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def generate_edit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code edit based on context"""
        pass
    
    @abstractmethod
    async def generate_text(self, prompt: str, options: Dict[str, Any] = None) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def analyze_code(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze code for various purposes"""
        pass


class ContainerAdapter(ABC):
    """Interface for container/workspace management"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def create_workspace(self, task_id: str) -> Workspace:
        """Create isolated workspace for task"""
        pass
    
    @abstractmethod
    async def execute_command(self, workspace: Workspace, command: str) -> Dict[str, Any]:
        """Execute command in workspace"""
        pass
    
    @abstractmethod
    async def cleanup_workspace(self, workspace: Workspace) -> None:
        """Cleanup workspace resources"""
        pass
