#!/bin/bash
# Docker-based AI Integration Demo for DevOpsZealot
# This script demonstrates running the AI integration workflow in a Docker container

set -e

# Color codes for better readability
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZEALOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_NAME="devops-zealot:ai-test"
DEMO_REPO_DIR="/Users/zacelston/AlZacAI/transcribe-demo"
CONTEXT_FILE="${SCRIPT_DIR}/context.json"
ENV_FILE="${SCRIPT_DIR}/.env"
DOCKERFILE="${ZEALOT_DIR}/docker/Dockerfile.zealot.test"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}DevOpsZealot Docker AI Integration Demo${NC}"
echo -e "${BLUE}=============================================${NC}"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo -e "\n${GREEN}Loading environment variables from ${ENV_FILE}...${NC}"
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo -e "\n${YELLOW}No .env file found at ${ENV_FILE}${NC}"
  echo -e "${YELLOW}Creating .env file from template...${NC}"
  cp "${SCRIPT_DIR}/.env.example" "${ENV_FILE}"
  echo -e "${RED}Please edit ${ENV_FILE} to add your API keys${NC}"
  echo -e "${YELLOW}Then run this script again.${NC}"
  exit 1
fi

# Validate environment variables
echo -e "\n${BLUE}Validating environment...${NC}"
ERROR=0

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "${RED}Error: Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set${NC}"
  echo -e "${YELLOW}Please set at least one API key in ${ENV_FILE}${NC}"
  ERROR=1
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "${YELLOW}Warning: GITHUB_TOKEN is not set. Git operations may be limited.${NC}"
fi

if [ $ERROR -eq 1 ]; then
  exit 1
fi

# Check target repository
if [ ! -d "$DEMO_REPO_DIR" ]; then
  echo -e "${RED}Error: Target repository directory does not exist: ${DEMO_REPO_DIR}${NC}"
  exit 1
fi

# 1. Build the Docker image
echo -e "\n${GREEN}Building Docker image...${NC}"
if [ -f "$DOCKERFILE" ]; then
  echo -e "${BLUE}Using Dockerfile at: ${DOCKERFILE}${NC}"
  docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" "$ZEALOT_DIR"
  RESULT=$?
  
  if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Docker image built successfully!${NC}"
  else
    echo -e "${RED}Docker build failed with exit code ${RESULT}${NC}"
    exit $RESULT
  fi
else
  echo -e "${RED}Error: Dockerfile not found at ${DOCKERFILE}${NC}"
  exit 1
fi

# Create temp directory for AI integration scripts
TEMP_DIR=$(mktemp -d)
echo -e "\n${BLUE}Created temporary directory: ${TEMP_DIR}${NC}"

# Copy AI integration scripts to temp directory
cp "${SCRIPT_DIR}/ai_file_editor.py" "${TEMP_DIR}/"
cp "${SCRIPT_DIR}/validators.py" "${TEMP_DIR}/"
cp "${CONTEXT_FILE}" "${TEMP_DIR}/context.json"

# 2. Create a runner script for the Docker container that supports remote repositories
cat > "${TEMP_DIR}/run_ai_integration.py" << 'EOF'
#!/usr/bin/env python3
"""
Docker container entrypoint for AI integration demo with remote repository support
"""
import os
import sys
import logging
import json
import shutil
from pathlib import Path
import subprocess
import traceback
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
    # Try to get branch from top-level first, then task level, then default
    branch_name = context.get('branch') or context.get('task', {}).get('branch') or context.get('repository', {}).get('branch', 'feature/nuvo1')
    
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
EOF

chmod +x "${TEMP_DIR}/run_ai_integration.py"

# Initialize git repository if not already one
if [ ! -d "${DEMO_REPO_DIR}/.git" ]; then
  echo -e "\n${YELLOW}No git repository found in target directory. Initializing one...${NC}"
  (cd "${DEMO_REPO_DIR}" && git init && git add . && \
   git config --local user.email "zealot@example.com" && \
   git config --local user.name "DevOps Zealot" && \
   git commit -m "Initial commit")
fi

# Setup environment variables for Docker
ENV_ARGS=()

# Required environment variables
[ -n "$OPENAI_API_KEY" ] && ENV_ARGS+=("--env" "OPENAI_API_KEY=$OPENAI_API_KEY")
[ -n "$ANTHROPIC_API_KEY" ] && ENV_ARGS+=("--env" "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY")
[ -n "$GITHUB_TOKEN" ] && ENV_ARGS+=("--env" "GITHUB_TOKEN=$GITHUB_TOKEN")

# Optional environment variables
[ -n "$LOG_LEVEL" ] && ENV_ARGS+=("--env" "LOG_LEVEL=$LOG_LEVEL")
[ -n "$AI_MODEL" ] && ENV_ARGS+=("--env" "AI_MODEL=$AI_MODEL")
[ -n "$VERBOSE_LOGGING" ] && ENV_ARGS+=("--env" "VERBOSE_LOGGING=$VERBOSE_LOGGING")

echo -e "${YELLOW}Environment variables set:${NC}"
for arg in "${ENV_ARGS[@]}"; do
  if [[ "$arg" == "--env" ]]; then
    continue
  fi
  
  VAR_NAME=$(echo "$arg" | cut -d= -f1)
  if [[ "$VAR_NAME" == *"KEY"* || "$VAR_NAME" == *"TOKEN"* ]]; then
    echo -e "  ${VAR_NAME}=***" # Mask sensitive values
  else
    echo -e "  ${arg}"
  fi
done

# 3. Run the Docker container
# Extract branch name from context.json for display
BRANCH_NAME=$(grep -o '"branch": "[^"]*"' "${TEMP_DIR}/context.json" | cut -d'"' -f4)
echo -e "\n${BLUE}Starting container with context file using remote repo${NC}"
echo -e "${BLUE}Using branch from context.json: ${BRANCH_NAME}${NC}"

# Create a workspace directory in the container with appropriate permissions
docker run --rm \
  -v "${TEMP_DIR}:/app" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  "${ENV_ARGS[@]}" \
  --env ZEALOT_CONTAINER_MODE=true \
  "${IMAGE_NAME}" bash -c "mkdir -p /tmp/workspace && chmod 777 /tmp/workspace"

# Run the AI integration script
docker run --rm \
  -v "${TEMP_DIR}:/app" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  "${ENV_ARGS[@]}" \
  --env ZEALOT_CONTAINER_MODE=true \
  "${IMAGE_NAME}" python /app/run_ai_integration.py

# Get exit code
EXIT_CODE=$?

# Clean up
rm -rf "$TEMP_DIR"

# Show results
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}AI Integration Demo completed successfully!${NC}"
  echo -e "${GREEN}=============================================${NC}"
  echo -e "\n${YELLOW}Changes have been made to the remote repository${NC}"
  echo -e "${YELLOW}Branch: ${BRANCH_NAME}${NC}"
  
  echo -e "\n${BLUE}To create a pull request for these changes:${NC}"
  echo -e "  Visit the repository's GitHub page and create a PR for branch '${BRANCH_NAME}'"
  
  # Extract repository URL from context.json
  REPO_URL=$(grep -o '"repository": "[^"]*"' "${TEMP_DIR}/context.json" | cut -d'"' -f4)
  if [[ $REPO_URL == https://github.com/* ]]; then
    PR_URL="${REPO_URL%.git}/compare/${BRANCH_NAME}?expand=1"
    echo -e "${BLUE}PR URL: ${PR_URL}${NC}"
  fi
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}AI Integration Demo failed with exit code ${EXIT_CODE}!${NC}"
  echo -e "${RED}=============================================${NC}"
  echo -e "${RED}Check the logs above for detailed error messages.${NC}"
fi
