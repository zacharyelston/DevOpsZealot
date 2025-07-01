"""DevOpsZealot CLI"""
import click
import requests
import json
import time
import os
import asyncio
from typing import Optional

# For container mode direct execution
from .engine import ZealotEngine, Task
from .config import Config

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
@click.option('--context-file', required=True, type=click.Path(exists=True), help='JSON file containing task context')
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8090, help='Server port')
@click.option('--api-key', envvar='ZEALOT_API_KEY', help='API key')
@click.option('--wait/--no-wait', default=True, help='Wait for completion')
def process_task(context_file: str, host: str, port: int, api_key: Optional[str], wait: bool):
    """Process a task from a context file"""
    try:
        # Read context file
        with open(context_file, 'r') as f:
            context = json.load(f)
        
        # Extract API keys from context if present
        if 'api_keys' in context:
            if not api_key and 'zealot_api_key' in context['api_keys']:
                api_key = context['api_keys']['zealot_api_key']
        
        # Extract task data
        if 'task' not in context:
            click.echo("Error: Context file must contain a 'task' object", err=True)
            return
            
        task_data = context['task']
        required_fields = ['repository', 'files', 'requirements']
        
        # Validate task data
        missing_fields = [field for field in required_fields if field not in task_data]
        if missing_fields:
            click.echo(f"Error: Task is missing required fields: {', '.join(missing_fields)}", err=True)
            return
            
        # Set default branch if not provided
        if 'branch' not in task_data:
            task_data['branch'] = 'main'
            
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-Zealot-API-Key"] = api_key
            
        # If running in local container mode, process directly
        if 'ZEALOT_CONTAINER_MODE' in os.environ:
            click.echo("Running in container mode - processing task directly")
            
            # Create task object
            task = Task(
                repository=task_data['repository'],
                branch=task_data.get('branch', 'main'),
                files=task_data['files'],
                requirements=task_data['requirements'],
                validation_rules=task_data.get('validation_rules', [])
            )
            
            # Set up config from environment and context
            config = Config()
            
            # Override config with values from context if present
            if 'config' in context:
                if 'ai_model' in context['config']:
                    config.ai_model = context['config']['ai_model']
                if 'verbose_logging' in context['config'] and context['config']['verbose_logging']:
                    config.log_level = 'DEBUG'
            
            # Override config with API keys from context
            if 'api_keys' in context:
                if 'openai_api_key' in context['api_keys']:
                    config.openai_api_key = context['api_keys']['openai_api_key']
                if 'anthropic_api_key' in context['api_keys']:
                    config.anthropic_api_key = context['api_keys']['anthropic_api_key']
                if 'github_token' in context['api_keys']:
                    config.github_token = context['api_keys']['github_token']
            
            # Initialize engine
            engine = ZealotEngine(config)
            
            # Process task directly
            click.echo(f"Processing task with repository: {task.repository}")
            click.echo(f"Files to modify: {', '.join(task.files)}")
            click.echo(f"Requirements: {', '.join(task.requirements[:3])}" + 
                      (f" (+{len(task.requirements) - 3} more)" if len(task.requirements) > 3 else ""))
            
            try:
                # Run task synchronously via asyncio
                result = asyncio.run(engine.process_task(task))
                
                if result.success:
                    click.echo("\n✅ Task completed successfully!")
                    if result.pr_url:
                        click.echo(f"PR URL: {result.pr_url}")
                    if result.commit_sha:
                        click.echo(f"Commit: {result.commit_sha[:8]}")
                    
                    click.echo("\nChanges made:")
                    for change in result.changes:
                        click.echo(f"- {change['file']}: {change['summary']}")
                else:
                    click.echo("\n❌ Task failed!")
                    click.echo(f"Error: {result.error}")
                
                # Return with appropriate exit code
                return 0 if result.success else 1
            except Exception as e:
                click.echo(f"\n❌ Error processing task: {str(e)}")
                return 1
            
        # Submit task
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
                    if status_data['status'] == 'completed' and 'result' in status_data:
                        click.echo(f"PR URL: {status_data['result'].get('pr_url', 'N/A')}")
                    if status_data['status'] == 'failed' and 'error' in status_data:
                        click.echo(f"Error: {status_data['error']}")
                    break
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
    """Main entry point"""
    return cli()

if __name__ == "__main__":
    main()
