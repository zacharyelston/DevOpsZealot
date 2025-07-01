"""Validation pipeline for code changes"""
import asyncio
import json
import yaml
import subprocess
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()

class ValidationResult:
    """Represents a validation result"""
    def __init__(self, passed: bool, validator: str, message: str = "", details: Optional[Dict] = None):
        self.passed = passed
        self.validator = validator
        self.message = message
        self.details = details or {}

class BaseValidator:
    """Base class for validators"""
    
    async def validate(self, content: str, container=None) -> ValidationResult:
        """Validate content"""
        raise NotImplementedError

class TerraformValidator(BaseValidator):
    """Terraform validation"""
    
    async def validate_syntax(self, content: str, container=None) -> ValidationResult:
        """Validate Terraform syntax"""
        if not container:
            return ValidationResult(False, "terraform", "No container provided")
        
        try:
            # Write content to temporary file
            await container.write_file("/workspace/temp.tf", content)
            
            # Run terraform fmt check
            fmt_result = await container.exec_command("terraform fmt -check /workspace/temp.tf")
            
            # Run terraform validate
            init_result = await container.exec_command("terraform init -backend=false /workspace")
            validate_result = await container.exec_command("terraform validate /workspace")
            
            if validate_result["exit_code"] == 0:
                return ValidationResult(True, "terraform", "Terraform syntax valid")
            else:
                return ValidationResult(
                    False, 
                    "terraform", 
                    "Terraform validation failed",
                    {"error": validate_result["stderr"]}
                )
                
        except Exception as e:
            logger.error("Terraform validation error", error=str(e))
            return ValidationResult(False, "terraform", f"Validation error: {str(e)}")

class PythonValidator(BaseValidator):
    """Python validation"""
    
    async def validate_syntax(self, content: str, container=None) -> ValidationResult:
        """Validate Python syntax"""
        try:
            # Basic syntax check
            compile(content, '<string>', 'exec')
            
            if container:
                # Write to file and run additional checks
                await container.write_file("/workspace/temp.py", content)
                
                # Run flake8
                flake8_result = await container.exec_command("python -m flake8 /workspace/temp.py")
                
                if flake8_result["exit_code"] != 0:
                    return ValidationResult(
                        False,
                        "python",
                        "Style issues found",
                        {"flake8": flake8_result["stdout"]}
                    )
            
            return ValidationResult(True, "python", "Python syntax valid")
            
        except SyntaxError as e:
            return ValidationResult(
                False,
                "python",
                f"Syntax error: {e.msg}",
                {"line": e.lineno, "offset": e.offset}
            )
        except Exception as e:
            return ValidationResult(False, "python", f"Validation error: {str(e)}")

class YamlValidator(BaseValidator):
    """YAML validation"""
    
    async def validate_syntax(self, content: str, container=None) -> ValidationResult:
        """Validate YAML syntax"""
        try:
            # Parse YAML
            data = yaml.safe_load(content)
            
            if container:
                # Write to file and run yamllint
                await container.write_file("/workspace/temp.yaml", content)
                
                lint_result = await container.exec_command("yamllint /workspace/temp.yaml")
                
                if lint_result["exit_code"] != 0:
                    return ValidationResult(
                        False,
                        "yaml",
                        "YAML lint issues found",
                        {"yamllint": lint_result["stdout"]}
                    )
            
            return ValidationResult(True, "yaml", "YAML syntax valid")
            
        except yaml.YAMLError as e:
            return ValidationResult(
                False,
                "yaml",
                f"YAML parse error: {str(e)}"
            )

class SecurityValidator(BaseValidator):
    """Security validation"""
    
    async def scan(self, content: str, file_type: str, container=None) -> ValidationResult:
        """Run security scans"""
        issues = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            "password",
            "api_key",
            "secret",
            "token",
            "private_key"
        ]
        
        for pattern in secret_patterns:
            if pattern in content.lower() and "=" in content:
                # Look for potential hardcoded values
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line.lower() and '=' in line and not line.strip().startswith('#'):
                        # Check if it looks like a hardcoded value
                        if '"' in line or "'" in line:
                            value_part = line.split('=', 1)[1].strip()
                            if not value_part.startswith('${') and not value_part.startswith('var.'):
                                issues.append(f"Line {i+1}: Potential hardcoded {pattern}")
        
        if file_type == "terraform" and container:
            # Run tfsec
            await container.write_file("/workspace/temp.tf", content)
            tfsec_result = await container.exec_command("tfsec /workspace/temp.tf --format json")
            
            if tfsec_result["stdout"]:
                try:
                    tfsec_data = json.loads(tfsec_result["stdout"])
                    for result in tfsec_data.get("results", []):
                        issues.append(f"{result['severity']}: {result['description']}")
                except:
                    pass
        
        if issues:
            return ValidationResult(
                False,
                "security",
                "Security issues found",
                {"issues": issues}
            )
        
        return ValidationResult(True, "security", "No security issues found")

class ValidationPipeline:
    """Orchestrates validation of code changes"""
    
    def __init__(self, config):
        self.config = config
        self.validators = {
            "terraform": TerraformValidator(),
            "python": PythonValidator(),
            "yaml": YamlValidator(),
            "security": SecurityValidator()
        }
    
    async def validate(self, 
                      file_type: str,
                      content: str,
                      original: str,
                      container=None,
                      rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run validation pipeline"""
        results = []
        
        # Always run syntax validation
        if file_type in self.validators:
            syntax_result = await self.validators[file_type].validate_syntax(content, container)
            results.append(syntax_result)
            
            if not syntax_result.passed:
                # Stop if syntax is invalid
                return self._format_results(results)
        
        # Run security validation if enabled
        if self.config.enable_security_validation:
            security_result = await self.validators["security"].scan(content, file_type, container)
            results.append(security_result)
        
        # Run custom validation rules
        if rules:
            for rule in rules:
                if rule == "terraform_plan" and file_type == "terraform":
                    plan_result = await self._validate_terraform_plan(content, container)
                    results.append(plan_result)
                elif rule == "no_breaking_changes":
                    breaking_result = await self._check_breaking_changes(original, content, file_type)
                    results.append(breaking_result)
        
        return self._format_results(results)
    
    async def _validate_terraform_plan(self, content: str, container) -> ValidationResult:
        """Validate terraform plan"""
        if not container:
            return ValidationResult(False, "terraform_plan", "No container provided")
        
        try:
            await container.write_file("/workspace/main.tf", content)
            await container.exec_command("terraform init -backend=false /workspace")
            
            plan_result = await container.exec_command("terraform plan -out=tfplan /workspace")
            
            if plan_result["exit_code"] == 0:
                # Check for destroy operations
                if "will be destroyed" in plan_result["stdout"]:
                    return ValidationResult(
                        False,
                        "terraform_plan",
                        "Plan contains destructive changes",
                        {"plan_output": plan_result["stdout"]}
                    )
                return ValidationResult(True, "terraform_plan", "Terraform plan successful")
            else:
                return ValidationResult(
                    False,
                    "terraform_plan",
                    "Terraform plan failed",
                    {"error": plan_result["stderr"]}
                )
        except Exception as e:
            return ValidationResult(False, "terraform_plan", f"Plan validation error: {str(e)}")
    
    async def _check_breaking_changes(self, original: str, content: str, file_type: str) -> ValidationResult:
        """Check for breaking changes"""
        # Simple heuristic - check if we're removing significant content
        original_lines = original.split('\n')
        content_lines = content.split('\n')
        
        removed_lines = len(original_lines) - len(content_lines)
        
        if removed_lines > len(original_lines) * 0.3:  # More than 30% removed
            return ValidationResult(
                False,
                "breaking_changes",
                f"Significant content removed ({removed_lines} lines)",
                {"lines_removed": removed_lines}
            )
        
        return ValidationResult(True, "breaking_changes", "No breaking changes detected")
    
    def _format_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Format validation results"""
        return {
            "passed": all(r.passed for r in results),
            "results": [
                {
                    "validator": r.validator,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ],
            "error": next((r.message for r in results if not r.passed), None)
        }
