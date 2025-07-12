import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Steam scraper bot"""
    
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'steam_scraper')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    
    # Steam configuration
    STEAM_API_KEY = os.getenv('STEAM_API_KEY', '')
    STEAM_WEB_API_URL = "https://api.steampowered.com"
    STEAM_PROFILE_URL = "https://steamcommunity.com/profiles/"
    SEED_PROFILE = os.getenv('SEED_PROFILE', '')
    
    # Bot configuration
    BOT_DELAY_MIN = int(os.getenv('BOT_DELAY_MIN', 2))  # Minimum delay between requests (seconds)
    BOT_DELAY_MAX = int(os.getenv('BOT_DELAY_MAX', 5))  # Maximum delay between requests (seconds)
    MAX_CONCURRENT_BOTS = int(os.getenv('MAX_CONCURRENT_BOTS', 5))
    MAX_FRIENDS_PER_PROFILE = int(os.getenv('MAX_FRIENDS_PER_PROFILE', 100))
    
    # Oracle configuration
    ORACLE_CHECK_INTERVAL = int(os.getenv('ORACLE_CHECK_INTERVAL', 10))  # seconds
    ORACLE_TIMEOUT = int(os.getenv('ORACLE_TIMEOUT', 30))  # seconds
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Rate limiting
    REQUESTS_PER_MINUTE = int(os.getenv('REQUESTS_PER_MINUTE', 60))
    
    @classmethod
    def validate_config(cls):
        """Validate essential configuration parameters"""
        required_configs = ['DB_HOST', 'DB_USER', 'DB_NAME']
        missing_configs = []
        
        for config in required_configs:
            if not getattr(cls, config):
                missing_configs.append(config)
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
        
        return True 