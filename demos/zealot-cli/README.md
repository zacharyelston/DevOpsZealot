# Zealot CLI

A simplified, clean interface for AI-driven code generation and validation with DevOpsZealot.

## Overview

Zealot CLI provides a straightforward way to generate code using AI and validate it against standards. It simplifies the process by:

- Using standardized context files
- Explicitly setting branch names and repositories
- Providing a clean interface for common operations
- Separating configuration from code generation logic

## Installation

1. Clone this repository
2. Make the `bin/zealot` script executable:
   ```bash
   chmod +x ./bin/zealot
   ```
3. Create a `.env` file in the `configs` directory with your API keys (a template will be generated on first run)

## Usage

### Basic Commands

```bash
# Generate code using a context file
./bin/zealot generate --context=whisper-mp4.json

# Specify a branch (overrides context file)
./bin/zealot generate --context=whisper-mp4.json --branch=feature/my-branch

# Generate and validate in one step
./bin/zealot generate --context=whisper-mp4.json --validate

# Just validate existing code
./bin/zealot validate --context=whisper-mp4.json

# Show help
./bin/zealot help
```

### Context Files

Context files are JSON files that describe the task for the AI. They should be placed in the `configs` directory.

A standard context file has this structure:

```json
{
  "task": {
    "type": "script_creation",
    "repository": "https://github.com/username/repo.git",
    "branch": "feature/branch-name",
    "name": "Task Name",
    "description": "Task description",
    "objective": "Clear objective statement",
    "details": "Detailed task requirements",
    "target_file": "output_file.sh",
    "requirements": [
      "Requirement 1",
      "Requirement 2"
    ],
    "validation_rules": [
      "shellcheck",
      "script_execution_test"
    ],
    "dependencies": [
      "dependency1",
      "dependency2"
    ]
  },
  "metadata": {
    "version": "1.0",
    "created_at": "YYYY-MM-DDThh:mm:ss-00:00",
    "format": "zealot-context-v1"
  }
}
```

## Directory Structure

```
zealot-cli/
├── bin/                # CLI scripts
│   └── zealot          # Main CLI entry point
├── configs/            # Context files and environment configuration
│   ├── .env            # API keys and environment settings
│   └── whisper-mp4.json # Example context file
├── templates/          # Template files for new projects
└── docs/              # Additional documentation
```

## Benefits Over Previous Approach

- **Clarity**: Clear separation of concerns and standardized interfaces
- **Flexibility**: Explicit control over branches and repositories
- **Maintainability**: Simpler codebase with better organization
- **User Experience**: Consistent command structure and helpful output
- **Future-proof**: Versioned context file format for backward compatibility

## Requirements

- Docker
- jq (for JSON processing)
- Bash 4.0 or higher
