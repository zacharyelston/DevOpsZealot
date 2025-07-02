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
ZEALOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEMO_REPO_DIR="/Users/zacelston/AlZacAI/transcribe-demo"
CONTEXT_FILE="${SCRIPT_DIR}/context-meeting-transcription.json"
ENV_FILE="${SCRIPT_DIR}/.env"
BRANCH_NAME="feature/whisper-meeting-notes-$(date +%Y%m%d-%H%M%S)"

# Display banner
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}Meeting Transcription Pipeline Enhancement${NC}"
echo -e "${BLUE}=============================================${NC}"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo -e "\n${GREEN}Loading environment variables from ${ENV_FILE}...${NC}"
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo -e "\n${YELLOW}No .env file found. Using environment variables from shell.${NC}"
fi

# Validate environment variables
echo -e "\n${BLUE}Validating environment...${NC}"
ERROR=0

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "${RED}Error: Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set${NC}"
  echo -e "${YELLOW}Please set at least one API key in the .env file or environment${NC}"
  ERROR=1
fi

if [ $ERROR -eq 1 ]; then
  exit 1
fi

# Check target repository
if [ ! -d "$DEMO_REPO_DIR" ]; then
  echo -e "${RED}Error: Target repository directory does not exist: ${DEMO_REPO_DIR}${NC}"
  exit 1
fi

# Ensure directories exist
mkdir -p "${DEMO_REPO_DIR}/templates" 2>/dev/null || true

# Create a new branch for our changes
echo -e "\n${BLUE}Creating a new branch for changes: ${BRANCH_NAME}${NC}"
(cd "${DEMO_REPO_DIR}" && git checkout -b "${BRANCH_NAME}" || git checkout -B "${BRANCH_NAME}")

# Check for required Python packages
echo -e "\n${BLUE}Checking for required Python packages...${NC}"
pip install --quiet openai GitPython anthropic &> /dev/null || {
  echo -e "${YELLOW}Installing required Python packages...${NC}"
  pip install openai GitPython anthropic
}

# Determine which API to use
if [ -n "$OPENAI_API_KEY" ]; then
  API_TYPE="openai"
  MODEL="gpt-4"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
  API_TYPE="anthropic"
  MODEL="claude-3-opus-20240229"
fi

echo -e "\n${GREEN}Using API: ${API_TYPE} with model: ${MODEL}${NC}"

# Display meeting transcription enhancement plan
echo -e "\n${BLUE}Meeting Transcription Enhancement Plan:${NC}"
echo -e "${YELLOW}Target repository: ${DEMO_REPO_DIR}${NC}"
echo -e "${YELLOW}Context file: ${CONTEXT_FILE}${NC}"

# Extract a simplified version of the context for display
echo -e "\n${BLUE}Enhancement Requirements:${NC}"
if command -v jq &> /dev/null; then
  jq -r '.task.requirements[] | "- " + .' "${CONTEXT_FILE}" 2>/dev/null || cat "${CONTEXT_FILE}"
else
  cat "${CONTEXT_FILE}" | grep -E '\s+".*",'
fi

# Run the Python script
echo -e "\n${BLUE}Running AI File Editor...${NC}"
echo -e "${YELLOW}This process may take several minutes. Please be patient.${NC}"

python "${SCRIPT_DIR}/ai_file_editor.py" \
  --repo "${DEMO_REPO_DIR}" \
  --context "${CONTEXT_FILE}" \
  --api "${API_TYPE}" \
  --model "${MODEL}" \
  --verbose

# Check exit status
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}Meeting Transcription Enhancement completed successfully!${NC}"
  echo -e "${GREEN}=============================================${NC}"
  echo -e "\n${YELLOW}Modified files in: ${DEMO_REPO_DIR}${NC}"
  (cd "${DEMO_REPO_DIR}" && git status)
  
  # Add example file and instructions
  echo -e "\n${BLUE}To test the enhanced transcription pipeline:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR}"
  echo -e "  ./transcribe_video.sh <input_video_file>"
  echo -e "  ./generate_meeting_notes.sh <transcript_file> \"Meeting Title\" \"$(date '+%Y-%m-%d %H:%M EDT')\" \"Participant Names\" <duration_minutes>"
  
  echo -e "\n${BLUE}To see detailed changes:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git diff"
  
  echo -e "\n${BLUE}To commit the changes:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git add . && git commit -m \"Enhanced transcription pipeline with Whisper CLI and meeting notes generation\""
else
  echo -e "\n${RED}=============================================${NC}"
  echo -e "${RED}Meeting Transcription Enhancement failed with exit code ${EXIT_CODE}!${NC}"
  echo -e "${RED}=============================================${NC}"
  echo -e "\n${YELLOW}To reset the repository:${NC}"
  echo -e "  cd ${DEMO_REPO_DIR} && git checkout main && git branch -D ${BRANCH_NAME}"
fi

# Exit with the AI File Editor's exit code
exit $EXIT_CODE
