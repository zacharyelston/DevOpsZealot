# DevOps AI Assistant

A Streamlit-based interface for launching containerized AI agents that clone Git repositories, create branches, apply AI-powered code modifications, and push changes back to the repository. Fully integrated with Redmine project management for complete traceability.

## Architecture

The system consists of two main components:

1. **Streamlit Orchestrator** - Web interface for configuring and monitoring container jobs
2. **Container Workers** - Isolated Docker containers that perform the actual Git operations

## Features

- **Repository Management**: Clone any Git repository with authentication support
- **Branch Creation**: Automatically create working branches for modifications  
- **AI Code Analysis**: Use OpenAI GPT-4o to intelligently modify code files
- **File Pattern Matching**: Target specific file types and patterns
- **Real-time Monitoring**: Track container status and view logs
- **Job History**: Review past jobs and their results
- **Container Isolation**: Each job runs in its own container for security and isolation

## Setup

### Prerequisites

- Docker installed and running
- Python 3.11+
- OpenAI API key

### Build the Container

```bash
# Build the worker container
./build_container.sh
```

### Run the Orchestrator

```bash
# Install dependencies
pip install streamlit gitpython openai pathlib

# Start the Streamlit interface
streamlit run app.py --server.port 5000
```

## Usage

### 1. Configure a Job

- Enter repository URL and authentication if needed
- Specify branch names (working branch and base branch)
- Provide AI instructions for code modifications
- Select file patterns to include in analysis

### 2. Launch Container

The system will:
- Create a unique job ID
- Launch a Docker container with the job configuration
- Monitor container execution in real-time

### 3. Monitor Progress

- View active jobs and their status
- Check container logs for detailed output
- Review results when jobs complete

### 4. Container Workflow

Each container performs these steps:
1. Clone the specified repository
2. Create and checkout the working branch
3. Find files matching the specified patterns
4. Process each file with AI modifications
5. Commit changes with descriptive messages
6. Push the branch to the remote repository

## Container Lifecycle

```
Configure Job → Launch Container → Execute Workflow → Push Changes → Container Exits
```

Multiple containers can work on the same repository by using different branch names, enabling iterative development workflows.

## File Structure

```
├── app.py                    # Streamlit orchestrator interface
├── container_manager.py     # Container lifecycle management
├── Dockerfile               # Container build configuration
├── container_requirements.txt # Container dependencies
├── container_worker/
│   ├── run_job.py           # Main container entry point
│   ├── git_worker.py        # Git operations handler
│   └── ai_worker.py         # AI code modification handler
└── build_container.sh       # Container build script
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - Required for AI code modifications

### Container Communication

Jobs communicate through mounted volumes:
- `/workspace/job_data/job_config.json` - Input configuration
- `/workspace/job_data/results.json` - Output results

## Security

- Each job runs in an isolated Docker container
- Containers are automatically removed after completion
- Git credentials are passed securely through environment variables
- No persistent data storage in containers

## Example Workflow

1. Configure job: Repository `https://github.com/user/project.git`
2. Set branch: `ai-refactor-2024`
3. AI prompt: "Add error handling to all Python functions"
4. File patterns: `*.py`
5. Launch container
6. Monitor progress through Streamlit interface
7. Review changes in the new branch on GitHub

## Troubleshooting

- Check container logs in the "Container Logs" page
- Verify Docker is running and accessible
- Ensure OpenAI API key is properly configured
- Check Git repository permissions for push access