#!/usr/bin/env python3
"""
Test script for the new commit message format in AIFileEditor
"""

import os
import sys
import json
import tempfile
import git
from pathlib import Path

# Add the current directory to the path so we can import the AIFileEditor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_file_editor import AIFileEditor

def create_test_repo():
    """Create a test repository with a sample file"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Initialize git repo
    repo = git.Repo.init(repo_path)
    
    # Create a sample file
    test_file = repo_path / "test.sh"
    with open(test_file, 'w') as f:
        f.write('#!/bin/bash\necho "Hello World"\n')
    
    # Configure git user
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    
    # Add and commit the file
    repo.git.add(test_file)
    repo.git.commit('-m', 'Initial commit')
    
    return repo_path, test_file

def create_test_context(repo_path, test_file):
    """Create a test context file"""
    context = {
        "task": {
            "type": "script_improvement",
            "repository": str(repo_path),
            "branch": "test-improvements",
            "files": [
                str(test_file.relative_to(repo_path))
            ],
            "requirements": [
                "Add better error handling to the script",
                "Improve script documentation with comments",
                "Add command line arguments support"
            ],
            "validation_rules": [
                "shellcheck",
                "script_execution_test"
            ]
        },
        "config": {
            "ai_model": "gpt-4",
            "verbose_logging": True
        }
    }
    
    context_file = repo_path / "context.json"
    with open(context_file, 'w') as f:
        json.dump(context, f, indent=2)
    
    return context_file

def simulate_file_changes(test_file):
    """Simulate changes to the test file that would be done by the AI"""
    with open(test_file, 'w') as f:
        f.write('''#!/bin/bash
# Improved test script with better error handling and command line support
# Usage: ./test.sh [message]

# Exit on error
set -e

# Default message
MESSAGE="Hello World"

# Process command line arguments
if [ $# -gt 0 ]; then
    MESSAGE="$1"
fi

# Display message
echo "$MESSAGE"

exit 0
''')

def main():
    # Create test repository
    print("Creating test repository...")
    repo_path, test_file = create_test_repo()
    print(f"Test repository created at: {repo_path}")
    
    # Create test context
    context_file = create_test_context(repo_path, test_file)
    print(f"Test context created at: {context_file}")
    
    # Initialize the AIFileEditor but don't call the AI API
    print("Initializing AIFileEditor...")
    editor = AIFileEditor(
        repo_path=str(repo_path),
        context_file=str(context_file),
        api_type="openai",
        model="gpt-4",
        verbose=True
    )
    
    # We'll simulate the AI making changes to the file
    print("Simulating file changes...")
    simulate_file_changes(test_file)
    
    # Get the repository and check if it's dirty
    repo = git.Repo(repo_path)
    if not repo.is_dirty():
        print("No changes detected in the repository.")
        return 1
    
    # Get the context task
    task = editor.context["task"]
    
    # Get list of changed files
    changed_files = [item.a_path for item in repo.index.diff(None)]
    print(f"Changed files: {', '.join(changed_files)}")
    
    # Add all changes
    repo.git.add('--all')
    
    # Call the _commit_changes method to test our new commit message format
    print("Committing changes with new message format...")
    editor._commit_changes(task)
    
    # Show the commit message
    print("\nCommit created with message:")
    print("=" * 60)
    commit = next(repo.iter_commits())
    print(commit.message)
    print("=" * 60)
    
    print(f"\nTest completed successfully!")
    print(f"You can inspect the repository at: {repo_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
