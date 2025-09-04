#!/usr/bin/env python3
"""Main application script for IITU Telegram Bot"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.iitu_bot.config import Config
from src.iitu_bot.scraper import IITUWebScraper
from src.iitu_bot.processor import DataProcessor
from src.iitu_bot.database import VectorDatabase
from src.iitu_bot.bot import IITUTelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class IITUBotApplication:
    """Main application class for IITU Bot"""
    
    def __init__(self):
        # Validate configuration
        try:
            Config.validate()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.scraper = IITUWebScraper()
        self.processor = DataProcessor()
        self.vector_db = VectorDatabase()
        self.bot = IITUTelegramBot()
    
    def setup_knowledge_base(self):
        """Set up the knowledge base by scraping and processing data"""
        logger.info("Setting up knowledge base...")
        
        # Check if processed data already exists
        processed_data = self.processor.load_processed_data()
        
        if not processed_data:
            logger.info("No processed data found. Starting web scraping...")
            
            # Scrape website
            scraped_data = self.scraper.scrape_website()
            self.scraper.save_scraped_data()
            
            # Process scraped data
            processed_data = self.processor.process_all_data(scraped_data)
            self.processor.save_processed_data(processed_data)
        else:
            logger.info(f"Loaded {len(processed_data)} processed pages from cache")
        
        # Extract chunks for vector database
        chunks = self.processor.extract_all_chunks(processed_data)
        
        # Build knowledge base
        self.vector_db.build_knowledge_base(chunks)
        
        logger.info("Knowledge base setup completed")
    
    def update_knowledge_base(self):
        """Update the knowledge base with fresh data"""
        logger.info("Updating knowledge base...")
        
        # Clear existing data
        try:
            os.remove('data/scraped_data.json')
            os.remove('data/processed_data.json')
            logger.info("Cleared cached data")
        except FileNotFoundError:
            pass
        
        # Rebuild knowledge base
        self.setup_knowledge_base()
        
        logger.info("Knowledge base updated successfully")
    
    async def run_bot(self):
        """Run the Telegram bot"""
        logger.info("Starting Telegram bot...")
        
        try:
            await self.bot.start_polling()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.bot.stop()
    
    def check_knowledge_base(self):
        """Check knowledge base status"""
        info = self.vector_db.get_collection_info()
        print(f"Knowledge Base Status:")
        print(f"  Collection: {info.get('name', 'Unknown')}")
        print(f"  Total chunks: {info.get('count', 0)}")
        print(f"  Database path: {info.get('path', 'Unknown')}")

def main():
    """Main entry point"""
    # Ensure directories exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    app = IITUBotApplication()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'setup':
            # Setup knowledge base
            app.setup_knowledge_base()
            
        elif command == 'update':
            # Update knowledge base
            app.update_knowledge_base()
            
        elif command == 'status':
            # Check status
            app.check_knowledge_base()
            
        elif command == 'bot':
            # Run bot
            asyncio.run(app.run_bot())
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: setup, update, status, bot")
            sys.exit(1)
    else:
        # Default: setup and run bot
        print("Setting up knowledge base and starting bot...")
        app.setup_knowledge_base()
        asyncio.run(app.run_bot())

if __name__ == '__main__':
    main()