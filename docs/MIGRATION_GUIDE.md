# DevOpsZealot Universal Architecture Migration Guide

## Overview

DevOpsZealot has been refactored from a hardcoded, platform-specific implementation to a universal, configuration-driven architecture. This guide explains the changes and how to migrate existing deployments.

## Key Changes

### Before: Hardcoded Dependencies
```python
# Old approach - tightly coupled to specific platforms
from ..ai.openai_client import OpenAIClient
from ..git.operations import GitManager
from ..validation.validator import ValidationPipeline

class ZealotEngine:
    def __init__(self, config: Config):
        self.ai_client = OpenAIClient(config.openai_api_key)
        # GitHub hardcoded in PR creation
        # Docker hardcoded for containers
        # Terraform-specific validation
```

### After: Universal Architecture
```python
# New approach - adapter-based, configuration-driven
from .adapters.base import IssueAdapter, VCSAdapter, LLMAdapter, ContainerAdapter
from .workflows.schema import Workflow, WorkflowMatcher

class UniversalZealotEngine:
    def __init__(self, config: UniversalConfig):
        # Adapters loaded based on configuration
        self.issue_adapter = self._load_adapter('issue', config.issue_source)
        self.vcs_adapter = self._load_adapter('vcs', config.vcs)
        self.llm_adapter = self._load_adapter('llm', config.llm)
        
        # Workflows loaded from configuration files
        self.workflows = WorkflowLoader.load_from_directory(config.workflows_dir)
```

## Architecture Components

### 1. Adapters
Adapters provide abstraction for external systems:

- **IssueAdapter**: Interface for issue tracking (Redmine, Jira, GitHub Issues)
- **VCSAdapter**: Interface for version control (Git, GitLab, Bitbucket)
- **LLMAdapter**: Interface for language models (OpenAI, Claude, Ollama)
- **ContainerAdapter**: Interface for workspaces (Docker, Kubernetes, Local)

### 2. Workflows
Workflows define task execution behavior:

- **Match Criteria**: How to select workflows based on task properties
- **Hooks**: Pre-edit, post-edit, and validation commands
- **Context Templates**: LLM prompts for different file types
- **Configuration**: Per-workflow LLM settings

### 3. Plugins
Plugins extend functionality:

- **CommandPlugin**: Execute shell commands
- **PythonPlugin**: Execute Python code
- **Custom Plugins**: Extend ZealotPlugin base class

## Migration Steps

### Step 1: Update Configuration

Replace old `config.py` environment variables with new configuration:

**Old (.env file):**
```bash
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
DOCKER_SOCKET=/var/run/docker.sock
```

**New (zealot-config.yaml):**
```yaml
issue_source:
  type: "github"
  token: "${GITHUB_TOKEN}"
  
vcs:
  type: "git"
  auth_token: "${GITHUB_TOKEN}"
  
llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  
container:
  type: "docker"
  socket: "/var/run/docker.sock"
```

### Step 2: Create Workflows

Move hardcoded logic to workflow configurations:

**Old (hardcoded in Python):**
```python
if file_path.endswith('.tf'):
    # Terraform-specific validation
    result = terraform_validate(content)
```

**New (workflow configuration):**
```yaml
workflows:
  - name: terraform_workflow
    match:
      file_patterns: ["*.tf"]
    validation:
      - name: terraform_validate
        hooks:
          - command: "terraform validate"
```

### Step 3: Update Task Submission

**Old API:**
```python
task = Task(
    type="infrastructure_edit",
    repository="https://github.com/example/repo",
    files=["main.tf"],
    requirements=["Add S3 bucket"],
    validation_rules=["terraform_validate"]
)
```

**New API:**
```python
task = UniversalTask(
    repository="https://github.com/example/repo",
    files=["main.tf"],
    labels=["terraform"],  # Triggers terraform workflow
    issue_id="123"  # Optional issue reference
)
```

### Step 4: Environment Variables

Update environment variable names:

| Old Variable | New Variable |
|-------------|--------------|
| OPENAI_API_KEY | ZEALOT_LLM_API_KEY |
| GITHUB_TOKEN | ZEALOT_VCS_AUTH_TOKEN |
| REDIS_URL | ZEALOT_REDIS_URL |
| DOCKER_SOCKET | ZEALOT_CONTAINER_SOCKET |

### Step 5: Custom Validations

Convert custom validation code to plugins:

**Old (Python validation):**
```python
class TerraformValidator:
    def validate(self, content):
        # Custom validation logic
```

**New (Plugin):**
```python
class TerraformPlugin(ZealotPlugin):
    async def validate(self, context: PluginContext) -> PluginResult:
        # Same validation logic
        return PluginResult(success=True)
```

## Benefits of Universal Architecture

1. **Platform Independence**: Switch between GitHub/GitLab/Bitbucket without code changes
2. **LLM Flexibility**: Use OpenAI, Claude, or local models via configuration
3. **Extensibility**: Add new workflows and validations without modifying core code
4. **Maintainability**: Clear separation of concerns with adapters
5. **Testability**: Mock adapters for testing

## Example Configurations

### Minimal Configuration
```yaml
workflows_dir: "./workflows"

issue_source:
  type: "github"
  token: "${GITHUB_TOKEN}"

vcs:
  type: "git"

llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"

container:
  type: "local"
```

### Enterprise Configuration
```yaml
workflows_dir: "/etc/zealot/workflows"
plugins_dir: "/etc/zealot/plugins"

issue_source:
  type: "jira"
  endpoint: "https://company.atlassian.net"
  api_token: "${JIRA_TOKEN}"

vcs:
  type: "gitlab"
  endpoint: "https://gitlab.company.com"
  token: "${GITLAB_TOKEN}"

llm:
  provider: "azure_openai"
  endpoint: "${AZURE_ENDPOINT}"
  api_key: "${AZURE_KEY}"

container:
  type: "kubernetes"
  namespace: "zealot"
```

## Troubleshooting

### Issue: Workflow not found
**Solution**: Check workflow match criteria and task labels

### Issue: Adapter loading fails
**Solution**: Verify adapter type in config matches available adapters

### Issue: Environment variables not loaded
**Solution**: Use ZEALOT_ prefix for all environment overrides

## Next Steps

1. Review example configurations in `examples/configs/`
2. Create custom workflows in `examples/workflows/`
3. Implement custom adapters if needed
4. Test with different configurations
5. Monitor performance and adjust

For more information, see the updated documentation in the `docs/` directory.
