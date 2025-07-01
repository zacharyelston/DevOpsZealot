"""Test engine functionality"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from zealot.engine import ZealotEngine, Task, TaskResult

@pytest.mark.asyncio
async def test_engine_initialization(mock_config):
    """Test engine initialization"""
    engine = ZealotEngine(mock_config)
    
    assert engine.config == mock_config
    assert engine._running == False
    assert engine.container_manager is not None
    assert engine.ai_client is not None
    assert engine.task_queue is not None

@pytest.mark.asyncio
async def test_task_creation():
    """Test task creation"""
    task = Task(
        repository="https://github.com/test/repo.git",
        files=["main.tf"],
        requirements=["Add S3 bucket"]
    )
    
    assert task.id is not None
    assert task.type == "infrastructure_edit"
    assert task.branch == "main"
    assert len(task.files) == 1
    assert len(task.requirements) == 1
    assert isinstance(task.created_at, datetime)

@pytest.mark.asyncio
async def test_submit_task(mock_config):
    """Test task submission"""
    engine = ZealotEngine(mock_config)
    
    # Mock the task queue
    engine.task_queue = AsyncMock()
    engine.task_queue.enqueue = AsyncMock()
    
    task = Task(
        repository="https://github.com/test/repo.git",
        files=["main.tf"],
        requirements=["Add S3 bucket"]
    )
    
    task_id = await engine.submit_task(task)
    
    assert task_id == task.id
    engine.task_queue.enqueue.assert_called_once_with(task)

@pytest.mark.asyncio
async def test_process_task_success(mock_config):
    """Test successful task processing"""
    engine = ZealotEngine(mock_config)
    
    # Create test task
    task = Task(
        repository="https://github.com/test/repo.git",
        files=["main.tf"],
        requirements=["Add S3 bucket"]
    )
    
    # Mock dependencies
    mock_container = AsyncMock()
    mock_container.id = "test-container"
    mock_container.workspace_path = "/tmp/test"
    mock_container.cleanup = AsyncMock()
    
    engine.container_manager.create_workspace = AsyncMock(return_value=mock_container)
    
    # Mock git operations
    with patch('zealot.engine.GitManager') as mock_git:
        mock_git_instance = Mock()
        mock_git_instance.clone_repository = Mock()
        mock_git_instance.create_feature_branch = Mock()
        mock_git_instance.read_file = Mock(return_value="resource \"aws_s3_bucket\" \"test\" {}")
        mock_git_instance.write_file = Mock()
        mock_git_instance.commit_changes = Mock(return_value="abc123")
        mock_git_instance.push_changes = Mock()
        mock_git.return_value = mock_git_instance
        
        # Mock AI client
        engine.ai_client.generate_edit = AsyncMock(return_value={
            "content": "resource \"aws_s3_bucket\" \"test\" {}\nresource \"aws_s3_bucket\" \"logs\" {}",
            "summary": "Added S3 bucket for logs",
            "tokens_used": {"total": 100}
        })
        
        # Mock validation
        engine._validate_changes = AsyncMock(return_value={
            "passed": True,
            "results": []
        })
        
        # Mock PR creation
        engine._create_pull_request = AsyncMock(return_value="https://github.com/test/repo/pull/1")
        
        # Process task
        result = await engine.process_task(task)
        
        # Verify result
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id
        assert result.success == True
        assert result.pr_url == "https://github.com/test/repo/pull/1"
        assert result.commit_sha == "abc123"
        assert len(result.changes) == 1
        
        # Verify cleanup was called
        mock_container.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_process_task_failure(mock_config):
    """Test task processing failure"""
    engine = ZealotEngine(mock_config)
    
    task = Task(
        repository="https://github.com/test/repo.git",
        files=["main.tf"],
        requirements=["Add S3 bucket"]
    )
    
    # Mock container creation to fail
    engine.container_manager.create_workspace = AsyncMock(side_effect=Exception("Docker error"))
    
    result = await engine.process_task(task)
    
    assert result.success == False
    assert result.error == "Docker error"
    assert result.task_id == task.id

@pytest.mark.asyncio
async def test_get_file_type():
    """Test file type detection"""
    engine = ZealotEngine(Mock())
    
    assert engine._get_file_type("main.tf") == "terraform"
    assert engine._get_file_type("script.py") == "python"
    assert engine._get_file_type("config.yaml") == "yaml"
    assert engine._get_file_type("config.yml") == "yaml"
    assert engine._get_file_type("Dockerfile") == "dockerfile"
    assert engine._get_file_type("README.md") == "text"

def test_generate_commit_message():
    """Test commit message generation"""
    engine = ZealotEngine(Mock())
    
    task = Task(
        id="test-123",
        requirements=["Add S3 bucket", "Configure logging", "Enable versioning"]
    )
    
    changes = [
        {"file": "main.tf"},
        {"file": "variables.tf"}
    ]
    
    message = engine._generate_commit_message(task, changes)
    
    assert "AI: Add S3 bucket; Configure logging; Enable versioning" in message
    assert "Task ID: test-123" in message
    assert "Files changed: main.tf, variables.tf" in message
    assert "DevOpsZealot" in message
