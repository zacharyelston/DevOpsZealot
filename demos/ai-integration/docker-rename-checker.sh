#!/usr/bin/env bash
#
# Docker Rename Checker - Run the rename checker utility in a Docker container
#
# This script runs the rename_checker.py utility in a Docker container
# to ensure proper file renaming operations are performed
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
  log_error "Usage: $0 <repo_path> <context_file>"
  exit 1
fi

REPO_PATH="$1"
CONTEXT_FILE="$2"

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

# Copy the rename checker script
COPY rename_checker.py /app/

# Entry point
ENTRYPOINT ["python", "rename_checker.py"]
EOF

log_header "Running Rename Checker in Docker"

# Copy rename checker to temp dir
cp "${SCRIPT_DIR}/rename_checker.py" "${TEMP_DIR}/"

# Build Docker image
log_info "Building Docker image for rename checker"
docker build -t rename-checker-image -f "$DOCKERFILE" "$TEMP_DIR" > /dev/null

# Pass GitHub token if available
GITHUB_TOKEN_ARGS=""
if [ -n "$GITHUB_TOKEN" ]; then
  GITHUB_TOKEN_ARGS="-e GITHUB_TOKEN=$GITHUB_TOKEN"
fi

# Extract Git user config from context file if available
GIT_USER_NAME="DevOps Zealot"
GIT_USER_EMAIL="zealot@example.com"

if [ -f "$CONTEXT_FILE" ]; then
  # Try to extract Git user config from context file
  EXTRACTED_NAME=$(grep -o '"name": "[^"]*"' "$CONTEXT_FILE" | grep -v repository | head -1 | cut -d'"' -f4)
  EXTRACTED_EMAIL=$(grep -o '"email": "[^"]*"' "$CONTEXT_FILE" | head -1 | cut -d'"' -f4)
  
  # Use extracted values if available
  if [ -n "$EXTRACTED_NAME" ]; then
    GIT_USER_NAME="$EXTRACTED_NAME"
  fi
  
  if [ -n "$EXTRACTED_EMAIL" ]; then
    GIT_USER_EMAIL="$EXTRACTED_EMAIL"
  fi
fi

# Pass Git config to container
GIT_CONFIG_ARGS="-e GIT_USER_NAME=$(printf %q "$GIT_USER_NAME") -e GIT_USER_EMAIL=$(printf %q "$GIT_USER_EMAIL")"

# Run container with appropriate mounts
log_info "Running rename checker container"
docker run --rm \
  -v "$REPO_PATH:/repo" \
  -v "$CONTEXT_FILE:/context.json" \
  -e "GIT_USER_NAME=$GIT_USER_NAME" \
  -e "GIT_USER_EMAIL=$GIT_USER_EMAIL" \
  $GITHUB_TOKEN_ARGS \
  rename-checker-image --repo /repo --context /context.json

EXIT_CODE=$?

# Clean up
rm -rf "$TEMP_DIR"

if [ $EXIT_CODE -eq 0 ]; then
  log_success "Rename checker completed successfully"
else
  log_error "Rename checker encountered issues (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
