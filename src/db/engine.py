from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import lancedb
import litellm

try:
    from ..config import Config
    from ..utils.logging import setup_logging, log_with_extra
except ImportError:
    from config import Config
    from utils.logging import setup_logging, log_with_extra


class DBEngine:
    """Shared database engine for LanceDB operations"""
    
    def __init__(self, config: Config, db_path: Optional[Path] = None, entity_id: Optional[str] = None):
        self.config = config
        self.logger = setup_logging(config.log_level)
        
        # Set up embedding model
        self.embedding_model = self._setup_embedding_model()
        
        # Set up LanceDB connection
        self.db_path = db_path if db_path else (config.data_dir / 'db.lancedb')
        self.db = lancedb.connect(str(self.db_path))
        self.table_name = f'notion_pages'
        
    def _setup_embedding_model(self) -> str:
        """Setup embedding model based on available API keys"""
        if os.getenv('OPENAI_API_KEY'):
            log_with_extra(self.logger, 'INFO', 'Using OpenAI embeddings via LiteLLM')
            return "text-embedding-3-small"
        elif os.getenv('GOOGLE_API_KEY'):
            log_with_extra(self.logger, 'INFO', 'Using Google Gemini embeddings via LiteLLM')
            return "text-embedding-004"
        else:
            raise ValueError(
                'Please set either OPENAI_API_KEY or GOOGLE_API_KEY environment variable'
            )
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using LiteLLM"""
        try:
            response = litellm.embedding(
                model=self.embedding_model,
                input=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Failed to get embedding',
                text_length=len(text), error=str(e)
            )
            raise
    
    def get_table(self):
        """Get the LanceDB table for direct access"""
        if self.table_name in self.db.table_names():
            return self.db.open_table(self.table_name)
        return None
    
    def table_exists(self) -> bool:
        """Check if the table exists"""
        return self.table_name in self.db.table_names()
    
    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            if not self.table_exists():
                return {'exists': False}
            
            table = self.get_table()
            count = table.count_rows()
            
            return {
                'exists': True,
                'total_pages': count,
                'table_name': self.table_name,
                'embedding_model': self.embedding_model
            }
            
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Failed to get table stats',
                error=str(e)
            )
            return {'exists': False, 'error': str(e)}