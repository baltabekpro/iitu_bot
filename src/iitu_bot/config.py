"""Configuration management for IITU Bot"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the IITU bot"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Google Gemini API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './data/chroma_db')
    
    # Web Scraping Configuration
    IITU_BASE_URL = os.getenv('IITU_BASE_URL', 'https://iitu.edu.kz')
    MAX_PAGES_TO_SCRAPE = int(os.getenv('MAX_PAGES_TO_SCRAPE', '100'))
    SCRAPE_DELAY = int(os.getenv('SCRAPE_DELAY', '1'))
    
    # Bot Configuration
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = ['TELEGRAM_BOT_TOKEN', 'GEMINI_API_KEY']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True