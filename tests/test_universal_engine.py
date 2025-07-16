"""
Comprehensive tests for the Universal Zealot Engine
Tests the core universal architecture functionality
"""
import unittest
import asyncio
import tempfile
import os
import sys
import yaml
from unittest.mock import Mock, AsyncMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from zealot.universal_engine import UniversalZealotEngine, UniversalTask, UniversalResult
from zealot.universal_config import UniversalConfig
from zealot.workflows.schema import Workflow, WorkflowMatch
from zealot.plugins.interface import PluginContext, PluginResult
from zealot.adapters.base import Workspace


class TestUniversalEngine(unittest.TestCase):
    """Test the Universal Zealot Engine"""
    
    def setUp(self):
        """Setup test environment"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = os.path.join(self.temp_dir, 'workflows')
        os.makedirs(self.workflows_dir)
        
        # Create a test workflow file
        test_workflow = {
            'workflows': [
                {
                    'name': 'test_workflow',
                    'description': 'Test workflow',
                    'match': {
                        'labels': ['test'],
                        'file_patterns': ['*.test']
                    },
                    'context_template': 'Test context: {issue_description}',
                    'pre_edit': [],
                    'post_edit': [],
                    'validation': [],
                    'llm_config': {
                        'temperature': 0.5
                    }
                }
            ]
        }
        
        workflow_file = os.path.join(self.workflows_dir, 'test.yaml')
        with open(workflow_file, 'w') as f:
            yaml.dump(test_workflow, f)
        
        # Create test configuration
        self.config = UniversalConfig(
            workflows_dir=self.workflows_dir,
            issue_source={'type': 'mock'},
            vcs={'type': 'mock'},
            llm={'provider': 'mock'},
            container={'type': 'mock'}
        )
    
    def tearDown(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_engine_initialization(self):
        """Test engine initializes with proper adapters"""
        engine = UniversalZealotEngine(self.config)
        
        self.assertIsNotNone(engine.issue_adapter)
        self.assertIsNotNone(engine.vcs_adapter)
        self.assertIsNotNone(engine.llm_adapter)
        self.assertIsNotNone(engine.container_adapter)
        self.assertIsNotNone(engine.workflows)
        self.assertIsNotNone(engine.workflow_matcher)
        self.assertIsNotNone(engine.plugin_manager)
    
    async def test_execute_simple_task(self):
        """Test executing a simple task"""
        engine = UniversalZealotEngine(self.config)
        
        # Create a test task
        task = UniversalTask(
            issue_id='TEST-123',
            repository='https://github.com/test/repo',
            files=['test.py'],
            labels=['test']
        )
        
        # Execute task
        result = await engine.execute(task)
        
        # Verify result
        self.assertIsInstance(result, UniversalResult)
        self.assertEqual(result.task_id, task.id)
        # Mock adapters should succeed
        self.assertTrue(result.success)
    
    async def test_workflow_matching(self):
        """Test workflow matching for tasks"""
        engine = UniversalZealotEngine(self.config)
        
        # Task that matches test_workflow
        task = UniversalTask(
            files=['example.test'],
            labels=['test']
        )
        
        # Mock the adapters to return expected values
        engine.issue_adapter.get_issue = AsyncMock(return_value={
            'title': 'Test Issue',
            'description': 'Test description'
        })
        
        workspace = Mock(spec=Workspace)
        workspace.path = '/tmp/test'
        workspace.cleanup = AsyncMock()
        engine.container_adapter.create_workspace = AsyncMock(return_value=workspace)
        
        engine.vcs_adapter.clone = AsyncMock()
        engine.vcs_adapter.create_branch = AsyncMock(return_value='test-branch')
        engine.vcs_adapter.commit = AsyncMock(return_value='abc123')
        engine.vcs_adapter.push = AsyncMock()
        
        engine.llm_adapter.generate_edit = AsyncMock(return_value={
            'content': 'Modified content',
            'summary': 'Changes made'
        })
        
        # Execute
        result = await engine.execute(task)
        
        # Verify workflow was matched and used
        self.assertTrue(result.success)
        self.assertEqual(result.metadata['workflow'], 'test_workflow')
    
    async def test_llm_context_generation(self):
        """Test LLM context is properly generated from template"""
        engine = UniversalZealotEngine(self.config)
        
        task = UniversalTask(
            issue_id='TEST-456',
            files=['example.py'],
            labels=['test']
        )
        
        # Mock issue data
        issue_data = {
            'title': 'Add new feature',
            'description': 'Implement feature X with requirements Y'
        }
        engine.issue_adapter.get_issue = AsyncMock(return_value=issue_data)
        
        # Setup mocks
        workspace = Mock(spec=Workspace)
        workspace.path = self.temp_dir
        workspace.cleanup = AsyncMock()
        engine.container_adapter.create_workspace = AsyncMock(return_value=workspace)
        
        # Create test file
        test_file = os.path.join(self.temp_dir, 'example.py')
        with open(test_file, 'w') as f:
            f.write('print("hello")')
        
        # Capture LLM call
        llm_calls = []
        async def capture_llm_call(config):
            llm_calls.append(config)
            return {'content': 'modified', 'summary': 'done'}
        
        engine.llm_adapter.generate_edit = capture_llm_call
        
        # Other mocks
        engine.vcs_adapter.clone = AsyncMock()
        engine.vcs_adapter.create_branch = AsyncMock(return_value='test-branch')
        engine.vcs_adapter.commit = AsyncMock(return_value='abc123')
        engine.vcs_adapter.push = AsyncMock()
        
        # Execute
        result = await engine.execute(task)
        
        # Verify LLM context
        self.assertEqual(len(llm_calls), 1)
        self.assertIn('context', llm_calls[0])
        self.assertIn('Implement feature X', llm_calls[0]['context'])
    
    async def test_plugin_execution(self):
        """Test plugin execution during workflow stages"""
        engine = UniversalZealotEngine(self.config)
        
        # Create workflow with plugin hooks
        workflow_with_plugins = {
            'workflows': [{
                'name': 'plugin_test',
                'match': {'labels': ['plugin-test']},
                'context_template': 'Test',
                'pre_edit': [{
                    'name': 'pre_stage',
                    'hooks': [{
                        'name': 'echo_test',
                        'command': 'echo "pre-edit"',
                        'timeout': 30
                    }]
                }],
                'validation': [{
                    'name': 'val_stage',
                    'hooks': [{
                        'name': 'validate_test',
                        'command': 'echo "validation"',
                        'timeout': 30
                    }]
                }]
            }]
        }
        
        # Write workflow
        workflow_file = os.path.join(self.workflows_dir, 'plugin_test.yaml')
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_with_plugins, f)
        
        # Reload workflows
        from zealot.workflows.schema import WorkflowLoader, WorkflowMatcher
        engine.workflows = WorkflowLoader.load_from_directory(self.workflows_dir)
        engine.workflow_matcher = WorkflowMatcher(engine.workflows)
        
        # Create task
        task = UniversalTask(
            files=['test.py'],
            labels=['plugin-test']
        )
        
        # Mock adapters
        workspace = Mock(spec=Workspace)
        workspace.path = self.temp_dir
        workspace.cleanup = AsyncMock()
        engine.container_adapter.create_workspace = AsyncMock(return_value=workspace)
        
        engine.vcs_adapter.clone = AsyncMock()
        engine.vcs_adapter.create_branch = AsyncMock(return_value='test-branch')
        engine.vcs_adapter.commit = AsyncMock(return_value='abc123')
        engine.vcs_adapter.push = AsyncMock()
        
        engine.llm_adapter.generate_edit = AsyncMock(return_value={
            'content': 'modified',
            'summary': 'done'
        })
        
        # Create test file
        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('test')
        
        # Execute
        result = await engine.execute(task)
        
        # Verify validation results exist
        self.assertTrue(result.success)
        self.assertIsInstance(result.validation_results, list)
    
    async def test_error_handling(self):
        """Test error handling in task execution"""
        engine = UniversalZealotEngine(self.config)
        
        # Create task that will fail
        task = UniversalTask(
            issue_id='FAIL-123',
            files=['nonexistent.py']
        )
        
        # Make issue adapter fail
        engine.issue_adapter.get_issue = AsyncMock(
            side_effect=Exception("Issue not found")
        )
        
        # Execute
        result = await engine.execute(task)
        
        # Verify failure is handled gracefully
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("Issue not found", result.error)
        self.assertIsNotNone(result.duration_seconds)
    
    def test_branch_name_generation(self):
        """Test branch name generation"""
        engine = UniversalZealotEngine(self.config)
        
        task = UniversalTask(
            id='abcd1234-5678-90ef',
            issue_id='TEST-789'
        )
        
        issue_data = {
            'title': 'Add New Feature!'
        }
        
        # Test default pattern
        branch_name = engine._generate_branch_name(task, issue_data)
        self.assertIn('abcd1234', branch_name)
        
        # Test with custom pattern
        engine.config.vcs['branch_pattern'] = 'feature/{issue_id}-{slug}'
        branch_name = engine._generate_branch_name(task, issue_data)
        self.assertEqual(branch_name, 'feature/TEST-789-add-new-feature')
    
    def test_commit_message_generation(self):
        """Test commit message generation"""
        engine = UniversalZealotEngine(self.config)
        
        task = UniversalTask(
            id='test-123',
            issue_id='TEST-999'
        )
        
        issue_data = {
            'title': 'Fix critical bug'
        }
        
        changes = [
            {'file': 'src/main.py'},
            {'file': 'tests/test_main.py'}
        ]
        
        message = engine._generate_commit_message(task, issue_data, changes)
        
        self.assertIn('Fix critical bug', message)
        self.assertIn('TEST-999', message)
        self.assertIn('src/main.py', message)
        self.assertIn('tests/test_main.py', message)


class TestUniversalIntegration(unittest.TestCase):
    """Integration tests for universal architecture"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = os.path.join(self.temp_dir, 'workflows')
        os.makedirs(self.workflows_dir)
        
        # Create complete test configuration
        self.config_file = os.path.join(self.temp_dir, 'config.yaml')
        config_data = {
            'workflows_dir': self.workflows_dir,
            'issue_source': {
                'type': 'mock',
                'test_mode': True
            },
            'vcs': {
                'type': 'mock',
                'branch_pattern': 'feature/{issue_id}'
            },
            'llm': {
                'provider': 'mock',
                'response': 'Test modification'
            },
            'container': {
                'type': 'mock',
                'workspace_dir': self.temp_dir
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create test workflow
        workflow_data = {
            'workflows': [{
                'name': 'integration_test',
                'description': 'Integration test workflow',
                'match': {
                    'labels': ['integration']
                },
                'context_template': '''
                Task: {issue_title}
                Description: {issue_description}
                File: {file_path}
                Content: {current_content}
                ''',
                'pre_edit': [{
                    'name': 'setup',
                    'hooks': [{
                        'name': 'prepare',
                        'command': 'echo "Preparing workspace"'
                    }]
                }],
                'validation': [{
                    'name': 'verify',
                    'hooks': [{
                        'name': 'check',
                        'command': 'echo "Validating changes"'
                    }]
                }]
            }]
        }
        
        workflow_file = os.path.join(self.workflows_dir, 'integration.yaml')
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_data, f)
    
    def tearDown(self):
        """Cleanup integration test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    async def test_full_workflow_execution(self):
        """Test complete workflow execution from config to result"""
        # Load config from file
        config = UniversalConfig.from_file(self.config_file)
        
        # Create engine
        engine = UniversalZealotEngine(config)
        
        # Create task
        task = UniversalTask(
            issue_id='INT-001',
            issue_source='mock',
            repository='https://github.com/test/integration',
            files=['main.py'],
            labels=['integration']
        )
        
        # Execute
        result = await engine.execute(task)
        
        # Verify complete execution
        self.assertTrue(result.success)
        self.assertEqual(result.metadata['workflow'], 'integration_test')
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0]['file'], 'main.py')


def run_async_test(test_func):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_func())
    finally:
        loop.close()


if __name__ == '__main__':
    # Run async tests
    print("Running Universal Engine async tests...")
    
    test = TestUniversalEngine()
    test.setUp()
    
    async_tests = [
        test.test_execute_simple_task,
        test.test_workflow_matching,
        test.test_llm_context_generation,
        test.test_plugin_execution,
        test.test_error_handling
    ]
    
    for async_test in async_tests:
        print(f"Running {async_test.__name__}...")
        run_async_test(async_test)
        print(f"✓ {async_test.__name__} passed")
    
    test.tearDown()
    
    # Run integration tests
    print("\nRunning integration tests...")
    integration_test = TestUniversalIntegration()
    integration_test.setUp()
    
    print("Running test_full_workflow_execution...")
    run_async_test(integration_test.test_full_workflow_execution)
    print("✓ test_full_workflow_execution passed")
    
    integration_test.tearDown()
    
    print("\nRunning synchronous tests...")
    # Run regular unittest for synchronous tests
    unittest.main(argv=[''], exit=False, verbosity=2)
