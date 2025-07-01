"""DevOpsZealot CLI"""
import click
import requests
import json
import time
from typing import Optional

@click.group()
def cli():
    """DevOpsZealot CLI - Autonomous infrastructure editing"""
    pass

@cli.command()
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8090, help='Server port')
def health(host: str, port: int):
    """Check server health"""
    try:
        response = requests.get(f"http://{host}:{port}/health")
        data = response.json()
        
        click.echo(f"Status: {data['status']}")
        click.echo(f"Version: {data['version']}")
        click.echo("\nComponents:")
        for component, status in data['components'].items():
            click.echo(f"  {component}: {status}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.option('--repo', required=True, help='Repository URL')
@click.option('--file', 'files', multiple=True, required=True, help='Files to edit')
@click.option('--requirement', 'requirements', multiple=True, required=True, help='Edit requirements')
@click.option('--branch', default='main', help='Branch name')
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8090, help='Server port')
@click.option('--api-key', envvar='ZEALOT_API_KEY', help='API key')
@click.option('--wait/--no-wait', default=True, help='Wait for completion')
def submit(repo: str, files: tuple, requirements: tuple, branch: str, 
          host: str, port: int, api_key: Optional[str], wait: bool):
    """Submit a new task"""
    
    # Prepare request
    task_data = {
        "repository": repo,
        "branch": branch,
        "files": list(files),
        "requirements": list(requirements)
    }
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Zealot-API-Key"] = api_key
    
    # Submit task
    try:
        response = requests.post(
            f"http://{host}:{port}/api/v1/tasks",
            json=task_data,
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        task_id = result['task_id']
        
        click.echo(f"Task submitted: {task_id}")
        click.echo(f"Status: {result['status']}")
        
        if not wait:
            return
        
        # Wait for completion
        click.echo("\nWaiting for completion...")
        with click.progressbar(length=100, label='Processing') as bar:
            last_progress = 0
            
            while True:
                time.sleep(2)
                
                # Get status
                status_response = requests.get(
                    f"http://{host}:{port}/api/v1/tasks/{task_id}",
                    headers=headers
                )
                status_data = status_response.json()
                
                # Update progress
                if status_data['status'] == 'processing':
                    progress = min(last_progress + 10, 90)
                elif status_data['status'] in ['completed', 'failed']:
                    progress = 100
                else:
                    progress = last_progress
                
                bar.update(progress - last_progress)
                last_progress = progress
                
                if status_data['status'] in ['completed', 'failed']:
                    click.echo(f"\nTask {status_data['status']}")
                    
                    if status_data.get('result'):
                        result = status_data['result']
                        if result.get('pr_url'):
                            click.echo(f"Pull Request: {result['pr_url']}")
                        if result.get('error'):
                            click.echo(f"Error: {result['error']}", err=True)
                    break
                    
    except requests.HTTPError as e:
        click.echo(f"HTTP Error: {e}", err=True)
        if e.response.text:
            click.echo(e.response.text, err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.argument('task_id')
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8090, help='Server port')
@click.option('--api-key', envvar='ZEALOT_API_KEY', help='API key')
def status(task_id: str, host: str, port: int, api_key: Optional[str]):
    """Get task status"""
    headers = {}
    if api_key:
        headers["X-Zealot-API-Key"] = api_key
    
    try:
        response = requests.get(
            f"http://{host}:{port}/api/v1/tasks/{task_id}",
            headers=headers
        )
        response.raise_for_status()
        
        data = response.json()
        
        click.echo(f"Task ID: {data['task_id']}")
        click.echo(f"Status: {data['status']}")
        
        if data.get('created_at'):
            click.echo(f"Created: {data['created_at']}")
        if data.get('started_at'):
            click.echo(f"Started: {data['started_at']}")
        if data.get('completed_at'):
            click.echo(f"Completed: {data['completed_at']}")
            
        if data.get('result'):
            result = data['result']
            click.echo("\nResult:")
            click.echo(f"  Success: {result['success']}")
            if result.get('pr_url'):
                click.echo(f"  PR URL: {result['pr_url']}")
            if result.get('commit_sha'):
                click.echo(f"  Commit: {result['commit_sha']}")
            if result.get('duration_seconds'):
                click.echo(f"  Duration: {result['duration_seconds']:.1f}s")
            if result.get('error'):
                click.echo(f"  Error: {result['error']}", err=True)
                
    except requests.HTTPError as e:
        click.echo(f"HTTP Error: {e}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.option('--status', help='Filter by status')
@click.option('--limit', default=10, help='Number of tasks to show')
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8090, help='Server port')
@click.option('--api-key', envvar='ZEALOT_API_KEY', help='API key')
def list(status: Optional[str], limit: int, host: str, port: int, api_key: Optional[str]):
    """List tasks"""
    headers = {}
    if api_key:
        headers["X-Zealot-API-Key"] = api_key
    
    params = {"limit": limit}
    if status:
        params["status"] = status
    
    try:
        response = requests.get(
            f"http://{host}:{port}/api/v1/tasks",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        
        data = response.json()
        tasks = data['tasks']
        
        if not tasks:
            click.echo("No tasks found")
            return
        
        click.echo(f"Found {len(tasks)} tasks:\n")
        
        for task in tasks:
            click.echo(f"ID: {task['id']}")
            click.echo(f"  Status: {task['status']}")
            click.echo(f"  Created: {task.get('created_at', 'N/A')}")
            click.echo()
            
    except requests.HTTPError as e:
        click.echo(f"HTTP Error: {e}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

def main():
    """CLI entry point"""
    cli()

if __name__ == "__main__":
    main()
