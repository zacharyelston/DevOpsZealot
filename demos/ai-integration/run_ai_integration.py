#!/usr/bin/env python3
"""
Docker container entrypoint for AI integration demo with remote repository support
"""
import os
import sys
import logging
import json  # Added missing import
import shutil
from pathlib import Path
import subprocess
from ai_file_editor import AIFileEditor
import validators

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entrypoint"""
    logger.info("Starting DevOpsZealot AI Integration Demo")
    
    # Load context file to get repository URL and branch name
    context_file = Path('/app/context.json')
    with open(context_file) as f:
        context = json.load(f)
        
    # Get repository URL and branch name
    repo_url = context.get('task', {}).get('repository', '')
    branch_name = context.get('task', {}).get('branch', 'redmine-123')
    
    # Determine if it's a remote or local repository
    is_remote_repo = repo_url.startswith('http') or repo_url.startswith('git@')
    
    if is_remote_repo:
        # Set up Git credentials with GITHUB_TOKEN if available
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            logger.info("Setting up Git credentials with GITHUB_TOKEN")
            # Convert https://github.com/user/repo to https://TOKEN@github.com/user/repo
            if repo_url.startswith('https://github.com'):
                auth_repo_url = repo_url.replace('https://github.com', f'https://{github_token}@github.com')
            else:
                auth_repo_url = repo_url  # Keep as is for SSH URLs
        else:
            logger.warning("GITHUB_TOKEN not set. May have issues with private repositories.")
            auth_repo_url = repo_url
        
        # Clone the repository
        target_repo = Path('/tmp/workspace')
        if target_repo.exists():
            logger.info(f"Cleaning workspace directory: {target_repo}")
            shutil.rmtree(target_repo)
        
        target_repo.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cloning repository: {repo_url} (auth URL redacted)")
        try:
            # Use subprocess instead of GitPython for initial clone to support auth
            subprocess.run(
                ['git', 'clone', auth_repo_url, str(target_repo)],
                check=True,
                stderr=subprocess.PIPE,  # Capture stderr to prevent token exposure in logs
                stdout=subprocess.PIPE
            )
            logger.info("Repository cloned successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e}")
            return 1
    else:
        # Local repository case (mounted at /target)
        target_repo = Path('/target')
        if not target_repo.exists() or not (target_repo / '.git').exists():
            logger.error(f"Target directory {target_repo} is not a valid Git repository")
            return 1
        logger.info(f"Using local repository: {target_repo}")
    
    # Determine API to use
    api_type = 'openai'
    model = 'gpt-4'
    
    if os.environ.get('ANTHROPIC_API_KEY') and not os.environ.get('OPENAI_API_KEY'):
        api_type = 'anthropic'
        model = 'claude-3-opus-20240229'
    
    if os.environ.get('AI_MODEL'):
        model = os.environ['AI_MODEL']
    
    # Display configuration
    logger.info(f"Target repository: {target_repo}")
    logger.info(f"Using API: {api_type} with model: {model}")
    
    # Configure Git identity
    logger.info("Setting Git user configuration")
    subprocess.run(
        ['git', 'config', 'user.email', 'zealot@example.com'],
        cwd=target_repo,
        check=True
    )
    subprocess.run(
        ['git', 'config', 'user.name', 'DevOps Zealot'],
        cwd=target_repo,
        check=True
    )
    
    # Create a branch for our changes
    logger.info(f"Creating branch: {branch_name}")
    try:
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=target_repo,
            check=True
        )
    except subprocess.CalledProcessError:
        # Branch might already exist, try to check it out
        logger.warning(f"Branch {branch_name} might already exist, trying to check it out")
        subprocess.run(
            ['git', 'checkout', branch_name],
            cwd=target_repo,
            check=True
        )
    
    # Initialize AI File Editor
    try:
        editor = AIFileEditor(
            repo_path=target_repo,
            context_file=context_file,
            api_type=api_type,
            model=model,
            verbose=True
        )
        
        # Process task
        editor.process_task()
        logger.info("AI file editing completed successfully!")
        
        # Run validators
        logger.info("Validating modified files...")
        validator = validators.Validator(target_repo, verbose=True)
        
        # Get list of modified files
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1'],
            cwd=target_repo,
            capture_output=True,
            text=True,
            check=True
        )
        
        modified_files = [target_repo / f for f in result.stdout.strip().split('\n') if f]
        
        # Get validation rules from context
        with open(context_file) as f:
            context = json.load(f)
        
        validation_rules = context.get('task', {}).get('validation_rules', ['shellcheck', 'script_execution_test'])
        
        # Run validation
        success, results = validator.validate(modified_files, validation_rules)
        
        if success:
            logger.info("All validations passed!")
        else:
            logger.error("Some validations failed:")
            import json
            print(json.dumps(results, indent=2))
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during AI integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
