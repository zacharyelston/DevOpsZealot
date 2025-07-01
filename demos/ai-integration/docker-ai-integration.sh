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

# 2. Create a runner script for the Docker container
cat > "${TEMP_DIR}/run_ai_integration.py" << 'EOF'
#!/usr/bin/env python3
"""
Docker container entrypoint for AI integration demo
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

# Import our modules
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
    
    # Configuration
    target_repo = Path('/target')
    context_file = Path('/app/context.json')
    
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
    branch_name = f"ai-improvements-{os.environ.get('HOSTNAME', 'docker')}"
    logger.info(f"Creating branch: {branch_name}")
    
    subprocess.run(
        ['git', 'checkout', '-b', branch_name],
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
        import json
        with open(context_file) as f:
            context = json.load(f)
        
        validation_rules = context.get('task', {}).get('validation_rules', ['shellcheck', 'script_execution_test'])
        
        # Run validation
        success, results = validator.validate(modified_files, validation_rules)
        
        if success:
            logger.info("All validations passed!")
        else:
            logger.error("Some validations failed:")
            import json
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
echo -e "\n${BLUE}Starting container with target repo: ${DEMO_REPO_DIR}${NC}"
docker run --rm \
  -v "${DEMO_REPO_DIR}:/target" \
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
  echo -e "\n${YELLOW}Modified files in: ${DEMO_REPO_DIR}${NC}"
  (cd "${DEMO_REPO_DIR}" && git status)
  
  echo -e "\n${BLUE}To see detailed changes:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git diff HEAD~1"
  
  echo -e "\n${BLUE}To push the changes:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git push origin \$(git branch --show-current)"
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}AI Integration Demo failed with exit code ${EXIT_CODE}!${NC}"
  echo -e "${RED}=============================================${NC}"
  echo -e "\n${YELLOW}To reset the repository:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git checkout master && git branch -D \$(git branch --show-current)"
fi
