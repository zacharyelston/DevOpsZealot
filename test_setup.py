#!/usr/bin/env python3
"""Quick test to verify DevOpsZealot setup"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zealot.engine import ZealotEngine, Task
from zealot.config import Config

async def test_engine():
    """Test basic engine functionality"""
    print("=" * 60)
    print("DevOpsZealot Setup Test")
    print("=" * 60)
    
    # Create test config
    config = Config()
    config.redis_url = "redis://localhost:6379/0"  # Assumes Redis is running
    
    print("\n1. Testing Engine Initialization...")
    try:
        engine = ZealotEngine(config)
        print("   ✅ Engine initialized successfully")
    except Exception as e:
        print(f"   ❌ Engine initialization failed: {e}")
        return False
    
    print("\n2. Testing Task Creation...")
    try:
        task = Task(
            id="test-001",
            type="terraform",
            repository="https://github.com/test/infrastructure.git",
            branch="main",
            files=["terraform/main.tf"],
            requirements=["Add new S3 bucket for logs"]
        )
        print("   ✅ Task created successfully")
        print(f"   Task ID: {task.id}")
        print(f"   Type: {task.type}")
        print(f"   Repository: {task.repository}")
    except Exception as e:
        print(f"   ❌ Task creation failed: {e}")
        return False
    
    print("\n3. Testing Container Manager...")
    try:
        health = await engine.container_manager.health_check()
        if health["status"] == "healthy":
            print(f"   ✅ Docker is healthy (version: {health['docker_version']})")
        else:
            print(f"   ⚠️  Docker health check failed: {health}")
    except Exception as e:
        print(f"   ❌ Container manager test failed: {e}")
        print("   Make sure Docker is running and accessible")
    
    print("\n4. Testing Redis Connection...")
    try:
        redis_healthy = await engine.task_queue.health_check()
        if redis_healthy:
            print("   ✅ Redis connection successful")
        else:
            print("   ⚠️  Redis connection failed")
            print("   Make sure Redis is running on localhost:6379")
    except Exception as e:
        print(f"   ❌ Redis test failed: {e}")
    
    print("\n5. Testing AI Client...")
    if config.openai_api_key:
        print("   ✅ OpenAI API key configured")
    else:
        print("   ⚠️  OpenAI API key not configured")
        print("   Set OPENAI_API_KEY environment variable")
    
    print("\n" + "=" * 60)
    print("Setup Test Complete!")
    print("=" * 60)
    
    print("\nNext Steps:")
    print("1. Build the Docker base image:")
    print("   docker build -f docker/Dockerfile.base -t zealot/base:latest docker/")
    print("\n2. Start Redis:")
    print("   docker run -d -p 6379:6379 redis:7-alpine")
    print("\n3. Copy .env.example to .env and add your API keys")
    print("\n4. Start the server:")
    print("   python -m zealot.server")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_engine())
    sys.exit(0 if success else 1)
