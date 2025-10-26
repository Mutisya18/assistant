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


