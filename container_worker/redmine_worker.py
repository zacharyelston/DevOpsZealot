import os
from typing import Optional, Dict, Any, List
from redminelib import Redmine

class RedmineWorker:
    """Redmine integration for container workers."""
    
    def __init__(self, redmine_url: str, api_key: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.redmine_url = redmine_url
        
        # Initialize Redmine connection
        if api_key:
            self.redmine = Redmine(redmine_url, key=api_key)
        elif username and password:
            self.redmine = Redmine(redmine_url, username=username, password=password)
        else:
            self.redmine = None
    
    def is_connected(self) -> bool:
        """Check if Redmine connection is available."""
        return self.redmine is not None
    
    def add_job_start_comment(self, issue_id: int, job_id: str, repo_url: str, branch_name: str) -> bool:
        """Add a comment when job starts."""
        if not self.redmine:
            return False
            
        try:
            notes = f"""AI Code Modification Job Started

Job ID: {job_id}
Repository: {repo_url}
Branch: {branch_name}

This issue is being worked on by an AI agent. The modifications will be committed to the branch above."""
            
            issue = self.redmine.issue.get(issue_id)
            issue.notes = notes
            issue.save()
            return True
        except Exception:
            return False
    
    def add_completion_comment(self, issue_id: int, job_id: str, commit_hash: str, files_modified: List[str]) -> bool:
        """Add a comment when job completes successfully."""
        if not self.redmine:
            return False
            
        try:
            files_list = "\n".join([f"- {file}" for file in files_modified])
            notes = f"""AI Code Modification Job Completed

Job ID: {job_id}
Commit: {commit_hash}

Files Modified:
{files_list}

The AI agent has successfully completed the code modifications for this issue."""
            
            issue = self.redmine.issue.get(issue_id)
            issue.notes = notes
            issue.save()
            return True
        except Exception:
            return False
    
    def add_failure_comment(self, issue_id: int, job_id: str, error_message: str) -> bool:
        """Add a comment when job fails."""
        if not self.redmine:
            return False
            
        try:
            notes = f"""AI Code Modification Job Failed

Job ID: {job_id}
Error: {error_message}

The AI agent encountered an error while processing this issue. Please review the error and try again."""
            
            issue = self.redmine.issue.get(issue_id)
            issue.notes = notes
            issue.save()
            return True
        except Exception:
            return False