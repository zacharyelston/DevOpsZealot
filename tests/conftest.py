"""Test configuration"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.openai_api_key = "test-key"
    config.redis_url = "redis://localhost:6379/0"
    config.docker_socket = "/var/run/docker.sock"
    config.container_memory_limit = "2g"
    config.container_cpu_quota = 50000
    config.ai_model = "gpt-4"
    config.allowed_repositories = ["https://github.com/test/*"]
    config.enable_security_validation = True
    config.enable_syntax_validation = True
    return config

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
