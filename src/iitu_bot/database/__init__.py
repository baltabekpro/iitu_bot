"""Vector database module for RAG knowledge base using ChromaDB"""

import chromadb
from chromadb.config import Settings
import logging
import uuid
from typing import List, Dict, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class VectorDatabase:
    """Vector database for storing and retrieving knowledge chunks"""
    
    def __init__(self):
        self.db_path = Config.CHROMA_DB_PATH
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # Get or create collection
        self.collection_name = "iitu_knowledge"
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Connected to existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "IITU university knowledge base"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def add_chunks(self, chunks: List[Dict]) -> None:
        """Add chunks to the vector database"""
        if not chunks:
            logger.warning("No chunks to add to database")
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            # Generate unique ID
            chunk_id = str(uuid.uuid4())
            
            # Prepare document
            content = chunk.get('content', '')
            if not content.strip():
                continue
                
            documents.append(content)
            
            # Prepare metadata
            metadata = {
                'source_url': chunk.get('source_url', ''),
                'page_title': chunk.get('page_title', ''),
                'page_description': chunk.get('page_description', ''),
                'chunk_index': chunk.get('chunk_index', 0),
                'total_chunks': chunk.get('total_chunks', 1)
            }
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        if documents:
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                
                logger.info(f"Added batch {i//batch_size + 1}: {len(batch_docs)} chunks")
            
            logger.info(f"Successfully added {len(documents)} chunks to vector database")
        else:
            logger.warning("No valid documents to add to database")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for relevant chunks"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            search_results = []
            
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    }
                    search_results.append(result)
            
            logger.info(f"Found {len(search_results)} results for query: {query[:50]}...")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            info = {
                'name': self.collection_name,
                'count': count,
                'path': self.db_path
            }
            logger.info(f"Collection info: {info}")
            return info
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}
    
    def clear_collection(self) -> None:
        """Clear all data from the collection"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "IITU university knowledge base"}
            )
            logger.info("Collection cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
    
    def build_knowledge_base(self, processed_chunks: List[Dict]) -> None:
        """Build the complete knowledge base from processed chunks"""
        logger.info("Building knowledge base...")
        
        # Clear existing data
        self.clear_collection()
        
        # Add all chunks
        self.add_chunks(processed_chunks)
        
        # Get final info
        info = self.get_collection_info()
        logger.info(f"Knowledge base built successfully: {info}")
    
    def is_relevant(self, query: str, threshold: float = 0.5) -> bool:
        """Check if query is relevant to the knowledge base"""
        results = self.search(query, n_results=1)
        
        if results and len(results) > 0:
            # Lower distance means higher similarity
            distance = results[0].get('distance', 1.0)
            similarity = 1.0 - distance
            return similarity >= threshold
        
        return False