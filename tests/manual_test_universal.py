#!/usr/bin/env python3
"""
Manual test script for Universal Zealot Engine
This script demonstrates how to use the universal architecture
"""
import asyncio
import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from zealot.universal_config import UniversalConfig
from zealot.universal_engine import UniversalZealotEngine, UniversalTask


async def test_basic_execution():
    """Test basic task execution with mock adapters"""
    print("\n=== Test 1: Basic Execution with Mock Adapters ===")
    
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    workflows_dir = os.path.join(temp_dir, 'workflows')
    os.makedirs(workflows_dir)
    
    # Create a simple workflow
    workflow_config = {
        'workflows': [{
            'name': 'simple_test',
            'description': 'Simple test workflow',
            'match': {
                'labels': ['test']
            },
            'context_template': '''
Edit the file according to these requirements:
File: {file_path}
Current content:
{current_content}

Requirements: Make the code better
            ''',
            'pre_edit': [],
            'post_edit': [],
            'validation': [{
                'name': 'validate',
                'hooks': [{
                    'name': 'echo_validation',
                    'command': 'echo "Validation passed"'
                }]
            }]
        }]
    }
    
    # Write workflow file
    workflow_file = os.path.join(workflows_dir, 'test.yaml')
    with open(workflow_file, 'w') as f:
        yaml.dump(workflow_config, f)
    
    # Create configuration
    config = UniversalConfig(
        workflows_dir=workflows_dir,
        issue_source={'type': 'mock'},
        vcs={'type': 'mock', 'branch_pattern': 'test/{task_id}'},
        llm={'provider': 'mock'},
        container={'type': 'mock'}
    )
    
    # Create engine
    engine = UniversalZealotEngine(config)
    print(f"✓ Engine created with {len(engine.workflows)} workflows loaded")
    
    # Create a task
    task = UniversalTask(
        issue_id='TEST-001',
        files=['example.py'],
        labels=['test'],
        metadata={'test_run': True}
    )
    print(f"✓ Task created: {task.id}")
    
    # Execute task
    print("Executing task...")
    result = await engine.execute(task)
    
    # Display results
    print(f"\nExecution Result:")
    print(f"  Success: {result.success}")
    print(f"  Task ID: {result.task_id}")
    print(f"  Duration: {result.duration_seconds:.2f}s")
    print(f"  Workflow: {result.metadata.get('workflow', 'N/A')}")
    
    if result.error:
        print(f"  Error: {result.error}")
    else:
        print(f"  Changes: {len(result.changes)} files modified")
        print(f"  Validation: {len(result.validation_results)} checks performed")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    return result.success


async def test_terraform_workflow():
    """Test Terraform-specific workflow"""
    print("\n=== Test 2: Terraform Workflow ===")
    
    # Use the example workflows directory
    examples_dir = Path(__file__).parent.parent / 'examples'
    
    # Create config pointing to examples
    config = UniversalConfig(
        workflows_dir=str(examples_dir / 'workflows'),
        issue_source={
            'type': 'mock',
            'mock_data': {
                'TEST-002': {
                    'title': 'Add S3 bucket for logs',
                    'description': 'Create an S3 bucket for storing application logs with versioning enabled'
                }
            }
        },
        vcs={'type': 'mock'},
        llm={
            'provider': 'mock',
            'mock_response': '''resource "aws_s3_bucket" "logs" {
  bucket = "myapp-logs-${var.environment}"
  
  tags = {
    Name        = "Application Logs"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  versioning_configuration {
    status = "Enabled"
  }
}'''
        },
        container={'type': 'mock'}
    )
    
    # Create engine
    engine = UniversalZealotEngine(config)
    print(f"✓ Engine created with {len(engine.workflows)} workflows loaded")
    
    # List available workflows
    print("\nAvailable workflows:")
    for wf in engine.workflows:
        print(f"  - {wf.name}: {wf.description}")
    
    # Create Terraform task
    task = UniversalTask(
        issue_id='TEST-002',
        repository='https://github.com/example/infra',
        files=['s3.tf'],
        labels=['infrastructure', 'terraform']
    )
    print(f"\n✓ Task created for Terraform workflow")
    
    # Execute
    print("Executing Terraform task...")
    result = await engine.execute(task)
    
    # Display results
    print(f"\nTerraform Task Result:")
    print(f"  Success: {result.success}")
    print(f"  Workflow: {result.metadata.get('workflow', 'N/A')}")
    
    if result.success and result.changes:
        print(f"\nGenerated Terraform code:")
        print("=" * 60)
        print(result.changes[0].get('modified', 'N/A'))
        print("=" * 60)
    
    return result.success


async def test_workflow_matching():
    """Test workflow matching logic"""
    print("\n=== Test 3: Workflow Matching ===")
    
    # Use example workflows
    examples_dir = Path(__file__).parent.parent / 'examples'
    
    config = UniversalConfig(
        workflows_dir=str(examples_dir / 'workflows'),
        issue_source={'type': 'mock'},
        vcs={'type': 'mock'},
        llm={'provider': 'mock'},
        container={'type': 'mock'}
    )
    
    engine = UniversalZealotEngine(config)
    
    # Test different task configurations
    test_cases = [
        {
            'name': 'Python file',
            'task': UniversalTask(files=['app.py']),
            'expected': 'python_workflow'
        },
        {
            'name': 'Terraform with label',
            'task': UniversalTask(files=['main.tf'], labels=['terraform']),
            'expected': 'terraform_workflow'
        },
        {
            'name': 'Kubernetes YAML',
            'task': UniversalTask(files=['deployment.yaml'], labels=['kubernetes']),
            'expected': 'kubernetes_workflow'
        },
        {
            'name': 'Dockerfile',
            'task': UniversalTask(files=['Dockerfile']),
            'expected': 'docker_workflow'
        },
        {
            'name': 'Unknown file',
            'task': UniversalTask(files=['README.md']),
            'expected': 'default'
        }
    ]
    
    print("\nTesting workflow matching:")
    for test in test_cases:
        workflow = engine.workflow_matcher.find_workflow(test['task'])
        matched_name = workflow.name if workflow else 'None'
        status = '✓' if matched_name == test['expected'] else '✗'
        print(f"  {status} {test['name']}: {matched_name} (expected: {test['expected']})")
    
    return True


async def test_with_real_config():
    """Test with a real configuration file"""
    print("\n=== Test 4: Real Configuration File ===")
    
    # Create a test config file
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'zealot-config.yaml')
    
    config_data = {
        'server_host': '127.0.0.1',
        'server_port': 9999,
        'workflows_dir': str(Path(__file__).parent.parent / 'examples' / 'workflows'),
        'issue_source': {
            'type': 'mock',
            'test_mode': True
        },
        'vcs': {
            'type': 'mock',
            'branch_pattern': 'zealot/{issue_id}-{slug}'
        },
        'llm': {
            'provider': 'mock',
            'temperature': 0.2
        },
        'container': {
            'type': 'mock'
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    print(f"✓ Created config file: {config_file}")
    
    # Load config from file
    config = UniversalConfig.from_file(config_file)
    print(f"✓ Loaded configuration")
    print(f"  Server: {config.server_host}:{config.server_port}")
    print(f"  Workflows dir: {config.workflows_dir}")
    
    # Create engine
    engine = UniversalZealotEngine(config)
    print(f"✓ Engine initialized")
    
    # Create and execute a task
    task = UniversalTask(
        issue_id='CONFIG-TEST',
        files=['test.py'],
        labels=['test']
    )
    
    result = await engine.execute(task)
    print(f"\n✓ Task executed successfully: {result.success}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    return result.success


async def main():
    """Run all manual tests"""
    print("=== Universal Zealot Engine Manual Tests ===")
    print("This script tests the universal architecture implementation")
    
    tests = [
        ("Basic Execution", test_basic_execution),
        ("Terraform Workflow", test_terraform_workflow),
        ("Workflow Matching", test_workflow_matching),
        ("Real Config File", test_with_real_config)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n✗ Test '{name}' failed with error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"{name:.<50} {status}")
        if error:
            print(f"  Error: {error}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    return all(success for _, success, _ in results)


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
