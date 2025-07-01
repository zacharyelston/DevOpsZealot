#!/bin/bash
# DevOpsZealot Local Test Runner
# This script runs DevOpsZealot locally in a Docker container,
# mounting a target repository and providing a context document

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
CONTEXT_FILE="${SCRIPT_DIR}/context.json"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE_FILE="${SCRIPT_DIR}/.env.example"
DEMO_REPO_DIR="/Users/zacelston/AlZacAI/transcribe-demo"
TARGET_REPO_DIR=""
IMAGE_NAME="devops-zealot:local"

# Show help function
function show_help {
  echo -e "${BLUE}DevOpsZealot Local Test Runner${NC}"
  echo -e "Usage: $0 -r <target_repo_path> [-c <context_file>] [-i <image_name>] [-d]"
  echo ""
  echo -e "${YELLOW}Options:${NC}"
  echo "  -r  Target repository path to be mounted and modified (required)"
  echo "  -c  Context file path (default: ${CONTEXT_FILE})"
  echo "  -i  Docker image name (default: ${IMAGE_NAME})"
  echo "  -d  Use the transcribe-demo repository (overrides -r)"
  echo "  -h  Show this help message"
  echo ""
  echo -e "${GREEN}Examples:${NC}"
  echo "  $0 -r ~/projects/my-terraform-repo    # Use your own repository"
  echo "  $0 -d                                # Use the transcribe-demo repository"
  exit 1
}

# Parse arguments
USE_DEMO_REPO=false
while getopts "r:c:i:dh" opt; do
  case ${opt} in
    r )
      TARGET_REPO_DIR=$(cd "$OPTARG" && pwd)
      ;;
    c )
      CONTEXT_FILE=$(cd "$(dirname "$OPTARG")" && pwd)/$(basename "$OPTARG")
      ;;
    i )
      IMAGE_NAME=$OPTARG
      ;;
    d )
      USE_DEMO_REPO=true
      ;;
    h )
      show_help
      ;;
    \? )
      show_help
      ;;
  esac
done

# Set target repo to demo if requested
if [ "$USE_DEMO_REPO" = true ]; then
  TARGET_REPO_DIR="$DEMO_REPO_DIR"
  echo -e "${BLUE}Using built-in demo repository at:${NC} $TARGET_REPO_DIR"
fi

# Validate input
if [ -z "$TARGET_REPO_DIR" ] && [ "$USE_DEMO_REPO" = false ]; then
  echo -e "${RED}Error: No target repository specified.${NC}"
  echo "Use -r to specify a target repository path or -d to use the demo repository."
  echo ""
  show_help
fi

# Ensure target repository exists
if [ ! -d "$TARGET_REPO_DIR" ]; then
  echo -e "${RED}Error: Target repository directory does not exist: $TARGET_REPO_DIR${NC}"
  exit 1
fi

# Create a temporary context file with environment variable substitution
TEMP_CONTEXT_FILE=$(mktemp)
cp "$CONTEXT_FILE" "$TEMP_CONTEXT_FILE"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}DevOpsZealot Local Test Runner${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "${YELLOW}Target Repository:${NC} $TARGET_REPO_DIR"
echo -e "${YELLOW}Context File:${NC} $CONTEXT_FILE"
echo -e "${YELLOW}Docker Image:${NC} $IMAGE_NAME"

# Check if .env file exists, create if not
if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE_FILE" ]; then
  echo -e "\n${YELLOW}No .env file found. Creating from example...${NC}"
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  echo -e "${GREEN}Created ${ENV_FILE}${NC}"
  echo -e "${YELLOW}Please edit it to add your API keys.${NC}"
  echo -e "You can proceed with this run, but it will likely fail without API keys.\n"
fi

# Load environment variables from .env file if it exists
if [ -f "$ENV_FILE" ]; then
  echo -e "\n${GREEN}Loading configuration from ${ENV_FILE}...${NC}"
  # Export all variables from .env
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check for API keys
API_KEYS_OK=true

# Check for AI API keys
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "\n${RED}Error: Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be set.${NC}"
  echo -e "Please add at least one of them to your ${ENV_FILE} file."
  API_KEYS_OK=false
fi

# Redmine integration is disabled for initial testing
echo -e "\n${BLUE}Redmine integration is disabled for initial testing${NC}"

# Default LOG_LEVEL if not set
if [ -z "$LOG_LEVEL" ]; then
  echo -e "${BLUE}Setting LOG_LEVEL=DEBUG${NC}"
  LOG_LEVEL="DEBUG"
  export LOG_LEVEL
fi

echo -e "\n${BLUE}=============================================${NC}"
echo -e "${YELLOW}API Keys configured:${NC} $([ "$API_KEYS_OK" = true ] && echo -e "${GREEN}YES${NC}" || echo -e "${RED}NO - Please update $ENV_FILE${NC}")"
echo -e "${BLUE}=============================================${NC}"

# Exit if API keys are not correctly set
if [ "$API_KEYS_OK" != true ]; then
  echo -e "\n${RED}WARNING: Required API keys not configured!${NC}"
  echo -e "${YELLOW}You need to edit ${ENV_FILE} and set at least your OpenAI or Anthropic API key${NC}"
  read -p "Do you want to continue anyway? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Exiting. Please update the API keys and try again.${NC}"
    exit 1
  fi
fi

# Build the Docker image
echo -e "\n${GREEN}Building Docker image...${NC}"

# Check if docker directory exists
if [ -d "$ZEALOT_DIR/docker" ] && [ -f "$ZEALOT_DIR/docker/Dockerfile.zealot" ]; then
  echo -e "${BLUE}Using Dockerfile.zealot from docker directory${NC}"
  docker build -t "$IMAGE_NAME" -f "$ZEALOT_DIR/docker/Dockerfile.zealot" "$ZEALOT_DIR" || {
    echo -e "${RED}Error: Failed to build Docker image${NC}"
    exit 1
  }
else
  echo -e "${RED}Error: Could not find Dockerfile.zealot in $ZEALOT_DIR/docker${NC}"
  exit 1
fi

# Initialize git repository if not already one
echo -e "\n${GREEN}Checking git repository...${NC}"
if [ ! -d "$TARGET_REPO_DIR/.git" ]; then
  echo -e "\n${YELLOW}No git repository found in target directory. Initializing one...${NC}"
  (cd "$TARGET_REPO_DIR" && git init && git add . && git config --local user.email "zealot@example.com" && git config --local user.name "DevOps Zealot" && git commit -m "Initial commit")
fi

# Run the container
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

# Run the container with all configured environment variables
docker run --rm -it \
  -v "$TARGET_REPO_DIR:/target" \
  -v "$TEMP_CONTEXT_FILE:/app/context.json" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  "${ENV_ARGS[@]}" \
  --env ZEALOT_CONTAINER_MODE=true \
  "$IMAGE_NAME" python -m zealot.cli process-task --context-file /app/context.json

# Get exit code
EXIT_CODE=$?

# Clean up
rm -f "$TEMP_CONTEXT_FILE"

if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}Task completed successfully!${NC}"
  echo -e "${GREEN}=============================================${NC}"
  echo -e "\n${YELLOW}Modified files in: $TARGET_REPO_DIR${NC}"
  echo -e "${YELLOW}Check 'git diff' in that directory to see changes${NC}"
  echo -e "\n${BLUE}Example command to see changes:${NC}"
  echo -e "  cd $TARGET_REPO_DIR && git diff"
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}Task failed!${NC}"
  echo -e "${RED}=============================================${NC}"
fi
