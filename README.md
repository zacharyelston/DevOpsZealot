# DevOpsZealot

An autonomous AI-powered infrastructure editing tool that enables AI agents to make code changes in secure, containerized environments without human intervention.

## Overview

DevOpsZealot allows AI agents (zealots) to:
- Checkout infrastructure code from Git repositories
- Make intelligent edits based on requirements
- Validate changes using industry-standard tools
- Commit and push changes via pull requests
- Operate completely autonomously with full observability

## Key Features

- 🤖 **AI-Powered**: Integrates with OpenAI GPT-4, Claude, and local LLMs
- 🔒 **Secure**: All operations in isolated Docker containers
- 🔍 **Observable**: Complete audit trail and metrics
- ✅ **Validated**: Pre-commit hooks and security scanning
- 🔄 **GitOps**: All changes through PR workflow with detailed commit messages
- 📊 **Monitored**: Prometheus metrics and structured logging

## Quick Start

```bash
# Clone repository
git clone https://github.com/zacharyelston/DevOpsZealot.git
cd DevOpsZealot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest

# Start server
python -m zealot.server
```

## Detailed Commit Messages

DevOpsZealot generates structured, informative commit messages that provide clear context about AI-driven changes:

```
DevOpsZealot: Script Improvement - Add support for..., Improve error...

Files modified: transcribe_video.sh, lib/utils.sh

## Changes Summary
This commit implements improvements to the script improvement as specified in the requirements.

## Requirements Implemented
- Add support for multiple output formats (srt, vtt, text)
- Improve error handling in both scripts with proper error codes
- Add batch processing mode to handle multiple files at once

## Validation
Changes have been validated against:
- shellcheck
- script_execution_test
```

These detailed commit messages make code reviews more efficient and create a clear audit trail of AI-driven changes.

## Architecture

```
Task Queue → Zealot Engine → Container → AI API → Validator → Git
```

## Documentation

- [Development Plan](docs/development-plan.md)
- [API Reference](docs/api-reference.md)
- [Integration Guide](docs/integration-guide.md)
- [Security Model](docs/security.md)

## License

MIT License - See LICENSE file for details
