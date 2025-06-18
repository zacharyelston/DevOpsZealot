import json
import os
from pathlib import Path
from typing import Optional
from openai import OpenAI

class AICodeAgent:
    """AI agent for analyzing and modifying code using OpenAI."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
    
    def modify_code(self, file_path: str, current_content: str, prompt: str, context: Optional[str] = None) -> str:
        """
        Analyze and modify code based on the given prompt.
        
        Args:
            file_path: Path to the file being modified
            current_content: Current content of the file
            prompt: User's modification request
            context: Additional context about the codebase
            
        Returns:
            Modified code content
        """
        try:
            # Determine file type
            file_extension = Path(file_path).suffix
            language = self._get_language_from_extension(file_extension)
            
            # Build the system prompt
            system_prompt = f"""You are an expert software engineer specializing in code analysis and modification.
Your task is to modify the provided {language} code according to the user's instructions.

Guidelines:
1. Preserve the original code structure and style as much as possible
2. Make only the necessary changes to fulfill the request
3. Ensure the modified code is syntactically correct and follows best practices
4. Add appropriate comments for significant changes
5. Maintain existing functionality unless explicitly asked to change it
6. Consider security implications and avoid introducing vulnerabilities

File: {file_path}
Language: {language}

Return only the modified code without any explanations or markdown formatting."""

            # Build the user prompt
            user_prompt = f"""Current code:
```{language}
{current_content}
```

Context: {context if context else 'No additional context provided'}

Instructions: {prompt}

Please modify the code according to the instructions and return only the complete modified code."""

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                
                modified_code = response.choices[0].message.content
                if not modified_code:
                    return current_content
                
                modified_code = modified_code.strip()
                
                # Clean up the response (remove markdown if present)
                if modified_code.startswith("```"):
                    lines = modified_code.split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].strip() == "```":
                        lines = lines[:-1]
                    modified_code = '\n'.join(lines)
                
                return modified_code
                
            except Exception as e:
                raise Exception(f"Failed to get AI response: {str(e)}")
        
        except Exception as e:
            raise Exception(f"Error in modify_code: {str(e)}")
    
    def _get_language_from_extension(self, extension: str) -> str:
        """Get the programming language name from file extension."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript (React)',
            '.tsx': 'TypeScript (React)',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.json': 'JSON',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.sql': 'SQL',
            '.sh': 'Shell Script',
            '.bat': 'Batch Script',
            '.ps1': 'PowerShell',
            '.md': 'Markdown',
            '.dockerfile': 'Dockerfile',
            '.tf': 'Terraform',
            '.vue': 'Vue.js',
            '.r': 'R',
            '.m': 'MATLAB',
            '.pl': 'Perl',
            '.lua': 'Lua',
            '.dart': 'Dart',
        }
        
        return language_map.get(extension.lower(), 'Text')
