"""
Universal configuration management for DevOpsZealot
Supports loading from environment variables and configuration files
"""
import os
import yaml
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class UniversalConfig:
    """Universal configuration for Zealot"""
    
    # Core settings
    server_host: str = "0.0.0.0"
    server_port: int = 8090
    server_workers: int = 4
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Workflows
    workflows_dir: str = "./workflows"
    plugins_dir: str = "./plugins"
    
    # Queue (optional)
    redis_url: Optional[str] = None
    
    # Adapters configuration
    issue_source: Dict[str, Any] = field(default_factory=dict)
    vcs: Dict[str, Any] = field(default_factory=dict)
    llm: Dict[str, Any] = field(default_factory=dict)
    container: Dict[str, Any] = field(default_factory=dict)
    
    # Security
    allowed_repositories: List[str] = field(default_factory=list)
    api_key_header: Optional[str] = None
    require_api_key: bool = False
    
    @classmethod
    def from_file(cls, filepath: str) -> 'UniversalConfig':
        """Load configuration from YAML or JSON file"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversalConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        # Update with provided values
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Apply environment variable overrides
        config._apply_env_overrides()
        
        return config
    
    @classmethod
    def from_env(cls) -> 'UniversalConfig':
        """Create configuration from environment variables"""
        config = cls()
        config._apply_env_overrides()
        return config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Core settings
        self.server_host = os.getenv('ZEALOT_SERVER_HOST', self.server_host)
        self.server_port = int(os.getenv('ZEALOT_SERVER_PORT', str(self.server_port)))
        self.server_workers = int(os.getenv('ZEALOT_SERVER_WORKERS', str(self.server_workers)))
        self.log_level = os.getenv('ZEALOT_LOG_LEVEL', self.log_level)
        self.log_format = os.getenv('ZEALOT_LOG_FORMAT', self.log_format)
        
        # Directories
        self.workflows_dir = os.getenv('ZEALOT_WORKFLOWS_DIR', self.workflows_dir)
        self.plugins_dir = os.getenv('ZEALOT_PLUGINS_DIR', self.plugins_dir)
        
        # Redis
        self.redis_url = os.getenv('ZEALOT_REDIS_URL', self.redis_url)
        
        # Security
        if os.getenv('ZEALOT_API_KEY_HEADER'):
            self.api_key_header = os.getenv('ZEALOT_API_KEY_HEADER')
        self.require_api_key = os.getenv('ZEALOT_REQUIRE_API_KEY', 'false').lower() == 'true'
        
        # Adapter configurations from environment
        self._load_adapter_env_config()
    
    def _load_adapter_env_config(self):
        """Load adapter configurations from environment variables"""
        # Issue source
        if os.getenv('ZEALOT_ISSUE_TYPE'):
            self.issue_source = {
                'type': os.getenv('ZEALOT_ISSUE_TYPE'),
                'endpoint': os.getenv('ZEALOT_ISSUE_ENDPOINT', ''),
                'api_key': os.getenv('ZEALOT_ISSUE_API_KEY', ''),
                'default_project': os.getenv('ZEALOT_ISSUE_PROJECT', '')
            }
        
        # VCS
        if os.getenv('ZEALOT_VCS_TYPE'):
            self.vcs = {
                'type': os.getenv('ZEALOT_VCS_TYPE', 'git'),
                'remote': os.getenv('ZEALOT_VCS_REMOTE', 'origin'),
                'default_branch': os.getenv('ZEALOT_VCS_DEFAULT_BRANCH', 'main'),
                'branch_pattern': os.getenv('ZEALOT_VCS_BRANCH_PATTERN', 'zealot/{task_id}'),
                'auth_token': os.getenv('ZEALOT_VCS_AUTH_TOKEN', ''),
                'user_name': os.getenv('ZEALOT_VCS_USER_NAME', 'DevOps Zealot'),
                'user_email': os.getenv('ZEALOT_VCS_USER_EMAIL', 'zealot@example.com')
            }
        
        # LLM
        if os.getenv('ZEALOT_LLM_PROVIDER'):
            self.llm = {
                'provider': os.getenv('ZEALOT_LLM_PROVIDER'),
                'api_key': os.getenv('ZEALOT_LLM_API_KEY', ''),
                'model': os.getenv('ZEALOT_LLM_MODEL', 'gpt-4'),
                'temperature': float(os.getenv('ZEALOT_LLM_TEMPERATURE', '0.3')),
                'max_tokens': int(os.getenv('ZEALOT_LLM_MAX_TOKENS', '4000')),
                'timeout': int(os.getenv('ZEALOT_LLM_TIMEOUT', '60'))
            }
        
        # Container
        if os.getenv('ZEALOT_CONTAINER_TYPE'):
            self.container = {
                'type': os.getenv('ZEALOT_CONTAINER_TYPE', 'docker'),
                'socket': os.getenv('ZEALOT_CONTAINER_SOCKET', '/var/run/docker.sock'),
                'memory_limit': os.getenv('ZEALOT_CONTAINER_MEMORY', '2g'),
                'cpu_quota': int(os.getenv('ZEALOT_CONTAINER_CPU_QUOTA', '50000')),
                'timeout': int(os.getenv('ZEALOT_CONTAINER_TIMEOUT', '300'))
            }
    
    def validate(self):
        """Validate configuration"""
        errors = []
        
        # Check required directories
        if not os.path.exists(self.workflows_dir):
            errors.append(f"Workflows directory not found: {self.workflows_dir}")
        
        # Check adapter configurations
        if not self.issue_source.get('type'):
            errors.append("Issue source type not configured")
        
        if not self.vcs.get('type'):
            errors.append("VCS type not configured")
        
        if not self.llm.get('provider'):
            errors.append("LLM provider not configured")
        
        if not self.container.get('type'):
            errors.append("Container type not configured")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'server_host': self.server_host,
            'server_port': self.server_port,
            'server_workers': self.server_workers,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'workflows_dir': self.workflows_dir,
            'plugins_dir': self.plugins_dir,
            'redis_url': self.redis_url,
            'issue_source': self.issue_source,
            'vcs': self.vcs,
            'llm': self.llm,
            'container': self.container,
            'allowed_repositories': self.allowed_repositories,
            'api_key_header': self.api_key_header,
            'require_api_key': self.require_api_key
        }
