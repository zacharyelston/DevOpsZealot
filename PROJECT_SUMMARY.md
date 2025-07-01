# DevOpsZealot Project Summary

## Project Overview

DevOpsZealot is an autonomous AI-powered infrastructure editing tool designed to enable AI agents ("zealots") to make code changes in secure, containerized environments without human intervention. The project follows a "GitOps" approach, ensuring all changes go through a structured pull request workflow with proper validation.

## Key Features

- **AI-Powered Automation**: Integrates with multiple AI providers (OpenAI, Claude, local LLMs) to make intelligent code edits based on requirements
- **Continue.dev Integration**: Advanced AI capabilities through Continue.dev integration via Model Context Protocol (MCP)
- **Security-Focused**: All operations run in isolated Docker containers to maintain security boundaries
- **Full Observability**: Complete audit trail and metrics for all automated actions
- **Validation Pipeline**: Pre-commit hooks and security scanning ensure code quality and safety
- **Multi-Model Support**: Smart selection between different AI providers with fallback capabilities

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

### MCP Server
- JavaScript-based MCP server for Continue.dev integration

## Technology Stack

- **Language**: Python 3.11+
- **Containerization**: Docker
- **Dependency Management**: pip/requirements.txt
- **Version Control**: Git
- **AI Providers**: OpenAI, Claude, Continue.dev
- **API Framework**: FastAPI
- **Queue System**: Redis-based

## Design Philosophy

DevOpsZealot embraces simplicity and modularity, focusing on:

- Clear separation of concerns between components
- Secure execution environments for all operations
- Observable and auditable workflows
- Scalable architecture for handling multiple concurrent tasks

## Current Status

The project is currently in alpha development (version 0.1.0), with active development on core functionality and Continue.dev integration.

## Future Directions

Based on the repository structure and documentation, future developments may include:
- Enhanced documentation (currently empty docs directory)
- Additional AI provider integrations
- Expanded validation capabilities
- Improved monitoring and observability features

---

*Summary created: July 1, 2025*
