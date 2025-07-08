#!/usr/bin/env bash
#
# Direct File Renaming Utility for Git Repositories
#
# This script performs file renaming operations directly based on task requirements
# without requiring AI API calls. It's useful when the AI service has rate limits
# or when you want to focus only on the rename part of the task.
#

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log functions with nice formatting
print_header() {
  echo -e "\033[1;34m====== $1 ======\033[0m"
}

print_info() {
  echo -e "\033[0;36mINFO: $1\033[0m"
}

print_success() {
  echo -e "\033[0;32mSUCCESS: $1\033[0m"
}

print_error() {
  echo -e "\033[0;31mERROR: $1\033[0m"
}

print_warning() {
  echo -e "\033[0;33mWARNING: $1\033[0m"
}

# Check arguments
if [ "$#" -lt 2 ]; then
  print_error "Usage: $0 <repo_url> <context_file> [branch_name]"
  exit 1
fi

REPO_URL="$1"
CONTEXT_FILE="$2"
BRANCH_NAME="${3:-feature/whisper-cli-subtasks}"

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
print_info "Working in temporary directory: $TEMP_DIR"

# Function to ensure the directory is cleaned up on exit
cleanup() {
  print_info "Cleaning up temporary directory"
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Clone the repository
print_info "Cloning repository: $REPO_URL"
if [ -n "$GITHUB_TOKEN" ]; then
  # Use token for auth if available
  AUTH_REPO_URL=${REPO_URL/https:\/\/github.com/https:\/\/$GITHUB_TOKEN@github.com}
  git clone "$AUTH_REPO_URL" "$TEMP_DIR" 2>/dev/null
else
  git clone "$REPO_URL" "$TEMP_DIR" 2>/dev/null
fi

# Change to the cloned repository directory
cd "$TEMP_DIR"

# Set up Git user identity
git config user.name "DevOps Zealot"
git config user.email "zealot@example.com"

# Checkout or create the target branch
print_info "Checking out branch: $BRANCH_NAME"
if git ls-remote --heads origin "$BRANCH_NAME" | grep -q "$BRANCH_NAME"; then
  # Branch exists remotely, check it out
  git checkout -b "$BRANCH_NAME" "origin/$BRANCH_NAME"
else
  # Create a new branch
  git checkout -b "$BRANCH_NAME"
fi

# Parse context file to extract rename requirements
print_info "Parsing context file for rename requirements"
if [ ! -f "$CONTEXT_FILE" ]; then
  print_error "Context file not found: $CONTEXT_FILE"
  exit 1
fi

# Extract rename requirements using grep and sed
REQUIREMENTS=$(grep -o '"requirements":\s*\[[^]]*\]' "$CONTEXT_FILE" | sed 's/"requirements":\s*\[\(.*\)\]/\1/')

# Process each rename requirement
print_info "Processing rename requirements"
echo "$REQUIREMENTS" | grep -o '"Rename [^"]*"' | while read -r line; do
  # Extract source and target from the rename requirement
  REQUIREMENT=$(echo "$line" | sed 's/"Rename //' | sed 's/"$//')
  
  if [[ "$REQUIREMENT" =~ \'([^\']+)\'\s+to\s+\'([^\']+)\' ]]; then
    SOURCE_FILE="${BASH_REMATCH[1]}"
    TARGET_FILE="${BASH_REMATCH[2]}"
    
    print_info "Found rename requirement: $SOURCE_FILE -> $TARGET_FILE"
    
    # Check if source file exists
    if [ -f "$SOURCE_FILE" ]; then
      # Perform the rename using git mv
      print_info "Renaming $SOURCE_FILE to $TARGET_FILE"
      git mv "$SOURCE_FILE" "$TARGET_FILE"
      
      # Find and update references in other files
      print_info "Updating references in other files"
      grep -l "$SOURCE_FILE" --include="*.sh" --include="*.py" --include="*.md" -r . | while read -r file; do
        # Skip the renamed file itself
        if [[ "$(basename "$file")" != "$(basename "$TARGET_FILE")" ]]; then
          print_info "Updating references in: $file"
          sed -i.bak "s|$SOURCE_FILE|$TARGET_FILE|g" "$file"
          rm -f "${file}.bak"
        fi
      done
      
      # Add changes to git
      git add -A
      
      # Create commit message
      COMMIT_MSG="DevOpsZealot: Fixed file renaming operations\n\n"
      COMMIT_MSG+="This commit properly implements the rename operations using git mv to maintain file history.\n\n"
      COMMIT_MSG+="Renames performed:\n"
      COMMIT_MSG+="- $SOURCE_FILE -> $TARGET_FILE\n"
      
      # Commit the changes
      git commit -m "$COMMIT_MSG"
      
      print_success "Successfully renamed $SOURCE_FILE to $TARGET_FILE"
    else
      print_warning "Source file not found: $SOURCE_FILE"
    fi
  else
    print_warning "Could not parse rename requirement: $REQUIREMENT"
  fi
done

# Push changes if GITHUB_TOKEN is available
if [ -n "$GITHUB_TOKEN" ]; then
  print_info "Pushing changes to remote repository"
  if git push origin "$BRANCH_NAME"; then
    print_success "Successfully pushed changes to remote repository"
  else
    print_error "Failed to push changes to remote repository"
    exit 1
  fi
else
  print_warning "GITHUB_TOKEN not set, skipping push to remote"
fi

print_success "File renaming operations completed successfully!"
