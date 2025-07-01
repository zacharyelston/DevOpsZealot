"""OpenAI client for code generation"""
import asyncio
import json
from typing import Dict, Any, List, Optional
import openai
from openai import AsyncOpenAI
import structlog
import tiktoken

from .prompts import PromptTemplates

logger = structlog.get_logger()

class OpenAIClient:
    """OpenAI API client for code generation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.prompt_templates = PromptTemplates()
        self._encoding = tiktoken.encoding_for_model("gpt-4")
        
        logger.info("OpenAI client initialized", model=model)
    
    async def generate_edit(self, 
                          current_content: str,
                          requirements: List[str],
                          file_type: str,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate code edit based on requirements"""
        
        # Build prompt
        system_prompt = self.prompt_templates.get_system_prompt(file_type)
        user_prompt = self.prompt_templates.build_edit_prompt(
            file_type=file_type,
            current_content=current_content,
            requirements=requirements,
            context=context
        )
        
        # Count tokens
        prompt_tokens = self._count_tokens(system_prompt + user_prompt)
        logger.info("Generating edit", 
                   file_type=file_type,
                   prompt_tokens=prompt_tokens,
                   requirements_count=len(requirements))
        
        try:
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate response structure
            if "content" not in result:
                raise ValueError("Invalid response: missing 'content' field")
            
            # Add metadata
            result['model'] = self.model
            result['tokens_used'] = {
                'prompt': prompt_tokens,
                'completion': response.usage.completion_tokens,
                'total': response.usage.total_tokens
            }
            
            logger.info("Edit generated successfully",
                       tokens_used=result['tokens_used']['total'])
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response", error=str(e))
            raise ValueError(f"Invalid JSON response from AI: {e}")
            
        except openai.APIError as e:
            logger.error("OpenAI API error", 
                        error=str(e),
                        status_code=getattr(e, 'status_code', None))
            raise
            
        except Exception as e:
            logger.error("Unexpected error generating edit", error=str(e))
            raise
    
    async def validate_changes(self,
                             original: str,
                             modified: str,
                             requirements: List[str],
                             file_type: str) -> Dict[str, Any]:
        """Use AI to validate that changes meet requirements"""
        
        validation_prompt = self.prompt_templates.build_validation_prompt(
            original=original,
            modified=modified,
            requirements=requirements,
            file_type=file_type
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code review expert. Analyze changes and ensure they meet requirements."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "valid": result.get("valid", False),
                "meets_requirements": result.get("meets_requirements", False),
                "issues": result.get("issues", []),
                "suggestions": result.get("suggestions", [])
            }
            
        except Exception as e:
            logger.error("Validation failed", error=str(e))
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def generate_commit_message(self, changes: List[Dict[str, Any]]) -> str:
        """Generate a commit message from changes"""
        
        # Summarize changes
        summary_prompt = self._build_commit_prompt(changes)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Generate concise, informative commit messages."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("Failed to generate commit message", error=str(e))
            # Fallback message
            return f"AI: Updated {len(changes)} files"
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self._encoding.encode(text))
    
    def _build_commit_prompt(self, changes: List[Dict[str, Any]]) -> str:
        """Build prompt for commit message generation"""
        changes_summary = []
        
        for change in changes:
            changes_summary.append(f"- {change['file']}: {change.get('summary', 'Modified')}")
        
        return f"""Generate a commit message for these changes:

Files changed:
{chr(10).join(changes_summary)}

Format:
- First line: concise summary (50 chars max)
- Empty line
- Bullet points with key changes
- Keep it informative but brief
"""
    
    async def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate API cost for tokens used"""
        # GPT-4 pricing (as of 2024)
        prompt_cost = (prompt_tokens / 1000) * 0.03  # $0.03 per 1K tokens
        completion_cost = (completion_tokens / 1000) * 0.06  # $0.06 per 1K tokens
        
        return round(prompt_cost + completion_cost, 4)
