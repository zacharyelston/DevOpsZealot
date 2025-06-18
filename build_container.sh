#!/bin/bash

# Build script for AI Git Modifier container

set -e

echo "Building AI Git Modifier container..."

# Build the Docker image
docker build -t git-ai-modifier:latest .

echo "Container built successfully!"
echo ""
echo "To test the container locally:"
echo "1. Create a test job config file"
echo "2. Run: docker run --rm -v /path/to/config:/workspace/job_data git-ai-modifier:latest"
echo ""
echo "Container is ready for use with the Streamlit orchestrator."