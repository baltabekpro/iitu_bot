"""Data processor module with AI integration for text improvement and chunking"""

import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import json
from typing import List, Dict
from ..config import Config

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process scraped data with AI enhancement and chunking"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def improve_text_with_ai(self, text: str, page_title: str = "") -> str:
        """Use AI to improve and clean text content"""
        if not text.strip():
            return text
            
        prompt = f"""
        Ты — эксперт по обработке текста для университета IITU. Улучши следующий текст:
        
        Заголовок страницы: {page_title}
        
        Текст: {text[:2000]}  # Limit text length for API
        
        Требования:
        1. Исправь грамматические и орфографические ошибки
        2. Улучши читаемость и структуру
        3. Сохрани всю важную информацию
        4. Удали ненужные элементы (навигация, реклама и т.д.)
        5. Структурируй информацию логично
        6. Сохрани информацию на оригинальном языке (казахский/русский/английский)
        
        Верни только улучшенный текст без дополнительных комментариев.
        """
        
        try:
            response = self.model.generate_content(prompt)
            improved_text = response.text.strip()
            logger.info(f"Text improved for page: {page_title}")
            return improved_text
        except Exception as e:
            logger.error(f"Error improving text: {str(e)}")
            return text  # Return original text if AI processing fails
    
    def create_chunks(self, text: str) -> List[str]:
        """Split text into chunks for vector storage"""
        if not text.strip():
            return []
            
        chunks = self.text_splitter.split_text(text)
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def process_page_data(self, page_data: Dict) -> Dict:
        """Process a single page's data"""
        logger.info(f"Processing page: {page_data.get('url', 'Unknown')}")
        
        # Skip pages with errors
        if 'error' in page_data:
            return page_data
        
        # Get original content
        original_content = page_data.get('content', '')
        page_title = page_data.get('title', '')
        
        # Improve content with AI
        improved_content = self.improve_text_with_ai(original_content, page_title)
        
        # Create chunks
        chunks = self.create_chunks(improved_content)
        
        # Return processed data
        processed_data = page_data.copy()
        processed_data.update({
            'original_content': original_content,
            'improved_content': improved_content,
            'chunks': chunks,
            'chunk_count': len(chunks),
            'processed': True
        })
        
        return processed_data
    
    def process_all_data(self, scraped_data: List[Dict]) -> List[Dict]:
        """Process all scraped data"""
        logger.info(f"Starting to process {len(scraped_data)} pages")
        
        processed_data = []
        
        for i, page_data in enumerate(scraped_data):
            try:
                processed_page = self.process_page_data(page_data)
                processed_data.append(processed_page)
                
                logger.info(f"Processed page {i+1}/{len(scraped_data)}: {page_data.get('url', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error processing page {i+1}: {str(e)}")
                # Add unprocessed page with error info
                error_page = page_data.copy()
                error_page['processing_error'] = str(e)
                processed_data.append(error_page)
        
        logger.info(f"Processing completed. {len(processed_data)} pages processed")
        return processed_data
    
    def save_processed_data(self, processed_data: List[Dict], filename: str = 'processed_data.json'):
        """Save processed data to JSON file"""
        import os
        
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Processed data saved to {filepath}")
    
    def load_processed_data(self, filename: str = 'processed_data.json') -> List[Dict]:
        """Load processed data from JSON file"""
        import os
        
        filepath = os.path.join('data', filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            logger.info(f"Loaded {len(processed_data)} processed pages from {filepath}")
            return processed_data
        else:
            logger.warning(f"No processed data file found at {filepath}")
            return []
    
    def extract_all_chunks(self, processed_data: List[Dict]) -> List[Dict]:
        """Extract all chunks with metadata for vector storage"""
        all_chunks = []
        
        for page_data in processed_data:
            if not page_data.get('processed') or 'chunks' not in page_data:
                continue
                
            url = page_data.get('url', '')
            title = page_data.get('title', '')
            description = page_data.get('description', '')
            
            for i, chunk in enumerate(page_data['chunks']):
                chunk_data = {
                    'content': chunk,
                    'source_url': url,
                    'page_title': title,
                    'page_description': description,
                    'chunk_index': i,
                    'total_chunks': len(page_data['chunks'])
                }
                all_chunks.append(chunk_data)
        
        logger.info(f"Extracted {len(all_chunks)} chunks from {len(processed_data)} pages")
        return all_chunks