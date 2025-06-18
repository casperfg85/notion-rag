from typing import List, Dict, Any, Optional

try:
    from ..config import Config
    from ..utils.logging import setup_logging, log_with_extra
except ImportError:
    from config import Config
    from utils.logging import setup_logging, log_with_extra

from .engine import DBEngine


def search_pages(query: str, limit: int = 5, config: Optional[Config] = None) -> List[Dict[str, Any]]:
    """Search the vector database for relevant pages"""
    if config is None:
        config = Config.load()
    
    db_engine = DBEngine(config)
    logger = setup_logging(config.log_level)
    
    try:
        if not db_engine.table_exists():
            log_with_extra(logger, 'WARNING', 'Table does not exist')
            return []
        
        table = db_engine.get_table()
        
        # Get query embedding
        query_vector = db_engine.get_embedding(query)
        
        # Vector search
        results = table.search(query_vector).limit(limit).to_list()
        
        log_with_extra(
            logger, 'INFO', 'Search completed',
            query=query, results_count=len(results)
        )
        
        return results
        
    except Exception as e:
        log_with_extra(
            logger, 'ERROR', 'Search failed',
            query=query, error=str(e)
        )
        return []


def get_page_by_id(page_id: str, config: Optional[Config] = None) -> Optional[Dict[str, Any]]:
    """Get a specific page by its ID"""
    if config is None:
        config = Config.load()
    
    db_engine = DBEngine(config)
    logger = setup_logging(config.log_level)
    
    try:
        if not db_engine.table_exists():
            return None
        
        table = db_engine.get_table()
        results = table.search().where(f"id = '{page_id}'").limit(1).to_list()
        
        return results[0] if results else None
        
    except Exception as e:
        log_with_extra(
            logger, 'ERROR', 'Failed to get page by ID',
            page_id=page_id, error=str(e)
        )
        return None


def get_table_stats(config: Optional[Config] = None) -> Dict[str, Any]:
    """Get statistics about the vector database"""
    if config is None:
        config = Config.load()
    
    db_engine = DBEngine(config)
    return db_engine.get_table_stats()