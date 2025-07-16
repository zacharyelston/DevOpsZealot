"""
Example custom plugin for DevOpsZealot
Shows how to extend functionality with custom plugins
"""
from typing import Dict, Any
import json
import re
from zealot.plugins.interface import ZealotPlugin, PluginContext, PluginResult


class SecurityScanPlugin(ZealotPlugin):
    """
    Custom security scanning plugin
    Demonstrates how to create domain-specific plugins
    """
    
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """Check for security issues before editing"""
        # Example: Check if we're editing sensitive files
        sensitive_patterns = self.config.get('sensitive_files', [
            '*.key', '*.pem', '*.crt', 'secrets.yaml', '.env'
        ])
        
        for file in context.files:
            for pattern in sensitive_patterns:
                if self._matches_pattern(file, pattern):
                    return PluginResult(
                        success=False,
                        error=f"Cannot edit sensitive file: {file}"
                    )
        
        return PluginResult(success=True)
    
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Scan for security issues after editing"""
        issues = []
        
        # Example security checks
        for file in context.files:
            file_path = f"{context.workspace_path}/{file}"
            
            # Check for hardcoded credentials
            if await self._check_hardcoded_secrets(file_path):
                issues.append(f"{file}: Contains hardcoded credentials")
            
            # Check for insecure configurations
            if file.endswith('.yaml') or file.endswith('.yml'):
                if await self._check_insecure_yaml(file_path):
                    issues.append(f"{file}: Insecure YAML configuration")
        
        if issues:
            return PluginResult(
                success=False,
                error="Security issues found",
                metadata={'issues': issues}
            )
        
        return PluginResult(
            success=True,
            output="Security scan passed"
        )
    
    async def validate(self, context: PluginContext) -> PluginResult:
        """Final security validation"""
        # Run comprehensive security scan
        scan_command = self.config.get('scan_command', 'echo "Security scan placeholder"')
        
        # In real implementation, would execute the scan command
        # For now, just return success
        return PluginResult(
            success=True,
            output="Security validation complete"
        )
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern"""
        # Convert glob pattern to regex
        pattern = pattern.replace('*', '.*')
        return bool(re.match(pattern, filename))
    
    async def _check_hardcoded_secrets(self, file_path: str) -> bool:
        """Check for hardcoded secrets in file"""
        # Simplified check - in reality would use more sophisticated scanning
        patterns = [
            r'api_key\s*=\s*["\'][\w\-]+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][\w\-]+["\']'
        ]
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        except:
            pass
        
        return False
    
    async def _check_insecure_yaml(self, file_path: str) -> bool:
        """Check for insecure YAML configurations"""
        # Example checks for Kubernetes manifests
        insecure_configs = [
            'privileged: true',
            'runAsRoot: true',
            'hostNetwork: true',
            'capabilities: ALL'
        ]
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            for config in insecure_configs:
                if config in content:
                    return True
        except:
            pass
        
        return False


class MetricsCollectorPlugin(ZealotPlugin):
    """
    Plugin to collect metrics about code changes
    """
    
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """Record pre-edit metrics"""
        metrics = {
            'task_id': context.task_id,
            'files_count': len(context.files),
            'start_time': context.metadata.get('start_time', ''),
            'issue_priority': context.issue_data.get('priority', 'normal')
        }
        
        # In real implementation, would send to metrics system
        self._send_metrics('pre_edit', metrics)
        
        return PluginResult(success=True)
    
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Record post-edit metrics"""
        metrics = {
            'task_id': context.task_id,
            'changes_made': True,
            'llm_tokens_used': context.metadata.get('tokens_used', 0)
        }
        
        self._send_metrics('post_edit', metrics)
        
        return PluginResult(success=True)
    
    async def validate(self, context: PluginContext) -> PluginResult:
        """Record validation metrics"""
        metrics = {
            'task_id': context.task_id,
            'validation_passed': True,
            'duration': context.metadata.get('duration', 0)
        }
        
        self._send_metrics('validation', metrics)
        
        return PluginResult(
            success=True,
            metadata={'metrics_sent': True}
        )
    
    def _send_metrics(self, stage: str, metrics: Dict[str, Any]):
        """Send metrics to monitoring system"""
        # In real implementation, would send to Prometheus, DataDog, etc.
        endpoint = self.config.get('metrics_endpoint', 'http://localhost:9090')
        print(f"[METRICS] {stage}: {json.dumps(metrics)}")


class CodeQualityPlugin(ZealotPlugin):
    """
    Plugin to enforce code quality standards
    """
    
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """No pre-edit checks for code quality"""
        return PluginResult(success=True)
    
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Check code quality after edits"""
        quality_issues = []
        
        for file in context.files:
            if file.endswith('.py'):
                # Check Python code quality
                issues = await self._check_python_quality(
                    f"{context.workspace_path}/{file}"
                )
                quality_issues.extend(issues)
            elif file.endswith('.js'):
                # Check JavaScript code quality
                issues = await self._check_js_quality(
                    f"{context.workspace_path}/{file}"
                )
                quality_issues.extend(issues)
        
        if quality_issues:
            return PluginResult(
                success=True,  # Don't fail, just report
                output="Code quality issues found",
                metadata={'issues': quality_issues}
            )
        
        return PluginResult(
            success=True,
            output="Code quality checks passed"
        )
    
    async def validate(self, context: PluginContext) -> PluginResult:
        """Final code quality validation"""
        # Could run more comprehensive checks here
        return PluginResult(success=True)
    
    async def _check_python_quality(self, file_path: str) -> list:
        """Check Python code quality"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Simple checks
            for i, line in enumerate(lines):
                # Line too long
                if len(line) > 120:
                    issues.append(f"Line {i+1}: Line too long ({len(line)} chars)")
                
                # TODO comments
                if 'TODO' in line:
                    issues.append(f"Line {i+1}: TODO comment found")
                
                # No docstring for function
                if line.strip().startswith('def ') and i+1 < len(lines):
                    if not lines[i+1].strip().startswith('"""'):
                        func_name = line.split('(')[0].replace('def ', '')
                        issues.append(f"Line {i+1}: Function {func_name} missing docstring")
        except:
            pass
        
        return issues
    
    async def _check_js_quality(self, file_path: str) -> list:
        """Check JavaScript code quality"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple checks
            if 'console.log' in content:
                issues.append("Contains console.log statements")
            
            if 'var ' in content:
                issues.append("Uses 'var' instead of 'let' or 'const'")
        except:
            pass
        
        return issues


# Example of how to register custom plugins
def register_custom_plugins(plugin_manager):
    """Register all custom plugins with the plugin manager"""
    plugin_manager.register_plugin_class('security_scan', SecurityScanPlugin)
    plugin_manager.register_plugin_class('metrics', MetricsCollectorPlugin)
    plugin_manager.register_plugin_class('code_quality', CodeQualityPlugin)
