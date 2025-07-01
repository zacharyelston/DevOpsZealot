#!/bin/bash
# Quick script to run the transcribe-demo test with simplified approach
# This avoids Docker build issues by using Python directly

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
DEMO_REPO_DIR="/Users/zacelston/AlZacAI/transcribe-demo"
CONTEXT_FILE="${SCRIPT_DIR}/context.json"
ENV_FILE="${SCRIPT_DIR}/.env"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}DevOpsZealot Quick Test Runner${NC}"
echo -e "${BLUE}=============================================${NC}"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo -e "\n${GREEN}Loading environment variables from ${ENV_FILE}...${NC}"
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check target repository
if [ ! -d "$DEMO_REPO_DIR" ]; then
  echo -e "${RED}Error: Target repository directory does not exist: ${DEMO_REPO_DIR}${NC}"
  exit 1
fi

# Initialize git repository if not already one
if [ ! -d "${DEMO_REPO_DIR}/.git" ]; then
  echo -e "\n${YELLOW}No git repository found in target directory. Initializing one...${NC}"
  (cd "${DEMO_REPO_DIR}" && git init && git add . && git config --local user.email "zealot@example.com" && git config --local user.name "DevOps Zealot" && git commit -m "Initial commit")
fi

# Create a temporary context file with absolute paths
TEMP_CONTEXT_FILE=$(mktemp)
cp "$CONTEXT_FILE" "$TEMP_CONTEXT_FILE"
echo -e "\n${BLUE}Created temporary context file: ${TEMP_CONTEXT_FILE}${NC}"

# Show environment variables (masking sensitive ones)
echo -e "${YELLOW}Environment variables set:${NC}"
if [ -n "$OPENAI_API_KEY" ]; then
  echo -e "  OPENAI_API_KEY=***" 
fi
if [ -n "$ANTHROPIC_API_KEY" ]; then
  echo -e "  ANTHROPIC_API_KEY=***"
fi
if [ -n "$GITHUB_TOKEN" ]; then
  echo -e "  GITHUB_TOKEN=***"
fi
if [ -n "$LOG_LEVEL" ]; then
  echo -e "  LOG_LEVEL=${LOG_LEVEL}"
fi
if [ -n "$AI_MODEL" ]; then
  echo -e "  AI_MODEL=${AI_MODEL}"
fi
if [ -n "$VERBOSE_LOGGING" ]; then
  echo -e "  VERBOSE_LOGGING=${VERBOSE_LOGGING}"
fi

# Set default log level if not set
if [ -z "$LOG_LEVEL" ]; then
  LOG_LEVEL="DEBUG"
  export LOG_LEVEL
  echo -e "${BLUE}Set default LOG_LEVEL=DEBUG${NC}"
fi

# Set verbose logging if not set
if [ -z "$VERBOSE_LOGGING" ]; then
  VERBOSE_LOGGING="true"
  export VERBOSE_LOGGING
  echo -e "${BLUE}Set default VERBOSE_LOGGING=true${NC}"
fi

# Run Docker using the local image if it exists, otherwise pull from Docker Hub
echo -e "\n${GREEN}Checking for local DevOpsZealot image...${NC}"
if docker image inspect devops-zealot:local >/dev/null 2>&1; then
  IMAGE_NAME="devops-zealot:local"
  echo -e "${GREEN}Using local image: ${IMAGE_NAME}${NC}"
else
  echo -e "${YELLOW}Local image not found, trying default Docker Hub image...${NC}"
  IMAGE_NAME="zacharyelston/devops-zealot:latest"
fi

echo -e "\n${GREEN}Running test with target repository: ${DEMO_REPO_DIR}${NC}"

# Run the Docker container
docker run --rm -it \
  -v "${DEMO_REPO_DIR}:/target" \
  -v "${TEMP_CONTEXT_FILE}:/app/context.json" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  -e OPENAI_API_KEY \
  -e ANTHROPIC_API_KEY \
  -e GITHUB_TOKEN \
  -e LOG_LEVEL \
  -e AI_MODEL \
  -e VERBOSE_LOGGING \
  -e ZEALOT_CONTAINER_MODE=true \
  "${IMAGE_NAME}" python -m zealot.cli process-task --context-file /app/context.json

# Get exit code
EXIT_CODE=$?

# Clean up
rm -f "$TEMP_CONTEXT_FILE"

# Show results
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}Task completed successfully!${NC}"
  echo -e "${GREEN}=============================================${NC}"
  echo -e "\n${YELLOW}Modified files in: ${DEMO_REPO_DIR}${NC}"
  echo -e "${YELLOW}Check 'git diff' in that directory to see changes${NC}"
  echo -e "\n${BLUE}Example command to see changes:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git diff"
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}Task failed with exit code ${EXIT_CODE}!${NC}"
  echo -e "${RED}=============================================${NC}"
fi
