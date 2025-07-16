"""
Git adapter for version control operations
"""
import os
import asyncio
from typing import Dict, Any
import structlog
from .base import VCSAdapter

logger = structlog.get_logger()


class GitVcsAdapter(VCSAdapter):
    """Git version control adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.remote = config.get('remote', 'origin')
        self.default_branch = config.get('default_branch', 'main')
        self.user_name = config.get('user_name', 'DevOps Zealot')
        self.user_email = config.get('user_email', 'zealot@example.com')
        
    async def clone(self, workspace_path: str, repository: str, branch: str = None) -> None:
        """Clone repository to workspace"""
        branch = branch or self.default_branch
        
        # Set up authentication if provided
        auth_cmd = ""
        if 'auth_token' in self.config:
            # For GitHub/GitLab style tokens
            repository = repository.replace('https://', f"https://{self.config['auth_token']}@")
        
        cmd = f"git clone --branch {branch} {repository} {workspace_path}"
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error("Git clone failed",
                       repository=repository,
                       branch=branch,
                       error=stderr.decode())
            raise RuntimeError(f"Git clone failed: {stderr.decode()}")
        
        # Configure git user
        await self._configure_git_user(workspace_path)
        
        logger.info("Repository cloned successfully",
                   repository=repository,
                   branch=branch,
                   workspace=workspace_path)
    
    async def create_branch(self, workspace_path: str, branch_name: str) -> str:
        """Create and checkout new branch"""
        cmd = f"git checkout -b {branch_name}"
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error("Failed to create branch",
                       branch=branch_name,
                       error=stderr.decode())
            raise RuntimeError(f"Failed to create branch: {stderr.decode()}")
        
        logger.info("Branch created", branch=branch_name)
        return branch_name
    
    async def commit(self, workspace_path: str, message: str) -> str:
        """Commit all changes"""
        # Stage all changes
        stage_cmd = "git add -A"
        proc = await asyncio.create_subprocess_shell(
            stage_cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await proc.communicate()
        
        # Commit
        commit_cmd = f'git commit -m "{message}"'
        proc = await asyncio.create_subprocess_shell(
            commit_cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            if "nothing to commit" in stderr.decode():
                logger.info("No changes to commit")
                return await self._get_current_commit(workspace_path)
            else:
                logger.error("Failed to commit",
                           error=stderr.decode())
                raise RuntimeError(f"Failed to commit: {stderr.decode()}")
        
        # Get commit SHA
        return await self._get_current_commit(workspace_path)
    
    async def push(self, workspace_path: str, branch: str) -> None:
        """Push branch to remote"""
        cmd = f"git push --set-upstream {self.remote} {branch}"
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error("Failed to push",
                       branch=branch,
                       error=stderr.decode())
            raise RuntimeError(f"Failed to push: {stderr.decode()}")
        
        logger.info("Changes pushed", branch=branch)
    
    async def get_current_branch(self, workspace_path: str) -> str:
        """Get current branch name"""
        cmd = "git rev-parse --abbrev-ref HEAD"
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to get branch: {stderr.decode()}")
        
        return stdout.decode().strip()
    
    async def _configure_git_user(self, workspace_path: str) -> None:
        """Configure git user for commits"""
        commands = [
            f'git config user.name "{self.user_name}"',
            f'git config user.email "{self.user_email}"'
        ]
        
        for cmd in commands:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
    
    async def _get_current_commit(self, workspace_path: str) -> str:
        """Get current commit SHA"""
        cmd = "git rev-parse HEAD"
        
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to get commit SHA: {stderr.decode()}")
        
        return stdout.decode().strip()
