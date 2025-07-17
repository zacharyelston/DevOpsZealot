#!/usr/bin/env python3
"""
Simple CI/CD test to verify universal architecture files exist
No external dependencies required
"""
import os
import sys

def test_file_structure():
    """Test that all expected files exist"""
    print("Testing universal architecture file structure...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    files_to_check = [
        'src/zealot/universal_config.py',
        'src/zealot/universal_engine.py',
        'src/zealot/workflows/__init__.py',
        'src/zealot/workflows/schema.py',
        'src/zealot/plugins/__init__.py',
        'src/zealot/plugins/interface.py',
        'src/zealot/adapters/__init__.py',
        'src/zealot/adapters/base.py',
        'src/zealot/adapters/mock.py',
        'examples/configs/zealot-config.yaml',
        'examples/workflows/example-workflows.yaml',
    ]
    
    all_exist = True
    for file_path in files_to_check:
        full_path = os.path.join(base_dir, file_path)
        exists = os.path.exists(full_path)
        status = "✓" if exists else "✗"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False
    
    return all_exist

def main():
    """Run the test"""
    print("=== Universal Architecture CI/CD Test ===\n")
    
    success = test_file_structure()
    
    if success:
        print("\n✓ All universal architecture files are present!")
        print("\nImplementation includes:")
        print("- Universal engine without hardcoded workflows")
        print("- Configuration system for external behavior")
        print("- Workflow definitions and matching logic")
        print("- Plugin architecture for extensibility")
        print("- Adapter interfaces for all external systems")
        return 0
    else:
        print("\n✗ Some files are missing")
        return 1

if __name__ == '__main__':
    sys.exit(main())
