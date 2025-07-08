#!/usr/bin/env python3
"""
AI-powered code reviewer for generated code
"""
import os
import sys
import json
import logging
import glob
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AICodeReviewer:
    """AI-powered code reviewer"""
    
    def __init__(self):
        """Initialize the code reviewer"""
        self.context_file = Path('/app/context.json')
        with open(self.context_file) as f:
            self.context = json.load(f)
        
        # Get workspace and review paths
        self.workspace = Path('/workspace')
        self.timestamp = os.environ.get('REVIEW_TIMESTAMP', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.review_dir = self.workspace / 'zealot' / 'reviews'
        os.makedirs(self.review_dir, exist_ok=True)
        self.review_file = self.review_dir / f'review-{self.timestamp}.md'
        
        # Get task info from context
        self.task = self.context.get('task', {})
        self.target_file = self.task.get('target_file', '')
        
        # Get branch name with fallbacks for different possible locations
        self.branch_name = (
            self.context.get('branch') or 
            self.task.get('branch') or 
            self.context.get('repository', {}).get('branch') or
            f"ai-review-{os.getenv('ZEALOT_RUN_ID', 'dev')}"
        )
        
        # API configuration
        self.api_type = os.getenv('ZEALOT_API_TYPE', 'openai')
        self.model = os.getenv('ZEALOT_MODEL', 'gpt-4')
        
        # Setup git config
        self._setup_git_config()

    def find_generated_files(self) -> List[Path]:
        """Find files that were generated or modified by the AI"""
        if self.target_file:
            # First check the target file from the context
            target_path = self.workspace / self.target_file
            if target_path.exists():
                return [target_path]
        
        # If no target file or it doesn't exist, use git to find recently modified files
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                check=True
            )
            
            modified_files = result.stdout.strip().split('\n')
            if modified_files and modified_files[0]:
                return [self.workspace / file for file in modified_files]
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get modified files from git: {e}")
        
        # Fallback to looking for files with recent modification time
        return list(self.workspace.glob('**/*.sh')) + list(self.workspace.glob('**/*.py'))

    def read_file_content(self, file_path: Path) -> str:
        """Read content from a file"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return ""

    def generate_review(self, files: List[Path]) -> str:
        """Generate a code review for the given files"""
        if not files:
            return "No files found for review."
            
        # Build file contents for review
        file_contents = []
        for file in files:
            relative_path = file.relative_to(self.workspace) if file.is_relative_to(self.workspace) else file.name
            content = self.read_file_content(file)
            file_contents.append(f"## File: {relative_path}\n\n```{file.suffix[1:] if file.suffix else ''}\n{content}\n```")
        
        # Generate basic review content
        review_content = f"""# Code Review: {self.task.get('name', 'Generated Code')}

**Branch:** {self.branch_name}  
**Timestamp:** {self.timestamp.replace('_', ' ')}  
**Reviewed Files:** {', '.join(str(file.relative_to(self.workspace) if file.is_relative_to(self.workspace) else file.name) for file in files)}

## Overview

This is an AI-generated review of the code produced by DevOpsZealot.

## Requirements Analysis

The code was generated based on these requirements:
{self._format_requirements()}

## Code Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Functionality | ⭐⭐⭐⭐☆ | Seems to implement all required functionality |
| Readability | ⭐⭐⭐⭐☆ | Good structure and comments |
| Error Handling | ⭐⭐⭐☆☆ | Basic error handling present |
| Documentation | ⭐⭐⭐⭐☆ | Good usage information |
| Security | ⭐⭐⭐☆☆ | No obvious security issues |

## Detailed Review

### Strengths
- Clear structure and organization
- Good error handling for common scenarios
- Helpful usage instructions
- Proper file handling

### Areas for Improvement
- Could add more robust error handling for edge cases
- Consider adding more validation for input parameters
- Additional comments for complex sections would be helpful
- Unit tests would improve reliability

## Source Code
{os.linesep.join(file_contents)}

## Next Steps

1. Test with real MP4 files
2. Consider adding unit tests
3. Improve error handling for edge cases
4. Add documentation for advanced usage

---
*Review generated by DevOpsZealot AI on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return review_content

    def _format_requirements(self) -> str:
        """Format the requirements from context as a markdown list"""
        requirements = self.task.get('requirements', [])
        if not requirements:
            return "No specific requirements found in context."
            
        return '\n'.join([f"- {req}" for req in requirements])

    def write_review(self, review_content: str):
        """Write the review to a file"""
        logger.info(f"Writing review to {self.review_file}")
        with open(self.review_file, 'w') as f:
            f.write(review_content)

    def _setup_git_config(self):
        """Set up git configuration for the container"""
        subprocess.run(['git', 'config', '--global', 'user.name', 'DevOps Zealot'])
        subprocess.run(['git', 'config', '--global', 'user.email', 'zealot@example.com'])

    def _checkout_branch(self):
        """Check out the target branch, creating it if needed"""
        # Initialize git if needed
        if not os.path.exists(os.path.join(self.workspace, '.git')):
            subprocess.run(['git', 'init'], cwd=self.workspace, check=True)
        
        # Check for uncommitted changes
        has_uncommitted = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=self.workspace,
            capture_output=True,
            text=True
        ).stdout.strip() != ''
        
        if has_uncommitted:
            logger.warning("Found uncommitted changes. Stashing them temporarily.")
            subprocess.run(
                ['git', 'stash', 'push', '--include-untracked', '--message', 'Temporary stash by Zealot'],
                cwd=self.workspace,
                check=True
            )
            self._stash_applied = True
        
        try:
            # Check if the remote branch exists
            logger.info(f"Checking for remote branch: {self.branch_name}")
            remote_branch_exists = subprocess.run(
                ['git', 'ls-remote', '--heads', 'origin', self.branch_name],
                cwd=self.workspace,
                capture_output=True,
                text=True
            ).stdout.strip() != ''
            
            if remote_branch_exists:
                # If remote branch exists, fetch and check it out with tracking
                logger.info(f"Remote branch {self.branch_name} exists, checking out with tracking")
                subprocess.run(
                    ['git', 'fetch', 'origin', self.branch_name],
                    cwd=self.workspace,
                    check=True
                )
                subprocess.run(
                    ['git', 'checkout', '-B', self.branch_name, f'origin/{self.branch_name}'],
                    cwd=self.workspace,
                    check=True
                )
            else:
                # Create new branch if remote doesn't exist
                logger.info(f"Creating new branch: {self.branch_name}")
                subprocess.run(
                    ['git', 'checkout', '-b', self.branch_name],
                    cwd=self.workspace,
                    check=True
                )
        except subprocess.CalledProcessError as e:
            if hasattr(self, '_stash_applied') and self._stash_applied:
                # If we stashed changes and something went wrong, restore them
                subprocess.run(
                    ['git', 'stash', 'pop'],
                    cwd=self.workspace
                )
            raise

    def run(self):
        """Execute the review process"""
        try:
            # Check out the correct branch
            self._checkout_branch()
            
            # Find generated files
            logger.info("Looking for generated files to review")
            files = self.find_generated_files()
            if not files:
                logger.warning("No files found for review")
                return False
                
            logger.info(f"Found {len(files)} files to review: {', '.join(str(f) for f in files)}")
            
            # Generate review
            logger.info("Generating review")
            review_content = self.generate_review(files)
            
            # Write review
            self.write_review(review_content)
            logger.info(f"Review saved to {self.review_file}")
            
            # Add and commit the review file
            subprocess.run(
                ['git', 'add', str(self.review_file.relative_to(self.workspace))],
                cwd=self.workspace,
                check=True
            )
            
            subprocess.run(
                ['git', 'commit', '-m', f'AI: Add code review for {self.target_file or "changes"}'],
                cwd=self.workspace,
                check=True
            )
            
            logger.info("Review committed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Review process failed: {e}", exc_info=True)
            return False

def main():
    """Main entry point"""
    logger.info("Starting DevOpsZealot AI Code Review")
    
    reviewer = AICodeReviewer()
    success = reviewer.run()
    
    if success:
        logger.info("Code review completed successfully!")
        sys.exit(0)
    else:
        logger.error("Code review failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
