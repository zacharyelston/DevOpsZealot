#!/usr/bin/env python3
"""
Basic test for Universal Zealot Engine without complex dependencies
This test focuses on testing the core universal architecture
"""
import os
import sys
import tempfile
import yaml
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_config_loading():
    """Test configuration loading from file"""
    print("Testing configuration loading...")
    
    # Create temporary config file
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'test-config.yaml')
    
    config_data = {
        'workflows_dir': './workflows',
        'issue_source': {
            'type': 'mock',
            'test_mode': True
        },
        'vcs': {
            'type': 'mock',
            'branch_pattern': 'feature/{issue_id}'
        },
        'llm': {
            'provider': 'mock'
        },
        'container': {
            'type': 'mock'
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    # Test loading
    try:
        from zealot.universal_config import UniversalConfig
        config = UniversalConfig.from_file(config_file)
        
        assert config.issue_source['type'] == 'mock'
        assert config.vcs['type'] == 'mock'
        assert config.llm['provider'] == 'mock'
        
        print("✓ Configuration loading works")
        return True
        
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def test_workflow_schema():
    """Test workflow schema loading"""
    print("Testing workflow schema...")
    
    temp_dir = tempfile.mkdtemp()
    workflow_file = os.path.join(temp_dir, 'test-workflow.yaml')
    
    workflow_data = {
        'workflows': [{
            'name': 'test_workflow',
            'description': 'Test workflow',
            'match': {
                'labels': ['test'],
                'file_patterns': ['*.py']
            },
            'context_template': 'Edit file {file_path}',
            'pre_edit': [{
                'name': 'setup',
                'hooks': [{
                    'name': 'check',
                    'command': 'echo "setup"'
                }]
            }],
            'validation': [{
                'name': 'validate',
                'hooks': [{
                    'name': 'test',
                    'command': 'echo "validate"'
                }]
            }]
        }]
    }
    
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_data, f)
    
    try:
        from zealot.workflows.schema import WorkflowLoader, WorkflowMatcher
        
        workflows = WorkflowLoader.load_from_file(workflow_file)
        assert len(workflows) == 1
        
        workflow = workflows[0]
        assert workflow.name == 'test_workflow'
        assert len(workflow.pre_edit) == 1
        assert len(workflow.validation) == 1
        
        # Test matching
        matcher = WorkflowMatcher(workflows)
        
        # Create a mock task object
        class MockTask:
            def __init__(self):
                self.labels = ['test']
                self.files = ['example.py']
                self.repository = 'test/repo'
                self.metadata = {}
        
        task = MockTask()
        try:
            matched_workflow = matcher.find_workflow(task)
            
            assert matched_workflow is not None
            assert matched_workflow.name == 'test_workflow'
        except Exception as e:
            print(f"Workflow matching error: {e}")
            print(f"Workflow patterns: {workflow.match.file_patterns if workflow.match else 'No match criteria'}")
            raise
        
        print("✓ Workflow schema works")
        return True
        
    except Exception as e:
        print(f"✗ Workflow schema failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def test_adapter_interfaces():
    """Test adapter interfaces"""
    print("Testing adapter interfaces...")
    
    try:
        from zealot.adapters.base import IssueAdapter, VCSAdapter, LLMAdapter, ContainerAdapter
        from zealot.adapters.mock import MockIssueAdapter, MockVCSAdapter, MockLLMAdapter, MockContainerAdapter
        
        # Test mock adapters can be created
        issue_adapter = MockIssueAdapter({'type': 'mock'})
        vcs_adapter = MockVCSAdapter({'type': 'mock'})
        llm_adapter = MockLLMAdapter({'provider': 'mock'})
        container_adapter = MockContainerAdapter({'type': 'mock'})
        
        # Verify they inherit from base classes
        assert isinstance(issue_adapter, IssueAdapter)
        assert isinstance(vcs_adapter, VCSAdapter)
        assert isinstance(llm_adapter, LLMAdapter)
        assert isinstance(container_adapter, ContainerAdapter)
        
        print("✓ Adapter interfaces work")
        return True
        
    except Exception as e:
        print(f"✗ Adapter interfaces failed: {e}")
        return False

def test_plugins():
    """Test plugin system"""
    print("Testing plugin system...")
    
    try:
        from zealot.plugins.interface import PluginManager, PluginContext, PluginResult
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Test plugin creation
        command_plugin = plugin_manager.create_plugin('command', {
            'validation_commands': ['echo "test"']
        })
        
        assert command_plugin is not None
        
        # Test context creation
        context = PluginContext(
            task_id='test-123',
            workspace_path='/tmp/test',
            issue_data={'title': 'Test'},
            files=['test.py'],
            metadata={},
            environment={'TEST': 'value'}
        )
        
        assert context.task_id == 'test-123'
        assert context.get_env('TEST') == 'value'
        
        print("✓ Plugin system works")
        return True
        
    except Exception as e:
        print(f"✗ Plugin system failed: {e}")
        return False

def test_universal_task():
    """Test universal task structure"""
    print("Testing universal task structure...")
    
    try:
        from zealot.universal_engine import UniversalTask, UniversalResult
        
        # Create task
        task = UniversalTask(
            issue_id='TEST-123',
            repository='https://github.com/test/repo',
            files=['main.py'],
            labels=['test', 'python']
        )
        
        assert task.issue_id == 'TEST-123'
        assert 'main.py' in task.files
        assert 'test' in task.labels
        
        # Create result
        result = UniversalResult(
            task_id=task.id,
            success=True,
            changes=[{'file': 'main.py', 'status': 'modified'}]
        )
        
        assert result.task_id == task.id
        assert result.success is True
        assert len(result.changes) == 1
        
        print("✓ Universal task structure works")
        return True
        
    except Exception as e:
        print(f"✗ Universal task structure failed: {e}")
        return False

def test_engine_creation():
    """Test engine creation without Redis"""
    print("Testing engine creation...")
    
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    # Create minimal workflow
    workflow_file = os.path.join(workflows_dir, 'test.yaml')
    workflow_data = {
        'workflows': [{
            'name': 'simple',
            'context_template': 'Edit {file_path}',
            'pre_edit': [],
            'post_edit': [],
            'validation': []
        }]
    }
    
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_data, f)
    
    try:
        from zealot.universal_config import UniversalConfig
        from zealot.universal_engine import UniversalZealotEngine
        
        config = UniversalConfig(
            workflows_dir=workflows_dir,
            issue_source={'type': 'mock'},
            vcs={'type': 'mock'},
            llm={'provider': 'mock'},
            container={'type': 'mock'},
            redis_url=None  # No Redis
        )
        
        engine = UniversalZealotEngine(config)
        
        assert engine is not None
        assert len(engine.workflows) == 1
        assert engine.workflows[0].name == 'simple'
        
        print("✓ Engine creation works")
        return True
        
    except Exception as e:
        print(f"✗ Engine creation failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def main():
    """Run all basic tests"""
    print("=== Universal Zealot Engine Basic Tests ===")
    print("Testing core components without complex dependencies\n")
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Workflow Schema", test_workflow_schema),
        ("Adapter Interfaces", test_adapter_interfaces),
        ("Plugin System", test_plugins),
        ("Universal Task Structure", test_universal_task),
        ("Engine Creation", test_engine_creation)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name} failed with error: {e}")
        print("")
    
    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"{name:.<40} {status}")
        if error:
            print(f"  Error: {error}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    return all(success for _, success, _ in results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
