#!/usr/bin/env python3
"""
AI File Editor - Core functionality demo for DevOpsZealot

This script demonstrates how DevOpsZealot interacts with AI APIs to:
1. Send context and file content to the AI
2. Receive edited content back
3. Apply changes to the repository
4. Commit changes to git

Usage:
    python ai_file_editor.py --repo [REPO_PATH] --context [CONTEXT_FILE] 
                             --api [openai|anthropic] --model [MODEL_NAME]
"""

import argparse
import os
import sys
import json
import glob
import logging
import tempfile
import git
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# For OpenAI API
import openai
# For Anthropic API (if available)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIFileEditor:
    """Main class to handle AI-powered file editing"""
    
    def __init__(self, 
                 repo_path: str, 
                 context_file: str,
                 api_type: str = "openai",
                 model: str = "gpt-4",
                 verbose: bool = False):
        """
        Initialize the AI File Editor
        
        Args:
            repo_path: Path to the repository to modify
            context_file: Path to the JSON context file
            api_type: Which AI API to use ('openai' or 'anthropic')
            model: Model name to use
            verbose: Enable verbose logging
        """
        self.repo_path = Path(repo_path).absolute()
        self.context_file = Path(context_file).absolute()
        self.api_type = api_type.lower()
        self.model = model
        self.verbose = verbose
        
        # Set logging level based on verbose flag
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Validate environment variables
        self._validate_env()
        
        # Initialize repository
        self.repo = git.Repo(self.repo_path)
        
        # Load context
        self.context = self._load_context()
        
        logger.info(f"Initialized AI File Editor with {self.api_type} API")
        logger.info(f"Target repository: {self.repo_path}")
        logger.info(f"Using AI model: {self.model}")
    
    def _validate_env(self) -> None:
        """Validate required environment variables are set and Git configuration"""
        # Validate API keys first
        if self.api_type == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY environment variable is required")
            openai.api_key = os.environ["OPENAI_API_KEY"]
        elif self.api_type == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        else:
            raise ValueError(f"Unknown API type: {self.api_type}. Use 'openai' or 'anthropic'")
        
        # Check for GitHub token if needed
        if not os.environ.get("GITHUB_TOKEN") and self.verbose:
            logger.warning("GITHUB_TOKEN environment variable not set. Git operations may be limited")
            
        # Validate Git configuration is set up properly
        try:
            # Check if repository exists first
            if os.path.exists(self.repo_path):
                repo = git.Repo(self.repo_path)
                try:
                    # Try to get git config
                    user_name = repo.git.config('user.name')
                    user_email = repo.git.config('user.email')
                    logger.info(f"Git config: user.name={user_name}, user.email={user_email}")
                except git.GitCommandError:
                    # Set default Git configuration if not configured
                    logger.warning("Git user configuration not set. Setting default values...")
                    repo.git.config('user.name', 'DevOps Zealot')
                    repo.git.config('user.email', 'zealot@example.com')
                    logger.info("Set default Git configuration: user.name='DevOps Zealot', user.email='zealot@example.com'")
        except (git.GitCommandError, git.InvalidGitRepositoryError) as e:
            logger.warning(f"Git validation skipped: {e}")
            # Not raising error as the repository might be cloned later
    
    def _load_context(self) -> Dict:
        """Load the context file"""
        if not self.context_file.exists():
            raise FileNotFoundError(f"Context file not found: {self.context_file}")
        
        with open(self.context_file, 'r') as f:
            context = json.load(f)
        
        logger.debug(f"Loaded context: {json.dumps(context, indent=2)}")
        return context
    
    def _validate_git_config(self) -> None:
        """Validate Git configuration using settings from context file"""
        # Check if we have Git configuration in context
        if "config" not in self.context or "git_config" not in self.context["config"]:
            logger.debug("No Git configuration in context file, skipping validation")
            return
        
        git_config = self.context["config"]["git_config"]
        validate_before_api = git_config.get("validate_before_api_call", False)
        
        if not validate_before_api:
            logger.debug("Git validation before API call disabled in config")
            return
            
        logger.info("Validating Git configuration before API calls")
        
        try:
            # Use user settings from config file if available
            user_config = git_config.get("user", {})
            default_name = user_config.get("name", "DevOps Zealot")
            default_email = user_config.get("email", "zealot@example.com")
            
            # Check and set Git config
            try:
                # Check if user.name and user.email are set
                user_name = self.repo.git.config('user.name')
                user_email = self.repo.git.config('user.email')
                logger.info(f"Git config validated: user.name={user_name}, user.email={user_email}")
            except git.GitCommandError:
                # Set Git config using values from context file
                logger.warning("Git user configuration not found, setting from context file...")
                self.repo.git.config('user.name', default_name)
                self.repo.git.config('user.email', default_email)
                logger.info(f"Set Git config: user.name='{default_name}', user.email='{default_email}'")
        except Exception as e:
            logger.error(f"Failed to validate Git configuration: {e}")
            raise ValueError(f"Git configuration validation failed: {e}")
    
    def process_task(self) -> None:
        """Main method to process the editing task"""
        if "task" not in self.context:
            raise ValueError("Context file must contain a 'task' object")
        
        task = self.context["task"]
        task_type = task.get("type")
        
        if task_type != "script_improvement":
            raise ValueError(f"Unsupported task type: {task_type}")
        
        # Validate Git configuration before proceeding with API calls
        self._validate_git_config()
        
        # Sync with remote branch if working on existing branch
        if 'branch' in task:
            branch_name = task['branch']
            
            # Check if branch exists locally or remotely
            try:
                if branch_name in self.repo.heads:
                    # Branch exists locally, checkout and pull
                    logger.info(f"Checking out existing branch: {branch_name}")
                    self.repo.git.checkout(branch_name)
                    self._pull_latest_changes(branch_name)
                else:
                    # Check if branch exists remotely
                    try:
                        remote_refs = self.repo.git.ls_remote('--heads', 'origin', branch_name).strip()
                        if remote_refs:
                            # Branch exists remotely but not locally, create tracking branch
                            logger.info(f"Branch {branch_name} exists remotely, creating tracking branch")
                            self.repo.git.checkout('-b', branch_name, f'origin/{branch_name}')
                        else:
                            # Branch doesn't exist anywhere, create new branch
                            logger.info(f"Creating new branch: {branch_name}")
                            self.repo.git.checkout('-b', branch_name)
                    except git.GitCommandError:
                        # Error checking remote, assume branch doesn't exist
                        logger.info(f"Creating new branch: {branch_name}")
                        self.repo.git.checkout('-b', branch_name)
            except git.GitCommandError as e:
                logger.error(f"Error working with branch {branch_name}: {e}")
                raise
        
        # Get list of files to modify
        files_to_modify = self._get_files_to_modify(task)
        
        # Process each file
        for file_path in files_to_modify:
            self._process_file(file_path, task)
        
        # Commit changes
        self._commit_changes(task)
    
    def _get_files_to_modify(self, task: Dict) -> List[Path]:
        """Get list of files to modify from task"""
        if "files" not in task:
            raise ValueError("Task must specify 'files' to modify")
        
        files = []
        for file_pattern in task["files"]:
            # Handle both relative and absolute paths
            if os.path.isabs(file_pattern):
                pattern = file_pattern
            else:
                pattern = os.path.join(self.repo_path, file_pattern)
            
            # Expand glob patterns
            for file_path in glob.glob(pattern):
                files.append(Path(file_path))
        
        if not files:
            raise ValueError(f"No files found matching patterns: {task['files']}")
        
        return files
    

    
    def _process_file(self, file_path: Path, task: Dict) -> None:
        """Process a single file with AI"""
        logger.info(f"Processing file: {file_path.relative_to(self.repo_path)}")
        
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Prepare AI prompt
        prompt = self._prepare_prompt(file_path, content, task)
        
        # Send to AI API
        modified_content = self._call_ai_api(prompt, file_path)
        
        # Update file if content changed
        if modified_content != content:
            logger.info(f"Updating file: {file_path.relative_to(self.repo_path)}")
            with open(file_path, 'w') as f:
                f.write(modified_content)
        else:
            logger.info(f"No changes needed for: {file_path.relative_to(self.repo_path)}")
    
    def _prepare_prompt(self, file_path: Path, content: str, task: Dict) -> str:
        """Prepare the prompt for AI API"""
        # Extract file extension for language identification
        file_ext = file_path.suffix.lstrip('.')
        
        # Determine language based on extension
        language_map = {
            'py': 'Python',
            'js': 'JavaScript',
            'sh': 'Bash',
            'conf': 'Configuration',
            'json': 'JSON',
            'md': 'Markdown',
            'txt': 'Text',
        }
        language = language_map.get(file_ext, 'Unknown')
        
        requirements = task.get('requirements', [])
        requirements_text = "\n".join(f"- {req}" for req in requirements)
        
        validation_rules = task.get('validation_rules', [])
        validation_text = "\n".join(f"- {rule}" for rule in validation_rules)
        
        # Build the base prompt
        prompt = f"""
You are an expert developer tasked with improving the following {language} code/file.
The file path is: {file_path.relative_to(self.repo_path)}

## Requirements:
{requirements_text}
"""

        # Add specific instructions for file renaming if needed
        if any("rename" in req.lower() for req in requirements):
            prompt += """
## IMPORTANT FILE RENAME INSTRUCTIONS:
1. DO NOT modify the file content if a rename is required. The system will handle the rename separately.
2. Only modify the content according to other requirements (like POSIX newlines).
3. In your commit message, clearly mention which files need to be renamed.
"""

        prompt += f"""
## Validation Rules:
{validation_text}
"""

        # Add explanation for validation rules the AI might not understand
        if any("filename_consistency" in rule.lower() for rule in validation_rules):
            prompt += """
### NOTE: 'filename_consistency_check' means the system will verify filenames match the required names.
"""

        if any("posix_newline" in rule.lower() for rule in validation_rules):
            prompt += """
### NOTE: 'posix_newline_check' means line endings must be LF (\n), not CRLF (\r\n).
"""

        # Complete the prompt with the file content and instructions
        prompt += f"""
## Current File Content:
```{file_ext}
{content}
```

## Task:
Please improve the code according to the requirements above. Return ONLY the improved file content, nothing else.
Maintain the same overall structure and functionality unless the requirements explicitly ask for changes.
Make sure your changes satisfy all the requirements and will pass the validation rules.

If this file needs to be renamed, DO NOT attempt to rename it yourself. Only make content changes and mention rename requirements in your notes.
"""
        logger.debug(f"Generated prompt with {len(prompt)} characters")
        return prompt
    
    def _call_ai_api(self, prompt: str, file_path: Path) -> str:
        """Call the AI API with prompt and return response"""
        try:
            if self.api_type == "openai":
                return self._call_openai(prompt, file_path)
            elif self.api_type == "anthropic":
                return self._call_anthropic(prompt, file_path)
            else:
                raise ValueError(f"Unknown API type: {self.api_type}")
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
    
    def _call_openai(self, prompt: str, file_path: Path) -> str:
        """Call OpenAI API"""
        logger.info(f"Calling OpenAI API with model {self.model}")
        
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a skilled developer tasked with improving code based on requirements."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Low temperature for more deterministic results
            max_tokens=4096
        )
        
        # Extract content from response
        content = response.choices[0].message.content.strip()
        
        # Clean up code blocks if present
        if "```" in content:
            # Extract code from markdown code blocks
            lines = content.split('\n')
            in_code_block = False
            file_content = []
            
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    file_content.append(line)
            
            content = '\n'.join(file_content)
        
        logger.debug(f"Received {len(content)} characters of modified content")
        return content
    
    def _call_anthropic(self, prompt: str, file_path: Path) -> str:
        """Call Anthropic API"""
        logger.info(f"Calling Anthropic API with model {self.model}")
        
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.2,
            system="You are a skilled developer tasked with improving code based on requirements.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract content from response
        content = response.content[0].text.strip()
        
        # Clean up code blocks if present
        if "```" in content:
            # Extract code from markdown code blocks
            lines = content.split('\n')
            in_code_block = False
            file_content = []
            
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    file_content.append(line)
            
            content = '\n'.join(file_content)
        
        logger.debug(f"Received {len(content)} characters of modified content")
        return content
    
    def _pull_latest_changes(self, branch_name: str) -> bool:
        """Pull latest changes from remote for the given branch
        
        Args:
            branch_name: The branch name to pull changes for
            
        Returns:
            bool: True if pull was successful, False otherwise
        """
        try:
            logger.info(f"Pulling latest changes for branch: {branch_name}")
            
            # Use GitHub token for authentication if available
            if os.environ.get("GITHUB_TOKEN"):
                remote_url = self.repo.remotes.origin.url
                if remote_url.startswith("https://github.com"):
                    auth_remote = remote_url.replace("https://", f"https://{os.environ['GITHUB_TOKEN']}@")
                    self.repo.git.pull(auth_remote, branch_name)
                else:
                    self.repo.git.pull("origin", branch_name)
            else:
                self.repo.git.pull("origin", branch_name)
                
            logger.info(f"Successfully pulled latest changes from origin/{branch_name}")
            return True
        except git.GitCommandError as e:
            # Handle merge conflicts if AUTO_MERGE enabled
            if os.environ.get("AUTO_MERGE", "true").lower() in ["true", "1", "yes"]:
                try:
                    logger.warning(f"Merge conflict detected, attempting auto-merge")
                    self.repo.git.config('pull.rebase', 'false')  # Use merge strategy
                    self.repo.git.pull("--no-edit")  # Auto-merge with default message
                    logger.info("Auto-merge successful")
                    return True
                except git.GitCommandError as merge_err:
                    logger.error(f"Auto-merge failed: {merge_err}")
                    return False
            else:
                logger.error(f"Error pulling from remote: {e}")
                return False

    def _push_to_remote(self, branch_name: str, force: bool = False) -> bool:
        """Push changes to remote repository
        
        Args:
            branch_name: The branch name to push
            force: Whether to use force push
            
        Returns:
            bool: True if push was successful, False otherwise
        """
        try:
            # Check if we have credentials configured
            if os.environ.get("GITHUB_TOKEN"):
                # Get the remote URL
                remote_url = self.repo.remotes.origin.url
                # Check if it's a GitHub URL and insert the token
                if remote_url.startswith("https://github.com"):
                    auth_remote = remote_url.replace("https://", f"https://{os.environ['GITHUB_TOKEN']}@")
                    logger.info("Using authenticated remote URL for push")
                    if force:
                        self.repo.git.push(auth_remote, branch_name, force=True)
                        logger.warning("Force push used - this may overwrite changes on the remote")
                    else:
                        self.repo.git.push(auth_remote, branch_name)
                else:
                    if force:
                        self.repo.git.push("origin", branch_name, force=True)
                        logger.warning("Force push used - this may overwrite changes on the remote")
                    else:
                        self.repo.git.push("origin", branch_name)
                
                logger.info(f"Successfully pushed to remote: origin/{branch_name}")
                return True
            else:
                logger.error("GITHUB_TOKEN not set, cannot push to remote. Set GITHUB_TOKEN environment variable.")
                return False
        except git.GitCommandError as e:
            logger.error(f"Error pushing to remote: {e}")
            logger.error("Hint: You might need to set up authentication or check repository permissions.")
            return False

    def _commit_changes(self, task: Dict) -> None:
        """Commit changes to the repository"""
        # Check if there are changes to commit
        if not self.repo.is_dirty():
            logger.info("No changes to commit")
            return
        
        logger.info("Committing changes to repository")
        
        # Get list of changed files
        changed_files = [item.a_path for item in self.repo.index.diff(None)]
        logger.info(f"Changed files: {', '.join(changed_files)}")
        
        # Add all changes
        self.repo.git.add('--all')
        
        # Create detailed commit message
        task_type = task.get('type', 'Unknown').replace('_', ' ').title()
        changed_files_list = ', '.join([Path(f).name for f in changed_files])
        
        # Generate a more specific commit title
        commit_title = f"DevOpsZealot: {task_type} - "
        
        # Add key improvement areas to title based on requirements
        key_areas = []
        for req in task.get('requirements', [])[:2]:  # Use first 2 requirements for title
            # Extract key phrases for title
            key_phrase = req.split(' ', 4)[0:3]  # Take first 3 words
            key_areas.append(' '.join(key_phrase) + '...')
        
        commit_title += ", ".join(key_areas) if key_areas else f"Updates to {changed_files_list}"
        
        # Create detailed message body
        commit_msg = f"{commit_title}\n\n"
        commit_msg += f"Files modified: {changed_files_list}\n\n"
        commit_msg += f"## Changes Summary\n"
        commit_msg += f"This commit implements improvements to the {task_type.lower()} as specified in the requirements.\n\n"
        commit_msg += f"## Requirements Implemented\n"
        for req in task.get('requirements', []):
            commit_msg += f"- {req}\n"
        
        # Add validation information if available
        if task.get('validation_rules'):
            commit_msg += f"\n## Validation\n"
            commit_msg += f"Changes have been validated against:\n"
            for rule in task.get('validation_rules', []):
                commit_msg += f"- {rule}\n"
        
        # Commit changes
        self.repo.git.commit('-m', commit_msg)
        logger.info(f"Changes committed with message:\n{commit_msg}")
        
        # Get branch name from task
        branch_name = task.get('branch', self.repo.active_branch.name)
                
        # Push changes to remote by default (only skip if explicitly disabled)
        if os.environ.get("DISABLE_PUSH_TO_REMOTE", "").lower() not in ["true", "1", "yes"]:
            logger.info("Pushing changes to remote repository")
            
            # Try normal push first
            push_success = self._push_to_remote(branch_name)
            
            # If push fails and PULL_BEFORE_PUSH is enabled, try pull and push again
            if not push_success and os.environ.get("PULL_BEFORE_PUSH", "true").lower() in ["true", "1", "yes"]:
                logger.info("Push failed, attempting pull-then-push workflow")
                
                # Stash any uncommitted changes (safety measure)
                has_changes = False
                if self.repo.is_dirty():
                    logger.info("Stashing uncommitted changes")
                    self.repo.git.stash('save', 'Automatic stash before pull')
                    has_changes = True
                
                # Pull latest changes
                pull_success = self._pull_latest_changes(branch_name)
                
                if pull_success:
                    # Try push again after successful pull
                    push_success = self._push_to_remote(branch_name)
                
                # If regular push still fails, try force push if enabled
                if not push_success and os.environ.get("FORCE_PUSH", "false").lower() in ["true", "1", "yes"]:
                    logger.warning("Regular push failed after pull, attempting force push")
                    push_success = self._push_to_remote(branch_name, force=True)
                
                # Pop stashed changes if any
                if has_changes:
                    try:
                        logger.info("Applying stashed changes")
                        self.repo.git.stash('pop')
                    except git.GitCommandError as e:
                        logger.error(f"Error applying stashed changes: {e}")
            
            # If all push attempts failed
            if not push_success:
                logger.error("All push attempts failed. Local changes are committed but not pushed.")
                logger.info("You may need to manually push with: git push origin " + branch_name)
        else:
            logger.info("Push to remote disabled by DISABLE_PUSH_TO_REMOTE environment variable")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='AI File Editor for DevOpsZealot')
    
    parser.add_argument('--repo', required=True,
                        help='Path to the repository to modify')
    parser.add_argument('--context', required=True,
                        help='Path to the JSON context file')
    parser.add_argument('--api', choices=['openai', 'anthropic'], default='openai',
                        help='AI API to use (default: openai)')
    parser.add_argument('--model', default='gpt-4',
                        help='AI model to use (default: gpt-4)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        editor = AIFileEditor(
            repo_path=args.repo,
            context_file=args.context,
            api_type=args.api,
            model=args.model,
            verbose=args.verbose
        )
        
        editor.process_task()
        logger.info("Task completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
