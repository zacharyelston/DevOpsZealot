import json
import os
from pathlib import Path
from typing import Dict, Optional, Any

class ConfigStorage:
    """Handles persistent storage of configuration data using environment secrets and local files."""
    
    def __init__(self):
        self.config_dir = Path(".config")
        self.job_defaults_file = self.config_dir / "job_defaults.json"
        self.app_settings_file = self.config_dir / "app_settings.json"
        self.config_dir.mkdir(exist_ok=True)
    
    def get_redmine_config(self) -> Dict[str, Optional[str]]:
        """Get Redmine configuration from environment secrets and defaults."""
        return {
            "url": os.environ.get("REDMINE_URL", "https://redstone.redminecloud.net"),
            "api_key": os.environ.get("REDMINE_API_KEY"),
            "username": os.environ.get("REDMINE_USERNAME"),
            "password": os.environ.get("REDMINE_PASSWORD")
        }
    
    def save_job_defaults(self, defaults: Dict[str, Any]) -> None:
        """Save default job configuration settings."""
        try:
            with open(self.job_defaults_file, 'w') as f:
                json.dump(defaults, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save job defaults: {str(e)}")
    
    def load_job_defaults(self) -> Dict[str, Any]:
        """Load default job configuration settings."""
        if not self.job_defaults_file.exists():
            return {
                "default_branch": "main",
                "default_author_name": "DevOps AI Zealot",
                "default_author_email": "zealot@devops.ai",
                "default_file_patterns": ["*.py", "*.js", "*.ts", "*.go", "*.java", "*.cpp", "*.c", "*.h"],
                "default_context": "Analyze the codebase and apply best practices for maintainability and performance."
            }
        
        try:
            with open(self.job_defaults_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                "default_branch": "main",
                "default_author_name": "DevOps AI Zealot",
                "default_author_email": "zealot@devops.ai",
                "default_file_patterns": ["*.py", "*.js", "*.ts", "*.go", "*.java", "*.cpp", "*.c", "*.h"],
                "default_context": "Analyze the codebase and apply best practices for maintainability and performance."
            }
    
    def save_app_settings(self, settings: Dict[str, Any]) -> None:
        """Save application settings."""
        try:
            with open(self.app_settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save app settings: {str(e)}")
    
    def load_app_settings(self) -> Dict[str, Any]:
        """Load application settings."""
        if not self.app_settings_file.exists():
            return {
                "auto_refresh_jobs": True,
                "max_log_lines": 1000,
                "show_advanced_options": False,
                "theme": "default"
            }
        
        try:
            with open(self.app_settings_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                "auto_refresh_jobs": True,
                "max_log_lines": 1000,
                "show_advanced_options": False,
                "theme": "default"
            }
    
    def clear_all_configs(self) -> None:
        """Clear all saved configurations (keeps environment secrets)."""
        for config_file in [self.job_defaults_file, self.app_settings_file]:
            if config_file.exists():
                try:
                    os.remove(config_file)
                except Exception:
                    pass