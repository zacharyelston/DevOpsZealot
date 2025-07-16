#!/bin/bash
# Run subtasks for Whisper CLI integration using Docker

set -e

# Color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_SCRIPT="${SCRIPT_DIR}/docker-ai-integration.sh"

# Print section header
print_header() {
  echo -e "\n${BLUE}==============================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}==============================================${NC}\n"
}

# Print error message
print_error() {
  echo -e "${RED}ERROR: $1${NC}"
}

# Print success message
print_success() {
  echo -e "${GREEN}SUCCESS: $1${NC}"
}

# Print info message
print_info() {
  echo -e "${YELLOW}INFO: $1${NC}"
}

# Check if Docker script exists
if [ ! -f "$DOCKER_SCRIPT" ]; then
  print_error "Docker AI integration script not found at ${DOCKER_SCRIPT}"
  exit 1
fi

# Run a specific subtask
run_subtask() {
  local context_file=$1
  local task_name=$2
  
  print_header "Running subtask: $task_name"
  
  # Copy the specific context file to the standard location expected by the Docker script
  print_info "Setting up context configuration for: ${task_name}"
  cp "$context_file" "${SCRIPT_DIR}/context.json"
  
  # Extract branch name from context for display
  local branch_name=$(grep -o '"branch": "[^"]*"' "${context_file}" | cut -d'"' -f4)
  print_info "Using branch from context file: ${branch_name}"
  
  # Run the Docker integration script
  print_info "Starting Docker container for task: ${task_name}"
  bash "${DOCKER_SCRIPT}"
  
  # Check the result of the Docker run
  local docker_result=$?
  
  if [ $docker_result -eq 0 ]; then
    print_info "Docker container execution successful, checking for required file renames..."
    
    # Get repository URL from context file
    local repo_url=$(grep -o '"repository": "[^"]*"' "${context_file}" | cut -d'"' -f4)
    
    # If the repo URL is from GitHub, clone it to a temp dir to check renames
    if [[ $repo_url == https://github.com/* ]]; then
      local temp_dir=$(mktemp -d)
      print_info "Cloning repository to check file renaming operations"
      
      # Use GitHub token if available for authentication
      if [ -n "$GITHUB_TOKEN" ]; then
        local auth_repo_url=${repo_url/https:\/\/github.com/https:\/\/$GITHUB_TOKEN@github.com}
        git clone "$auth_repo_url" "$temp_dir" --branch "$branch_name" 2>/dev/null
      else
        git clone "$repo_url" "$temp_dir" --branch "$branch_name" 2>/dev/null
      fi
      
      # Check which subtask we're running and apply the appropriate validators
      local subtask_index=$(echo "$context_file" | grep -o "[0-9]" | head -1)
      
      if [[ "$context_file" == *"subtasks.json"* ]]; then
        # Subtask 0: File Renaming & POSIX Newlines
        print_info "Running validators for Subtask 0: File Renaming & POSIX Newlines"
        
        # Step 1: Run the rename validator to check for required renames
        print_info "Running rename validator to check and perform required file renames..."
        
        # Run with auto-fix enabled to actually perform the renames
        ${SCRIPT_DIR}/docker-rename-validator.sh "${temp_dir}" "${context_file}" --auto-fix
        
        # Step 2: Run the POSIX newline validator to check for newlines at EOF
        print_info "Running POSIX newline validator to check and fix newline issues..."
        
        # Run with auto-fix enabled to add missing newlines
        ${SCRIPT_DIR}/docker-newline-validator.sh "${temp_dir}" "${context_file}" --auto-fix
      elif [[ "$context_file" == *"whisper-path.json"* ]]; then
        # Subtask 1: Whisper CLI Path Consistency
        print_info "Running validator for Subtask 1: Whisper CLI Path Consistency"
        
        # Run the Whisper CLI validator to check for CLI integration issues
        print_info "Running Whisper CLI validator to check and fix path consistency issues..."
        
        # Run with auto-fix enabled to fix Whisper CLI integration issues
        ${SCRIPT_DIR}/docker-whisper-cli-validator.sh "${temp_dir}" "${context_file}" --auto-fix
      fi
      
      # All validators are run with auto-fix enabled to ensure requirements are met
      # The validation results will help the AI understand what was fixed automatically
      
      # Clean up temp directory
      rm -rf "$temp_dir"
    fi
    
    # Subtask 1: Whisper CLI Path Consistency
    if [ "$task_name" = "Whisper CLI Path Consistency" ]; then
      print_header "Running Subtask 1: Whisper CLI Path Consistency"
      context_file="${SCRIPT_DIR}/context-meeting-transcription-whisper-path.json"
      
      # Create temporary directory for checking out the repository
      temp_dir=$(mktemp -d)
      print_info "Created temporary directory: $temp_dir"
      
      # Load the repository information from the context file
      repo_url=$(jq -r '.task.repository' "$context_file")
      branch_name=$(jq -r '.task.branch' "$context_file")
      
      # Clone the repository
      print_info "Cloning repository: $repo_url (branch: $branch_name)"
      git clone "$repo_url" "$temp_dir" --branch "$branch_name" 2>/dev/null
      
      # Run the Whisper CLI validator to check for CLI integration issues
      print_info "Running Whisper CLI validator to check and fix path consistency issues..."
      
      # Run with auto-fix enabled to fix Whisper CLI integration issues
      ${SCRIPT_DIR}/docker-whisper-cli-validator.sh "${temp_dir}" "${context_file}" --auto-fix
      
      # Clean up temporary directory
      rm -rf "$temp_dir"
    fi
    
    print_success "Subtask '${task_name}' completed successfully!"
    return 0
  else
    print_error "Subtask '${task_name}' failed."
    return 1
  fi
}

# Main function
main() {
  print_header "Whisper CLI Integration - Subtask-Based Approach"
  
  # Source the environment variables
  if [ -f "${SCRIPT_DIR}/.env" ]; then
    print_info "Loading environment variables from .env file"
    source "${SCRIPT_DIR}/.env"
  else
    print_error "No .env file found. Please create one with the required API keys."
    exit 1
  fi
  
  # Define the subtasks with their context files and names
  local subtasks=(
    "context-meeting-transcription-subtasks.json:File Renaming & POSIX Newlines"
    "context-meeting-transcription-whisper-path.json:Whisper CLI Path Consistency"
    "context-meeting-transcription-error-handling.json:Error Handling Implementation"
    "context-meeting-transcription-whisper-cli.json:Whisper CLI Integration"
  )
  
  # Run the subtasks if specified, or all of them
  if [ $# -gt 0 ]; then
    # Run only specified subtasks by index
    for index in "$@"; do
      if [[ $index =~ ^[0-9]+$ ]] && [ $index -ge 0 ] && [ $index -lt ${#subtasks[@]} ]; then
        IFS=':' read -r context_file task_name <<< "${subtasks[$index]}"
        run_subtask "$context_file" "$task_name" || exit 1
      else
        print_error "Invalid subtask index: $index"
        echo "Available subtasks:"
        for i in "${!subtasks[@]}"; do
          IFS=':' read -r _ task_name <<< "${subtasks[$i]}"
          echo "  $i: $task_name"
        done
        exit 1
      fi
    done
  else
    # Run all subtasks in sequence
    local success=true
    for subtask in "${subtasks[@]}"; do
      IFS=':' read -r context_file task_name <<< "$subtask"
      run_subtask "$context_file" "$task_name" || success=false
      
      # If any subtask fails, stop processing
      if [ "$success" = false ]; then
        print_error "Stopping due to subtask failure"
        exit 1
      fi
    done
  fi
  
  print_header "Whisper CLI Integration completed successfully!"
  
  echo "To test the enhanced transcription pipeline:"
  echo "  git clone https://github.com/zacharyelston/transcribe-demo -b feature/whisper-cli-subtasks transcribe-demo-enhanced"
  echo "  cd transcribe-demo-enhanced"
  echo "  ./transcribe_video.sh <input_video_file>"
  
  echo "To create a pull request:"
  echo "  https://github.com/zacharyelston/transcribe-demo/compare/feature/whisper-cli-subtasks?expand=1"
}

main "$@"
