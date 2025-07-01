"""FastAPI server for DevOpsZealot with Continue.dev integration"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import structlog
import uvicorn

from .engine import ZealotEngine, Task, TaskResult
from .config import Config
from .mcp_api import router as mcp_router, init_mcp_server

# Import Continue integration
from ..ai.continue_integration import HybridAIClient, ContinueConfig, HybridConfig
from ..ai.continue_integration.hybrid_client import ModelProvider

logger = structlog.get_logger()

# Load configuration
config = Config.from_env()

# Global engine instance
engine: Optional[ZealotEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global engine
    
    # Startup
    logger.info("Starting DevOpsZealot server with Continue.dev integration")
    
    # Create hybrid AI client
    continue_config = ContinueConfig(
        continue_config_path=config.continue_config_path,
        api_url=config.continue_api_url,
        default_model=config.continue_default_model,
        use_local_models=config.use_local_models,
        local_model_path=config.local_model_path
    )
    
    hybrid_config = HybridConfig(
        continue_config=continue_config,
        openai_api_key=config.openai_api_key,
        openai_model=config.ai_model,
        default_provider=ModelProvider.AUTO,
        prefer_local=config.prefer_local_models,
        fallback_enabled=True
    )
    
    # Create engine with hybrid AI client
    engine = ZealotEngine(config)
    
    # Replace the AI client with hybrid client if Continue is enabled
    if config.enable_continue_integration:
        engine.ai_client = HybridAIClient(hybrid_config)
        logger.info("Continue.dev integration enabled")
    
    # Initialize MCP server
    init_mcp_server(engine)
    
    # Start engine in background
    engine_task = asyncio.create_task(engine.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevOpsZealot server")
    if hasattr(engine.ai_client, 'close'):
        await engine.ai_client.close()
    await engine.stop()
    engine_task.cancel()

# Create FastAPI app
app = FastAPI(
    title="DevOpsZealot",
    description="Autonomous AI-powered infrastructure editing tool with Continue.dev integration",
    version="0.2.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include MCP router
app.include_router(mcp_router)

# Request/Response models
class TaskRequest(BaseModel):
    """Task submission request"""
    type: str = Field(default="infrastructure_edit", description="Task type")
    repository: str = Field(..., description="Git repository URL")
    branch: str = Field(default="main", description="Branch to work from")
    files: List[str] = Field(..., description="Files to edit")
    requirements: List[str] = Field(..., description="Edit requirements")
    validation_rules: List[str] = Field(default=[], description="Validation rules to apply")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    ai_provider: Optional[str] = Field(default=None, description="Override AI provider (continue/openai/auto)")

class TaskResponse(BaseModel):
    """Task submission response"""
    task_id: str = Field(..., description="Unique task ID")
    status: str = Field(..., description="Current task status")
    message: str = Field(..., description="Status message")
    ai_provider: Optional[str] = Field(default=None, description="AI provider that will be used")

class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    ai_provider_used: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    components: Dict[str, Any]
    ai_providers: Optional[Dict[str, Any]] = None

class AIProviderStatsResponse(BaseModel):
    """AI provider statistics"""
    providers: Dict[str, Any]
    recommendations: Dict[str, str]

# Authentication dependency
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key"""
    if config.api_key_header and not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "name": "DevOpsZealot",
        "version": "0.2.0",
        "description": "Autonomous AI-powered infrastructure editing tool with Continue.dev integration",
        "continue_enabled": config.enable_continue_integration
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Check components
    docker_health = await engine.container_manager.health_check()
    redis_health = await engine.task_queue.health_check()
    
    # Get AI provider stats if hybrid client is available
    ai_stats = None
    if hasattr(engine.ai_client, 'get_performance_report'):
        ai_stats = engine.ai_client.get_performance_report()
    
    return HealthResponse(
        status="healthy" if docker_health["status"] == "healthy" and redis_health else "unhealthy",
        version="0.2.0",
        components={
            "docker": docker_health,
            "redis": {"status": "healthy" if redis_health else "unhealthy"},
            "engine": {"status": "running" if engine._running else "stopped"},
            "continue_integration": config.enable_continue_integration
        },
        ai_providers=ai_stats
    )

@app.post("/api/v1/tasks", response_model=TaskResponse)
async def submit_task(request: TaskRequest, api_key: str = Depends(verify_api_key)):
    """Submit a new task"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Validate repository against allowed list
    allowed = any(
        request.repository.startswith(allowed_repo.rstrip("*"))
        for allowed_repo in config.allowed_repositories
    )
    
    if not allowed:
        raise HTTPException(status_code=403, detail="Repository not allowed")
    
    # Parse AI provider override
    provider_override = None
    if request.ai_provider:
        try:
            provider_override = ModelProvider(request.ai_provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid AI provider: {request.ai_provider}")
    
    # Add provider override to metadata if specified
    if provider_override:
        request.metadata["ai_provider_override"] = provider_override.value
    
    # Create task
    task = Task(
        type=request.type,
        repository=request.repository,
        branch=request.branch,
        files=request.files,
        requirements=request.requirements,
        validation_rules=request.validation_rules,
        metadata=request.metadata
    )
    
    # Submit to engine
    task_id = await engine.submit_task(task)
    
    # Determine which provider will be used
    selected_provider = None
    if hasattr(engine.ai_client, '_select_provider'):
        selected_provider = engine.ai_client._select_provider(
            file_type='terraform',  # Default assumption
            task_type='edit',
            override=provider_override
        ).value
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Task submitted successfully",
        ai_provider=selected_provider
    )

@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, api_key: str = Depends(verify_api_key)):
    """Get task status"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Get task status
    status_data = await engine.task_queue.get_task_status(task_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get result if completed
    result = None
    ai_provider_used = None
    
    if status_data.get("status") in ["completed", "failed"]:
        task_result = await engine.get_task_status(task_id)
        if task_result:
            result = {
                "success": task_result.success,
                "pr_url": task_result.pr_url,
                "commit_sha": task_result.commit_sha,
                "error": task_result.error,
                "duration_seconds": task_result.duration_seconds,
                "changes": task_result.changes if task_result.changes else []
            }
            
            # Extract AI provider from changes if available
            if task_result.changes and len(task_result.changes) > 0:
                first_change = task_result.changes[0]
                if isinstance(first_change, dict) and 'provider_used' in first_change:
                    ai_provider_used = first_change['provider_used']
    
    return TaskStatusResponse(
        task_id=task_id,
        status=status_data.get("status", "unknown"),
        created_at=status_data.get("created_at"),
        started_at=status_data.get("started_at"),
        completed_at=status_data.get("completed_at"),
        result=result,
        ai_provider_used=ai_provider_used
    )

@app.get("/api/v1/ai/stats", response_model=AIProviderStatsResponse)
async def get_ai_provider_stats(api_key: str = Depends(verify_api_key)):
    """Get AI provider performance statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    if not hasattr(engine.ai_client, 'get_performance_report'):
        raise HTTPException(status_code=501, detail="AI statistics not available")
    
    stats = engine.ai_client.get_performance_report()
    
    # Generate recommendations based on stats
    recommendations = {}
    for provider, data in stats.items():
        if data['performance_score'] > 0.8:
            recommendations[provider] = "Excellent performance"
        elif data['performance_score'] > 0.6:
            recommendations[provider] = "Good performance"
        else:
            recommendations[provider] = "Consider using alternative provider"
    
    return AIProviderStatsResponse(
        providers=stats,
        recommendations=recommendations
    )

@app.post("/api/v1/ai/analyze")
async def analyze_codebase(
    repository_path: str,
    analysis_type: str = "security",
    api_key: str = Depends(verify_api_key)
):
    """Analyze codebase using Continue's advanced context capabilities"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    if not hasattr(engine.ai_client, 'analyze_codebase'):
        raise HTTPException(status_code=501, detail="Codebase analysis not available")
    
    if analysis_type not in ["security", "performance", "quality"]:
        raise HTTPException(status_code=400, detail="Invalid analysis type")
    
    result = await engine.ai_client.analyze_codebase(repository_path, analysis_type)
    
    return result

@app.get("/api/v1/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, api_key: str = Depends(verify_api_key)):
    """Get task execution logs"""
    # TODO: Implement log streaming
    return {"task_id": task_id, "logs": ["Not implemented yet"]}

@app.get("/api/v1/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List tasks"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    tasks = await engine.task_queue.list_tasks(status=status, limit=limit)
    
    return {"tasks": tasks, "total": len(tasks)}

@app.post("/api/v1/validate")
async def validate_changes(
    request: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """Validate code changes without applying them"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Use the validation pipeline
    result = await engine.validation_pipeline.validate(
        file_type=request.get("file_type", "terraform"),
        content=request.get("content", ""),
        original=request.get("original", ""),
        container=None,
        rules=request.get("rules", ["syntax", "security"])
    )
    
    return result

@app.get("/api/v1/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """Get queue statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    stats = await engine.task_queue.get_queue_stats()
    
    # Add AI provider stats if available
    if hasattr(engine.ai_client, 'get_performance_report'):
        stats['ai_providers'] = engine.ai_client.get_performance_report()
    
    return stats

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "detail": str(exc)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error("Internal server error", error=str(exc))
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}

def main():
    """Run the server"""
    uvicorn.run(
        "zealot.server:app",
        host=config.server_host,
        port=config.server_port,
        workers=config.server_workers,
        log_level=config.log_level.lower(),
        reload=False
    )

if __name__ == "__main__":
    main()
