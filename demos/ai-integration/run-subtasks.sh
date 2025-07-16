#!/bin/bash
# Run DevOpsZealot with subtask-based approach for meeting transcription enhancement

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

# Check if Docker is installed and running
check_docker() {
  if ! command -v docker &> /dev/null; then
    print_error "Docker is required but not installed."
    exit 1
  fi
  
  if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running."
    exit 1
  fi
}

# Build Docker image for DevOpsZealot
build_docker_image() {
  print_header "Building Docker image for DevOpsZealot"
  
  docker build -f ../../docker/Dockerfile.zealot.test -t devops-zealot:ai-test ../../docker
  
  if [ $? -eq 0 ]; then
    print_success "Docker image built successfully!"
  else
    print_error "Failed to build Docker image."
    exit 1
  fi
}

# Run a specific subtask
run_subtask() {
  local context_file=$1
  local task_name=$2
  
  print_header "Running subtask: $task_name"
  
  # Create a temporary directory for this run
  local temp_dir=$(mktemp -d)
  print_info "Created temporary directory: ${temp_dir}"
  
  # Set up environment variables
  export OPENAI_API_KEY="${OPENAI_API_KEY}"
  export GITHUB_TOKEN="${GITHUB_TOKEN}"
  export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
  export AI_MODEL="${AI_MODEL:-gpt-4}"
  export VERBOSE_LOGGING="${VERBOSE_LOGGING:-true}"
  export PULL_BEFORE_PUSH="${PULL_BEFORE_PUSH:-true}"
  export AUTO_MERGE="${AUTO_MERGE:-true}"
  export FORCE_PUSH="${FORCE_PUSH:-false}"
  
  # Print masked environment variables
  echo "Environment variables set:"
  echo "  OPENAI_API_KEY=***"
  echo "  GITHUB_TOKEN=***"
  echo "  LOG_LEVEL=${LOG_LEVEL}"
  echo "  AI_MODEL=${AI_MODEL}"
  echo "  VERBOSE_LOGGING=${VERBOSE_LOGGING}"
  echo "  PULL_BEFORE_PUSH=${PULL_BEFORE_PUSH}"
  echo "  AUTO_MERGE=${AUTO_MERGE}"
  echo "  FORCE_PUSH=${FORCE_PUSH}"
  echo ""
  
  # Copy context and necessary files to temp dir
  cp "${context_file}" "${temp_dir}/context.json"
  cp ai_file_editor.py "${temp_dir}/"
  cp run_ai_integration.py "${temp_dir}/"
  cp validators.py "${temp_dir}/"
  
  # Extract branch name from context.json
  local branch_name=$(grep -o '"branch": *"[^"]*"' "${context_file}" | cut -d'"' -f4)
  echo "Using branch from context.json: ${branch_name}"
  
  # Run the container
  print_info "Starting container with context file using remote repo"
  docker run --rm \
    -v "${temp_dir}:/tmp/workspace" \
    -e OPENAI_API_KEY \
    -e GITHUB_TOKEN \
    -e LOG_LEVEL \
    -e AI_MODEL \
    -e VERBOSE_LOGGING \
    -e PULL_BEFORE_PUSH \
    -e AUTO_MERGE \
    -e FORCE_PUSH \
    devops-zealot:ai-test \
    python /tmp/workspace/run_ai_integration.py /tmp/workspace/context.json
  
  # Check the result
  if [ $? -eq 0 ]; then
    print_success "Subtask '${task_name}' completed successfully!"
  else
    print_error "Subtask '${task_name}' failed."
    return 1
  fi
}

# Main function
main() {
  print_header "DevOpsZealot Subtask-Based Meeting Transcription Enhancement"
  
  # Check requirements
  check_docker
  
  # Check required environment variables
  if [ -z "$OPENAI_API_KEY" ]; then
    print_error "OPENAI_API_KEY environment variable is not set."
    exit 1
  fi
  
  if [ -z "$GITHUB_TOKEN" ]; then
    print_error "GITHUB_TOKEN environment variable is not set."
    exit 1
  fi
  
  # Build Docker image
  build_docker_image
  
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
        run_subtask "$context_file" "$task_name"
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
    for subtask in "${subtasks[@]}"; do
      IFS=':' read -r context_file task_name <<< "$subtask"
      run_subtask "$context_file" "$task_name"
    done
  fi
  
  print_header "Meeting Transcription Enhancement completed successfully!"
  
  echo "To test the enhanced transcription pipeline:"
  echo "  git clone https://github.com/zacharyelston/transcribe-demo -b feature/whisper-cli-subtasks transcribe-demo-enhanced"
  echo "  cd transcribe-demo-enhanced"
  echo "  ./transcribe_video.sh <input_video_file>"
  
  echo "To create a pull request:"
  echo "  https://github.com/zacharyelston/transcribe-demo/compare/feature/whisper-cli-subtasks?expand=1"
}

main "$@"
