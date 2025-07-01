"""Prompt templates for AI code generation"""
from typing import List, Dict, Any, Optional

class PromptTemplates:
    """Manages prompt templates for different file types"""
    
    def __init__(self):
        self.system_prompts = {
            "terraform": """You are an expert Terraform/Infrastructure as Code developer. 
Generate valid HCL code following best practices:
- Use consistent formatting and indentation
- Add descriptive comments for complex resources
- Follow security best practices (least privilege, encryption at rest)
- Ensure backward compatibility
- Use variables for reusable values
- Always output valid JSON with a 'content' field containing the code.""",
            
            "python": """You are an expert Python developer.
Generate clean, maintainable Python code following:
- PEP 8 style guidelines
- Type hints where appropriate
- Comprehensive docstrings
- Error handling
- Security best practices
- Always output valid JSON with a 'content' field containing the code.""",
            
            "yaml": """You are an expert in YAML configuration.
Generate properly formatted YAML following:
- Consistent indentation (2 spaces)
- Proper quoting for strings
- Comments for clarity
- Valid YAML syntax
- Always output valid JSON with a 'content' field containing the YAML.""",
            
            "dockerfile": """You are an expert in Docker and containerization.
Generate optimized Dockerfiles following:
- Multi-stage builds where appropriate
- Security best practices
- Minimal image size
- Proper layer caching
- Always output valid JSON with a 'content' field containing the Dockerfile.""",
            
            "default": """You are an expert software developer.
Generate high-quality code following best practices for the given language.
Always output valid JSON with a 'content' field containing the code."""
        }
        
        self.edit_templates = {
            "terraform": """Current Terraform Configuration:
```hcl
{current_content}
```

Requirements:
{requirements}

Context:
- Repository: {repository}
- File: {file_path}

Instructions:
1. Analyze the current configuration
2. Implement ALL requested changes
3. Maintain existing code style and patterns
4. Add comments explaining significant changes
5. Ensure the configuration remains valid
6. Follow Terraform best practices

Generate the complete updated configuration.

Output as JSON:
{
  "content": "complete updated terraform code here",
  "summary": "brief description of changes",
  "changes_made": ["list", "of", "specific", "changes"]
}""",

            "python": """Current Python Code:
```python
{current_content}
```

Requirements:
{requirements}

Context:
- Repository: {repository}
- File: {file_path}

Instructions:
1. Analyze the current code
2. Implement ALL requested changes
3. Maintain existing code style
4. Preserve all imports and dependencies
5. Add/update docstrings as needed
6. Ensure code remains functional

Generate the complete updated code.

Output as JSON:
{
  "content": "complete updated python code here",
  "summary": "brief description of changes",
  "changes_made": ["list", "of", "specific", "changes"]
}""",

            "yaml": """Current YAML Configuration:
```yaml
{current_content}
```

Requirements:
{requirements}

Context:
- Repository: {repository}
- File: {file_path}

Instructions:
1. Analyze the current YAML
2. Implement ALL requested changes
3. Maintain proper YAML formatting
4. Preserve comments where valuable
5. Ensure valid YAML syntax

Generate the complete updated YAML.

Output as JSON:
{
  "content": "complete updated yaml here",
  "summary": "brief description of changes",
  "changes_made": ["list", "of", "specific", "changes"]
}""",

            "default": """Current Content:
```
{current_content}
```

Requirements:
{requirements}

Context:
- Repository: {repository}
- File: {file_path}

Generate the complete updated content.

Output as JSON:
{
  "content": "complete updated content here",
  "summary": "brief description of changes",
  "changes_made": ["list", "of", "specific", "changes"]
}"""
        }
        
        self.validation_template = """Review this code change:

Original:
```{file_type}
{original}
```

Modified:
```{file_type}
{modified}
```

Requirements that should be met:
{requirements}

Validate that:
1. All requirements are properly implemented
2. No unintended changes were made
3. The code follows best practices
4. There are no security vulnerabilities introduced
5. The change is minimal and focused

Output as JSON:
{
  "valid": true/false,
  "meets_requirements": true/false,
  "issues": ["list of any issues found"],
  "suggestions": ["list of improvement suggestions"],
  "security_concerns": ["list of security issues if any"]
}"""
    
    def get_system_prompt(self, file_type: str) -> str:
        """Get system prompt for file type"""
        return self.system_prompts.get(file_type, self.system_prompts["default"])
    
    def build_edit_prompt(self,
                         file_type: str,
                         current_content: str,
                         requirements: List[str],
                         context: Optional[Dict[str, Any]] = None) -> str:
        """Build edit prompt for file type"""
        template = self.edit_templates.get(file_type, self.edit_templates["default"])
        
        # Format requirements
        formatted_requirements = "\n".join(f"{i+1}. {req}" for i, req in enumerate(requirements))
        
        # Get context values
        context = context or {}
        repository = context.get("repository", "unknown")
        file_path = context.get("file_path", "unknown")
        
        return template.format(
            current_content=current_content,
            requirements=formatted_requirements,
            repository=repository,
            file_path=file_path
        )
    
    def build_validation_prompt(self,
                               original: str,
                               modified: str,
                               requirements: List[str],
                               file_type: str) -> str:
        """Build validation prompt"""
        formatted_requirements = "\n".join(f"- {req}" for req in requirements)
        
        return self.validation_template.format(
            file_type=file_type,
            original=original,
            modified=modified,
            requirements=formatted_requirements
        )
