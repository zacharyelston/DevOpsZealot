"""Git operations for DevOpsZealot"""
import os
import git
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()

class GitManager:
    """Manages Git operations for code repositories"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.repo: Optional[git.Repo] = None
        
    def clone_repository(self, repo_url: str, branch: str = "main") -> None:
        """Clone repository to workspace"""
        logger.info("Cloning repository", url=repo_url, branch=branch)
        
        try:
            # Clone with depth 1 for faster operations
            self.repo = git.Repo.clone_from(
                repo_url, 
                self.workspace_path,
                branch=branch,
                depth=1
            )
            logger.info("Repository cloned successfully", path=self.workspace_path)
            
        except git.exc.GitCommandError as e:
            logger.error("Git clone failed", error=str(e))
            raise ValueError(f"Failed to clone repository: {e}")
    
    def create_feature_branch(self, branch_name: str) -> None:
        """Create and checkout new feature branch"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        logger.info("Creating feature branch", branch=branch_name)
        
        try:
            # Create new branch from current HEAD
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
            logger.info("Feature branch created and checked out", branch=branch_name)
            
        except git.exc.GitCommandError as e:
            logger.error("Failed to create branch", error=str(e))
            raise ValueError(f"Failed to create branch: {e}")
    
    def read_file(self, file_path: str) -> str:
        """Read file content from repository"""
        full_path = os.path.join(self.workspace_path, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to file in repository"""
        full_path = os.path.join(self.workspace_path, file_path)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.debug("File written", path=file_path)
    
    def get_changed_files(self) -> List[str]:
        """Get list of changed files"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        # Get both staged and unstaged changes
        changed = []
        
        # Unstaged changes
        for item in self.repo.index.diff(None):
            changed.append(item.a_path)
            
        # Staged changes
        for item in self.repo.index.diff("HEAD"):
            if item.a_path not in changed:
                changed.append(item.a_path)
                
        # Untracked files
        changed.extend(self.repo.untracked_files)
        
        return changed
    
    def commit_changes(self, message: str) -> str:
        """Commit all changes with given message"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        logger.info("Committing changes", message=message.split('\n')[0])
        
        try:
            # Add all changes
            self.repo.git.add(all=True)
            
            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
                logger.warning("No changes to commit")
                return ""
            
            # Commit
            commit = self.repo.index.commit(message)
            
            logger.info("Changes committed", sha=commit.hexsha[:8])
            return commit.hexsha
            
        except git.exc.GitCommandError as e:
            logger.error("Commit failed", error=str(e))
            raise ValueError(f"Failed to commit changes: {e}")
    
    def push_changes(self, branch_name: str, remote: str = "origin") -> None:
        """Push changes to remote repository"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        logger.info("Pushing changes", branch=branch_name, remote=remote)
        
        try:
            # Push to remote
            origin = self.repo.remote(remote)
            origin.push(f"{branch_name}:{branch_name}", set_upstream=True)
            
            logger.info("Changes pushed successfully")
            
        except git.exc.GitCommandError as e:
            logger.error("Push failed", error=str(e))
            raise ValueError(f"Failed to push changes: {e}")
    
    def get_diff(self) -> str:
        """Get diff of current changes"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        return self.repo.git.diff()
    
    def get_file_history(self, file_path: str, max_count: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a file"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        history = []
        
        try:
            commits = list(self.repo.iter_commits(paths=file_path, max_count=max_count))
            
            for commit in commits:
                history.append({
                    "sha": commit.hexsha[:8],
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "message": commit.message.strip()
                })
                
        except Exception as e:
            logger.error("Failed to get file history", file=file_path, error=str(e))
            
        return history
    
    def checkout_file(self, file_path: str, ref: str = "HEAD") -> None:
        """Checkout specific version of a file"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        try:
            self.repo.git.checkout(ref, "--", file_path)
            logger.info("File checked out", file=file_path, ref=ref)
            
        except git.exc.GitCommandError as e:
            logger.error("Checkout failed", error=str(e))
            raise ValueError(f"Failed to checkout file: {e}")
    
    def get_current_branch(self) -> str:
        """Get current branch name"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        return self.repo.active_branch.name
    
    def get_remote_url(self) -> str:
        """Get remote repository URL"""
        if not self.repo:
            raise ValueError("No repository initialized")
            
        try:
            return self.repo.remote("origin").url
        except ValueError:
            return ""
