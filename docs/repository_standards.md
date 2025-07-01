# Repository Standards for DevOpsZealot Integration

This document outlines the standards and best practices for repositories that will be managed by DevOpsZealot's AI-powered code improvement capabilities.

## Core Repository Requirements

### Minimum Repository Structure

```
repository-root/
├── .github/                        # GitHub-specific configurations
│   ├── workflows/                  # CI/CD workflow definitions
│   └── CODEOWNERS                  # Define ownership for review routing
├── .devopszealot/                  # DevOpsZealot configuration
│   ├── config.yml                  # Main configuration
│   └── templates/                  # Custom templates for PRs, commits, etc.
├── docs/                           # Documentation
│   └── README.md                   # Project documentation
├── src/ or lib/                    # Source code
├── tests/                          # Test suite
├── .gitignore                      # Specify intentionally untracked files
└── README.md                       # Repository overview
```

### Required Files

1. **README.md**: Must include:
   - Project purpose and overview
   - Installation/setup instructions
   - Usage examples
   - Contribution guidelines

2. **LICENSE**: Clear license information

3. **.gitignore**: Properly configured to exclude:
   - Environment files (.env)
   - Build artifacts
   - Dependency directories
   - Local configuration

4. **CI Configuration**: Automated tests that run on pull requests

### DevOpsZealot Configuration

Add a `.devopszealot/config.yml` file to customize the AI integration:

```yaml
version: 1

# Repository metadata
repository:
  name: "Your Project Name"
  description: "Brief description of the repository's purpose"
  maintainers:
    - "username1"
    - "username2"

# Branch and PR management
branching:
  prefix: "zealot/"
  naming_convention: "{prefix}{task_type}-{description}-{date}"
  branch_from: "main"  # Branch to use as base

# Pull request settings
pull_requests:
  title_template: "DevOpsZealot: {task_type} - {description}"
  auto_create: true
  draft: true  # Start as draft PR
  reviewers:
    - "senior-dev"
    - "team-lead"
  labels:
    - "ai-assisted"
    - "needs-review"

# Task definition 
tasks:
  allowed_types:
    - "bugfix"
    - "refactor"
    - "docs"
    - "test"
    - "feature"
  
# Access controls
access:
  allowed_paths:
    - "src/"
    - "lib/"
    - "docs/"
    - "tests/"
  restricted_paths:
    - "config/credentials/"
    - ".github/workflows/"
    - "security/"

# Validation requirements
validation:
  required_tests: true
  linter_checks: true
  validation_commands:
    - "npm test"        # Example for Node.js project
    - "npm run lint"    # Example linting command
```

## Code Quality Standards

### Documentation Standards

1. **Module Documentation**: Every module should have a header comment explaining its purpose
2. **Function Documentation**: Functions should have docstrings explaining parameters and return values
3. **Complex Logic**: Document any complex algorithms or business logic
4. **TODO/FIXME**: Clearly mark areas needing improvement with standardized tags

### Testing Requirements

1. **Test Coverage**: Minimum 70% code coverage for core functionality
2. **Unit Tests**: For individual functions and methods
3. **Integration Tests**: For module interactions
4. **Test Fixtures**: Standardized test data
5. **Mocking**: Clear separation between tests and external services

### Error Handling

1. **Consistent Error Pattern**: Standardized error handling approach
2. **Logging**: Appropriate log levels for different error types
3. **User Messages**: Clear error messages for end users
4. **Recovery**: Graceful recovery from expected error conditions

## Git Workflow Standards

### Commit Standards

1. **Atomic Commits**: Each commit should represent a single logical change

2. **Standard Commit Messages**: Follow conventional commits format:
   ```
   type(scope): description
   
   [optional body]
   
   [optional footer]
   ```

3. **AI-Generated Commit Messages**: DevOpsZealot uses a comprehensive format:
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
   
4. **Signed Commits**: Consider requiring commit signing

### Branch Strategy

1. **Main Branches**: 
   - `main` or `master`: Production-ready code
   - `develop`: Integration branch (optional)
   
2. **Feature Branches**:
   - From: `develop` or `main`
   - Naming: `feature/description`
   
3. **DevOpsZealot Branches**:
   - From: `develop` or `main`
   - Naming: `zealot/task-type-description`
   
4. **Release Branches** (if applicable):
   - From: `develop`
   - Naming: `release/version`

### Pull Request Process

1. **Required Information**:
   - Clear description of changes
   - Reference to issues being addressed
   - Testing performed
   - Screenshots (if UI changes)
   
2. **Review Process**:
   - At least one approval from code owners
   - All CI checks passing
   - No unresolved comments
   
3. **Merge Strategy**:
   - Squash and merge (preferred for feature branches)
   - Rebase and merge (for small changes)
   - No fast-forward merges

## Security Standards

### Code Security

1. **Dependency Management**:
   - Regular updates of dependencies
   - Vulnerability scanning
   - Lock files committed to repository
   
2. **Secret Management**:
   - No hardcoded secrets
   - Use environment variables
   - Secrets stored in appropriate vault systems
   
3. **Access Control**:
   - Principle of least privilege
   - Clear permission boundaries
   - Regular access reviews

### Infrastructure Security (if applicable)

1. **Infrastructure as Code**:
   - Version controlled
   - Peer reviewed
   - Validated with appropriate tools
   
2. **Deployment Security**:
   - Immutable infrastructure
   - Secure defaults
   - Regular security scanning

## DevOpsZealot Specific Guidelines

### AI-Safe Code Patterns

1. **Modular Design**: Smaller, focused files are easier for AI to understand and modify
2. **Clear Function Names**: Descriptive function names help AI understand purpose
3. **Type Annotations**: When applicable, use strong typing to guide AI
4. **Comments**: Strategic comments to explain "why" not just "what"
5. **Configuration Separation**: Keep configuration and code separate

### Tasks Appropriate for DevOpsZealot

DevOpsZealot excels at:

1. **Refactoring**: Improving code structure without changing behavior
2. **Documentation**: Adding or improving comments and docs
3. **Test Coverage**: Adding missing tests
4. **Error Handling**: Improving robustness
5. **Performance Optimization**: Non-architectural improvements

### Tasks Not Suitable for DevOpsZealot

Avoid using DevOpsZealot for:

1. **Security-Critical Code**: Authentication, encryption, authorization
2. **Major Architectural Changes**: Significant design pattern changes
3. **Business Logic Modifications**: Core algorithm changes
4. **UI/UX Design**: Creative design decisions
5. **Infrastructure Management**: Cloud resource configuration

## Implementation Checklist

- [ ] Repository structure follows standard layout
- [ ] `.devopszealot/config.yml` created and configured
- [ ] Branch protections enabled on GitHub
- [ ] CI pipeline validates all pull requests
- [ ] CODEOWNERS file configured
- [ ] Documentation requirements satisfied
- [ ] GitHub Token created with appropriate permissions
- [ ] Security scanning integrated into pipeline
- [ ] Review process documented and configured
- [ ] Team members trained on DevOpsZealot workflow

## Conclusion

Following these standards ensures your repository is optimized for DevOpsZealot AI integration, maintains high code quality, and follows security best practices while leveraging the power of AI-assisted development.