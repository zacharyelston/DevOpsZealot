#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from git_worker import GitWorker
from ai_worker import AIWorker
from redmine_worker import RedmineWorker

def main():
    """Main entry point for container job execution."""
    try:
        # Load job configuration
        config_path = "/workspace/job_data/job_config.json"
        if not os.path.exists(config_path):
            log_error("Job configuration file not found")
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        job_id = config.get("job_id", "unknown")
        log_info(f"Starting job {job_id}")
        
        # Initialize workers
        git_worker = GitWorker()
        ai_worker = AIWorker()
        redmine_worker = None
        
        # Initialize Redmine worker if credentials available
        redmine_url = os.getenv("REDMINE_URL")
        redmine_api_key = os.getenv("REDMINE_API_KEY")
        if redmine_url and redmine_api_key:
            redmine_worker = RedmineWorker(redmine_url, api_key=redmine_api_key)
        
        # Execute job workflow
        results = execute_job(config, git_worker, ai_worker, redmine_worker)
        
        # Save results
        results_path = "/workspace/job_data/results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        if results.get("success", False):
            log_info(f"Job {job_id} completed successfully")
            sys.exit(0)
        else:
            log_error(f"Job {job_id} failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")
        sys.exit(1)

def execute_job(config, git_worker, ai_worker, redmine_worker):
    """Execute the complete job workflow."""
    results = {
        "job_id": config["job_id"],
        "success": False,
        "files_modified": [],
        "commit_hash": None,
        "error": None,
        "logs": []
    }
    
    try:
        # Step 0: Add Redmine start comment if applicable
        redmine_issue_id = config.get("redmine_issue_id")
        if redmine_issue_id and redmine_worker and redmine_worker.is_connected():
            log_info(f"Adding start comment to Redmine issue #{redmine_issue_id}...")
            redmine_worker.add_job_start_comment(
                redmine_issue_id,
                config["job_id"],
                config["repo_url"],
                config["branch_name"]
            )
            results["logs"].append(f"Added start comment to Redmine issue #{redmine_issue_id}")
        
        # Step 1: Clone repository
        log_info("Cloning repository...")
        repo_path = git_worker.clone_repository(
            config["repo_url"],
            config.get("auth")
        )
        results["logs"].append("Repository cloned successfully")
        
        # Step 2: Create working branch
        log_info(f"Creating branch {config['branch_name']}...")
        git_worker.create_branch(
            config["branch_name"],
            config.get("base_branch", "main")
        )
        results["logs"].append(f"Branch {config['branch_name']} created")
        
        # Step 3: Find files to modify
        log_info("Finding files to modify...")
        target_files = git_worker.find_files(config.get("file_patterns", ["*.py"]))
        results["logs"].append(f"Found {len(target_files)} files to analyze")
        
        if not target_files:
            results["error"] = "No files found matching the specified patterns"
            return results
        
        # Step 4: Process files with AI
        log_info(f"Processing {len(target_files)} files with AI...")
        modified_files = []
        
        for file_path in target_files:
            try:
                log_info(f"Processing {file_path}...")
                
                # Read current content
                current_content = git_worker.read_file(file_path)
                
                # Get AI modifications
                modified_content = ai_worker.modify_code(
                    file_path=file_path,
                    current_content=current_content,
                    prompt=config["prompt"],
                    context=config.get("context", "")
                )
                
                # Check if content actually changed
                if modified_content and modified_content != current_content:
                    # Write modified content
                    git_worker.write_file(file_path, modified_content)
                    modified_files.append(file_path)
                    results["logs"].append(f"Modified {file_path}")
                else:
                    results["logs"].append(f"No changes needed for {file_path}")
                    
            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                log_error(error_msg)
                results["logs"].append(error_msg)
        
        results["files_modified"] = modified_files
        
        if not modified_files:
            results["error"] = "No files were modified by the AI"
            return results
        
        # Step 5: Commit changes
        log_info("Committing changes...")
        commit_message = f"AI modifications: {config['prompt'][:100]}..."
        commit_hash = git_worker.commit_changes(
            message=commit_message,
            author_name="AI Code Modifier",
            author_email="ai@codemodifier.com"
        )
        results["commit_hash"] = commit_hash
        results["logs"].append(f"Changes committed: {commit_hash}")
        
        # Step 6: Push changes
        log_info("Pushing changes...")
        git_worker.push_changes()
        results["logs"].append("Changes pushed to remote repository")
        
        # Step 7: Add Redmine completion comment if applicable
        if redmine_issue_id and redmine_worker and redmine_worker.is_connected():
            log_info(f"Adding completion comment to Redmine issue #{redmine_issue_id}...")
            redmine_worker.add_completion_comment(
                redmine_issue_id,
                config["job_id"],
                commit_hash,
                modified_files
            )
            results["logs"].append(f"Added completion comment to Redmine issue #{redmine_issue_id}")
        
        results["success"] = True
        log_info("Job completed successfully")
        
    except Exception as e:
        error_msg = f"Job execution failed: {str(e)}"
        log_error(error_msg)
        results["error"] = error_msg
        results["logs"].append(error_msg)
    
    return results

def log_info(message):
    """Log info message."""
    print(f"[INFO] {message}")

def log_error(message):
    """Log error message."""
    print(f"[ERROR] {message}", file=sys.stderr)

if __name__ == "__main__":
    main()