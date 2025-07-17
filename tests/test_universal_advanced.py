#!/usr/bin/env python3
"""
Advanced test for Universal Zealot Engine
Tests actual task execution with mock adapters
"""
import os
import sys
import tempfile
import yaml
import shutil
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_full_task_execution():
    """Test complete task execution end-to-end"""
    print("Testing full task execution...")
    
    # Create temporary environment
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    # Create comprehensive workflow
    workflow_file = os.path.join(workflows_dir, 'python-workflow.yaml')
    workflow_data = {
        'workflows': [{
            'name': 'python_development',
            'description': 'Python development workflow',
            'match': {
                'labels': ['python'],
                'file_patterns': ['*.py']
            },
            'context_template': '''
You are editing a Python file.

File: {file_path}
Current content:
{current_content}

Issue: {issue_title}
Description: {issue_description}

Please make the necessary changes to implement the requirements.
Follow Python best practices and PEP 8.
            ''',
            'pre_edit': [{
                'name': 'setup',
                'hooks': [{
                    'name': 'check_python',
                    'command': 'python --version',
                    'timeout': 30
                }]
            }],
            'post_edit': [{
                'name': 'format',
                'hooks': [{
                    'name': 'format_code',
                    'command': 'echo "Formatting Python code"',
                    'timeout': 60
                }]
            }],
            'validation': [{
                'name': 'validate',
                'hooks': [{
                    'name': 'syntax_check',
                    'command': 'python -m py_compile {file_path}',
                    'timeout': 30
                }, {
                    'name': 'lint',
                    'command': 'echo "Linting Python code"',
                    'timeout': 60,
                    'continue_on_failure': True
                }]
            }],
            'llm_config': {
                'temperature': 0.2,
                'max_tokens': 2000
            }
        }]
    }
    
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_data, f)
    
    try:
        from zealot.universal_config import UniversalConfig
        from zealot.universal_engine import UniversalZealotEngine, UniversalTask
        
        # Create configuration
        config = UniversalConfig(
            workflows_dir=workflows_dir,
            issue_source={
                'type': 'mock',
                'mock_data': {
                    'PY-123': {
                        'title': 'Add greeting function',
                        'description': 'Create a function that greets users by name'
                    }
                }
            },
            vcs={
                'type': 'mock',
                'branch_pattern': 'feature/{issue_id}'
            },
            llm={
                'provider': 'mock',
                'mock_response': '''def greet_user(name):
    """Greet a user by name"""
    if not name:
        return "Hello, stranger!"
    return f"Hello, {name}!"

# Example usage
if __name__ == "__main__":
    print(greet_user("Alice"))
    print(greet_user(""))
'''
            },
            container={'type': 'mock'},
            redis_url=None  # No Redis
        )
        
        # Create engine
        engine = UniversalZealotEngine(config)
        
        # Create task
        task = UniversalTask(
            issue_id='PY-123',
            repository='https://github.com/test/python-project',
            branch='main',
            files=['greet.py'],
            labels=['python', 'feature']
        )
        
        # Execute task
        result = await engine.execute(task)
        
        # Verify results
        assert result.success, f"Task failed: {result.error}"
        assert result.task_id == task.id
        assert result.metadata['workflow'] == 'python_development'
        assert len(result.changes) == 1
        assert result.changes[0]['file'] == 'greet.py'
        assert 'def greet_user' in result.changes[0]['modified']
        
        print("✓ Full task execution works")
        return True
        
    except Exception as e:
        print(f"✗ Full task execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)

async def test_workflow_matching():
    """Test workflow matching with different task types"""
    print("Testing workflow matching...")
    
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    # Create multiple workflows
    workflows_file = os.path.join(workflows_dir, 'all-workflows.yaml')
    workflows_data = {
        'workflows': [
            {
                'name': 'python_workflow',
                'match': {
                    'file_patterns': ['*.py'],
                    'labels': ['python']
                },
                'context_template': 'Python file editing'
            },
            {
                'name': 'terraform_workflow', 
                'match': {
                    'file_patterns': ['*.tf'],
                    'labels': ['terraform', 'infrastructure']
                },
                'context_template': 'Terraform file editing'
            },
            {
                'name': 'default_workflow',
                'context_template': 'General file editing'
            }
        ]
    }
    
    with open(workflows_file, 'w') as f:
        yaml.dump(workflows_data, f)
    
    try:
        from zealot.universal_config import UniversalConfig
        from zealot.universal_engine import UniversalZealotEngine, UniversalTask
        
        config = UniversalConfig(
            workflows_dir=workflows_dir,
            issue_source={'type': 'mock'},
            vcs={'type': 'mock'},
            llm={'provider': 'mock'},
            container={'type': 'mock'}
        )
        
        engine = UniversalZealotEngine(config)
        
        # Test cases
        test_cases = [
            {
                'task': UniversalTask(files=['app.py'], labels=['python']),
                'expected_workflow': 'python_workflow'
            },
            {
                'task': UniversalTask(files=['main.tf'], labels=['terraform']),
                'expected_workflow': 'terraform_workflow'
            },
            {
                'task': UniversalTask(files=['README.md'], labels=['docs']),
                'expected_workflow': 'default_workflow'
            },
            {
                'task': UniversalTask(files=['script.py'], labels=['automation']),
                'expected_workflow': 'default_workflow'  # No python label
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            workflow = engine.workflow_matcher.find_workflow(test_case['task'])
            assert workflow is not None, f"No workflow found for test case {i+1}"
            assert workflow.name == test_case['expected_workflow'], \
                f"Expected {test_case['expected_workflow']}, got {workflow.name} for test case {i+1}"
        
        print("✓ Workflow matching works")
        return True
        
    except Exception as e:
        print(f"✗ Workflow matching failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

async def test_mock_adapters():
    """Test all mock adapters work correctly"""
    print("Testing mock adapters...")
    
    try:
        from zealot.adapters.mock import (
            MockIssueAdapter, MockVCSAdapter, 
            MockLLMAdapter, MockContainerAdapter
        )
        
        # Test Issue Adapter
        issue_adapter = MockIssueAdapter({'type': 'mock'})
        issue = await issue_adapter.get_issue('TEST-123')
        assert issue['id'] == 'TEST-123'
        assert 'title' in issue
        assert 'description' in issue
        
        # Test VCS Adapter
        vcs_adapter = MockVCSAdapter({'type': 'mock'})
        await vcs_adapter.clone('/tmp/test', 'https://github.com/test/repo')
        branch = await vcs_adapter.create_branch('/tmp/test', 'feature/test')
        assert branch == 'feature/test'
        commit_sha = await vcs_adapter.commit('/tmp/test', 'Test commit')
        assert len(commit_sha) == 8  # Mock returns 8-char SHA
        
        # Test LLM Adapter
        llm_adapter = MockLLMAdapter({'provider': 'mock'})
        edit_result = await llm_adapter.generate_edit({
            'file_type': 'py',
            'context': 'Test context'
        })
        assert 'content' in edit_result
        assert 'summary' in edit_result
        assert 'def hello_world' in edit_result['content']  # Mock Python content
        
        # Test Container Adapter
        container_adapter = MockContainerAdapter({'type': 'mock'})
        workspace = await container_adapter.create_workspace('test-task')
        assert workspace.id == 'test-task'
        assert os.path.exists(workspace.path)
        
        cmd_result = await container_adapter.execute_command(workspace, 'echo test')
        assert cmd_result['returncode'] == 0
        assert 'test' in cmd_result['stdout']
        
        print("✓ Mock adapters work")
        return True
        
    except Exception as e:
        print(f"✗ Mock adapters failed: {e}")
        return False

async def test_error_handling():
    """Test error handling in various scenarios"""
    print("Testing error handling...")
    
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    # Create minimal workflow
    workflow_file = os.path.join(workflows_dir, 'test.yaml')
    workflow_data = {
        'workflows': [{
            'name': 'error_test',
            'context_template': 'Test',
            'pre_edit': [],
            'post_edit': [],
            'validation': []
        }]
    }
    
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_data, f)
    
    try:
        from zealot.universal_config import UniversalConfig
        from zealot.universal_engine import UniversalZealotEngine, UniversalTask
        
        config = UniversalConfig(
            workflows_dir=workflows_dir,
            issue_source={'type': 'mock'},
            vcs={'type': 'mock'},
            llm={'provider': 'mock'},
            container={'type': 'mock'}
        )
        
        engine = UniversalZealotEngine(config)
        
        # Test 1: Task without matching workflow
        task = UniversalTask(
            issue_id='NONEXISTENT-123',
            files=['unknown.xyz'],
            labels=['nonexistent']
        )
        
        result = await engine.execute(task)
        assert result.success, "Should succeed with default workflow"
        
        # Test 2: Task with invalid issue ID (should still work with mock)
        task2 = UniversalTask(
            issue_id='INVALID',
            files=['test.py']
        )
        
        result2 = await engine.execute(task2)
        assert result2.success, "Should handle invalid issue IDs gracefully"
        
        print("✓ Error handling works")
        return True
        
    except Exception as e:
        print(f"✗ Error handling failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

async def test_branch_and_commit_generation():
    """Test branch name and commit message generation"""
    print("Testing branch and commit generation...")
    
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    workflow_file = os.path.join(workflows_dir, 'test.yaml')
    workflow_data = {
        'workflows': [{
            'name': 'branch_test',
            'context_template': 'Test'
        }]
    }
    
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_data, f)
    
    try:
        from zealot.universal_config import UniversalConfig
        from zealot.universal_engine import UniversalZealotEngine, UniversalTask
        
        config = UniversalConfig(
            workflows_dir=workflows_dir,
            issue_source={
                'type': 'mock',
                'mock_data': {
                    'BRANCH-123': {
                        'title': 'Add User Authentication Feature!'
                    }
                }
            },
            vcs={
                'type': 'mock',
                'branch_pattern': 'feature/{issue_id}-{slug}'
            },
            llm={'provider': 'mock'},
            container={'type': 'mock'}
        )
        
        engine = UniversalZealotEngine(config)
        
        task = UniversalTask(
            issue_id='BRANCH-123',
            repository='https://github.com/test/repo',
            files=['auth.py', 'user.py']
        )
        
        # Test branch name generation
        issue_data = {'title': 'Add User Authentication Feature!'}
        branch_name = engine._generate_branch_name(task, issue_data)
        
        assert 'BRANCH-123' in branch_name
        assert 'add-user-authentication-feature' in branch_name
        
        # Test commit message generation
        changes = [
            {'file': 'auth.py'},
            {'file': 'user.py'}
        ]
        
        commit_message = engine._generate_commit_message(task, issue_data, changes)
        
        assert 'Add User Authentication Feature!' in commit_message
        assert 'BRANCH-123' in commit_message
        assert 'auth.py' in commit_message
        assert 'user.py' in commit_message
        
        print("✓ Branch and commit generation works")
        return True
        
    except Exception as e:
        print(f"✗ Branch and commit generation failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

async def main():
    """Run all advanced tests"""
    print("=== Universal Zealot Engine Advanced Tests ===")
    print("Testing comprehensive functionality with mock adapters\n")
    
    tests = [
        ("Full Task Execution", test_full_task_execution),
        ("Workflow Matching", test_workflow_matching),
        ("Mock Adapters", test_mock_adapters),
        ("Error Handling", test_error_handling),
        ("Branch & Commit Generation", test_branch_and_commit_generation)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name} failed with error: {e}")
        print("")
    
    # Summary
    print("=" * 60)
    print("ADVANCED TEST SUMMARY")
    print("=" * 60)
    
    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"{name:.<45} {status}")
        if error:
            print(f"  Error: {error}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)
    
    print(f"\nTotal: {passed_tests}/{total_tests} advanced tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Universal architecture is working correctly.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Review implementation.")
    
    return all(success for _, success, _ in results)

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
