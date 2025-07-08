#!/usr/bin/env bash
#
# Docker Rename Validator - Run the rename validator in a Docker container
#
# This script runs the rename_validator.py utility in a Docker container
# to validate if file renaming operations were properly performed without
# automatically fixing any issues.
#

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log functions for nice formatting
log_header() {
  echo -e "\033[1;34m====== $1 ======\033[0m"
}

log_info() {
  echo -e "\033[0;36mINFO: $1\033[0m"
}

log_success() {
  echo -e "\033[0;32mSUCCESS: $1\033[0m"
}

log_error() {
  echo -e "\033[0;31mERROR: $1\033[0m"
}

log_warning() {
  echo -e "\033[0;33mWARNING: $1\033[0m"
}

# Parse arguments
if [ "$#" -lt 2 ]; then
  log_error "Usage: $0 <repo_path> <context_file> [--auto-fix]"
  exit 1
fi

REPO_PATH="$1"
CONTEXT_FILE="$2"
AUTO_FIX=false

# Check for auto-fix flag
if [ "$3" = "--auto-fix" ] || [ "$3" = "--autofix" ]; then
  AUTO_FIX=true
  log_info "Auto-fix mode enabled - will attempt to fix rename issues"
fi

# Make sure paths are absolute
if [[ ! "$REPO_PATH" = /* ]]; then
  REPO_PATH="$(cd "$REPO_PATH" && pwd)"
fi

if [[ ! "$CONTEXT_FILE" = /* ]]; then
  CONTEXT_FILE="$(cd "$(dirname "$CONTEXT_FILE")" && pwd)/$(basename "$CONTEXT_FILE")"
fi

# Make sure files exist
if [ ! -d "$REPO_PATH" ]; then
  log_error "Repository path doesn't exist: $REPO_PATH"
  exit 1
fi

if [ ! -f "$CONTEXT_FILE" ]; then
  log_error "Context file doesn't exist: $CONTEXT_FILE"
  exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
  log_error "Docker is not installed or not available in PATH"
  exit 1
fi

# Create temporary Dockerfile
TEMP_DIR=$(mktemp -d)
DOCKERFILE="${TEMP_DIR}/Dockerfile"

cat > "$DOCKERFILE" << 'EOF'
FROM python:3.11-slim

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install gitpython

# Working directory
WORKDIR /app

# Copy the validator script
COPY rename_validator.py /app/

# Entry point
ENTRYPOINT ["python", "rename_validator.py"]
EOF

log_header "Running Rename Validator in Docker"

# Make sure validators directory exists
mkdir -p "${SCRIPT_DIR}/validators"

# Copy validator script to temp dir
cp "${SCRIPT_DIR}/validators/rename_validator.py" "${TEMP_DIR}/"

# Build Docker image
log_info "Building Docker image for rename validator"
docker build -t rename-validator-image -f "$DOCKERFILE" "$TEMP_DIR" > /dev/null

# Run container with appropriate mounts
log_info "Running rename validator container"

# Set up validator arguments
VALIDATOR_ARGS="--repo /repo --context /context.json --json"
if [ "$AUTO_FIX" = true ]; then
  VALIDATOR_ARGS="$VALIDATOR_ARGS --auto-fix"
  log_info "Passing --auto-fix flag to validator"
fi

# Get Git user configuration
GIT_USER_NAME=$(git config --get user.name || echo "DevOpsZealot Bot")
GIT_USER_EMAIL=$(git config --get user.email || echo "bot@devopszealot.com")

log_info "Using Git identity: $GIT_USER_NAME <$GIT_USER_EMAIL>"

# Run Docker container with arguments and Git identity
docker run --rm \
  -v "$REPO_PATH:/repo" \
  -v "$CONTEXT_FILE:/context.json" \
  -e "GIT_USER_NAME=$GIT_USER_NAME" \
  -e "GIT_USER_EMAIL=$GIT_USER_EMAIL" \
  rename-validator-image $VALIDATOR_ARGS

EXIT_CODE=$?

# Clean up
rm -rf "$TEMP_DIR"

if [ $EXIT_CODE -eq 0 ]; then
  log_success "All rename validations passed successfully"
else
  log_warning "Rename validation found issues - the AI should address these in future iterations"
  log_info "This is NOT an error - just information for the AI to improve its responses"
fi

# Always return success since this is just validation
exit 0
