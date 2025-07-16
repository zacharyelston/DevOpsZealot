"""
Unit tests for universal architecture components
"""
import unittest
import asyncio
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from zealot.universal_config import UniversalConfig
from zealot.workflows.schema import Workflow, WorkflowMatch, WorkflowMatcher
from zealot.plugins.interface import PluginManager, PluginContext, CommandPlugin
from zealot.universal_engine import UniversalTask


class TestUniversalConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        config_data = {
            'server_host': '127.0.0.1',
            'server_port': 9090,
            'workflows_dir': '/tmp/workflows',
            'issue_source': {'type': 'mock'},
            'vcs': {'type': 'mock'},
            'llm': {'provider': 'mock'},
            'container': {'type': 'mock'}
        }
        
        config = UniversalConfig.from_dict(config_data)
        
        self.assertEqual(config.server_host, '127.0.0.1')
        self.assertEqual(config.server_port, 9090)
        self.assertEqual(config.workflows_dir, '/tmp/workflows')
        self.assertEqual(config.issue_source['type'], 'mock')
    
    def test_env_override(self):
        """Test environment variable overrides"""
        os.environ['ZEALOT_SERVER_PORT'] = '8888'
        
        config = UniversalConfig.from_env()
        
        self.assertEqual(config.server_port, 8888)
        
        # Cleanup
        del os.environ['ZEALOT_SERVER_PORT']


class TestWorkflowMatching(unittest.TestCase):
    """Test workflow matching logic"""
    
    def setUp(self):
        """Setup test workflows"""
        self.workflows = [
            Workflow(
                name="terraform",
                match=WorkflowMatch(
                    labels=["infrastructure"],
                    file_patterns=["*.tf", "*.tfvars"]
                )
            ),
            Workflow(
                name="python",
                match=WorkflowMatch(
                    file_patterns=["*.py"],
                    metadata_filters={"language": "python"}
                )
            ),
            Workflow(name="default")
        ]
        
        self.matcher = WorkflowMatcher(self.workflows)
    
    def test_match_by_label(self):
        """Test matching by labels"""
        task = UniversalTask(
            files=["main.tf"],
            labels=["infrastructure"]
        )
        
        workflow = self.matcher.find_workflow(task)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.name, "terraform")
    
    def test_match_by_file_pattern(self):
        """Test matching by file patterns"""
        task = UniversalTask(
            files=["app.py", "test.py"]
        )
        
        workflow = self.matcher.find_workflow(task)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.name, "python")
    
    def test_default_workflow(self):
        """Test default workflow selection"""
        task = UniversalTask(
            files=["README.md"]
        )
        
        workflow = self.matcher.find_workflow(task)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.name, "default")


class TestPluginSystem(unittest.TestCase):
    """Test plugin system"""
    
    def setUp(self):
        """Setup plugin manager"""
        self.plugin_manager = PluginManager()
    
    def test_builtin_plugins(self):
        """Test built-in plugins are registered"""
        self.assertIn('command', self.plugin_manager.plugins)
        self.assertIn('python', self.plugin_manager.plugins)
    
    def test_create_command_plugin(self):
        """Test creating command plugin"""
        plugin = self.plugin_manager.create_plugin('command', {
            'pre_edit_commands': ['echo "test"']
        })
        
        self.assertIsInstance(plugin, CommandPlugin)
    
    async def test_plugin_execution(self):
        """Test plugin execution"""
        plugin = self.plugin_manager.create_plugin('command', {
            'pre_edit_commands': ['echo "Hello from plugin"']
        })
        
        context = PluginContext(
            task_id='test-123',
            workspace_path='/tmp/test',
            issue_data={},
            files=[],
            metadata={},
            environment={}
        )
        
        result = await plugin.pre_edit(context)
        self.assertTrue(result.success)


class TestAdapterLoading(unittest.TestCase):
    """Test adapter loading mechanism"""
    
    def test_mock_adapter_loading(self):
        """Test loading mock adapters"""
        from zealot.adapters.mock import (
            MockIssueAdapter,
            MockVCSAdapter,
            MockLLMAdapter,
            MockContainerAdapter
        )
        
        # Test instantiation
        issue_adapter = MockIssueAdapter({})
        vcs_adapter = MockVCSAdapter({})
        llm_adapter = MockLLMAdapter({})
        container_adapter = MockContainerAdapter({})
        
        self.assertIsNotNone(issue_adapter)
        self.assertIsNotNone(vcs_adapter)
        self.assertIsNotNone(llm_adapter)
        self.assertIsNotNone(container_adapter)


if __name__ == '__main__':
    # Run async tests
    async def run_async_tests():
        test = TestPluginSystem()
        test.setUp()
        await test.test_plugin_execution()
        print("✓ Async plugin test passed")
    
    asyncio.run(run_async_tests())
    
    # Run sync tests
    unittest.main(verbosity=2)
