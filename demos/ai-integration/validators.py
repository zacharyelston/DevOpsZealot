#!/usr/bin/env python3
"""
Script Validation Utilities for DevOpsZealot

This module provides validation functions to verify that modified scripts
meet the required standards and pass validation checks.
"""

import os
import sys
import subprocess
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Validator:
    """Class to validate modified files against validation rules"""
    
    def __init__(self, repo_path: str, verbose: bool = False):
        """
        Initialize the validator
        
        Args:
            repo_path: Path to the repository
            verbose: Enable verbose logging
        """
        self.repo_path = Path(repo_path).absolute()
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def validate(self, files: List[Path], rules: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate files according to specified rules
        
        Args:
            files: List of files to validate
            rules: List of validation rules to apply
            
        Returns:
            Tuple containing success status and validation results
        """
        results = {
            "success": True,
            "rule_results": {}
        }
        
        for rule in rules:
            rule_method = getattr(self, f"validate_{rule}", None)
            if rule_method is None:
                logger.warning(f"Unknown validation rule: {rule}")
                continue
                
            logger.info(f"Applying validation rule: {rule}")
            rule_success, rule_result = rule_method(files)
            
            results["rule_results"][rule] = {
                "success": rule_success,
                "details": rule_result
            }
            
            if not rule_success:
                results["success"] = False
        
        return results["success"], results
    
    def validate_shellcheck(self, files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate shell scripts using shellcheck
        
        Args:
            files: List of files to validate
            
        Returns:
            Tuple containing success status and validation results
        """
        shell_files = [f for f in files if f.suffix == '.sh' or os.access(f, os.X_OK)]
        if not shell_files:
            return True, {"message": "No shell scripts to validate"}
        
        # Check if shellcheck is installed
        try:
            subprocess.run(["shellcheck", "--version"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("shellcheck not installed, skipping shell script validation")
            return True, {"message": "shellcheck not installed, validation skipped"}
        
        results = {}
        success = True
        
        for script in shell_files:
            relative_path = script.relative_to(self.repo_path)
            logger.debug(f"Validating shell script: {relative_path}")
            
            try:
                # Run shellcheck
                proc = subprocess.run(
                    ["shellcheck", "-x", str(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if proc.returncode == 0:
                    results[str(relative_path)] = {
                        "success": True,
                        "message": "Passed shellcheck validation"
                    }
                else:
                    success = False
                    results[str(relative_path)] = {
                        "success": False,
                        "message": "Failed shellcheck validation",
                        "errors": proc.stderr
                    }
                    logger.error(f"Shellcheck errors in {relative_path}:\n{proc.stderr}")
            except Exception as e:
                success = False
                results[str(relative_path)] = {
                    "success": False,
                    "message": f"Error running shellcheck: {str(e)}"
                }
                logger.error(f"Error validating {relative_path}: {str(e)}")
        
        return success, results
    
    def validate_script_execution_test(self, files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
        """
        Test if scripts can execute without syntax errors
        
        Args:
            files: List of files to validate
            
        Returns:
            Tuple containing success status and validation results
        """
        shell_files = [f for f in files if f.suffix == '.sh' or os.access(f, os.X_OK)]
        if not shell_files:
            return True, {"message": "No shell scripts to validate"}
        
        results = {}
        success = True
        
        for script in shell_files:
            relative_path = script.relative_to(self.repo_path)
            logger.debug(f"Testing execution of shell script: {relative_path}")
            
            try:
                # Test with bash -n for syntax checking
                proc = subprocess.run(
                    ["bash", "-n", str(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if proc.returncode == 0:
                    results[str(relative_path)] = {
                        "success": True,
                        "message": "Script has valid syntax"
                    }
                else:
                    success = False
                    results[str(relative_path)] = {
                        "success": False,
                        "message": "Script has syntax errors",
                        "errors": proc.stderr
                    }
                    logger.error(f"Syntax errors in {relative_path}:\n{proc.stderr}")
            except Exception as e:
                success = False
                results[str(relative_path)] = {
                    "success": False,
                    "message": f"Error testing script: {str(e)}"
                }
                logger.error(f"Error validating {relative_path}: {str(e)}")
        
        return success, results
    
    def validate_python_lint(self, files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate Python files using pylint or flake8
        
        Args:
            files: List of files to validate
            
        Returns:
            Tuple containing success status and validation results
        """
        python_files = [f for f in files if f.suffix == '.py']
        if not python_files:
            return True, {"message": "No Python files to validate"}
        
        # Check if pylint or flake8 is installed
        lint_tool = None
        for tool in ["flake8", "pylint"]:
            try:
                subprocess.run([tool, "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              check=True)
                lint_tool = tool
                break
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        if lint_tool is None:
            logger.warning("No Python linting tools found, skipping Python validation")
            return True, {"message": "No Python linting tools found, validation skipped"}
        
        results = {}
        success = True
        
        for py_file in python_files:
            relative_path = py_file.relative_to(self.repo_path)
            logger.debug(f"Validating Python file: {relative_path}")
            
            try:
                # Run linter
                proc = subprocess.run(
                    [lint_tool, str(py_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if proc.returncode == 0:
                    results[str(relative_path)] = {
                        "success": True,
                        "message": f"Passed {lint_tool} validation"
                    }
                else:
                    # Don't fail on lint warnings, just report them
                    results[str(relative_path)] = {
                        "success": True,
                        "message": f"{lint_tool} found issues",
                        "warnings": proc.stdout or proc.stderr
                    }
                    logger.warning(f"{lint_tool} issues in {relative_path}:\n{proc.stdout or proc.stderr}")
            except Exception as e:
                results[str(relative_path)] = {
                    "success": False,
                    "message": f"Error running {lint_tool}: {str(e)}"
                }
                logger.error(f"Error validating {relative_path}: {str(e)}")
        
        return success, results


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate files against rules')
    parser.add_argument('--repo', required=True, help='Repository path')
    parser.add_argument('--files', required=True, nargs='+', help='Files to validate')
    parser.add_argument('--rules', required=True, nargs='+', help='Rules to apply')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    validator = Validator(args.repo, args.verbose)
    file_paths = [Path(f) for f in args.files]
    success, results = validator.validate(file_paths, args.rules)
    
    print(json.dumps(results, indent=2))
    sys.exit(0 if success else 1)
