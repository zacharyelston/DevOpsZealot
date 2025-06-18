import git
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import shutil

class GitManager:
    """Handles all Git operations for the repository."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = None
    
    def clone_repository(self, repo_url: str, auth: Optional[Tuple[str, str]] = None) -> None:
        """Clone a repository to the specified path."""
        try:
            if auth:
                username, password = auth
                # Insert credentials into URL
                if '://' in repo_url:
                    protocol, rest = repo_url.split('://', 1)
                    repo_url = f"{protocol}://{username}:{password}@{rest}"
            
            self.repo = git.Repo.clone_from(repo_url, self.repo_path)
            
        except git.exc.GitCommandError as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error during clone: {str(e)}")
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """Create a new branch from the specified base branch."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            # Check if base branch exists
            if base_branch not in [ref.name.split('/')[-1] for ref in self.repo.refs]:
                # Try 'master' if 'main' doesn't exist
                if base_branch == "main":
                    base_branch = "master"
            
            # Checkout base branch
            self.repo.git.checkout(base_branch)
            
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
        except git.exc.GitCommandError as e:
            raise Exception(f"Failed to create branch '{branch_name}': {str(e)}")
    
    def list_files(self, extensions: Optional[List[str]] = None) -> List[str]:
        """List all files in the repository, optionally filtered by extensions."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        files = []
        repo_path = Path(self.repo_path)
        
        for root, dirs, filenames in os.walk(repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(repo_path)
                
                # Filter by extensions if specified
                if extensions:
                    if not any(str(relative_path).endswith(ext) for ext in extensions):
                        continue
                
                files.append(str(relative_path))
        
        return sorted(files)
    
    def read_file(self, file_path: str) -> str:
        """Read the content of a file in the repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        full_path = Path(self.repo_path) / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252']:
                try:
                    with open(full_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise Exception(f"Could not decode file {file_path}")
    
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file in the repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        full_path = Path(self.repo_path) / file_path
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise Exception(f"Failed to write file {file_path}: {str(e)}")
    
    def get_status(self) -> Dict[str, List[str]]:
        """Get the current status of the repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            status = {
                'modified': [],
                'added': [],
                'deleted': [],
                'untracked': []
            }
            
            # Get modified files
            for item in self.repo.index.diff(None):
                if item.change_type == 'M':
                    status['modified'].append(item.a_path)
                elif item.change_type == 'D':
                    status['deleted'].append(item.a_path)
            
            # Get staged files
            for item in self.repo.index.diff("HEAD"):
                if item.change_type == 'A':
                    status['added'].append(item.a_path)
                elif item.change_type == 'M':
                    if item.a_path not in status['modified']:
                        status['modified'].append(item.a_path)
                elif item.change_type == 'D':
                    if item.a_path not in status['deleted']:
                        status['deleted'].append(item.a_path)
            
            # Get untracked files
            status['untracked'] = list(self.repo.untracked_files)
            
            return status
            
        except Exception as e:
            raise Exception(f"Failed to get repository status: {str(e)}")
    
    def commit_changes(self, message: str, author_name: str, author_email: str) -> str:
        """Commit all changes with the specified message and author."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            # Add all changes
            self.repo.git.add(A=True)
            
            # Configure author
            with self.repo.config_writer() as config:
                config.set_value("user", "name", author_name)
                config.set_value("user", "email", author_email)
            
            # Commit changes
            commit = self.repo.index.commit(message)
            return commit.hexsha
            
        except Exception as e:
            raise Exception(f"Failed to commit changes: {str(e)}")
    
    def push_changes(self, remote_name: str = "origin") -> None:
        """Push changes to the remote repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            current_branch = self.repo.active_branch.name
            origin = self.repo.remote(remote_name)
            origin.push(current_branch)
            
        except Exception as e:
            raise Exception(f"Failed to push changes: {str(e)}")
    
    def get_repository_info(self) -> Dict[str, str]:
        """Get basic information about the repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            return {
                "current_branch": self.repo.active_branch.name,
                "remote_url": list(self.repo.remote().urls)[0] if self.repo.remotes else "No remote",
                "last_commit": str(self.repo.head.commit)[:8],
                "total_commits": str(self.repo.git.rev_list('--count', 'HEAD')),
                "repository_path": self.repo_path
            }
        except Exception as e:
            return {"error": f"Could not get repository info: {str(e)}"}
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        if self.repo_path and os.path.exists(self.repo_path):
            try:
                # Only clean up if it's a temporary directory
                if 'tmp' in self.repo_path:
                    shutil.rmtree(self.repo_path, ignore_errors=True)
            except Exception:
                pass  # Ignore cleanup errors
