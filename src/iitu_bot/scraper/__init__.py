"""Web scraper module for IITU website"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from typing import List, Dict, Set
from ..config import Config

logger = logging.getLogger(__name__)

class IITUWebScraper:
    """Web scraper for IITU university website"""
    
    def __init__(self):
        self.base_url = Config.IITU_BASE_URL
        self.max_pages = Config.MAX_PAGES_TO_SCRAPE
        self.delay = Config.SCRAPE_DELAY
        self.visited_urls: Set[str] = set()
        self.scraped_data: List[Dict] = []
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to IITU domain"""
        parsed = urlparse(url)
        return 'iitu.edu.kz' in parsed.netloc
    
    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract meaningful text content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid links from the page"""
        links = []
        for link in soup.find_all('a', href=True):
            url = urljoin(current_url, link['href'])
            if self.is_valid_url(url) and url not in self.visited_urls:
                links.append(url)
        return links
    
    def scrape_page(self, url: str) -> Dict:
        """Scrape a single page and extract content"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract page metadata
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # Extract main content
            content = self.extract_text_content(soup)
            
            # Extract links for further crawling
            links = self.extract_links(soup, url)
            
            page_data = {
                'url': url,
                'title': title_text,
                'description': description,
                'content': content,
                'links': links,
                'scraped_at': time.time()
            }
            
            logger.info(f"Successfully scraped: {url}")
            return page_data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'title': '',
                'description': '',
                'content': '',
                'links': [],
                'error': str(e),
                'scraped_at': time.time()
            }
    
    def scrape_website(self) -> List[Dict]:
        """Scrape the entire IITU website"""
        logger.info(f"Starting to scrape {self.base_url}")
        
        # Start with the main page
        urls_to_visit = [self.base_url]
        
        while urls_to_visit and len(self.scraped_data) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            self.visited_urls.add(current_url)
            
            # Scrape the page
            page_data = self.scrape_page(current_url)
            self.scraped_data.append(page_data)
            
            # Add new links to visit
            if 'links' in page_data:
                for link in page_data['links']:
                    if link not in self.visited_urls and link not in urls_to_visit:
                        urls_to_visit.append(link)
            
            # Respect delay
            time.sleep(self.delay)
            
            logger.info(f"Scraped {len(self.scraped_data)} pages, {len(urls_to_visit)} URLs remaining")
        
        logger.info(f"Scraping completed. Total pages: {len(self.scraped_data)}")
        return self.scraped_data
    
    def save_scraped_data(self, filename: str = 'scraped_data.json'):
        """Save scraped data to JSON file"""
        import json
        import os
        
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Scraped data saved to {filepath}")
    
    def load_scraped_data(self, filename: str = 'scraped_data.json') -> List[Dict]:
        """Load previously scraped data from JSON file"""
        import json
        import os
        
        filepath = os.path.join('data', filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.scraped_data = json.load(f)
            logger.info(f"Loaded {len(self.scraped_data)} pages from {filepath}")
        else:
            logger.warning(f"No scraped data file found at {filepath}")
            
        return self.scraped_data