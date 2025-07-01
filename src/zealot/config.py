"""Configuration management for DevOpsZealot"""
import os
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Application configuration"""
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    
    # Server
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8090"))
    server_workers: int = int(os.getenv("SERVER_WORKERS", "4"))
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # Docker
    docker_socket: str = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")
    container_memory_limit: str = os.getenv("CONTAINER_MEMORY_LIMIT", "2g")
    container_cpu_quota: int = int(os.getenv("CONTAINER_CPU_QUOTA", "50000"))
    container_timeout: int = int(os.getenv("CONTAINER_TIMEOUT_SECONDS", "300"))
    
    # AI
    ai_model: str = os.getenv("DEFAULT_AI_MODEL", "gpt-4")
    ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.3"))
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "4000"))
    ai_request_timeout: int = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))
    
    # Security
    allowed_repositories: List[str] = os.getenv(
        "ALLOWED_REPOSITORIES", 
        "https://github.com/zacharyelston/*"
    ).split(",")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    enable_security_scanning: bool = os.getenv("ENABLE_SECURITY_SCANNING", "true").lower() == "true"
    
    # Validation
    enable_syntax_validation: bool = os.getenv("ENABLE_SYNTAX_VALIDATION", "true").lower() == "true"
    enable_security_validation: bool = os.getenv("ENABLE_SECURITY_VALIDATION", "true").lower() == "true"
    validation_timeout: int = int(os.getenv("VALIDATION_TIMEOUT_SECONDS", "120"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    
    def validate(self):
        """Validate configuration"""
        errors = []
        
        if not self.openai_api_key and self.ai_model.startswith("gpt"):
            errors.append("OpenAI API key is required for GPT models")
            
        if not self.github_token:
            errors.append("GitHub token is required")
            
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        config = cls()
        config.validate()
        return config
