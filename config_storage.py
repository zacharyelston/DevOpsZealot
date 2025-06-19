import json
import os
from pathlib import Path
from typing import Dict, Optional

class ConfigStorage:
    """Handles persistent storage of configuration data."""
    
    def __init__(self):
        self.config_dir = Path(".config")
        self.config_file = self.config_dir / "redmine_config.json"
        self.config_dir.mkdir(exist_ok=True)
    
    def save_redmine_config(self, url: str, api_key: Optional[str] = None, 
                           username: Optional[str] = None, password: Optional[str] = None) -> None:
        """Save Redmine connection configuration."""
        config = {
            "url": url,
            "api_key": api_key,
            "username": username,
            "password": password
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save configuration: {str(e)}")
    
    def load_redmine_config(self) -> Dict[str, Optional[str]]:
        """Load Redmine connection configuration."""
        if not self.config_file.exists():
            return {
                "url": "https://redstone.redminecloud.net",
                "api_key": None,
                "username": None,
                "password": None
            }
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return {
                    "url": config.get("url", "https://redstone.redminecloud.net"),
                    "api_key": config.get("api_key"),
                    "username": config.get("username"),
                    "password": config.get("password")
                }
        except Exception:
            return {
                "url": "https://redstone.redminecloud.net",
                "api_key": None,
                "username": None,
                "password": None
            }
    
    def clear_redmine_config(self) -> None:
        """Clear saved Redmine configuration."""
        if self.config_file.exists():
            try:
                os.remove(self.config_file)
            except Exception:
                pass