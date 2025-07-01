# GitHub Integration for DevOpsZealot

## Security Model

DevOpsZealot implements a security-first approach to GitHub integration by using limited-scope API tokens with carefully restricted permissions. This document outlines the security model, token management, and repository standards.

## GitHub Token (`GITHUB_TOKEN`) Purpose

The GitHub token is the **primary security boundary** that limits what actions DevOpsZealot can perform on your repositories. By carefully restricting token permissions, you can ensure that automated AI-powered code modifications follow your organization's security policies.

## Token Permission Standards

### Recommended GitHub Token Scope

For optimal security, tokens used with DevOpsZealot should have **only** the following permissions:

| Permission | Level | Purpose |
|------------|-------|---------|
| Repository contents | Read & Write | Allow reading files and creating commits/branches |
| Pull requests | Read & Write | Enable creation of PRs for review |
| Issues | Read only | Allow linking PRs to issues |
| Metadata | Read only | Basic repository information |

### What to Explicitly Deny

Your GitHub tokens should **NOT** have permissions for:

- Repository deletion
- Admin access
- Workflow/Actions management
- Organization management
- User management
- Webhooks or security settings

## Token Creation Guidelines

1. Create fine-grained personal access tokens (PATs) instead of classic tokens
2. Set appropriate expiration dates (30-90 days recommended)
3. Restrict to specific repositories when possible
4. Document token purpose in its description (e.g., "DevOpsZealot AI Integration")
5. Rotate tokens regularly following security best practices

## Environment Variable Management

Store the GitHub token securely as an environment variable:

```bash
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxx
```

Never commit the actual token value to any repository. Use:
- `.env` files (added to `.gitignore`)
- CI/CD secret variables
- Environment variable management systems

## Branch Protection Requirements

Repositories using DevOpsZealot should implement these branch protection rules:

1. **Protected Default Branches**: `main`/`master` branches should require pull request reviews
2. **Required Reviews**: At least 1 review before merging
3. **Status Checks**: Require passing CI/CD checks before merging
4. **Branch Name Patterns**: Configure DevOpsZealot to use standardized branch name prefixes (`zealot/`, `ai-improvements/`)

## Pull Request Workflow

DevOpsZealot will follow this standard PR workflow:

1. Create a new branch with an appropriate naming convention
2. Make changes according to the specified requirements
3. Commit changes with detailed, structured messages (see "Commit Message Format" below)
4. Open a pull request with an AI-generated summary
5. Add appropriate labels and assignees (if configured)
6. Wait for human review and approval

## Commit Message Format

DevOpsZealot generates structured, informative commit messages that provide clear context about AI-driven changes:

```
DevOpsZealot: {Task Type} - {Key Changes Summary}

Files modified: file1.sh, file2.sh

## Changes Summary
This commit implements improvements to the {task type} as specified in the requirements.

## Requirements Implemented
- Requirement 1
- Requirement 2
- Requirement 3

## Validation
Changes have been validated against:
- validation_rule_1
- validation_rule_2
```

This detailed format:
- Makes code reviews more efficient by clearly stating the purpose and scope
- Creates a clear audit trail of AI-driven changes
- Connects changes to specific requirements
- Documents validation methods used
- Improves repository history and changelog generation

## Repository Standards for DevOpsZealot Integration

### Required Repository Structure

Repositories that will be managed by DevOpsZealot should follow these standards:

1. **Documentation**: Include README with repository purpose and structure
2. **Validation Tools**: Include linters, tests, or other validation tools
3. **CI Configuration**: Automated testing of changes
4. **Branch Protection**: As outlined above

### Repository Configuration File

Add a `.devopszealot.yml` file to the repository root to configure DevOpsZealot behavior:

```yaml
# DevOpsZealot Configuration
version: 1

# Branch naming settings
branches:
  prefix: "zealot/"
  include_date: true  # Adds YYYYMMDD to branch names

# Pull request settings
pull_requests:
  auto_create: true
  assignees: ["team-lead", "senior-dev"]
  labels: ["ai-improvement", "needs-review"]
  
# Access control
access:
  allowed_paths:
    - "src/"
    - "scripts/"
    - "docs/"
  restricted_paths:
    - "config/security/"
    - "credentials/"

# Validation requirements
validation:
  run_tests: true
  linter_checks: true
  required_approvals: 1
```

## Audit and Monitoring

All actions performed by DevOpsZealot using GitHub tokens should be:

1. Logged with detailed timestamps and operations
2. Subject to regular audit reviews
3. Monitored for unusual activity patterns
4. Able to be revoked immediately if suspicious activity is detected

## Conclusion

By following these guidelines, your organization can safely leverage DevOpsZealot's AI-powered improvements while maintaining security best practices and ensuring all changes undergo appropriate human review.