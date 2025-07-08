#!/usr/bin/env python3
"""
Rename Checker - A utility to validate file renaming operations for the AI integration workflow.

This script checks if file renaming was properly executed by the AI integration system
and performs any necessary fixes.

Usage:
    python rename_checker.py --repo [REPO_PATH] --context [CONTEXT_FILE]
"""

import os
import sys
import json
import logging
import argparse
import re
import git
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RenameChecker:
    """Checks and fixes file renaming operations in Git repositories"""
    
    def __init__(self, repo_path, context_file):
        """Initialize with repository path and context file"""
        self.repo_path = Path(repo_path)
        self.context_file = Path(context_file)
        self.repo = git.Repo(repo_path)
        
        # Load context
        with open(context_file, 'r') as f:
            self.context = json.load(f)
            
    def _configure_git(self):
        """Configure Git user information from environment variables"""
        try:
            # Get Git user info from environment variables or use defaults
            git_name = os.environ.get('GIT_USER_NAME', 'DevOps Zealot')
            git_email = os.environ.get('GIT_USER_EMAIL', 'zealot@example.com')
            
            # Configure Git
            logger.info(f"Configuring Git with user.name={git_name}, user.email={git_email}")
            self.repo.git.config('user.name', git_name)
            self.repo.git.config('user.email', git_email)
            return True
        except Exception as e:
            logger.error(f"Failed to configure Git: {e}")
            return False
            
    def check_and_fix_renames(self):
        """Check for rename requirements and fix if necessary"""
        if "task" not in self.context:
            logger.error("Context file does not contain a 'task' object")
            return False
            
        # Configure Git before making any changes
        if not self._configure_git():
            logger.error("Failed to configure Git, cannot proceed with rename operations")
            return False
            
        task = self.context["task"]
        requirements = task.get("requirements", [])
        
        # Look for rename requirements in the format "Rename 'X' to 'Y'"
        rename_pattern = re.compile(r"Rename\s+'([^']+)'\s+to\s+'([^']+)'", re.IGNORECASE)
        
        renames_needed = []
        for req in requirements:
            match = rename_pattern.search(req)
            if match:
                source_file = match.group(1)
                target_file = match.group(2)
                logger.info(f"Found rename requirement: {source_file} -> {target_file}")
                renames_needed.append((source_file, target_file))
                
        if not renames_needed:
            logger.info("No rename requirements found")
            return True
            
        # Check if the rename operations have been performed
        for source_file, target_file in renames_needed:
            source_path = self.repo_path / source_file
            target_path = self.repo_path / target_file
            
            if source_path.exists() and not target_path.exists():
                # Source exists but target doesn't - renaming needed
                logger.info(f"Renaming {source_file} to {target_file}")
                try:
                    # Use git mv for proper rename tracking
                    self.repo.git.mv(source_path, target_path)
                    logger.info(f"Successfully renamed {source_file} to {target_file}")
                    
                    # Update references to the renamed file in other files
                    self._update_references(source_file, target_file)
                    
                except git.GitCommandError as e:
                    logger.error(f"Failed to rename {source_file}: {e}")
                    return False
            elif not source_path.exists() and target_path.exists():
                # Rename already done
                logger.info(f"Rename already completed: {source_file} -> {target_file}")
            elif source_path.exists() and target_path.exists():
                # Both exist - this is incorrect
                logger.error(f"Both {source_file} and {target_file} exist, manual intervention needed")
                return False
            else:
                # Neither exists - this is an error
                logger.error(f"Neither {source_file} nor {target_file} exists")
                return False
                
        # Commit the rename operations
        if self.repo.is_dirty():
            commit_message = "DevOpsZealot: Fixed file renaming operations\n\n"
            commit_message += "This commit properly implements the rename operations using git mv to maintain file history.\n\n"
            commit_message += "Renames performed:\n"
            for source_file, target_file in renames_needed:
                commit_message += f"- {source_file} -> {target_file}\n"
            
            self.repo.git.add('--all')
            self.repo.git.commit('-m', commit_message)
            logger.info("Committed rename operations")
            
            # Push changes if we have the right environment
            if os.environ.get("GITHUB_TOKEN") and os.environ.get("DISABLE_PUSH_TO_REMOTE", "").lower() not in ["true", "1", "yes"]:
                try:
                    branch_name = task.get('branch', self.repo.active_branch.name)
                    remote_url = self.repo.remotes.origin.url
                    
                    if remote_url.startswith("https://github.com"):
                        auth_remote = remote_url.replace("https://", f"https://{os.environ['GITHUB_TOKEN']}@")
                        logger.info("Pushing rename fixes to remote repository")
                        self.repo.git.push(auth_remote, branch_name)
                        logger.info(f"Successfully pushed rename fixes to origin/{branch_name}")
                    else:
                        logger.info("Pushing rename fixes to remote repository")
                        self.repo.git.push("origin", branch_name)
                        logger.info(f"Successfully pushed rename fixes to origin/{branch_name}")
                except git.GitCommandError as e:
                    logger.error(f"Failed to push rename fixes: {e}")
                    return False
        
        return True
        
    def _update_references(self, old_filename, new_filename):
        """Update references to the renamed file in other files"""
        # Find all script files
        script_files = []
        for ext in ['.sh', '.py', '.md']:
            script_files.extend(list(self.repo_path.glob(f'**/*{ext}')))
            
        # Filter out the renamed files themselves
        script_files = [f for f in script_files 
                       if f.name != old_filename and f.name != new_filename]
        
        for script_file in script_files:
            try:
                with open(script_file, 'r') as f:
                    content = f.read()
                    
                # Check if the old filename is referenced
                if old_filename in content:
                    logger.info(f"Updating references in {script_file}")
                    updated_content = content.replace(old_filename, new_filename)
                    
                    with open(script_file, 'w') as f:
                        f.write(updated_content)
            except Exception as e:
                logger.warning(f"Error checking file {script_file}: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Check and fix file renaming operations")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--context", required=True, help="Path to the context file")
    return parser.parse_args()
    
def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        checker = RenameChecker(args.repo, args.context)
        success = checker.check_and_fix_renames()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
        
if __name__ == "__main__":
    sys.exit(main())
