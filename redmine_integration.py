import requests
from redminelib import Redmine
from typing import List, Dict, Optional, Any
import os

class RedmineIntegration:
    """Integration with Redmine project management system."""
    
    def __init__(self, url: str, api_key: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        
        # Initialize Redmine connection
        if api_key:
            self.redmine = Redmine(url, key=api_key)
        elif username and password:
            self.redmine = Redmine(url, username=username, password=password)
        else:
            raise ValueError("Either API key or username/password must be provided")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Redmine server."""
        try:
            user = self.redmine.auth()
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "login": user.login,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "mail": user.mail
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of available projects."""
        try:
            projects = self.redmine.project.all()
            return [
                {
                    "id": project.id,
                    "identifier": project.identifier,
                    "name": project.name,
                    "description": getattr(project, 'description', ''),
                    "status": project.status,
                    "created_on": str(project.created_on),
                    "updated_on": str(project.updated_on)
                }
                for project in projects
            ]
        except Exception as e:
            raise Exception(f"Failed to fetch projects: {str(e)}")
    
    def get_project_issues(self, project_id: str, status_filter: str = "open") -> List[Dict[str, Any]]:
        """Get issues for a specific project."""
        try:
            filters = {"project_id": project_id}
            
            if status_filter == "open":
                filters["status_id"] = "open"
            elif status_filter == "closed":
                filters["status_id"] = "closed"
            elif status_filter == "all":
                pass  # No status filter
            
            issues = self.redmine.issue.filter(**filters)
            
            return [
                {
                    "id": issue.id,
                    "subject": issue.subject,
                    "description": getattr(issue, 'description', ''),
                    "status": {
                        "id": issue.status.id,
                        "name": issue.status.name
                    },
                    "priority": {
                        "id": issue.priority.id,
                        "name": issue.priority.name
                    },
                    "tracker": {
                        "id": issue.tracker.id,
                        "name": issue.tracker.name
                    },
                    "author": {
                        "id": issue.author.id,
                        "name": issue.author.name
                    },
                    "assigned_to": {
                        "id": issue.assigned_to.id,
                        "name": issue.assigned_to.name
                    } if hasattr(issue, 'assigned_to') else None,
                    "created_on": str(issue.created_on),
                    "updated_on": str(issue.updated_on),
                    "due_date": str(issue.due_date) if hasattr(issue, 'due_date') and issue.due_date else None,
                    "estimated_hours": getattr(issue, 'estimated_hours', None),
                    "spent_hours": getattr(issue, 'spent_hours', 0),
                    "done_ratio": getattr(issue, 'done_ratio', 0)
                }
                for issue in issues
            ]
        except Exception as e:
            raise Exception(f"Failed to fetch issues: {str(e)}")
    
    def get_issue_details(self, issue_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific issue."""
        try:
            issue = self.redmine.issue.get(issue_id, include=['journals', 'attachments'])
            
            # Get journals (history/comments)
            journals = []
            if hasattr(issue, 'journals'):
                for journal in issue.journals:
                    journal_data = {
                        "id": journal.id,
                        "user": {
                            "id": journal.user.id,
                            "name": journal.user.name
                        },
                        "created_on": str(journal.created_on),
                        "notes": getattr(journal, 'notes', ''),
                        "details": []
                    }
                    
                    if hasattr(journal, 'details'):
                        for detail in journal.details:
                            journal_data["details"].append({
                                "property": detail.property,
                                "name": detail.name,
                                "old_value": getattr(detail, 'old_value', ''),
                                "new_value": getattr(detail, 'new_value', '')
                            })
                    
                    journals.append(journal_data)
            
            # Get attachments
            attachments = []
            if hasattr(issue, 'attachments'):
                for attachment in issue.attachments:
                    attachments.append({
                        "id": attachment.id,
                        "filename": attachment.filename,
                        "filesize": attachment.filesize,
                        "content_type": attachment.content_type,
                        "description": getattr(attachment, 'description', ''),
                        "created_on": str(attachment.created_on),
                        "author": {
                            "id": attachment.author.id,
                            "name": attachment.author.name
                        }
                    })
            
            return {
                "id": issue.id,
                "subject": issue.subject,
                "description": getattr(issue, 'description', ''),
                "status": {
                    "id": issue.status.id,
                    "name": issue.status.name
                },
                "priority": {
                    "id": issue.priority.id,
                    "name": issue.priority.name
                },
                "tracker": {
                    "id": issue.tracker.id,
                    "name": issue.tracker.name
                },
                "project": {
                    "id": issue.project.id,
                    "name": issue.project.name,
                    "identifier": issue.project.identifier
                },
                "author": {
                    "id": issue.author.id,
                    "name": issue.author.name
                },
                "assigned_to": {
                    "id": issue.assigned_to.id,
                    "name": issue.assigned_to.name
                } if hasattr(issue, 'assigned_to') else None,
                "created_on": str(issue.created_on),
                "updated_on": str(issue.updated_on),
                "due_date": str(issue.due_date) if hasattr(issue, 'due_date') and issue.due_date else None,
                "estimated_hours": getattr(issue, 'estimated_hours', None),
                "spent_hours": getattr(issue, 'spent_hours', 0),
                "done_ratio": getattr(issue, 'done_ratio', 0),
                "journals": journals,
                "attachments": attachments
            }
        except Exception as e:
            raise Exception(f"Failed to fetch issue details: {str(e)}")
    
    def add_issue_note(self, issue_id: int, notes: str) -> bool:
        """Add a note/comment to an issue."""
        try:
            issue = self.redmine.issue.get(issue_id)
            issue.notes = notes
            issue.save()
            return True
        except Exception as e:
            raise Exception(f"Failed to add note to issue: {str(e)}")
    
    def update_issue_status(self, issue_id: int, status_id: int, notes: str = "") -> bool:
        """Update the status of an issue."""
        try:
            issue = self.redmine.issue.get(issue_id)
            issue.status_id = status_id
            if notes:
                issue.notes = notes
            issue.save()
            return True
        except Exception as e:
            raise Exception(f"Failed to update issue status: {str(e)}")
    
    def get_statuses(self) -> List[Dict[str, Any]]:
        """Get available issue statuses."""
        try:
            statuses = self.redmine.issue_status.all()
            return [
                {
                    "id": status.id,
                    "name": status.name,
                    "is_closed": getattr(status, 'is_closed', False)
                }
                for status in statuses
            ]
        except Exception as e:
            raise Exception(f"Failed to fetch statuses: {str(e)}")
    
    def create_issue_link_comment(self, issue_id: int, job_id: str, repo_url: str, branch_name: str) -> bool:
        """Create a comment linking the issue to a container job."""
        try:
            notes = f"""AI Code Modification Job Started

Job ID: {job_id}
Repository: {repo_url}
Branch: {branch_name}

This issue is being worked on by an AI agent. The modifications will be committed to the branch above."""
            
            return self.add_issue_note(issue_id, notes)
        except Exception as e:
            raise Exception(f"Failed to create issue link comment: {str(e)}")
    
    def create_completion_comment(self, issue_id: int, job_id: str, commit_hash: str, files_modified: List[str]) -> bool:
        """Create a comment when the job completes."""
        try:
            files_list = "\n".join([f"- {file}" for file in files_modified])
            notes = f"""AI Code Modification Job Completed

Job ID: {job_id}
Commit: {commit_hash}

Files Modified:
{files_list}

The AI agent has successfully completed the code modifications for this issue."""
            
            return self.add_issue_note(issue_id, notes)
        except Exception as e:
            raise Exception(f"Failed to create completion comment: {str(e)}")