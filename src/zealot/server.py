"""FastAPI server for DevOpsZealot"""
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
    logger.info("Starting DevOpsZealot server")
    engine = ZealotEngine(config)
    
    # Start engine in background
    engine_task = asyncio.create_task(engine.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevOpsZealot server")
    await engine.stop()
    engine_task.cancel()

# Create FastAPI app
app = FastAPI(
    title="DevOpsZealot",
    description="Autonomous AI-powered infrastructure editing tool",
    version="0.1.0",
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

class TaskResponse(BaseModel):
    """Task submission response"""
    task_id: str = Field(..., description="Unique task ID")
    status: str = Field(..., description="Current task status")
    message: str = Field(..., description="Status message")

class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    components: Dict[str, Any]

# Authentication dependency
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key"""
    # TODO: Implement proper API key validation
    if config.api_key_header and not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_api_key

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "name": "DevOpsZealot",
        "version": "0.1.0",
        "description": "Autonomous AI-powered infrastructure editing tool"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Check components
    docker_health = await engine.container_manager.health_check()
    redis_health = await engine.task_queue.health_check()
    
    return HealthResponse(
        status="healthy" if docker_health["status"] == "healthy" and redis_health else "unhealthy",
        version="0.1.0",
        components={
            "docker": docker_health,
            "redis": {"status": "healthy" if redis_health else "unhealthy"},
            "engine": {"status": "running" if engine._running else "stopped"}
        }
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
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="Task submitted successfully"
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
    if status_data.get("status") in ["completed", "failed"]:
        task_result = await engine.get_task_status(task_id)
        if task_result:
            result = {
                "success": task_result.success,
                "pr_url": task_result.pr_url,
                "commit_sha": task_result.commit_sha,
                "error": task_result.error,
                "duration_seconds": task_result.duration_seconds
            }
    
    return TaskStatusResponse(
        task_id=task_id,
        status=status_data.get("status", "unknown"),
        created_at=status_data.get("created_at"),
        started_at=status_data.get("started_at"),
        completed_at=status_data.get("completed_at"),
        result=result
    )

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
    # TODO: Implement validation endpoint
    return {"status": "not_implemented"}

@app.get("/api/v1/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """Get queue statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    stats = await engine.task_queue.get_queue_stats()
    
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
