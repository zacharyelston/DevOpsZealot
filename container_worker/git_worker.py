import git
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import fnmatch

class GitWorker:
    """Handles Git operations within the container."""
    
    def __init__(self):
        self.repo = None
        self.repo_path = None
    
    def clone_repository(self, repo_url: str, auth: Optional[Dict[str, str]] = None) -> str:
        """Clone repository to a temporary directory."""
        try:
            # Create temporary directory for the repo
            self.repo_path = tempfile.mkdtemp(prefix="git_repo_")
            
            # Handle authentication
            if auth and auth.get("username") and auth.get("token"):
                username = auth["username"]
                token = auth["token"]
                
                # Insert credentials into URL
                if '://' in repo_url:
                    protocol, rest = repo_url.split('://', 1)
                    repo_url = f"{protocol}://{username}:{token}@{rest}"
            
            # Clone repository
            self.repo = git.Repo.clone_from(repo_url, self.repo_path)
            return self.repo_path
            
        except git.exc.GitCommandError as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error during clone: {str(e)}")
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """Create and checkout a new branch."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            # Check if base branch exists, fallback to master if main doesn't exist
            available_branches = [ref.name.split('/')[-1] for ref in self.repo.refs]
            if base_branch not in available_branches:
                if base_branch == "main" and "master" in available_branches:
                    base_branch = "master"
                else:
                    raise Exception(f"Base branch '{base_branch}' not found")
            
            # Checkout base branch
            self.repo.git.checkout(base_branch)
            
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
        except git.exc.GitCommandError as e:
            raise Exception(f"Failed to create branch '{branch_name}': {str(e)}")
    
    def find_files(self, patterns: List[str]) -> List[str]:
        """Find files matching the given patterns."""
        if not self.repo_path:
            raise Exception("Repository not initialized")
        
        matched_files = []
        repo_path = Path(self.repo_path)
        
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            # Skip common build/dependency directories
            dirs[:] = [d for d in dirs if d not in [
                'node_modules', '__pycache__', '.pytest_cache', 'target',
                'build', 'dist', '.venv', 'venv', '.env'
            ]]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(repo_path)
                
                # Check if file matches any pattern
                for pattern in patterns:
                    if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(file, pattern):
                        matched_files.append(str(relative_path))
                        break
        
        return sorted(list(set(matched_files)))  # Remove duplicates and sort
    
    def read_file(self, file_path: str) -> str:
        """Read content of a file."""
        if not self.repo_path:
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
        """Write content to a file."""
        if not self.repo_path:
            raise Exception("Repository not initialized")
        
        full_path = Path(self.repo_path) / file_path
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise Exception(f"Failed to write file {file_path}: {str(e)}")
    
    def commit_changes(self, message: str, author_name: str, author_email: str) -> str:
        """Commit all changes."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            # Add all changes
            self.repo.git.add(A=True)
            
            # Configure author
            with self.repo.config_writer() as config:
                config.set_value("user", "name", author_name)
                config.set_value("user", "email", author_email)
            
            # Check if there are any changes to commit
            if not self.repo.is_dirty() and len(self.repo.untracked_files) == 0:
                raise Exception("No changes to commit")
            
            # Commit changes
            commit = self.repo.index.commit(message)
            return commit.hexsha
            
        except Exception as e:
            raise Exception(f"Failed to commit changes: {str(e)}")
    
    def push_changes(self, remote_name: str = "origin") -> None:
        """Push changes to remote repository."""
        if not self.repo:
            raise Exception("Repository not initialized")
        
        try:
            current_branch = self.repo.active_branch.name
            origin = self.repo.remote(remote_name)
            
            # Push the current branch
            origin.push(f"{current_branch}:{current_branch}")
            
        except Exception as e:
            raise Exception(f"Failed to push changes: {str(e)}")
    
    def get_status(self) -> Dict[str, List[str]]:
        """Get repository status."""
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
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.repo_path and os.path.exists(self.repo_path):
            try:
                shutil.rmtree(self.repo_path, ignore_errors=True)
            except Exception:
                pass  # Ignore cleanup errors