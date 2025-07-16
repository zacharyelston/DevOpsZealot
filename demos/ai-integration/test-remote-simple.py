#!/usr/bin/env python3
"""
Simple test script for remote repository cloning
Following our design philosophy of clarity over complexity
"""
import os
import sys
import json
import logging
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Main function that tests remote repository cloning"""
    logger.info("Starting simple remote repository test")
    
    # 1. Load configuration
    try:
        with open('context-remote-example.json', 'r') as f:
            context = json.load(f)
            logger.info(f"Loaded context: {context}")
    except Exception as e:
        logger.error(f"Failed to load context file: {e}")
        return 1
    
    # 2. Extract repository info
    repo_url = context.get('task', {}).get('repository', '')
    branch_name = context.get('task', {}).get('branch', 'main')
    
    logger.info(f"Repository URL: {repo_url}")
    logger.info(f"Branch name: {branch_name}")
    
    # 3. Set up workspace
    workspace_dir = Path('test-workspace')
    if workspace_dir.exists():
        logger.info(f"Cleaning existing workspace: {workspace_dir}")
        try:
            import shutil
            shutil.rmtree(workspace_dir)
        except Exception as e:
            logger.error(f"Failed to clean workspace: {e}")
            return 1
    
    workspace_dir.mkdir(exist_ok=True)
    logger.info(f"Created workspace: {workspace_dir}")
    
    # 4. Clone repository
    try:
        github_token = os.environ.get('GITHUB_TOKEN', '')
        
        logger.info(f"Cloning repository to {workspace_dir}")
        
        # Set up Git command environment with token for authentication if available
        env = os.environ.copy()
        if github_token and repo_url.startswith('https://github.com'):
            logger.info("Using GitHub token authentication")
            # Use GIT_ASKPASS to provide the token securely
            env['GIT_ASKPASS'] = 'echo'
            env['GIT_USERNAME'] = 'x-access-token'
            env['GIT_PASSWORD'] = github_token
        else:
            logger.info("Using standard URL without authentication")
        
        # Clone the repository using subprocess
        result = subprocess.run(
            ['git', 'clone', repo_url, str(workspace_dir)],
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"Clone failed: {result.stderr}")
            return 1
            
        logger.info("Repository cloned successfully")
    except Exception as e:
        logger.error(f"Failed to clone repository: {e}")
        return 1
    
    # 5. Create and checkout branch
    try:
        logger.info(f"Creating branch: {branch_name}")
        subprocess.run(['git', 'checkout', '-b', branch_name], cwd=workspace_dir, check=True)
        logger.info(f"Branch {branch_name} created and checked out")
    except subprocess.CalledProcessError:
        # Branch might already exist
        logger.info(f"Branch might exist, trying to check it out: {branch_name}")
        try:
            subprocess.run(['git', 'checkout', branch_name], cwd=workspace_dir, check=True)
            logger.info(f"Branch {branch_name} checked out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout branch: {e}")
            return 1
    
    # 6. Report success with PR instructions
    logger.info("Remote repository test completed successfully!")
    logger.info(f"To create a PR, visit: https://github.com/{repo_url.split('github.com/')[-1].split('.git')[0]}/pull/new/{branch_name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())