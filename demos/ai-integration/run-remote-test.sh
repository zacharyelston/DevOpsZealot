#!/bin/bash
# Run the Docker AI integration with remote repository configuration
# Following our design philosophy of clarity over complexity

set -e

# Color codes for better readability
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_FILE="${SCRIPT_DIR}/context-remote-example.json"
DOCKER_SCRIPT="${SCRIPT_DIR}/docker-ai-integration.sh"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}DevOpsZealot Remote Repository Test${NC}"
echo -e "${BLUE}=============================================${NC}"

# Check if the docker script exists
if [ ! -f "$DOCKER_SCRIPT" ]; then
  echo -e "${RED}Error: Docker AI integration script not found at ${DOCKER_SCRIPT}${NC}"
  exit 1
fi

# Check if context file exists
if [ ! -f "$CONTEXT_FILE" ]; then
  echo -e "${RED}Error: Context file not found at ${CONTEXT_FILE}${NC}"
  exit 1
fi

# Copy the remote context file to the standard location
echo -e "\n${YELLOW}Copying remote context configuration...${NC}"
cp "$CONTEXT_FILE" "${SCRIPT_DIR}/context.json"

# Run the Docker AI integration script
echo -e "\n${GREEN}Starting Docker AI integration with remote repository...${NC}"
echo -e "${BLUE}Using context file: ${CONTEXT_FILE}${NC}"
echo -e "${BLUE}Branch name: feature/script-improvements${NC}"

# Execute the Docker AI integration script
"$DOCKER_SCRIPT"

# Restore the original context file if it exists
if [ -f "${SCRIPT_DIR}/context.json.bak" ]; then
  echo -e "\n${YELLOW}Restoring original context file...${NC}"
  mv "${SCRIPT_DIR}/context.json.bak" "${SCRIPT_DIR}/context.json"
fi

echo -e "\n${GREEN}Test completed!${NC}"