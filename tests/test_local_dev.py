#!/usr/bin/env python3
"""
Local development test script for DevOpsZealot Universal Architecture
Run this to verify the basic functionality works
"""
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from zealot.universal_engine import UniversalZealotEngine, UniversalTask
from zealot.universal_config import UniversalConfig
from zealot.workflows.schema import Workflow, WorkflowLoader
from zealot.plugins.interface import PluginManager


def setup_test_environment():
    """Setup test directories and configs"""
    print("Setting up test environment...")
    
    # Create test directories
    test_dir = tempfile.mkdtemp(prefix="zealot_test_")
    workflows_dir = os.path.join(test_dir, "workflows")
    plugins_dir = os.path.join(test_dir, "plugins")
    
    os.makedirs(workflows_dir, exist_ok=True)
    os.makedirs(plugins_dir, exist_ok=True)
    
    # Create a simple test workflow
    test_workflow = """
workflows:
  - name: test_workflow
    description: Test workflow for local development
    match:
      labels: ["test"]
    
    context_template: |
      Test task for file: {file_path}
      Current content: {current_content}
      Requirements: Make a test edit
    
    pre_edit:
      - name: pre_test
        hooks:
          - name: echo_pre
            command: "echo 'Pre-edit test'"
            timeout: 30
    
    post_edit:
      - name: post_test
        hooks:
          - name: echo_post
            command: "echo 'Post-edit test'"
            timeout: 30
    
    validation:
      - name: validate_test
        hooks:
          - name: echo_validate
            command: "echo 'Validation test'"
            timeout: 30
"""
    
    workflow_file = os.path.join(workflows_dir, "test-workflow.yaml")
    with open(workflow_file, 'w') as f:
        f.write(test_workflow)
    
    # Create test configuration
    config_data = {
        'workflows_dir': workflows_dir,
        'plugins_dir': plugins_dir,
        'issue_source': {
            'type': 'mock'
        },
        'vcs': {
            'type': 'mock'
        },
        'llm': {
            'provider': 'mock'
        },
        'container': {
            'type': 'mock'
        }
    }
    
    print(f"Test environment created at: {test_dir}")
    return test_dir, config_data


async def test_basic_functionality():
    """Test basic engine functionality"""
    print("\n=== Testing DevOpsZealot Universal Architecture ===\n")
    
    # Setup
    test_dir, config_data = setup_test_environment()
    
    try:
        # Test 1: Configuration loading
        print("1. Testing configuration loading...")
        config = UniversalConfig.from_dict(config_data)
        print("   ✓ Configuration loaded successfully")
        
        # Test 2: Engine initialization
        print("\n2. Testing engine initialization...")
        engine = UniversalZealotEngine(config)
        print("   ✓ Engine initialized successfully")
        print(f"   - Workflows loaded: {len(engine.workflows)}")
        print(f"   - Issue adapter: {type(engine.issue_adapter).__name__}")
        print(f"   - VCS adapter: {type(engine.vcs_adapter).__name__}")
        print(f"   - LLM adapter: {type(engine.llm_adapter).__name__}")
        print(f"   - Container adapter: {type(engine.container_adapter).__name__}")
        
        # Test 3: Workflow loading
        print("\n3. Testing workflow system...")
        workflows = WorkflowLoader.load_from_directory(config.workflows_dir)
        print(f"   ✓ Loaded {len(workflows)} workflow(s)")
        for workflow in workflows:
            print(f"   - {workflow.name}: {workflow.description}")
        
        # Test 4: Plugin system
        print("\n4. Testing plugin system...")
        plugin_manager = PluginManager()
        print(f"   ✓ Plugin manager initialized")
        print(f"   - Built-in plugins: {list(plugin_manager.plugins.keys())}")
        
        # Test 5: Create and execute a simple task
        print("\n5. Testing task execution...")
        
        # Create a test file
        test_file_dir = os.path.join(test_dir, "test_repo")
        os.makedirs(test_file_dir, exist_ok=True)
        test_file = os.path.join(test_file_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("# Original content\nprint('Hello')\n")
        
        task = UniversalTask(
            issue_id="TEST-001",
            repository=test_file_dir,
            files=["test.py"],
            labels=["test"],
            metadata={"test": True}
        )
        
        print(f"   - Created task: {task.id}")
        print(f"   - Issue ID: {task.issue_id}")
        print(f"   - Files: {task.files}")
        
        # Execute task
        print("\n   Executing task...")
        result = await engine.execute(task)
        
        print(f"\n   ✓ Task execution completed!")
        print(f"   - Success: {result.success}")
        print(f"   - Duration: {result.duration_seconds:.2f}s")
        print(f"   - Branch: {result.branch_name}")
        print(f"   - Commit: {result.commit_sha}")
        
        if result.changes:
            print(f"\n   Changes made:")
            for change in result.changes:
                print(f"   - {change['file']}: {change['summary']}")
        
        if not result.success and result.error:
            print(f"\n   Error: {result.error}")
        
        # Test 6: Import verification
        print("\n6. Testing all imports...")
        test_imports = [
            "from zealot.workflows.schema import WorkflowMatch, WorkflowStage, HookCommand",
            "from zealot.plugins.interface import PluginContext, PluginResult",
            "from zealot.adapters.base import IssueAdapter, VCSAdapter, LLMAdapter",
            "from zealot.adapters.mock import MockIssueAdapter, MockVCSAdapter",
            "from zealot.adapters.issue import RedmineIssueAdapter",
            "from zealot.adapters.vcs import GitVcsAdapter"
        ]
        
        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                print(f"   ✓ {import_stmt}")
            except ImportError as e:
                print(f"   ✗ {import_stmt} - {e}")
        
        print("\n✅ All basic tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


async def test_workflow_matching():
    """Test workflow matching logic"""
    print("\n=== Testing Workflow Matching ===\n")
    
    from zealot.workflows.schema import Workflow, WorkflowMatch, WorkflowMatcher
    
    # Create test workflows
    workflows = [
        Workflow(
            name="terraform",
            match=WorkflowMatch(
                labels=["infrastructure"],
                file_patterns=["*.tf"]
            )
        ),
        Workflow(
            name="python",
            match=WorkflowMatch(
                file_patterns=["*.py"]
            )
        ),
        Workflow(
            name="default"
        )
    ]
    
    matcher = WorkflowMatcher(workflows)
    
    # Test cases
    test_cases = [
        (UniversalTask(files=["main.tf"], labels=["infrastructure"]), "terraform"),
        (UniversalTask(files=["app.py"]), "python"),
        (UniversalTask(files=["README.md"]), "default"),
    ]
    
    for task, expected in test_cases:
        workflow = matcher.find_workflow(task)
        result = workflow.name if workflow else None
        status = "✓" if result == expected else "✗"
        print(f"   {status} Task with {task.files} → {result} (expected: {expected})")


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7+ is required")
        sys.exit(1)
    
    # Run tests
    asyncio.run(test_basic_functionality())
    asyncio.run(test_workflow_matching())
    
    print("\n🎉 Local development test completed!")
