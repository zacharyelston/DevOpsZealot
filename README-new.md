# DevOpsZealot 

- **DOZer**

An autonomous AI-powered infrastructure editing tool that enables AI agents to make code changes in secure, containerized environments without human intervention.

## Overview

DevOpsZealot is an autonomous AI-powered infrastructure editing tool designed to enable AI agents ("zealots") to make code changes in secure, containerized environments without human intervention. The project follows a "GitOps" approach, ensuring all changes go through a structured pull request workflow with proper validation.

## Key Features

- 🤖 **AI-Powered**: Integrates with OpenAI GPT-4, Claude, and local LLMs to make intelligent code edits
- 🔗 **Continue.dev Integration**: Advanced AI capabilities through Continue.dev integration via Model Context Protocol (MCP)
- 🔒 **Secure**: All operations in isolated Docker containers to maintain security boundaries
- 🔍 **Observable**: Complete audit trail and metrics for all automated actions
- ✅ **Validated**: Pre-commit hooks and security scanning ensure code quality and safety
- 🔄 **GitOps**: All changes through PR workflow with detailed commit messages
- 📊 **Monitored**: Prometheus metrics and structured logging
- 🔀 **Multi-Model Support**: Smart selection between different AI providers with fallback capabilities

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
Task Queue → Zealot Engine → Container → AI API → Validator → Git
```

With Continue.dev integration:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Continue.dev  │────▶│   MCP Server    │────▶│  DevOpsZealot   │
│   (IDE/Local)   │     │   (Bridge)      │     │   (Server)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         │                                                ▼
         │                                        ┌─────────────────┐
         │                                        │  Hybrid AI      │
         └───────────────────────────────────────▶│  Engine        │
                                                  └─────────────────┘
```

## Technical Components

### Core System (src/zealot/)
- **Server**: API and orchestration service for processing tasks
- **Engine**: Core logic for executing infrastructure change workflows
- **Task Queue**: Management of asynchronous infrastructure edit tasks
- **MCP API**: Bridge for Model Context Protocol integration
- **Config**: Configuration management and environment settings

### AI Integration (src/ai/)
- **OpenAI Client**: Integration with OpenAI's API for AI-assisted code editing
- **Continue Integration**: Connection to Continue.dev for enhanced AI capabilities
- **Prompts**: Structured prompts for effective AI interactions

### Infrastructure Components
- **Container Management**: Docker container orchestration for isolated execution
- **Git Operations**: Repository handling, branch management, and PR workflows
- **Validation**: Code quality and security scanning tools
- **Monitoring**: Metrics collection and reporting

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

# Run the demo
./demos/ai-integration/docker-ai-integration.sh
```

## Core Design Philosophy: Built for Clarity

This project adheres to a single guiding principle: **clarity over complexity**. Every feature and implementation follows this philosophy to ensure the system remains maintainable, understandable, and efficient.

### Key tenets of the Clarity-First approach:

- **Simplicity by Default**: Prioritize clear, straightforward solutions over complex ones
- **Modular Architecture**: Create focused components with single responsibilities
- **Proper Encapsulation**: Hide implementation details behind clean interfaces
- **SOLID Principles**: Especially single responsibility and dependency inversion
- **Practical Heuristics**: Apply KISS, DRY, and YAGNI in all implementations
- **Continuous Refinement**: Refactor to improve clarity and reduce complexity

## Recent Enhancements

### Remote Repository Integration (July 2025)
- Added support for remote GitHub repositories instead of local paths
- Implemented secure GitHub token authentication for private repositories
- Created workspace handling for containerized repository operations
- Added dynamic branch naming from context.json configuration

### Enhanced Commit Messages (July 2025)
- Designed structured commit message format for AI-generated changes
- Added sections for files modified, changes summary, and requirements
- Implemented validation rules section in commit messages

## Technology Stack

- **Language**: Python 3.11+
- **Containerization**: Docker
- **Dependency Management**: pip/requirements.txt
- **Version Control**: Git
- **AI Providers**: OpenAI, Claude, Continue.dev
- **API Framework**: FastAPI
- **Queue System**: Redis-based

## License

[MIT License](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

---

*Updated: July 2, 2025*