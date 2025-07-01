"""
Continue.dev AI Engine for DevOpsZealot
Uses Continue's model management and context capabilities
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
import httpx
import structlog
from dataclasses import dataclass
from pathlib import Path

logger = structlog.get_logger()

@dataclass
class ContinueConfig:
    """Configuration for Continue integration"""
    continue_config_path: str = "~/.continue/config.json"
    api_url: str = "http://localhost:11434"  # Local Continue API
    default_model: str = "gpt-4"
    fallback_model: str = "claude-3-opus"
    use_local_models: bool = False
    local_model_path: Optional[str] = None
    
class ContinueAIEngine:
    """
    Continue.dev AI engine implementation
    Provides multi-model support and enhanced context management
    """
    
    def __init__(self, config: ContinueConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=120.0)
        self._model_cache = {}
        self._load_continue_config()
        
        logger.info("ContinueAIEngine initialized", 
                   default_model=config.default_model,
                   use_local=config.use_local_models)
    
    def _load_continue_config(self):
        """Load Continue's configuration to get available models"""
        config_path = Path(self.config.continue_config_path).expanduser()
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    continue_config = json.load(f)
                    self._model_cache = {
                        model.get('title', model['model']): model
                        for model in continue_config.get('models', [])
                    }
                    logger.info(f"Loaded {len(self._model_cache)} models from Continue config")
            else:
                logger.warning("Continue config not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load Continue config: {e}")
    
    async def generate_edit(self, 
                          current_content: str,
                          requirements: List[str],
                          file_type: str,
                          context: Optional[Dict[str, Any]] = None,
                          model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate code edit using Continue's model infrastructure
        
        Args:
            current_content: Current file content
            requirements: List of requirements for the edit
            file_type: Type of file (terraform, python, yaml, etc.)
            context: Additional context (repository, metadata)
            model_override: Override default model selection
        
        Returns:
            Dict with 'content', 'summary', 'tokens_used', etc.
        """
        model = model_override or self._select_model_for_task(file_type)
        
        logger.info(f"Generating edit with model: {model}", 
                   file_type=file_type,
                   requirements_count=len(requirements))
        
        # Build structured prompt
        prompt = self._build_edit_prompt(
            current_content=current_content,
            requirements=requirements,
            file_type=file_type,
            context=context
        )
        
        try:
            # Try primary model
            response = await self._call_model(model, prompt)
            
            if response and response.get('success'):
                return self._parse_edit_response(response, model)
            
            # Fallback to secondary model if primary fails
            logger.warning(f"Primary model {model} failed, trying fallback")
            fallback_response = await self._call_model(
                self.config.fallback_model, 
                prompt
            )
            
            if fallback_response and fallback_response.get('success'):
                return self._parse_edit_response(fallback_response, self.config.fallback_model)
            
            raise ValueError("Both primary and fallback models failed")
            
        except Exception as e:
            logger.error(f"Generate edit failed: {e}")
            raise
    
    async def validate_changes(self,
                             original: str,
                             modified: str,
                             requirements: List[str],
                             file_type: str) -> Dict[str, Any]:
        """
        Use AI to validate that changes meet requirements
        Uses a different model optimized for validation
        """
        # Use a model better suited for validation/review
        validation_model = self._select_model_for_task(file_type, task_type='validation')
        
        prompt = self._build_validation_prompt(
            original=original,
            modified=modified,
            requirements=requirements,
            file_type=file_type
        )
        
        try:
            response = await self._call_model(validation_model, prompt, temperature=0.1)
            
            if response and response.get('success'):
                result = json.loads(response['content'])
                return {
                    "valid": result.get("valid", False),
                    "meets_requirements": result.get("meets_requirements", False),
                    "issues": result.get("issues", []),
                    "suggestions": result.get("suggestions", []),
                    "model_used": validation_model
                }
            
            return {
                "valid": False,
                "error": "Validation model failed to respond",
                "model_used": validation_model
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def generate_documentation(self, 
                                   code: str, 
                                   file_type: str,
                                   style: str = "technical") -> str:
        """
        Generate documentation for code
        Uses a model optimized for documentation
        """
        doc_model = self._select_model_for_task(file_type, task_type='documentation')
        
        prompt = f"""Generate {style} documentation for this {file_type} code:

```{file_type}
{code}
```

Include:
- Purpose and overview
- Key components/resources
- Configuration options
- Usage examples
- Important notes or warnings
"""
        
        response = await self._call_model(doc_model, prompt, temperature=0.7)
        
        if response and response.get('success'):
            return response['content']
        
        return "Documentation generation failed"
    
    def _select_model_for_task(self, file_type: str, task_type: str = 'edit') -> str:
        """
        Select appropriate model based on task and file type
        Implements model routing logic
        """
        # Model selection matrix
        model_matrix = {
            'edit': {
                'terraform': 'gpt-4',  # Better at HCL syntax
                'python': 'claude-3-opus',  # Better at Python patterns
                'yaml': 'gpt-4',
                'dockerfile': 'gpt-4',
                'default': self.config.default_model
            },
            'validation': {
                'terraform': 'claude-3-opus',  # Better at finding security issues
                'python': 'claude-3-opus',
                'yaml': 'gpt-4',
                'dockerfile': 'claude-3-opus',
                'default': 'claude-3-opus'
            },
            'documentation': {
                'default': 'claude-3-opus'  # Generally better at writing
            }
        }
        
        task_models = model_matrix.get(task_type, {})
        selected_model = task_models.get(file_type, task_models.get('default', self.config.default_model))
        
        # Check if model is available in Continue config
        if selected_model not in self._model_cache and not self.config.use_local_models:
            logger.warning(f"Model {selected_model} not in Continue config, using default")
            selected_model = self.config.default_model
        
        return selected_model
    
    async def _call_model(self, model: str, prompt: str, temperature: float = 0.3) -> Dict[str, Any]:
        """
        Call a model through Continue's infrastructure
        
        This is a simplified version - in production, you'd integrate with
        Continue's actual API or use their SDK when available
        """
        # For local models via Ollama
        if self.config.use_local_models:
            return await self._call_local_model(model, prompt, temperature)
        
        # For API-based models
        # In reality, Continue doesn't expose a direct API like this
        # You'd need to either:
        # 1. Use Continue's internal APIs (not recommended)
        # 2. Use the underlying model APIs directly
        # 3. Create a Continue plugin that exposes this functionality
        
        # For this PoC, we'll simulate the API call
        logger.info(f"Calling model {model} through Continue API")
        
        try:
            # Simulated API call structure
            response = await self.client.post(
                f"{self.config.api_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self._get_system_prompt(model)},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "content": response.json()['choices'][0]['message']['content'],
                    "model": model,
                    "tokens": response.json().get('usage', {})
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Model call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _call_local_model(self, model: str, prompt: str, temperature: float) -> Dict[str, Any]:
        """Call a local model through Ollama"""
        try:
            response = await self.client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "format": "json",
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "content": result['response'],
                    "model": model,
                    "tokens": {
                        "total": result.get('total_duration', 0) // 1000000  # Convert ns to ms
                    }
                }
                
        except Exception as e:
            logger.error(f"Local model call failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_edit_prompt(self, current_content: str, requirements: List[str], 
                          file_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build structured prompt for code editing"""
        context_str = ""
        if context:
            context_str = f"\nContext:\n- Repository: {context.get('repository', 'unknown')}\n"
            context_str += f"- File: {context.get('file_path', 'unknown')}\n"
            if 'metadata' in context:
                context_str += f"- Additional info: {json.dumps(context['metadata'], indent=2)}\n"
        
        requirements_str = "\n".join(f"- {req}" for req in requirements)
        
        return f"""You are an expert {file_type} developer. Edit the following code to meet these requirements:

Requirements:
{requirements_str}
{context_str}
Current code:
```{file_type}
{current_content}
```

Provide your response as a JSON object with:
{{
  "content": "the complete modified code",
  "summary": "brief summary of changes made",
  "changes": ["list", "of", "specific", "changes"],
  "confidence": 0.95  // 0-1 confidence score
}}

Ensure the code is complete, valid, and production-ready."""
    
    def _build_validation_prompt(self, original: str, modified: str, 
                               requirements: List[str], file_type: str) -> str:
        """Build prompt for validation"""
        requirements_str = "\n".join(f"- {req}" for req in requirements)
        
        return f"""As a {file_type} expert, validate these code changes against requirements:

Requirements:
{requirements_str}

Original code:
```{file_type}
{original}
```

Modified code:
```{file_type}
{modified}
```

Analyze whether the changes:
1. Meet all stated requirements
2. Maintain code quality and best practices
3. Don't introduce security issues
4. Are properly implemented

Respond with JSON:
{{
  "valid": true/false,
  "meets_requirements": true/false,
  "issues": ["list of issues found"],
  "suggestions": ["improvement suggestions"],
  "security_concerns": ["any security issues"]
}}"""
    
    def _get_system_prompt(self, model: str) -> str:
        """Get appropriate system prompt for model"""
        base_prompt = "You are an expert infrastructure and DevOps engineer with deep knowledge of Terraform, Kubernetes, AWS, and security best practices."
        
        # Model-specific adjustments
        if "claude" in model.lower():
            return base_prompt + " Be concise and precise in your responses."
        elif "gpt" in model.lower():
            return base_prompt + " Provide detailed, well-structured responses."
        else:
            return base_prompt
    
    def _parse_edit_response(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Parse model response into standard format"""
        try:
            content = response['content']
            if isinstance(content, str):
                result = json.loads(content)
            else:
                result = content
            
            return {
                'content': result['content'],
                'summary': result.get('summary', 'Changes applied'),
                'changes': result.get('changes', []),
                'confidence': result.get('confidence', 0.8),
                'model': model,
                'tokens_used': response.get('tokens', {})
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse model response: {e}")
            # Fallback - treat entire response as content
            return {
                'content': response.get('content', ''),
                'summary': 'Changes applied (parse error)',
                'changes': [],
                'confidence': 0.5,
                'model': model,
                'tokens_used': response.get('tokens', {})
            }
    
    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()
