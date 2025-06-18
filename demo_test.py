#!/usr/bin/env python3
"""
Demo script to test the container orchestration system without Docker.
This simulates the container workflow for testing purposes.
"""

import json
import tempfile
import os
from pathlib import Path
from container_manager import ContainerManager

def create_test_repo():
    """Create a temporary test repository with sample Python files."""
    repo_dir = tempfile.mkdtemp(prefix="test_repo_")
    
    # Create sample Python files
    sample_files = {
        "main.py": '''def hello_world():
    print("Hello, World!")

def add_numbers(a, b):
    return a + b

if __name__ == "__main__":
    hello_world()
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")
''',
        "utils.py": '''def validate_input(value):
    if value is None:
        return False
    return True

def format_output(data):
    return str(data)
''',
        "config.py": '''DATABASE_URL = "sqlite:///app.db"
DEBUG = True
SECRET_KEY = "dev-key"
'''
    }
    
    for filename, content in sample_files.items():
        file_path = Path(repo_dir) / filename
        with open(file_path, 'w') as f:
            f.write(content)
    
    print(f"Created test repository at: {repo_dir}")
    return repo_dir

def demo_container_manager():
    """Demonstrate the container manager functionality."""
    print("=== AI Git Container Orchestrator Demo ===\n")
    
    # Initialize container manager
    manager = ContainerManager()
    
    # Create a demo job configuration
    print("1. Creating job configuration...")
    config = manager.create_container_config(
        repo_url="https://github.com/example/test-repo.git",
        branch_name="ai-demo-modifications",
        base_branch="main",
        prompt="Add error handling and input validation to all functions",
        context="This is a Python web application with database connectivity",
        file_patterns=["*.py"],
        auth_username=None,
        auth_token=None
    )
    
    print(f"✓ Job created with ID: {config['job_id']}")
    print(f"  Repository: {config['repo_url']}")
    print(f"  Branch: {config['branch_name']}")
    print(f"  Patterns: {config['file_patterns']}")
    
    # Show job configuration
    print("\n2. Job Configuration:")
    print(json.dumps({
        "job_id": config["job_id"],
        "repo_url": config["repo_url"],
        "branch_name": config["branch_name"],
        "base_branch": config["base_branch"],
        "file_patterns": config["file_patterns"],
        "prompt": config["prompt"][:100] + "..."
    }, indent=2))
    
    # Simulate container launch (would normally use Docker)
    print(f"\n3. Container launch simulation...")
    print(f"   Command would be: docker run --rm -d git-ai-modifier:latest")
    print(f"   Container ID: mock-container-{config['job_id']}")
    
    # Show what the container would do
    print(f"\n4. Container workflow simulation:")
    print(f"   ✓ Clone repository: {config['repo_url']}")
    print(f"   ✓ Create branch: {config['branch_name']}")
    print(f"   ✓ Find files matching: {config['file_patterns']}")
    print(f"   ✓ Process files with AI prompt")
    print(f"   ✓ Commit changes")
    print(f"   ✓ Push to remote")
    
    # List jobs
    print(f"\n5. Job listing:")
    jobs = manager.list_jobs()
    for job_id, job_info in jobs.items():
        print(f"   Job {job_id}:")
        print(f"     Status: {job_info['status']}")
        print(f"     Repository: {job_info['repo_url']}")
        print(f"     Branch: {job_info['branch_name']}")
    
    print(f"\n=== Demo Complete ===")
    print(f"To use the full system:")
    print(f"1. Build container: ./build_container.sh")
    print(f"2. Start Streamlit: streamlit run app.py --server.port 5000")
    print(f"3. Configure jobs through the web interface")

if __name__ == "__main__":
    demo_container_manager()