# Environment Variables for DevOpsZealot

This document outlines the environment variables used by DevOpsZealot, their purpose, and security best practices.

## Core Environment Variables

| Variable | Required | Description | Example |
|----------|:--------:|-------------|---------|
| `OPENAI_API_KEY` | Yes | Authentication key for OpenAI API access | `sk-...` |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token (PAT) for repository operations | `github_pat_...` |
| `AI_MODEL` | No | Specifies which AI model to use | `gpt-4` |
| `LOG_LEVEL` | No | Controls logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `VERBOSE_LOGGING` | No | Enables additional detailed logs | `true`, `false` |
| `SERVER_MODE` | No | Sets operational mode | `live`, `test` |

## Security Guidelines

### Token Storage

1. **Never commit tokens to version control**:
   - Use `.env` files added to `.gitignore`
   - Use environment variable management systems
   - Use CI/CD secret variables

2. **Token rotation**:
   - Rotate API keys and tokens regularly (30-90 days recommended)
   - Use fine-grained tokens with expiration dates

3. **Least privilege**:
   - GitHub tokens should have minimal required permissions
   - Create dedicated tokens for DevOpsZealot (don't share with other systems)

4. **Detection and response**:
   - Monitor for leaked tokens
   - Have a clear response plan for compromised credentials

## GitHub Token Permissions

The `GITHUB_TOKEN` is the **primary security boundary** for DevOpsZealot. It determines what actions the AI can perform on your repositories.

### Required Permissions

For standard operation, your GitHub token needs:

| Permission | Level | Justification |
|------------|-------|---------------|
| Repository contents | Read & Write | Read files and create commits/branches |
| Pull requests | Read & Write | Create PRs for code review |
| Issues | Read only | Link PRs to existing issues |
| Metadata | Read only | Access basic repo information |

### Explicitly Denied Permissions

Your GitHub token should **NOT** have:

- Admin access
- Delete repository permission
- Workflow management permission
- Secrets management
- Environment management
- Organization management
- User management
- Security settings management

## Setting Up Environment Variables

### Local Development

Create a `.env` file in the DevOpsZealot root directory:

```bash
# API Keys
OPENAI_API_KEY=sk_XXXXXXXXXXXX
GITHUB_TOKEN=github_pat_XXXXXXXXXXXX

# Configuration
AI_MODEL=gpt-4
LOG_LEVEL=INFO
VERBOSE_LOGGING=true
SERVER_MODE=live
```

### Docker Environment

Pass environment variables to Docker using:

```bash
docker run --env-file .env devops-zealot:ai-test
```

Or with individual variables:

```bash
docker run \
  -e OPENAI_API_KEY=sk_XXXXXXXXXXXX \
  -e GITHUB_TOKEN=github_pat_XXXXXXXXXXXX \
  -e AI_MODEL=gpt-4 \
  -e LOG_LEVEL=INFO \
  devops-zealot:ai-test
```

### CI/CD Pipelines

In GitHub Actions workflows:

```yaml
jobs:
  zealot-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run DevOpsZealot
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.ZEALOT_GITHUB_TOKEN }}
          AI_MODEL: gpt-4
        run: ./run_zealot.sh
```

In other CI systems, add environment variables through their respective secret management systems.

## Token Creation Guide

### Creating a GitHub Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set a descriptive name: "DevOpsZealot AI Integration"
4. Set an expiration date (30-90 days recommended)
5. Select the specific repositories or all repositories
6. Set permissions as outlined above
7. Click "Generate token"
8. Copy the token and store it securely

### Creating an OpenAI API Key

1. Log in to the OpenAI platform
2. Go to API keys section
3. Create a new API key with a descriptive name
4. Set usage limits if available
5. Copy the key and store it securely

## Environment Variable Validation

DevOpsZealot validates environment variables on startup:

```
[0;34mValidating environment...[0m
[0;32mFound OPENAI_API_KEY...[0m
[0;32mFound GITHUB_TOKEN...[0m
[0;32mFound LOG_LEVEL=DEBUG...[0m
[0;32mFound AI_MODEL=gpt-4...[0m
```

Missing required variables will result in an error and early termination.

## Security Monitoring

### Log Redaction

Sensitive environment variable values are automatically redacted in logs:

```
[0;33mEnvironment variables set:[0m
  OPENAI_API_KEY=***
  GITHUB_TOKEN=***
  LOG_LEVEL=DEBUG
  AI_MODEL=gpt-4
```

### Token Usage Auditing

DevOpsZealot logs all GitHub API operations for audit purposes:

```
2025-07-01 20:36:18,737 [INFO] Creating branch: ai-improvements-7c71d0133c3a
2025-07-01 20:38:22,045 [INFO] Committing changes with message: DevOpsZealot: Automated script improvements
```

## Conclusion

Proper environment variable management is essential for both functionality and security of DevOpsZealot. By following these guidelines, you can ensure your AI integration operates safely and effectively while maintaining appropriate security boundaries.