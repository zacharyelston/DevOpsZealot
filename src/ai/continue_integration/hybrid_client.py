"""
Hybrid AI Client that combines Continue.dev with existing OpenAI client
Provides seamless fallback and model selection
"""
import asyncio
from typing import Dict, Any, List, Optional, Literal
import structlog
from dataclasses import dataclass
from enum import Enum

from ..openai_client import OpenAIClient
from .continue_engine import ContinueAIEngine, ContinueConfig

logger = structlog.get_logger()

class ModelProvider(Enum):
    """Available model providers"""
    CONTINUE = "continue"
    OPENAI = "openai"
    AUTO = "auto"  # Automatically select best provider

@dataclass
class HybridConfig:
    """Configuration for hybrid AI client"""
    # Continue configuration
    continue_config: ContinueConfig
    
    # OpenAI configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Hybrid settings
    default_provider: ModelProvider = ModelProvider.AUTO
    prefer_local: bool = False  # Prefer local models when available
    fallback_enabled: bool = True
    
    # Task routing rules
    task_routing: Dict[str, ModelProvider] = None
    
    def __post_init__(self):
        if self.task_routing is None:
            self.task_routing = {
                'terraform': ModelProvider.CONTINUE,  # Use Continue for IaC
                'python': ModelProvider.CONTINUE,
                'validation': ModelProvider.CONTINUE,  # Better validation models
                'documentation': ModelProvider.OPENAI,  # GPT-4 for docs
                'commit': ModelProvider.OPENAI,  # Quick responses
            }

class HybridAIClient:
    """
    Hybrid AI client that intelligently routes between Continue and OpenAI
    
    Features:
    - Automatic provider selection based on task
    - Fallback support
    - Performance tracking
    - Cost optimization
    """
    
    def __init__(self, config: HybridConfig):
        self.config = config
        self.continue_client = ContinueAIEngine(config.continue_config)
        self.openai_client = OpenAIClient(config.openai_api_key, config.openai_model)
        
        # Performance tracking
        self._performance_stats = {
            'continue': {'success': 0, 'failure': 0, 'avg_time': 0},
            'openai': {'success': 0, 'failure': 0, 'avg_time': 0}
        }
        
        logger.info("HybridAIClient initialized",
                   default_provider=config.default_provider.value,
                   fallback_enabled=config.fallback_enabled)
    
    async def generate_edit(self, 
                          current_content: str,
                          requirements: List[str],
                          file_type: str,
                          context: Optional[Dict[str, Any]] = None,
                          provider_override: Optional[ModelProvider] = None) -> Dict[str, Any]:
        """
        Generate code edit using the best available provider
        
        Provider selection logic:
        1. Use override if specified
        2. Check task routing rules
        3. Use performance-based selection
        4. Fall back to default provider
        """
        provider = self._select_provider(file_type, 'edit', provider_override)
        
        logger.info(f"Generating edit with provider: {provider.value}",
                   file_type=file_type,
                   requirements_count=len(requirements))
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Try primary provider
            result = await self._call_provider(
                provider=provider,
                method='generate_edit',
                current_content=current_content,
                requirements=requirements,
                file_type=file_type,
                context=context
            )
            
            # Track success
            self._record_performance(provider, True, start_time)
            result['provider_used'] = provider.value
            
            return result
            
        except Exception as e:
            logger.error(f"Primary provider {provider.value} failed: {e}")
            self._record_performance(provider, False, start_time)
            
            # Try fallback if enabled
            if self.config.fallback_enabled:
                fallback_provider = self._get_fallback_provider(provider)
                
                if fallback_provider:
                    logger.info(f"Attempting fallback to {fallback_provider.value}")
                    
                    try:
                        result = await self._call_provider(
                            provider=fallback_provider,
                            method='generate_edit',
                            current_content=current_content,
                            requirements=requirements,
                            file_type=file_type,
                            context=context
                        )
                        
                        self._record_performance(fallback_provider, True, start_time)
                        result['provider_used'] = fallback_provider.value
                        result['fallback'] = True
                        
                        return result
                        
                    except Exception as fallback_e:
                        logger.error(f"Fallback provider {fallback_provider.value} failed: {fallback_e}")
                        self._record_performance(fallback_provider, False, start_time)
            
            raise ValueError(f"All providers failed for edit task: {str(e)}")
    
    async def validate_changes(self,
                             original: str,
                             modified: str,
                             requirements: List[str],
                             file_type: str,
                             provider_override: Optional[ModelProvider] = None) -> Dict[str, Any]:
        """Validate changes using the best provider for validation"""
        provider = self._select_provider(file_type, 'validation', provider_override)
        
        try:
            if provider == ModelProvider.CONTINUE:
                result = await self.continue_client.validate_changes(
                    original, modified, requirements, file_type
                )
            else:
                result = await self.openai_client.validate_changes(
                    original, modified, requirements, file_type
                )
            
            result['provider_used'] = provider.value
            return result
            
        except Exception as e:
            logger.error(f"Validation failed with {provider.value}: {e}")
            
            # Try fallback
            if self.config.fallback_enabled:
                fallback_provider = self._get_fallback_provider(provider)
                if fallback_provider:
                    return await self.validate_changes(
                        original, modified, requirements, file_type,
                        provider_override=fallback_provider
                    )
            raise
    
    async def generate_commit_message(self, 
                                    changes: List[Dict[str, Any]],
                                    provider_override: Optional[ModelProvider] = None) -> str:
        """Generate commit message - typically faster with OpenAI"""
        provider = provider_override or self.config.task_routing.get('commit', ModelProvider.OPENAI)
        
        if provider == ModelProvider.CONTINUE:
            # Continue doesn't have a direct commit message generator
            # Build a simple prompt
            prompt = f"Generate a concise commit message for these changes: {changes}"
            response = await self.continue_client._call_model(
                self.continue_client.config.default_model,
                prompt,
                temperature=0.3
            )
            return response.get('content', 'Update files')
        else:
            return await self.openai_client.generate_commit_message(changes)
    
    async def analyze_codebase(self, 
                             repository_path: str,
                             analysis_type: Literal['security', 'performance', 'quality']) -> Dict[str, Any]:
        """
        Advanced analysis using Continue's context capabilities
        This showcases Continue's strength in handling large contexts
        """
        # Continue excels at codebase-wide analysis
        logger.info(f"Analyzing codebase: {repository_path}, type: {analysis_type}")
        
        # In a real implementation, this would use Continue's 
        # codebase indexing and context features
        analysis_prompt = f"""Analyze the codebase at {repository_path} for {analysis_type} issues.
        
Focus on:
- Critical issues that need immediate attention
- Best practice violations
- Potential improvements
- Security vulnerabilities (if security analysis)

Provide structured output with severity levels."""
        
        response = await self.continue_client._call_model(
            self.continue_client.config.default_model,
            analysis_prompt,
            temperature=0.1
        )
        
        return {
            'analysis_type': analysis_type,
            'repository': repository_path,
            'findings': response.get('content', ''),
            'provider': 'continue'
        }
    
    def _select_provider(self, 
                        file_type: str, 
                        task_type: str,
                        override: Optional[ModelProvider] = None) -> ModelProvider:
        """Select the best provider for a given task"""
        # 1. Use override if specified
        if override and override != ModelProvider.AUTO:
            return override
        
        # 2. Check task routing rules
        routing_key = f"{file_type}_{task_type}" if task_type != 'edit' else file_type
        if routing_key in self.config.task_routing:
            return self.config.task_routing[routing_key]
        
        # 3. Use performance-based selection if AUTO
        if self.config.default_provider == ModelProvider.AUTO:
            return self._select_by_performance()
        
        # 4. Use default provider
        return self.config.default_provider
    
    def _select_by_performance(self) -> ModelProvider:
        """Select provider based on performance stats"""
        continue_score = self._calculate_performance_score('continue')
        openai_score = self._calculate_performance_score('openai')
        
        # Prefer local models if configured and Continue score is close
        if self.config.prefer_local and continue_score > openai_score * 0.8:
            return ModelProvider.CONTINUE
        
        return ModelProvider.CONTINUE if continue_score > openai_score else ModelProvider.OPENAI
    
    def _calculate_performance_score(self, provider: str) -> float:
        """Calculate performance score for a provider"""
        stats = self._performance_stats[provider]
        
        if stats['success'] + stats['failure'] == 0:
            return 0.5  # No data, neutral score
        
        success_rate = stats['success'] / (stats['success'] + stats['failure'])
        
        # Factor in average time (lower is better)
        # Normalize to 0-1 where 1 is fastest (under 1 second)
        time_score = max(0, 1 - (stats['avg_time'] / 10))
        
        # Combined score (70% success rate, 30% speed)
        return (success_rate * 0.7) + (time_score * 0.3)
    
    def _get_fallback_provider(self, primary: ModelProvider) -> Optional[ModelProvider]:
        """Get fallback provider for a given primary provider"""
        if primary == ModelProvider.CONTINUE:
            return ModelProvider.OPENAI
        elif primary == ModelProvider.OPENAI:
            return ModelProvider.CONTINUE
        return None
    
    async def _call_provider(self, provider: ModelProvider, method: str, **kwargs) -> Any:
        """Call a method on the specified provider"""
        if provider == ModelProvider.CONTINUE:
            client = self.continue_client
        else:
            client = self.openai_client
        
        method_func = getattr(client, method)
        return await method_func(**kwargs)
    
    def _record_performance(self, provider: ModelProvider, success: bool, start_time: float):
        """Record performance metrics for a provider"""
        elapsed = asyncio.get_event_loop().time() - start_time
        stats = self._performance_stats[provider.value]
        
        if success:
            stats['success'] += 1
        else:
            stats['failure'] += 1
        
        # Update rolling average time
        total_calls = stats['success'] + stats['failure']
        stats['avg_time'] = (stats['avg_time'] * (total_calls - 1) + elapsed) / total_calls
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all providers"""
        report = {}
        
        for provider, stats in self._performance_stats.items():
            total_calls = stats['success'] + stats['failure']
            success_rate = stats['success'] / total_calls if total_calls > 0 else 0
            
            report[provider] = {
                'total_calls': total_calls,
                'success_rate': round(success_rate, 3),
                'average_time': round(stats['avg_time'], 2),
                'performance_score': round(self._calculate_performance_score(provider), 3)
            }
        
        return report
    
    async def close(self):
        """Cleanup resources"""
        await self.continue_client.close()
        # OpenAI client doesn't need explicit cleanup
