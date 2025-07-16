#!/bin/bash
# Meeting Transcription Pipeline Integration with DevOpsZealot
# This script uses the AI integration demo to enhance the transcribe-demo code
# to replace MacWhisper with direct Whisper CLI and add meeting notes generation.

set -e

# Color codes for better readability
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_FILE="${SCRIPT_DIR}/context-meeting-transcription.json"
DOCKER_SCRIPT="${SCRIPT_DIR}/docker-ai-integration.sh"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Meeting Transcription Pipeline Enhancement${NC}"
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

# Copy the meeting transcription context file to the standard location
echo -e "\n${YELLOW}Setting up meeting transcription context configuration...${NC}"
cp "$CONTEXT_FILE" "${SCRIPT_DIR}/context.json"

# Display meeting transcription enhancement plan
echo -e "\n${BLUE}Meeting Transcription Enhancement Plan:${NC}"
echo -e "${YELLOW}Context file: ${CONTEXT_FILE}${NC}"

# Extract repository and branch from context
REPO_URL=$(grep -o '"repository": "[^"]*"' "${CONTEXT_FILE}" | cut -d'"' -f4)
BRANCH_NAME=$(grep -o '"branch": "[^"]*"' "${CONTEXT_FILE}" | cut -d'"' -f4)

echo -e "${YELLOW}Target repository: ${REPO_URL}${NC}"
echo -e "${YELLOW}Branch: ${BRANCH_NAME}${NC}"

# Extract a simplified version of the context for display
echo -e "\n${BLUE}Enhancement Requirements:${NC}"
if command -v jq &> /dev/null; then
  jq -r '.task.requirements[] | "- " + .' "${CONTEXT_FILE}" 2>/dev/null || cat "${CONTEXT_FILE}"
else
  cat "${CONTEXT_FILE}" | grep -E '\s+".*",'
fi

# Setup environment variables for Docker script
export PULL_BEFORE_PUSH=true
export FORCE_PUSH=false
export AUTO_MERGE=true
export DISABLE_PUSH_TO_REMOTE=false  # Ensure push is enabled
echo -e "\n${BLUE}Environment variables set:${NC}"
echo -e "  PULL_BEFORE_PUSH=$PULL_BEFORE_PUSH"
echo -e "  FORCE_PUSH=$FORCE_PUSH"
echo -e "  AUTO_MERGE=$AUTO_MERGE"
echo -e "  DISABLE_PUSH_TO_REMOTE=$DISABLE_PUSH_TO_REMOTE"

# Run the Docker AI integration script
echo -e "\n${GREEN}Starting Docker AI integration with remote repository...${NC}"
echo -e "${YELLOW}This process may take several minutes. Please be patient.${NC}"

"$DOCKER_SCRIPT"

# Check exit status
EXIT_CODE=$?

# Restore the original context file if it exists
if [ -f "${SCRIPT_DIR}/context.json.bak" ]; then
  echo -e "\n${YELLOW}Restoring original context file...${NC}"
  mv "${SCRIPT_DIR}/context.json.bak" "${SCRIPT_DIR}/context.json"
fi

# Show results
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}Meeting Transcription Enhancement completed successfully!${NC}"
  echo -e "${GREEN}=============================================${NC}"
  
  echo -e "\n${BLUE}To test the enhanced transcription pipeline:${NC}"
  echo -e "  git clone ${REPO_URL} -b ${BRANCH_NAME} transcribe-demo-enhanced"
  echo -e "  cd transcribe-demo-enhanced"
  echo -e "  ./transcribe_video.sh <input_video_file>"
  echo -e "  ./generate_meeting_notes.sh <transcript_file> \"Meeting Title\" \"$(date '+%Y-%m-%d %H:%M EDT')\" \"Participant Names\" <duration_minutes>"
  
  # Create PR URL if it's a GitHub repository
  if [[ $REPO_URL == https://github.com/* ]]; then
    PR_URL="${REPO_URL%.git}/compare/${BRANCH_NAME}?expand=1"
    echo -e "\n${BLUE}To create a pull request:${NC}"
    echo -e "  ${PR_URL}"
  fi
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}Meeting Transcription Enhancement failed with exit code ${EXIT_CODE}!${NC}"
  echo -e "${RED}=============================================${NC}"
  echo -e "${RED}Check the logs above for detailed error messages.${NC}"
fi

# Exit with the Docker script's exit code
exit $EXIT_CODE
