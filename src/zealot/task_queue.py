"""Task queue management using Redis"""
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import redis.asyncio as redis
import structlog

from .engine import Task, TaskResult

logger = structlog.get_logger()

class TaskQueue:
    """Redis-based task queue"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.queue_key = "zealot:tasks:queue"
        self.processing_key = "zealot:tasks:processing"
        self.results_key = "zealot:tasks:results"
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Connected to Redis", url=self.redis_url)
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def enqueue(self, task: Task) -> None:
        """Add task to queue"""
        await self.connect()
        
        task_data = {
            "id": task.id,
            "type": task.type,
            "repository": task.repository,
            "branch": task.branch,
            "files": task.files,
            "requirements": task.requirements,
            "validation_rules": task.validation_rules,
            "created_at": task.created_at.isoformat(),
            "metadata": task.metadata
        }
        
        # Add to queue
        await self.redis.lpush(self.queue_key, json.dumps(task_data))
        
        # Set initial status
        await self.redis.hset(
            f"zealot:task:{task.id}",
            mapping={
                "status": "queued",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info("Task enqueued", task_id=task.id)
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue"""
        await self.connect()
        
        # Move from queue to processing atomically
        task_json = await self.redis.brpoplpush(
            self.queue_key, 
            self.processing_key,
            timeout=1
        )
        
        if not task_json:
            return None
        
        try:
            task_data = json.loads(task_json)
            
            # Update status
            await self.redis.hset(
                f"zealot:task:{task_data['id']}",
                mapping={
                    "status": "processing",
                    "started_at": datetime.utcnow().isoformat()
                }
            )
            
            # Convert back to Task object
            task = Task(
                id=task_data["id"],
                type=task_data["type"],
                repository=task_data["repository"],
                branch=task_data["branch"],
                files=task_data["files"],
                requirements=task_data["requirements"],
                validation_rules=task_data.get("validation_rules", []),
                metadata=task_data.get("metadata", {})
            )
            
            logger.info("Task dequeued", task_id=task.id)
            return task
            
        except Exception as e:
            logger.error("Failed to deserialize task", error=str(e))
            # Remove from processing queue
            await self.redis.lrem(self.processing_key, 1, task_json)
            return None
    
    async def set_result(self, task_id: str, result: TaskResult) -> None:
        """Store task result"""
        await self.connect()
        
        result_data = {
            "task_id": result.task_id,
            "success": result.success,
            "changes": json.dumps(result.changes),
            "validation_results": json.dumps(result.validation_results) if result.validation_results else None,
            "error": result.error,
            "duration_seconds": result.duration_seconds,
            "pr_url": result.pr_url,
            "commit_sha": result.commit_sha,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        # Store result
        await self.redis.hset(
            f"zealot:task:{task_id}:result",
            mapping={k: v for k, v in result_data.items() if v is not None}
        )
        
        # Update status
        await self.redis.hset(
            f"zealot:task:{task_id}",
            mapping={
                "status": "completed" if result.success else "failed",
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
        # Remove from processing queue
        task_data = await self.redis.hgetall(f"zealot:task:{task_id}")
        if task_data:
            await self.redis.lrem(self.processing_key, 1, json.dumps(task_data))
        
        # Set expiration (7 days)
        await self.redis.expire(f"zealot:task:{task_id}", 604800)
        await self.redis.expire(f"zealot:task:{task_id}:result", 604800)
        
        logger.info("Task result stored", task_id=task_id, success=result.success)
    
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result"""
        await self.connect()
        
        result_data = await self.redis.hgetall(f"zealot:task:{task_id}:result")
        
        if not result_data:
            return None
        
        try:
            return TaskResult(
                task_id=result_data.get("task_id"),
                success=result_data.get("success") == "True",
                changes=json.loads(result_data.get("changes", "[]")),
                validation_results=json.loads(result_data.get("validation_results", "{}")) if result_data.get("validation_results") else None,
                error=result_data.get("error"),
                duration_seconds=float(result_data.get("duration_seconds", 0)),
                pr_url=result_data.get("pr_url"),
                commit_sha=result_data.get("commit_sha")
            )
        except Exception as e:
            logger.error("Failed to deserialize result", task_id=task_id, error=str(e))
            return None
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        await self.connect()
        
        status_data = await self.redis.hgetall(f"zealot:task:{task_id}")
        return status_data if status_data else None
    
    async def list_tasks(self, status: Optional[str] = None, limit: int = 100) -> list[Dict[str, Any]]:
        """List tasks with optional status filter"""
        await self.connect()
        
        # Get all task keys
        keys = await self.redis.keys("zealot:task:*")
        tasks = []
        
        for key in keys[:limit]:
            if ":result" in key:
                continue
                
            task_data = await self.redis.hgetall(key)
            if task_data:
                if status is None or task_data.get("status") == status:
                    task_id = key.split(":")[-1]
                    task_data["id"] = task_id
                    tasks.append(task_data)
        
        # Sort by created_at descending
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return tasks
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            await self.connect()
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        await self.connect()
        
        queued = await self.redis.llen(self.queue_key)
        processing = await self.redis.llen(self.processing_key)
        
        # Count completed tasks
        completed = 0
        failed = 0
        
        keys = await self.redis.keys("zealot:task:*")
        for key in keys:
            if ":result" not in key:
                status = await self.redis.hget(key, "status")
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1
        
        return {
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "total": queued + processing + completed + failed
        }
