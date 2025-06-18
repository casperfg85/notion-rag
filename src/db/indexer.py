from pathlib import Path
from typing import List, Dict, Any, Optional
import json

try:
    from ..config import Config
    from ..utils.logging import setup_logging, log_with_extra
except ImportError:
    from config import Config
    from utils.logging import setup_logging, log_with_extra

from .models import NotionPageSchema
from .engine import DBEngine


class NotionIndexer:
    """LanceDB indexer for Notion content - focused only on indexing operations"""
    
    def __init__(self, config: Config, entity_data_dir: Optional[Path] = None, db_path: Optional[Path] = None, entity_id: Optional[str] = None):
        self.config = config
        self.logger = setup_logging(config.log_level)
        self.entity_data_dir = entity_data_dir if entity_data_dir else config.data_dir
        self.db_path = db_path
        self.entity_id = entity_id
        self.db_engine = DBEngine(config, db_path, entity_id)
    
    def create_index(self, recreate: bool = False) -> Dict[str, Any]:
        """Create vector index from parsed content"""
        log_with_extra(
            self.logger, 'INFO', 'Starting index creation',
            recreate=recreate
        )
        
        try:
            # Check if parsed data exists
            parsed_file = self.entity_data_dir / 'parsed' / 'parsed_pages.json'
            if not parsed_file.exists():
                raise FileNotFoundError(
                    f'Parsed pages file not found: {parsed_file}'
                )
            
            # Load parsed data
            with open(parsed_file, 'r') as f:
                pages_data = json.load(f)
            
            if not pages_data:
                raise ValueError("No pages data found")
            
            # Convert to Pydantic models and add embeddings
            log_with_extra(self.logger, 'INFO', 'Converting to schema and generating embeddings', total_pages=len(pages_data))
            
            validated_pages = []
            for i, page_data in enumerate(pages_data):
                if i % 10 == 0:
                    log_with_extra(self.logger, 'INFO', f'Processing page {i+1}/{len(pages_data)}')
                
                try:
                    # Convert to Pydantic model for validation
                    page_schema = NotionPageSchema(**page_data)
                    
                    # Generate embedding for the text content
                    if page_schema.text:
                        page_schema.vector = self.db_engine.get_embedding(page_schema.text)
                    else:
                        # Default empty embedding
                        page_schema.vector = [0.0] * 1536  # Standard embedding size
                    
                    validated_pages.append(page_schema.to_dict())
                    
                except Exception as e:
                    log_with_extra(
                        self.logger, 'WARNING', 'Failed to validate page',
                        page_id=page_data.get('id', 'unknown'), error=str(e)
                    )
            
            pages_data = validated_pages
            
            # Drop existing table if recreating
            if recreate and self.db_engine.table_exists():
                self.db_engine.db.drop_table(self.db_engine.table_name)
                log_with_extra(self.logger, 'INFO', 'Dropped existing table')
            
            # Create or get table
            if not self.db_engine.table_exists():
                # Create new table
                table = self.db_engine.db.create_table(self.db_engine.table_name, data=pages_data)
                log_with_extra(self.logger, 'INFO', 'Created new table')
            else:
                # Add to existing table
                table = self.db_engine.get_table()
                table.add(pages_data)
                log_with_extra(self.logger, 'INFO', 'Added data to existing table')
            
            # Get stats
            stats = self._get_index_stats()
            
            log_with_extra(
                self.logger, 'INFO', 'Index creation completed',
                **stats
            )
            
            return stats
            
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Index creation failed',
                error=str(e)
            )
            raise
    
    def _get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        stats = self.db_engine.get_table_stats()
        if stats.get('exists'):
            return {
                'indexed_documents': stats['total_pages'],
                'table_name': stats['table_name'],
                'embedding_model': stats['embedding_model']
            }
        else:
            return {
                'indexed_documents': 'unknown',
                'table_name': self.db_engine.table_name,
                'embedding_model': self.db_engine.embedding_model
            }
    
    def get_table(self):
        """Get the LanceDB table for direct access"""
        return self.db_engine.get_table()