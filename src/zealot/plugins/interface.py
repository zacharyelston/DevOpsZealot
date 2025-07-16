"""
Plugin interface for extending Zealot functionality
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
from dataclasses import dataclass


@dataclass
class PluginContext:
    """Context passed to plugins during execution"""
    task_id: str
    workspace_path: str
    issue_data: Dict[str, Any]
    files: List[str]
    metadata: Dict[str, Any]
    environment: Dict[str, str]
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with fallback"""
        return self.environment.get(key, default)


@dataclass
class PluginResult:
    """Result from plugin execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ZealotPlugin(ABC):
    """Base class for all Zealot plugins"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """Called before AI edits are made"""
        pass
    
    @abstractmethod
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Called after AI edits are made"""
        pass
    
    @abstractmethod
    async def validate(self, context: PluginContext) -> PluginResult:
        """Called to validate changes"""
        pass
    
    async def cleanup(self, context: PluginContext) -> None:
        """Optional cleanup after execution"""
        pass


class CommandPlugin(ZealotPlugin):
    """Plugin that executes shell commands"""
    
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """Execute pre-edit commands"""
        commands = self.config.get('pre_edit_commands', [])
        return await self._execute_commands(commands, context)
    
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Execute post-edit commands"""
        commands = self.config.get('post_edit_commands', [])
        return await self._execute_commands(commands, context)
    
    async def validate(self, context: PluginContext) -> PluginResult:
        """Execute validation commands"""
        commands = self.config.get('validation_commands', [])
        return await self._execute_commands(commands, context)
    
    async def _execute_commands(self, commands: List[str], context: PluginContext) -> PluginResult:
        """Execute a list of shell commands"""
        outputs = []
        
        for command in commands:
            # Substitute environment variables
            for key, value in context.environment.items():
                command = command.replace(f'${{{key}}}', value)
            command = command.replace('${WORKSPACE}', context.workspace_path)
            command = command.replace('${TASK_ID}', context.task_id)
            
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=context.workspace_path
                )
                
                stdout, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    return PluginResult(
                        success=False,
                        error=f"Command failed: {command}\n{stderr.decode()}"
                    )
                
                outputs.append(stdout.decode())
                
            except Exception as e:
                return PluginResult(
                    success=False,
                    error=f"Command execution failed: {str(e)}"
                )
        
        return PluginResult(
            success=True,
            output="\n".join(outputs)
        )


class PythonPlugin(ZealotPlugin):
    """Plugin that executes Python code"""
    
    async def pre_edit(self, context: PluginContext) -> PluginResult:
        """Execute pre-edit Python code"""
        code = self.config.get('pre_edit_code', '')
        return await self._execute_python(code, context)
    
    async def post_edit(self, context: PluginContext) -> PluginResult:
        """Execute post-edit Python code"""
        code = self.config.get('post_edit_code', '')
        return await self._execute_python(code, context)
    
    async def validate(self, context: PluginContext) -> PluginResult:
        """Execute validation Python code"""
        code = self.config.get('validation_code', '')
        return await self._execute_python(code, context)
    
    async def _execute_python(self, code: str, context: PluginContext) -> PluginResult:
        """Execute Python code with context"""
        if not code:
            return PluginResult(success=True)
        
        # Create execution namespace
        namespace = {
            'context': context,
            'workspace_path': context.workspace_path,
            'task_id': context.task_id,
            'issue_data': context.issue_data,
            'files': context.files,
            'metadata': context.metadata,
            'env': context.environment
        }
        
        try:
            # Execute code
            exec(code, namespace)
            
            # Check for result
            if 'result' in namespace:
                return namespace['result']
            
            return PluginResult(success=True)
            
        except Exception as e:
            return PluginResult(
                success=False,
                error=f"Python execution failed: {str(e)}"
            )


class PluginManager:
    """Manages plugin loading and execution"""
    
    def __init__(self):
        self.plugins: Dict[str, ZealotPlugin] = {}
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """Register built-in plugins"""
        self.register_plugin_class('command', CommandPlugin)
        self.register_plugin_class('python', PythonPlugin)
    
    def register_plugin_class(self, name: str, plugin_class: type):
        """Register a plugin class"""
        self.plugins[name] = plugin_class
    
    def create_plugin(self, plugin_type: str, config: Dict[str, Any]) -> ZealotPlugin:
        """Create a plugin instance"""
        if plugin_type not in self.plugins:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
        
        plugin_class = self.plugins[plugin_type]
        return plugin_class(config)
    
    def load_plugin_from_module(self, module_path: str):
        """Load a plugin from a Python module"""
        import importlib.util
        import sys
        
        spec = importlib.util.spec_from_file_location("plugin", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["plugin"] = module
        spec.loader.exec_module(module)
        
        # Find plugin classes in module
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type) and 
                issubclass(obj, ZealotPlugin) and 
                obj != ZealotPlugin):
                self.register_plugin_class(name.lower(), obj)
