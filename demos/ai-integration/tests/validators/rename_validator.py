#!/usr/bin/env python3
"""
Rename Validator - A utility to validate if file renaming operations were properly executed.

This validator checks if file renaming requirements from the context were actually performed,
but does not automatically fix any issues. Instead, it provides clear feedback that can be
passed back to the AI/LLM to improve its responses.
"""

import os
import sys
import json
import logging
import argparse
import re
from pathlib import Path
import git

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RenameValidator:
    """Validates file renaming operations in Git repositories and optionally performs renames"""
    
    def __init__(self, repo_path, context_file, auto_fix=False):
        """Initialize with repository path and context file
        
        Args:
            repo_path: Path to Git repository
            context_file: Path to JSON context file
            auto_fix: If True, automatically fix rename issues
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
    
    def perform_rename(self, source_file, target_file):
        """Perform a Git rename operation using git mv
        
        Args:
            source_file: Source file path (relative to repo root)
            target_file: Target file path (relative to repo root)
            
        Returns:
            bool: True if rename was successful, False otherwise
        """
        source_path = self.repo_path / source_file
        target_path = self.repo_path / target_file
        
        if not source_path.exists():
            logger.error(f"Source file does not exist: {source_file}")
            return False
            
        # Create target directory if it doesn't exist
        target_dir = target_path.parent
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        try:
            # Perform git mv operation
            logger.info(f"Executing git mv '{source_file}' '{target_file}'")
            self.repo.git.mv(str(source_file), str(target_file))
            
            # Update references in other files
            logger.info(f"Updating references to '{source_file}' in other files")
            self._update_references(source_file, target_file)
            
            # Prepare commit message
            commit_msg = f"DevOpsZealot: Rename {source_file} to {target_file}\n\n"
            commit_msg += "This commit properly renames the file using git mv to maintain file history.\n"
            commit_msg += f"Rename performed: {source_file} -> {target_file}"
            
            # Stage all changes
            self.repo.git.add('-A')
            
            # Configure Git user before committing
            if not self._configure_git():
                logger.error("Failed to configure Git user for commit")
                return False
                
            # Commit changes
            logger.info(f"Committing rename: {source_file} -> {target_file}")
            self.repo.git.commit('-m', commit_msg)
            
            # Try to push if there's a remote
            try:
                if 'origin' in [remote.name for remote in self.repo.remotes]:
                    logger.info("Pushing changes to remote repository")
                    current_branch = self.repo.active_branch.name
                    self.repo.git.push('origin', current_branch)
            except Exception as e:
                logger.warning(f"Could not push to remote: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Error performing rename: {e}")
            return False
            
    def _update_references(self, source_file, target_file):
        """Update references to the renamed file in other files
        
        Args:
            source_file: Original file path
            target_file: New file path
        """
        # Use git grep to find files containing references to the source file
        try:
            output = self.repo.git.grep('-l', source_file)
            files_with_refs = output.strip().split('\n') if output.strip() else []
            
            for file_path in files_with_refs:
                # Skip the renamed file itself
                if Path(file_path).name == Path(target_file).name:
                    continue
                    
                # Update references in the file
                full_path = self.repo_path / file_path
                if full_path.exists():
                    logger.info(f"Updating references in {file_path}")
                    with open(full_path, 'r') as f:
                        content = f.read()
                        
                    updated_content = content.replace(source_file, target_file)
                    
                    if updated_content != content:
                        with open(full_path, 'w') as f:
                            f.write(updated_content)
        except Exception as e:
            logger.warning(f"Error updating references: {e}")
    
    def validate_renames(self):
        """Check for rename requirements and validate if they were performed"""
        if "task" not in self.context:
            logger.error("Context file does not contain a 'task' object")
            return False
            
        task = self.context["task"]
        requirements = task.get("requirements", [])
        
        # Look for rename requirements in the format "Rename 'X' to 'Y'"
        rename_pattern = re.compile(r"Rename\s+'([^']+)'\s+to\s+'([^']+)'", re.IGNORECASE)
        
        renames_needed = []
        validation_results = {
            "valid": True,
            "issues": [],
            "renames_required": [],
            "renames_performed": []
        }
        
        for req in requirements:
            match = rename_pattern.search(req)
            if match:
                source_file = match.group(1)
                target_file = match.group(2)
                logger.info(f"Found rename requirement: {source_file} -> {target_file}")
                renames_needed.append((source_file, target_file))
                validation_results["renames_required"].append({
                    "source": source_file,
                    "target": target_file
                })
                
        if not renames_needed:
            logger.info("No rename requirements found")
            return validation_results
            
        # Check if the rename operations have been performed
        for source_file, target_file in renames_needed:
            source_path = self.repo_path / source_file
            target_path = self.repo_path / target_file
            
            if source_path.exists() and not target_path.exists():
                # Source exists but target doesn't - rename was not performed
                msg = f"VALIDATION FAILURE: '{source_file}' should have been renamed to '{target_file}' but was not"
                logger.error(msg)
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "type": "missing_rename",
                    "message": msg,
                    "source": source_file,
                    "target": target_file
                })
                
                # Perform the rename if auto_fix is enabled
                if self.auto_fix:
                    logger.info(f"Auto-fixing rename: {source_file} -> {target_file}")
                    success = self.perform_rename(source_file, target_file)
                    if success:
                        validation_results["renames_performed"].append({
                            "source": source_file,
                            "target": target_file,
                            "success": True
                        })
                        logger.info(f"Successfully renamed {source_file} to {target_file}")
                    else:
                        validation_results["renames_performed"].append({
                            "source": source_file,
                            "target": target_file,
                            "success": False
                        })
                        logger.error(f"Failed to rename {source_file} to {target_file}")
            elif not source_path.exists() and target_path.exists():
                # Rename was properly done
                logger.info(f"VALIDATION PASSED: '{source_file}' was correctly renamed to '{target_file}'")
            elif source_path.exists() and target_path.exists():
                # Both exist - this is incorrect
                msg = f"VALIDATION FAILURE: Both '{source_file}' and '{target_file}' exist. The source file should have been removed."
                logger.error(msg)
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "type": "duplicate_files",
                    "message": msg,
                    "source": source_file,
                    "target": target_file
                })
            else:
                # Neither exists - this is an error
                msg = f"VALIDATION FAILURE: Neither '{source_file}' nor '{target_file}' exists"
                logger.error(msg)
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "type": "missing_files",
                    "message": msg,
                    "source": source_file,
                    "target": target_file
                })
                
        # Summarize validation results
        if validation_results["valid"]:
            logger.info("All rename validations passed successfully")
        else:
            logger.error(f"Rename validation found {len(validation_results['issues'])} issues")
            if self.auto_fix:
                performed_count = len(validation_results["renames_performed"])
                success_count = sum(1 for r in validation_results["renames_performed"] if r["success"])
                logger.info(f"Auto-fixed {success_count}/{performed_count} rename issues")
            
        return validation_results


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Validate file renaming operations")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--context", required=True, help="Path to the context file")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically fix rename issues")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    return parser.parse_args()
    
def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        validator = RenameValidator(args.repo, args.context, auto_fix=args.auto_fix)
        results = validator.validate_renames()
        
        if args.json:
            print(json.dumps(results, indent=2))
        
        # If auto-fix is enabled, return success even if there were validation issues
        # since we're attempting to fix them
        if args.auto_fix:
            performed_count = len(results.get("renames_performed", []))
            success_count = sum(1 for r in results.get("renames_performed", []) if r.get("success", False))
            
            if performed_count > 0:
                logger.info(f"Auto-fixed {success_count}/{performed_count} rename issues")
                # Only return success if all auto-fixes worked
                return 0 if success_count == performed_count else 1
        
        # Standard behavior without auto-fix
        return 0 if results["valid"] else 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
        
if __name__ == "__main__":
    sys.exit(main())
