# DevOpsZealot with Continue.dev Integration

An autonomous AI-powered infrastructure editing tool that now integrates with Continue.dev for enhanced AI capabilities and developer experience.

## 🚀 What's New

- **Multi-Model AI Support**: Seamlessly switch between OpenAI, Claude, and local models
- **Continue.dev Integration**: Use Continue's advanced features while maintaining autonomous operation
- **MCP Server**: Connect Continue.dev to DevOpsZealot via Model Context Protocol
- **Hybrid Architecture**: Best of both worlds - autonomous infrastructure management with enhanced AI

## Overview

DevOpsZealot allows AI agents (zealots) to:
- Checkout infrastructure code from Git repositories
- Make intelligent edits based on requirements using multiple AI providers
- Validate changes using industry-standard tools
- Commit and push changes via pull requests
- Operate completely autonomously with full observability
- **NEW**: Integrate with Continue.dev for enhanced development workflows

## Key Features

### Core Features
- 🤖 **AI-Powered**: Now with multi-model support (OpenAI, Claude, local models)
- 🔒 **Secure**: All operations in isolated Docker containers
- 🔍 **Observable**: Complete audit trail and metrics
- ✅ **Validated**: Pre-commit hooks and security scanning
- 🔄 **GitOps**: All changes through PR workflow
- 📊 **Monitored**: Prometheus metrics and structured logging

### Continue.dev Integration
- 🎯 **Smart Model Selection**: Automatically chooses the best AI model for each task
- 🔧 **MCP Support**: Full Model Context Protocol integration
- 💻 **IDE Integration**: Use Continue in VS Code while DevOpsZealot handles automation
- 📈 **Performance Tracking**: Monitor AI provider performance and costs
- 🔄 **Fallback Support**: Automatic failover between AI providers

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Continue.dev  │────▶│   MCP Server    │────▶│  DevOpsZealot   │
│   (IDE/Local)   │     │   (Bridge)      │     │   (Server)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         │                                                ▼
         │                                        ┌─────────────────┐
         │                                        │  Hybrid AI      │
         │                                        │  ┌─────────┐   │
         └───────────────────────────────────────▶│  │Continue │   │
                                                  │  │Engine   │   │
                                                  │  └─────────┘   │
                                                  │  ┌─────────┐   │
                                                  │  │OpenAI   │   │
                                                  │  │Client   │   │
                                                  │  └─────────┘   │
                                                  └─────────────────┘
```

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/zacharyelston/DevOpsZealot.git
cd DevOpsZealot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Edit .env with your configuration
# Required:
OPENAI_API_KEY=your-key-here
GITHUB_TOKEN=your-token-here

# Optional Continue.dev settings:
ENABLE_CONTINUE_INTEGRATION=true
CONTINUE_DEFAULT_MODEL=gpt-4
USE_LOCAL_MODELS=false
PREFER_LOCAL_MODELS=false
```

### 3. Install Continue.dev Extension

1. Install Continue in VS Code:
   ```bash
   code --install-extension Continue.continue
   ```

2. Copy the Continue configuration:
   ```bash
   cp -r .continue ~/.continue
   ```

3. Install MCP server dependencies:
   ```bash
   cd mcp
   npm install
   cd ..
   ```

### 4. Start Services

```bash
# Start Redis (required)
docker run -d -p 6379:6379 redis:alpine

# Start DevOpsZealot server
python -m zealot.server

# In another terminal, start MCP server (optional, for Continue integration)
cd mcp
npm start
```

## Usage

### Via API (Autonomous Mode)

```python
import httpx

# Create a task
response = httpx.post("http://localhost:8080/api/v1/tasks", json={
    "repository": "https://github.com/your/repo",
    "files": ["terraform/main.tf"],
    "requirements": ["Enable encryption", "Add monitoring"],
    "ai_provider": "auto"  # or "continue", "openai"
})

task_id = response.json()["task_id"]
```

### Via Continue.dev (Interactive Mode)

1. Open your infrastructure code in VS Code
2. Use slash commands:
   - `/zealot-task` - Create a DevOpsZealot task
   - `/validate-tf` - Validate Terraform
   - `/security-scan` - Run security analysis

3. Or use the MCP integration:
   - Type `@` and select "MCP"
   - Choose DevOpsZealot resources or tools

### Via Demo Script

```bash
python examples/demo_hybrid.py
```

## API Endpoints

### Tasks
- `POST /api/v1/tasks` - Create a new task
- `GET /api/v1/tasks/{task_id}` - Get task status
- `GET /api/v1/tasks` - List all tasks

### AI Integration
- `GET /api/v1/ai/stats` - Get AI provider statistics
- `POST /api/v1/ai/analyze` - Analyze codebase

### MCP Integration
- `GET /mcp/resource` - Get MCP resources
- `POST /mcp/tool` - Execute MCP tools
- `GET /mcp/config` - Get MCP configuration

## Configuration

### AI Provider Selection

The hybrid client automatically selects the best AI provider based on:

1. **Task Type**: Different models for different tasks
   - Terraform editing → GPT-4
   - Validation → Claude
   - Documentation → Claude

2. **Performance**: Tracks success rates and response times

3. **Availability**: Automatic fallback if primary fails

### Custom Model Routing

Edit task routing in config:

```python
task_routing = {
    'terraform': ModelProvider.CONTINUE,
    'python': ModelProvider.CONTINUE,
    'validation': ModelProvider.CONTINUE,
    'documentation': ModelProvider.OPENAI,
}
```

## Continue.dev Features

### Available MCP Resources
- `zealot://tasks/active` - Active tasks
- `zealot://tasks/history` - Task history
- `zealot://templates/infrastructure` - Infrastructure templates
- `zealot://validation/rules` - Validation rules

### Available MCP Tools
- `create_infrastructure_task` - Create new tasks
- `validate_infrastructure_code` - Validate code
- `get_task_status` - Check task status
- `analyze_infrastructure_drift` - Analyze drift

### Available Prompts
- `terraform_security_hardening` - Security best practices
- `kubernetes_resource_optimization` - Resource optimization
- `infrastructure_documentation` - Generate docs

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_hybrid_client.py
```

### Adding New AI Providers

1. Implement provider in `src/ai/continue_integration/`
2. Add to `HybridAIClient`
3. Update routing rules
4. Add tests

### Creating Custom MCP Tools

1. Add tool definition in `mcp_bridge.py`
2. Implement handler
3. Update MCP server
4. Add to Continue config

## Performance Monitoring

Check AI provider performance:

```bash
curl http://localhost:8080/api/v1/ai/stats
```

Response:
```json
{
  "providers": {
    "continue": {
      "total_calls": 42,
      "success_rate": 0.952,
      "average_time": 2.3,
      "performance_score": 0.85
    },
    "openai": {
      "total_calls": 38,
      "success_rate": 0.974,
      "average_time": 1.8,
      "performance_score": 0.92
    }
  }
}
```

## Troubleshooting

### Continue.dev Connection Issues
- Ensure MCP server is running: `cd mcp && npm start`
- Check Continue config: `~/.continue/config.json`
- Verify API is accessible: `curl http://localhost:8080/health`

### AI Provider Failures
- Check API keys in `.env`
- Verify network connectivity
- Check provider-specific rate limits
- Review logs for detailed errors

### Performance Issues
- Monitor AI provider stats
- Adjust `prefer_local_models` setting
- Configure task routing rules
- Consider using local models for non-critical tasks

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Create Pull Request

## Roadmap

- [ ] Continue SDK integration (when available)
- [ ] Advanced model routing algorithms
- [ ] Cost optimization features
- [ ] Real-time collaboration features
- [ ] Extended MCP capabilities
- [ ] Plugin system for custom validators
