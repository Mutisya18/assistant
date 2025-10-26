"""
Safina Lite - Application Entry Point
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from api.app import create_app
from utils.logger import setup_logger
from utils.config import Config

def main():
    """Initialize and run Safina Lite"""
    print("=" * 60)
    print("Safina Lite - Initializing...")
    print("=" * 60)
    
    # Load configuration
    config = Config()
    is_valid, errors = config.validate()
    
    if not is_valid:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("✓ Configuration loaded")
    
    # Setup logging
    logger = setup_logger("safina")
    print(f"✓ Logging configured: {config.get('logging.base_directory')}")
    
    # Create Flask app
    app = create_app(config)
    
    print("=" * 60)
    print("✓ Safina Lite initialized!")
    print(f"  Environment: {config.get('app.environment')}")
    print(f"  Version: {config.get('app.version')}")
    print(f"  API: http://{config.get('api.host')}:{config.get('api.port')}")
    print("=" * 60)
    
    # Run server
    app.run(
        host=config.get('api.host'),
        port=config.get('api.port'),
        debug=config.get('api.debug')
    )

if __name__ == "__main__":
    main()
```

#### Step 1.2: Create utils/config.py
```python
"""Configuration management with environment variable substitution"""
import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv

class Config:
    """Configuration loader with environment variable substitution"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.config_data = {}
        self.env_vars = {}
        
        self._load_env_vars()
        self._load_yaml()
        self._substitute_env_vars()
    
    def _load_env_vars(self):
        """Load environment variables from .env file"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        self.env_vars = dict(os.environ)
    
    def _load_yaml(self):
        """Load YAML configuration file"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r') as f:
            self.config_data = yaml.safe_load(f)
    
    def _substitute_env_vars(self):
        """Recursively substitute ${VAR_NAME} with environment variables"""
        self.config_data = self._recursive_substitute(self.config_data)
    
    def _recursive_substitute(self, obj: Any) -> Any:
        """Recursively process object for environment variable substitution"""
        if isinstance(obj, dict):
            return {k: self._recursive_substitute(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._recursive_substitute(item) for item in obj]
        elif isinstance(obj, str):
            # Match ${VAR_NAME} pattern
            pattern = r'\$\{([A-Z_]+)\}'
            match = re.search(pattern, obj)
            if match:
                var_name = match.group(1)
                if var_name in self.env_vars:
                    return self.env_vars[var_name]
                else:
                    print(f"⚠️  Warning: Environment variable not found: {var_name}")
            return obj
        else:
            return obj
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key_path.split('.')
        current = self.config_data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate required configuration"""
        errors = []
        
        # Required keys
        required = [
            "app.name",
            "api.host",
            "api.port",
            "llm.default_provider",
            "logging.base_directory"
        ]
        
        for key in required:
            if self.get(key) is None:
                errors.append(f"Missing required configuration: {key}")
        
        # Validate LLM configuration
        default_provider = self.get("llm.default_provider")
        providers = self.get("llm.providers", {})
        
        if default_provider not in providers:
            errors.append(f"Default provider '{default_provider}' not configured")
        
        # Check Gemini API key
        if "gemini" in providers and providers["gemini"].get("enabled"):
            if not providers["gemini"].get("api_key"):
                errors.append("Gemini API key not configured (set GEMINI_API_KEY)")
        
        return len(errors) == 0, errors

# Global config instance
config = None

def get_config() -> Config:
    """Get global config instance"""
    global config
    if config is None:
        config = Config()
    return config