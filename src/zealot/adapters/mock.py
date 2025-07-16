"""
Mock adapters for testing and development
"""
from typing import Dict, Any, List
import uuid
import os
import tempfile
from .base import IssueAdapter, VCSAdapter, LLMAdapter, ContainerAdapter, Workspace


class MockIssueAdapter(IssueAdapter):
    """Mock issue adapter for testing"""
    
    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Return mock issue data"""
        return {
            'id': issue_id,
            'title': f'Mock Issue {issue_id}',
            'description': 'This is a mock issue for testing',
            'status': 'open',
            'priority': 'normal',
            'labels': ['mock', 'test'],
            'assignee': 'test-user',
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z',
            'metadata': {
                'project': 'test-project',
                'mock': True
            }
        }
    
    async def update_issue(self, issue_id: str, updates: Dict[str, Any]) -> bool:
        """Mock issue update"""
        print(f"[MOCK] Updating issue {issue_id} with: {updates}")
        return True
    
    async def list_issues(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return mock issue list"""
        return [
            await self.get_issue('MOCK-1'),
            await self.get_issue('MOCK-2'),
            await self.get_issue('MOCK-3')
        ]


class MockVCSAdapter(VCSAdapter):
    """Mock VCS adapter for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.branches = ['main']
        self.current_branch = 'main'
        self.commits = []
    
    async def clone(self, workspace_path: str, repository: str, branch: str = None) -> None:
        """Mock repository clone"""
        branch = branch or 'main'
        print(f"[MOCK] Cloning {repository} (branch: {branch}) to {workspace_path}")
        
        # Create a dummy file to simulate repo
        os.makedirs(workspace_path, exist_ok=True)
        with open(os.path.join(workspace_path, 'README.md'), 'w') as f:
            f.write(f"# Mock Repository\nCloned from: {repository}\n")
    
    async def create_branch(self, workspace_path: str, branch_name: str) -> str:
        """Mock branch creation"""
        print(f"[MOCK] Creating branch: {branch_name}")
        self.branches.append(branch_name)
        self.current_branch = branch_name
        return branch_name
    
    async def commit(self, workspace_path: str, message: str) -> str:
        """Mock commit"""
        commit_sha = str(uuid.uuid4())[:8]
        print(f"[MOCK] Committing with message: {message}")
        print(f"[MOCK] Commit SHA: {commit_sha}")
        self.commits.append({
            'sha': commit_sha,
            'message': message,
            'branch': self.current_branch
        })
        return commit_sha
    
    async def push(self, workspace_path: str, branch: str) -> None:
        """Mock push"""
        print(f"[MOCK] Pushing branch {branch} to remote")
    
    async def get_current_branch(self, workspace_path: str) -> str:
        """Get current branch"""
        return self.current_branch


class MockLLMAdapter(LLMAdapter):
    """Mock LLM adapter for testing"""
    
    async def generate_edit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock code edit"""
        print(f"[MOCK] Generating edit with context keys: {list(context.keys())}")
        
        # Simulate editing based on file type
        file_type = context.get('file_type', 'txt')
        current_content = context.get('context', '').split('\n')
        
        # Extract current content if provided
        for line in current_content:
            if line.startswith('Current content:'):
                break
        
        # Generate mock edited content
        if file_type == 'py':
            content = '''# Mock edited Python file
def hello_world():
    """This function was edited by mock LLM"""
    print("Hello from mock LLM!")
    return True
'''
        elif file_type == 'tf':
            content = '''# Mock edited Terraform file
resource "mock_resource" "example" {
  name = "edited-by-mock-llm"
  description = "This resource was edited by mock LLM"
}
'''
        else:
            content = f"# Mock edited file\nThis file was edited by mock LLM\nOriginal type: {file_type}\n"
        
        return {
            'content': content,
            'summary': f'Mock edit for {file_type} file',
            'metadata': {
                'model': 'mock-llm',
                'tokens_used': 100,
                'mock': True
            }
        }
    
    async def generate_text(self, prompt: str, options: Dict[str, Any] = None) -> str:
        """Generate mock text"""
        return f"Mock response to: {prompt[:50]}..."
    
    async def analyze_code(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """Mock code analysis"""
        return {
            'analysis_type': analysis_type,
            'findings': ['Mock finding 1', 'Mock finding 2'],
            'summary': f'Mock {analysis_type} analysis complete',
            'mock': True
        }


class MockContainerAdapter(ContainerAdapter):
    """Mock container adapter for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.workspaces = {}
    
    async def create_workspace(self, task_id: str) -> Workspace:
        """Create mock workspace"""
        # Create a temporary directory for the workspace
        workspace_path = tempfile.mkdtemp(prefix=f"zealot_mock_{task_id}_")
        print(f"[MOCK] Created workspace at: {workspace_path}")
        
        workspace = Workspace(
            id=task_id,
            path=workspace_path,
            metadata={'mock': True, 'adapter': 'mock'}
        )
        
        self.workspaces[task_id] = workspace
        return workspace
    
    async def execute_command(self, workspace: Workspace, command: str) -> Dict[str, Any]:
        """Mock command execution"""
        print(f"[MOCK] Executing in workspace {workspace.id}: {command}")
        
        return {
            'stdout': f'Mock output for: {command}',
            'stderr': '',
            'returncode': 0,
            'mock': True
        }
    
    async def cleanup_workspace(self, workspace: Workspace) -> None:
        """Mock workspace cleanup"""
        print(f"[MOCK] Cleaning up workspace: {workspace.id}")
        
        # Remove from tracking
        if workspace.id in self.workspaces:
            del self.workspaces[workspace.id]
        
        # In real implementation, would delete the directory
        # For mock, we'll keep it for inspection
