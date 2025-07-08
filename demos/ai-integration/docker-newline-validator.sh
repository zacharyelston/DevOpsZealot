#!/bin/bash
# Docker wrapper for POSIX newline validator
# This script runs the POSIX newline validator in a Docker container

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
log_info() {
  echo "INFO: $1"
}

log_warning() {
  echo "WARNING: $1"
}

log_error() {
  echo "ERROR: $1" >&2
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
  log_info "Auto-fix mode enabled - will attempt to fix newline issues"
fi

# Make sure paths are absolute
if [[ ! "$REPO_PATH" = /* ]]; then
  REPO_PATH="$(cd "$REPO_PATH" && pwd)"
fi
if [[ ! "$CONTEXT_FILE" = /* ]]; then
  CONTEXT_FILE="$(cd "$(dirname "$CONTEXT_FILE")" && pwd)/$(basename "$CONTEXT_FILE")"
fi

if [ ! -d "$REPO_PATH" ]; then
  log_error "Repository path does not exist: $REPO_PATH"
  exit 1
fi

if [ ! -f "$CONTEXT_FILE" ]; then
  log_error "Context file does not exist: $CONTEXT_FILE"
  exit 1
fi

# Build Docker image for the validator
log_info "Building Docker image for POSIX newline validator"

# Create a temporary Dockerfile
TMP_DOCKERFILE=$(mktemp)
cat > "$TMP_DOCKERFILE" <<EOF
FROM python:3.11-slim

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install gitpython

# Set up working directory
WORKDIR /app

# Copy the validator script
COPY validators/posix_newline_validator.py /app/
EOF

# Build the Docker image
docker build -t newline-validator-image -f "$TMP_DOCKERFILE" "$SCRIPT_DIR"
rm "$TMP_DOCKERFILE"

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
  newline-validator-image python /app/posix_newline_validator.py $VALIDATOR_ARGS

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  log_info "SUCCESS: All POSIX newline validations passed successfully"
else
  if [ "$AUTO_FIX" = true ]; then
    log_info "Auto-fix attempted for newline issues"
  else
    log_warning "POSIX newline validation failed. Run with --auto-fix to fix issues"
  fi
fi

exit $EXIT_CODE
