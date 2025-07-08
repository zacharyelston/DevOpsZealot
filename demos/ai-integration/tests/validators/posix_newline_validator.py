#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSIX Newline Validator

This validator checks if files in a Git repository end with a proper newline
character as per POSIX requirements and optionally fixes the issues.

Usage:
  python posix_newline_validator.py --repo /path/to/repo --context /path/to/context.json [--auto-fix]
"""

import os
import sys
import json
import logging
import argparse
import re
from pathlib import Path
import git

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class POSIXNewlineValidator:
    """Validates and optionally fixes POSIX newline requirements in Git repositories"""
    
    def __init__(self, repo_path, context_file, auto_fix=False):
        """Initialize with repository path and context file
        
        Args:
            repo_path: Path to Git repository
            context_file: Path to JSON context file
            auto_fix: If True, automatically fix newline issues
        """
        self.repo_path = Path(repo_path)
        self.context_file = Path(context_file)
        self.repo = git.Repo(repo_path)
        self.auto_fix = auto_fix
        
        # Load context
        with open(context_file, 'r') as f:
            self.context = json.load(f)
            
    def _configure_git(self):
        """Configure Git user identity from environment variables"""
        try:
            # Try to get Git user info from environment variables
            git_user_name = os.environ.get("GIT_USER_NAME", "DevOpsZealot Bot")
            git_user_email = os.environ.get("GIT_USER_EMAIL", "bot@devopszealot.com")
            
            # Configure Git
            logger.info(f"Configuring Git user: {git_user_name} <{git_user_email}>")
            self.repo.git.config("user.name", git_user_name)
            self.repo.git.config("user.email", git_user_email)
            return True
        except Exception as e:
            logger.error(f"Failed to configure Git: {e}")
            return False
    
    def _get_target_files(self):
        """Extract target files from context requirements
        
        Returns:
            list: List of target files to check
        """
        if "task" not in self.context:
            logger.error("Context file does not contain a 'task' object")
            return []
            
        task = self.context["task"]
        requirements = task.get("requirements", [])
        
        # Look for file paths in the requirements
        target_files = []
        for req in requirements:
            # Look for POSIX newline requirements
            if "POSIX" in req and "newline" in req:
                logger.info(f"Found POSIX newline requirement: {req}")
                
            # Look for file paths in single quotes
            file_matches = re.findall(r"'([^']+\.(sh|py|js|json|md))'", req)
            for match in file_matches:
                target_files.append(match[0])
                
        # If no specific files found, try to get repo files from context
        if not target_files and "repo" in task:
            repo_info = task["repo"]
            files = repo_info.get("files", [])
            target_files = [file for file in files if file.endswith(('.sh', '.py', '.js', '.json', '.md'))]
            
        return list(set(target_files))  # Remove duplicates
    
    def check_file_newline(self, file_path):
        """Check if a file ends with a newline character
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file ends with newline, False otherwise
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False
            
        try:
            # Open in binary mode to check exact line endings
            with open(full_path, 'rb') as f:
                content = f.read()
                
            # Check if the file ends with a newline
            has_newline = content.endswith(b'\n')
            
            if has_newline:
                logger.info(f"VALIDATION PASSED: '{file_path}' ends with a newline")
            else:
                logger.error(f"VALIDATION FAILURE: '{file_path}' does not end with a newline")
                
            return has_newline
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return False
    
    def fix_file_newline(self, file_path):
        """Add a newline to the end of a file if missing
        
        Args:
            file_path: Path to the file to fix
            
        Returns:
            bool: True if fixed successfully, False otherwise
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False
            
        try:
            # Check if file already has newline
            has_newline = self.check_file_newline(file_path)
            if has_newline:
                logger.info(f"File '{file_path}' already has a newline at EOF")
                return True
                
            # Add newline
            logger.info(f"Adding newline to file: {file_path}")
            with open(full_path, 'ab') as f:
                f.write(b'\n')
                
            # Stage the change
            self.repo.git.add(str(file_path))
            
            # Configure Git user before committing
            if not self._configure_git():
                logger.error("Failed to configure Git user for commit")
                return False
                
            # Commit the change
            commit_msg = f"DevOpsZealot: Add POSIX-compliant newline to {file_path}\n\n"
            commit_msg += "Added newline character at end of file to ensure POSIX compliance."
            
            logger.info(f"Committing POSIX newline fix for: {file_path}")
            self.repo.git.commit('-m', commit_msg)
            
            # Try to push if there's a remote
            try:
                if 'origin' in [remote.name for remote in self.repo.remotes]:
                    logger.info("Pushing changes to remote repository")
                    current_branch = self.repo.active_branch.name
                    self.repo.git.push('origin', current_branch)
            except Exception as e:
                logger.warning(f"Could not push to remote: {e}")
                
            logger.info(f"Successfully added newline to '{file_path}'")
            return True
        except Exception as e:
            logger.error(f"Error fixing file {file_path}: {e}")
            return False
    
    def validate_posix_newlines(self):
        """Check for POSIX newline requirements and validate if they were met
        
        Returns:
            dict: Validation results
        """
        target_files = self._get_target_files()
        
        if not target_files:
            logger.warning("No target files found for POSIX newline validation")
            # If no specific files found, get all script files
            for ext in ['.sh', '.py', '.js']:
                for file_path in self.repo_path.glob(f"**/*{ext}"):
                    if ".git" not in str(file_path):
                        target_files.append(str(file_path.relative_to(self.repo_path)))
            
            if not target_files:
                logger.error("No files found to check for POSIX newlines")
                return {"valid": True, "message": "No files to check"}
        
        logger.info(f"Validating POSIX newlines for {len(target_files)} files")
        
        validation_results = {
            "valid": True,
            "issues": [],
            "files_checked": target_files,
            "fixes_applied": []
        }
        
        for file_path in target_files:
            has_newline = self.check_file_newline(file_path)
            
            if not has_newline:
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "file": file_path,
                    "issue": "missing_newline",
                    "message": f"File does not end with a newline: {file_path}"
                })
                
                # Fix the issue if auto_fix is enabled
                if self.auto_fix:
                    logger.info(f"Auto-fixing newline for: {file_path}")
                    success = self.fix_file_newline(file_path)
                    validation_results["fixes_applied"].append({
                        "file": file_path,
                        "success": success
                    })
        
        # Summarize validation results
        if validation_results["valid"]:
            logger.info("All files have proper POSIX-compliant newlines")
        else:
            issue_count = len(validation_results["issues"])
            logger.error(f"Found {issue_count} files with missing newlines")
            if self.auto_fix:
                fix_count = len(validation_results["fixes_applied"])
                success_count = sum(1 for fix in validation_results["fixes_applied"] if fix["success"])
                logger.info(f"Auto-fixed {success_count}/{fix_count} newline issues")
        
        return validation_results

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Validate POSIX newline requirements")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--context", required=True, help="Path to the context file")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically fix newline issues")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        validator = POSIXNewlineValidator(args.repo, args.context, auto_fix=args.auto_fix)
        results = validator.validate_posix_newlines()
        
        if args.json:
            print(json.dumps(results, indent=2))
        
        # If auto-fix is enabled, return success even if there were validation issues
        # since we're attempting to fix them
        if args.auto_fix:
            fix_count = len(results.get("fixes_applied", []))
            success_count = sum(1 for fix in results.get("fixes_applied", []) if fix.get("success", False))
            
            if fix_count > 0:
                logger.info(f"Auto-fixed {success_count}/{fix_count} newline issues")
                # Only return success if all auto-fixes worked
                return 0 if success_count == fix_count else 1
        
        # Standard behavior without auto-fix
        return 0 if results["valid"] else 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
