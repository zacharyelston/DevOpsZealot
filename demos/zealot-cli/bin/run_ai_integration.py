#!/usr/bin/env python3
"""
Docker container entrypoint for simplified Zealot AI integration
"""
import os
import sys
import json
import logging
import shutil
from pathlib import Path
import subprocess
from typing import Dict, Any, Optional, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIIntegration:
    """Simplified AI Integration controller"""
    
    def __init__(self):
        """Initialize with context from context.json"""
        self.context_file = Path('/app/context.json')
        with open(self.context_file) as f:
            self.context = json.load(f)
        
        # Set up workspace
        self.workspace = Path('/tmp/workspace')
        os.makedirs(self.workspace, exist_ok=True)
        
        # Get config from context
        self.task = self.context.get('task', {})
        self.repo_url = self.task.get('repository', '')
        if isinstance(self.repo_url, dict):
            self.repo_url = self.repo_url.get('url', '')
        
        # Get branch name with fallbacks for different possible locations
        self.branch_name = (
            self.context.get('branch') or 
            self.task.get('branch') or 
            self.context.get('repository', {}).get('branch') or
            f"ai-improvements-{os.getenv('ZEALOT_RUN_ID', 'dev')}"
        )
        
        # Model configuration
        self.api_type = os.getenv('ZEALOT_API_TYPE', 'openai')
        self.model = os.getenv('ZEALOT_MODEL', 'gpt-4')
        
        # Setup git config
        self._setup_git_config()

    def _setup_git_config(self):
        """Set up git configuration for the container"""
        subprocess.run(['git', 'config', '--global', 'user.name', 'DevOps Zealot'])
        subprocess.run(['git', 'config', '--global', 'user.email', 'zealot@example.com'])
    
    def clone_repository(self):
        """Clone the target repository"""
        logger.info(f"Cloning repository: {self.repo_url}")
        
        # Determine if it's a remote or local repository
        is_remote_repo = self.repo_url.startswith('http') or self.repo_url.startswith('git@')
        
        if is_remote_repo:
            # Set up Git credentials with GITHUB_TOKEN if available
            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token and self.repo_url.startswith('https://github.com'):
                auth_repo_url = self.repo_url.replace(
                    'https://github.com', 
                    f'https://{github_token}@github.com'
                )
            else:
                auth_repo_url = self.repo_url
                
            # Clone the repository
            logger.info(f"Cloning remote repository: {self.repo_url}")
            subprocess.run(
                ['git', 'clone', auth_repo_url, str(self.workspace)],
                check=True
            )
        else:
            # For local development, mount the repo and just pull latest
            logger.info(f"Using local repository: {self.repo_url}")
            
            # Initialize git if needed
            if not os.path.exists(os.path.join(self.workspace, '.git')):
                subprocess.run(['git', 'init'], cwd=self.workspace, check=True)
                
        # Check if the remote branch exists
        logger.info(f"Checking for remote branch: {self.branch_name}")
        remote_branch_exists = subprocess.run(
            ['git', 'ls-remote', '--heads', 'origin', self.branch_name],
            cwd=self.workspace,
            capture_output=True,
            text=True
        ).stdout.strip() != ''
        
        if remote_branch_exists:
            # If remote branch exists, check it out with tracking
            logger.info(f"Remote branch {self.branch_name} exists, checking out with tracking")
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
    
    def initialize_ai_editor(self):
        """Initialize the AI File Editor"""
        # This would be a good place to integrate with your existing AIFileEditor class
        # For now, we'll just simulate it with a placeholder
        logger.info(f"Initializing AI File Editor with {self.api_type} API")
        logger.info(f"Target repository: {self.workspace}")
        logger.info(f"Using AI model: {self.model}")
    
    def process_task(self):
        """Process the task by generating code based on context"""
        # This is where the main AI processing would happen
        # For this demo, we'll just create a minimal script based on the task requirements
        
        target_file = self.task.get('target_file', 'output.sh')
        file_path = self.workspace / target_file
        
        logger.info(f"Generating file: {target_file}")
        
        # Generate script content based on requirements
        requirements = self.task.get('requirements', [])
        dependencies = self.task.get('dependencies', [])
        description = self.task.get('description', 'AI-generated script')
        
        # Create parent directories if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create the script
        with open(file_path, 'w') as f:
            f.write(f'''#!/bin/bash
# {target_file} - {description}
# Generated by DevOpsZealot AI
# Branch: {self.branch_name}

set -e

# Color codes for better readability
GREEN="\\033[0;32m"
YELLOW="\\033[1;33m"
RED="\\033[0;31m"
NC="\\033[0m" # No Color

# Check dependencies
''')
            # Add dependency checks
            for dep in dependencies:
                f.write(f'''
check_{dep}() {{
    if ! command -v {dep} &> /dev/null; then
        echo -e "${{RED}}Error: {dep} is not installed or not in PATH${{NC}}"
        echo -e "${{YELLOW}}Please install {dep} to use this script${{NC}}"
        return 1
    fi
    return 0
}}
''')
            
            # Add main functionality based on requirements
            if "Extract audio using ffmpeg" in " ".join(requirements):
                f.write('''
extract_audio() {
    local input_file="$1"
    local output_file="${input_file%.*}.wav"
    
    echo -e "${YELLOW}Extracting audio from: $input_file${NC}"
    ffmpeg -i "$input_file" -q:a 0 -map a "$output_file" -y
    echo -e "${GREEN}Audio extracted to: $output_file${NC}"
    
    echo "$output_file"
}
''')
            
            if "Process the audio with Whisper CLI" in " ".join(requirements):
                f.write('''
transcribe_audio() {
    local input_file="$1"
    local output_dir="${2:-./output}"
    local whisper_model="${WHISPER_MODEL:-base}"
    
    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"
    
    # Determine whisper CLI path
    local whisper_path="${WHISPER_CLI_PATH:-whisper}"
    
    echo -e "${YELLOW}Transcribing audio with Whisper model: $whisper_model${NC}"
    "$whisper_path" "$input_file" --model "$whisper_model" --output_dir "$output_dir"
    
    # Find the generated transcript file
    local transcript_file="$output_dir/$(basename "${input_file%.*}").txt"
    
    if [ -f "$transcript_file" ]; then
        echo -e "${GREEN}Transcript saved to: $transcript_file${NC}"
        echo "$transcript_file"
    else
        echo -e "${RED}Transcription failed or output file not found${NC}"
        return 1
    fi
}
''')
            
            # Add usage section
            f.write('''
# Display usage instructions
show_usage() {
    echo "Usage: $(basename "$0") <input_mp4_file> [output_directory] [whisper_model]"
    echo ""
    echo "Arguments:"
    echo "  input_mp4_file    Path to the MP4 file to transcribe"
    echo "  output_directory  Directory to save the transcript (default: ./output)"
    echo "  whisper_model     Whisper model to use (default: base)"
    echo ""
    echo "Environment variables:"
    echo "  WHISPER_CLI_PATH  Path to the Whisper CLI executable (default: whisper)"
    echo "  WHISPER_MODEL     Default Whisper model to use (default: base)"
    echo ""
    echo "Example:"
    echo "  $(basename "$0") meeting.mp4 ./transcripts medium"
    echo "  WHISPER_CLI_PATH=/opt/whisper/bin/whisper $(basename "$0") video.mp4"
}

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing input file${NC}"
    show_usage
    exit 1
fi

# Check if input file exists
if [ ! -f "$1" ]; then
    echo -e "${RED}Error: Input file not found: $1${NC}"
    exit 1
fi

# Check dependencies
''')
            # Add dependency check calls
            for dep in dependencies:
                f.write(f"check_{dep} || exit 1\n")
                
            # Add main execution
            f.write('''
# Process input arguments
INPUT_FILE="$1"
OUTPUT_DIR="${2:-./output}"
WHISPER_MODEL="${3:-${WHISPER_MODEL:-base}}"

# Main execution
echo -e "${GREEN}Starting MP4 to transcript process${NC}"
AUDIO_FILE=$(extract_audio "$INPUT_FILE")
TRANSCRIPT_FILE=$(transcribe_audio "$AUDIO_FILE" "$OUTPUT_DIR")

echo -e "${GREEN}Process completed successfully!${NC}"
echo -e "Transcript is available at: ${TRANSCRIPT_FILE}"
''')
        
        # Make the script executable
        os.chmod(file_path, 0o755)
        
        logger.info(f"File generated: {file_path}")
        
    def commit_changes(self):
        """Commit the changes to the repository"""
        logger.info("Committing changes to repository")
        
        # Stage all changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=self.workspace,
            check=True
        )
        
        # Commit the changes
        commit_message = f"AI: {self.task.get('name', 'Generated code')}"
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            cwd=self.workspace,
            check=True
        )
        
        logger.info(f"Changes committed with message: {commit_message}")
        
        # For remote repositories, push the changes if GITHUB_TOKEN is available
        if (self.repo_url.startswith('http') or self.repo_url.startswith('git@')) and os.environ.get('GITHUB_TOKEN'):
            logger.info(f"Pushing changes to remote branch: {self.branch_name}")
            try:
                subprocess.run(
                    ['git', 'push', '-u', 'origin', self.branch_name],
                    cwd=self.workspace,
                    check=True
                )
                logger.info("Changes pushed successfully!")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to push changes: {e}")
                logger.info("You may need to push manually.")

    def run(self):
        """Execute the entire AI integration workflow"""
        try:
            # Clone the repository and set up branch
            self.clone_repository()
            
            # Initialize AI editor
            self.initialize_ai_editor()
            
            # Process the task
            self.process_task()
            
            # Commit and push changes
            self.commit_changes()
            
            logger.info("AI integration completed successfully!")
            return True
        except Exception as e:
            logger.error(f"AI integration failed: {e}")
            return False

def main():
    """Main entrypoint"""
    logger.info("Starting DevOpsZealot Simplified AI Integration")
    
    integration = AIIntegration()
    success = integration.run()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
