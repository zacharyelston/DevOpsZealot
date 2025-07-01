#!/bin/bash
# Quick script to build and run the DevOpsZealot local test

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
IMAGE_NAME="devops-zealot:local"
DEMO_REPO_DIR="/Users/zacelston/AlZacAI/transcribe-demo"
CONTEXT_FILE="${SCRIPT_DIR}/context.json"
ENV_FILE="${SCRIPT_DIR}/.env"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}DevOpsZealot Local Test Builder${NC}"
echo -e "${BLUE}=============================================${NC}"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo -e "\n${GREEN}Loading environment variables from ${ENV_FILE}...${NC}"
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# 1. Build the Docker image
echo -e "\n${GREEN}Building Docker image...${NC}"
DOCKERFILE="${ZEALOT_DIR}/docker/Dockerfile.zealot.test"

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

# 2. Create temporary context file
TEMP_CONTEXT_FILE=$(mktemp)
cp "$CONTEXT_FILE" "$TEMP_CONTEXT_FILE"
echo -e "\n${BLUE}Created temporary context file: ${TEMP_CONTEXT_FILE}${NC}"

# 3. Check target repository
if [ ! -d "$DEMO_REPO_DIR" ]; then
  echo -e "${RED}Error: Target repository directory does not exist: ${DEMO_REPO_DIR}${NC}"
  exit 1
fi

# Initialize git repository if not already one
if [ ! -d "${DEMO_REPO_DIR}/.git" ]; then
  echo -e "\n${YELLOW}No git repository found in target directory. Initializing one...${NC}"
  (cd "${DEMO_REPO_DIR}" && git init && git add . && git config --local user.email "zealot@example.com" && git config --local user.name "DevOps Zealot" && git commit -m "Initial commit")
fi

# 4. Run the container
echo -e "\n${GREEN}Running DevOpsZealot container...${NC}"

# Prepare environment variable arguments for docker run
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

# Run the Docker container
echo -e "\n${BLUE}Starting container with target repo: ${DEMO_REPO_DIR}${NC}"
docker run --rm \
  -v "${DEMO_REPO_DIR}:/target" \
  -v "${TEMP_CONTEXT_FILE}:/app/context.json" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  "${ENV_ARGS[@]}" \
  --env ZEALOT_CONTAINER_MODE=true \
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
