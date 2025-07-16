"""
Redmine adapter for issue tracking
"""
from typing import Dict, Any, List
import httpx
import structlog
from .base import IssueAdapter

logger = structlog.get_logger()


class RedmineIssueAdapter(IssueAdapter):
    """Redmine issue tracking adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('endpoint', 'http://localhost:3000')
        self.api_key = config.get('api_key', '')
        self.project_id = config.get('default_project', '')
        
    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Get issue details from Redmine"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/issues/{issue_id}.json",
                headers={'X-Redmine-API-Key': self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                issue = data.get('issue', {})
                
                # Normalize to common format
                return {
                    'id': issue.get('id'),
                    'title': issue.get('subject', ''),
                    'description': issue.get('description', ''),
                    'status': issue.get('status', {}).get('name', ''),
                    'priority': issue.get('priority', {}).get('name', ''),
                    'labels': [issue.get('tracker', {}).get('name', '')],
                    'assignee': issue.get('assigned_to', {}).get('name', ''),
                    'created_at': issue.get('created_on'),
                    'updated_at': issue.get('updated_on'),
                    'metadata': {
                        'project': issue.get('project', {}).get('name', ''),
                        'done_ratio': issue.get('done_ratio', 0),
                        'estimated_hours': issue.get('estimated_hours'),
                        'custom_fields': {
                            cf.get('name'): cf.get('value')
                            for cf in issue.get('custom_fields', [])
                        }
                    }
                }
            else:
                logger.error("Failed to get issue from Redmine",
                           issue_id=issue_id,
                           status_code=response.status_code)
                raise ValueError(f"Failed to get issue {issue_id}: {response.text}")
    
    async def update_issue(self, issue_id: str, updates: Dict[str, Any]) -> bool:
        """Update issue in Redmine"""
        # Map common fields to Redmine fields
        redmine_updates = {}
        
        if 'status' in updates:
            # Would need to map status name to ID
            redmine_updates['status_id'] = updates['status']
        
        if 'description' in updates:
            redmine_updates['description'] = updates['description']
        
        if 'assignee' in updates:
            # Would need to map user name to ID
            redmine_updates['assigned_to_id'] = updates['assignee']
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/issues/{issue_id}.json",
                json={'issue': redmine_updates},
                headers={'X-Redmine-API-Key': self.api_key}
            )
            
            return response.status_code in [200, 204]
    
    async def list_issues(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List issues from Redmine based on filters"""
        params = {
            'limit': filters.get('limit', 25),
            'offset': filters.get('offset', 0)
        }
        
        if self.project_id:
            params['project_id'] = self.project_id
        
        if 'status' in filters:
            params['status_id'] = filters['status']
        
        if 'assignee' in filters:
            params['assigned_to_id'] = filters['assignee']
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/issues.json",
                params=params,
                headers={'X-Redmine-API-Key': self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = []
                
                for issue in data.get('issues', []):
                    issues.append({
                        'id': issue.get('id'),
                        'title': issue.get('subject', ''),
                        'status': issue.get('status', {}).get('name', ''),
                        'priority': issue.get('priority', {}).get('name', ''),
                        'assignee': issue.get('assigned_to', {}).get('name', ''),
                        'created_at': issue.get('created_on'),
                        'updated_at': issue.get('updated_on')
                    })
                
                return issues
            else:
                logger.error("Failed to list issues from Redmine",
                           status_code=response.status_code)
                return []
