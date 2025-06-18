import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, Set, Union
from enum import Enum

from .client import NotionAPIClient
from .models import NotionBlock, NotionPage, NotionDatabase, NotionBlockList, NotionDatabaseQuery, FileAttachmentType

try:
    from ..config import Config
    from ..utils.persistence import PullState, save_json
    from ..utils.logging import setup_logging, log_with_extra
except ImportError:
    from config import Config
    from utils.persistence import PullState, save_json
    from utils.logging import setup_logging, log_with_extra


class EntityType(str, Enum):
    BLOCK = 'block'
    PAGE = 'page'
    DATABASE = 'database'


class NotionPuller:
    """Stateful Notion content puller that handles pages, blocks, databases, and files"""
    
    def __init__(self, config: Config, entity_data_dir: Optional[Path] = None):
        self.config = config
        self.client = NotionAPIClient(config)
        self.logger = setup_logging(config.log_level)
        
        # Use entity-specific data directory if provided, otherwise use config default
        data_dir = entity_data_dir if entity_data_dir else config.data_dir
        self.state = PullState(data_dir / 'pull_state.json')
        
        # Create directories
        self.raw_dir = data_dir / 'raw'
        self.raw_dir.mkdir(parents=True, exist_ok=True)
    
    def pull_all(self, root_entity_id: str, entity_type: EntityType = EntityType.BLOCK):
        """Pull all content starting from root entity"""
        log_with_extra(
            self.logger, 'INFO', 'Starting pull operation',
            root_entity_id=root_entity_id,
            entity_type=entity_type
        )
        
        try:
            self._pull_entity_recursive(root_entity_id, entity_type, self.raw_dir)
            
            log_with_extra(
                self.logger, 'INFO', 'Pull operation completed successfully',
                completed_count=len(self.state.completed_entities),
                failed_count=len(self.state.failed_entities)
            )
            
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Pull operation failed',
                error=str(e),
                root_entity_id=root_entity_id
            )
            raise
    
    def _pull_entity_recursive(self, entity_id: str, entity_type: EntityType, base_path: Path):
        """Recursively pull entity and all its children"""
        
        # Skip if already processed
        if self.state.is_completed(entity_id):
            log_with_extra(
                self.logger, 'DEBUG', 'Skipping already processed entity',
                entity_id=entity_id,
                entity_type=entity_type
            )
            return
        
        try:
            log_with_extra(
                self.logger, 'INFO', 'Processing entity',
                entity_id=entity_id,
                entity_type=entity_type
            )
            
            # Pull main entity data with strong typing
            main_entity: Optional[Union[NotionBlock, NotionPage, NotionDatabase]] = None
            
            if entity_type == EntityType.BLOCK:
                raw_data = self.client.get_block(entity_id)
                main_entity = NotionBlock(**raw_data)
                self._save_entity_data(entity_id, 'block', 'main', raw_data, base_path)
                
                # If it's a child page, also get page data
                if main_entity.type.value == 'child_page':
                    page_raw_data = self.client.get_page(entity_id)
                    page_entity = NotionPage(**page_raw_data)
                    self._save_entity_data(entity_id, 'block', 'page_data', page_raw_data, base_path)
                    
            elif entity_type == EntityType.PAGE:
                raw_data = self.client.get_page(entity_id)
                main_entity = NotionPage(**raw_data)
                self._save_entity_data(entity_id, 'page', 'main', raw_data, base_path)
                
            elif entity_type == EntityType.DATABASE:
                raw_data = self.client.get_database(entity_id)
                main_entity = NotionDatabase(**raw_data)
                self._save_entity_data(entity_id, 'database', 'main', raw_data, base_path)
            
            # Pull children using typed entity
            if main_entity:
                self._pull_children(entity_id, entity_type, main_entity, base_path)
            
            # Mark as completed
            self.state.mark_completed(entity_id)
            
        except Exception as e:
            error_msg = f'{type(e).__name__}: {str(e)}'
            self.state.mark_failed(entity_id, error_msg)
            log_with_extra(
                self.logger, 'ERROR', 'Failed to process entity',
                entity_id=entity_id,
                entity_type=entity_type,
                error=error_msg
            )
            # Continue with other entities instead of failing completely
    
    def _pull_children(self, entity_id: str, entity_type: EntityType, main_entity: Union[NotionBlock, NotionPage, NotionDatabase], base_path: Path):
        """Pull children based on entity type using typed entities"""
        
        if entity_type in [EntityType.BLOCK, EntityType.PAGE]:
            self._pull_block_children(entity_id, base_path)
        elif entity_type == EntityType.DATABASE:
            self._pull_database_children(entity_id, base_path)
    
    def _pull_block_children(self, block_id: str, base_path: Path):
        """Pull all children of a block/page with strong typing"""
        all_children = []
        next_cursor = None
        
        while True:
            children_response_raw = self.client.get_block_children(block_id, next_cursor)
            children_response = NotionBlockList(**children_response_raw)
            # use the children from response_raw instead of Notion block to avoid creating unnecesary fields
            all_children.extend([child for child in children_response_raw['results']])  
            
            if not children_response.has_more:
                break
            next_cursor = children_response.next_cursor
        
        # Save children data (raw format for compatibility)
        children_data = {
            'object': 'list',
            'results': all_children,
            'has_more': False,
            'type': 'block'
        }
        self._save_entity_data(block_id, 'block', 'children', children_data, base_path)
        
        # Process each child with strong typing
        if all_children:
            entity_dir = base_path / f'block_{block_id}'
            entity_dir.mkdir(parents=True, exist_ok=True)
            
            for child_raw in all_children:
                try:
                    child_block = NotionBlock(**child_raw)
                    child_id = child_block.id
                    child_type = child_block.type.value
                    
                    # Handle different child types
                    if child_type == 'child_page':
                        self._pull_entity_recursive(child_id, EntityType.BLOCK, entity_dir)
                    elif child_type == 'child_database':
                        self._pull_entity_recursive(child_id, EntityType.DATABASE, entity_dir)
                    elif child_block.has_children:
                        self._pull_entity_recursive(child_id, EntityType.BLOCK, entity_dir)
                    elif child_type in [t.value for t in FileAttachmentType]:
                        self._download_file_attachment(child_block, entity_dir)
                        
                except Exception as e:
                    log_with_extra(
                        self.logger, 'WARNING', 'Failed to process child block',
                        parent_id=block_id,
                        child_id=child_raw.get('id', 'unknown'),
                        error=str(e)
                    )
    
    def _pull_database_children(self, database_id: str, base_path: Path):
        """Pull all pages from a database with strong typing"""
        all_pages = []
        next_cursor = None
        
        while True:
            pages_response_raw = self.client.query_database(database_id, next_cursor)
            pages_response = NotionDatabaseQuery(**pages_response_raw)
            # use the children from response_raw instead of Notion model to avoid creating unnecesary fields
            all_pages.extend([page for page in pages_response_raw['results']])  
            
            if not pages_response.has_more:
                break
            next_cursor = pages_response.next_cursor
        
        # Save database children (raw format for compatibility)
        children_data = {
            'object': 'list',
            'results': all_pages,
            'has_more': False,
            'type': 'page'
        }
        self._save_entity_data(database_id, 'database', 'children', children_data, base_path)
        
        # Process each page with strong typing
        if all_pages:
            entity_dir = base_path / f'database_{database_id}'
            entity_dir.mkdir(parents=True, exist_ok=True)
            
            for page_raw in all_pages:
                try:
                    page = NotionPage(**page_raw)
                    self._pull_entity_recursive(page.id, EntityType.BLOCK, entity_dir)
                except Exception as e:
                    log_with_extra(
                        self.logger, 'WARNING', 'Failed to process database page',
                        database_id=database_id,
                        page_id=page_raw.get('id', 'unknown'),
                        error=str(e)
                    )
    
    def _download_file_attachment(self, file_block: NotionBlock, entity_dir: Path):
        """Download file attachments using typed block"""
        try:
            file_type = file_block.type.value
            file_data = getattr(file_block, file_type, None)
            
            if file_data and hasattr(file_data, 'file') and file_data.file:
                url = file_data.file.url
                filename = urllib.parse.urlparse(url).path.split('/')[-1]
                
                if not filename:
                    filename = f"{file_block.id}.{file_type}"
                
                local_path = entity_dir / filename
                urllib.request.urlretrieve(url, local_path)
                
                log_with_extra(
                    self.logger, 'DEBUG', 'Downloaded file attachment',
                    filename=filename,
                    local_path=str(local_path),
                    block_id=file_block.id
                )
                
        except Exception as e:
            log_with_extra(
                self.logger, 'WARNING', 'Failed to download file attachment',
                block_id=file_block.id,
                error=str(e)
            )
    
    def _save_entity_data(self, entity_id: str, entity_type: str, data_type: str, data: Dict[str, Any], base_path: Path):
        """Save entity data to disk"""
        filename = f'{entity_type}_{entity_id}_{data_type}.json'
        file_path = base_path / filename
        save_json(data, file_path)
        
        log_with_extra(
            self.logger, 'DEBUG', 'Saved entity data',
            entity_id=entity_id,
            entity_type=entity_type,
            data_type=data_type,
            file_path=str(file_path)
        )
    
    def get_pull_summary(self) -> Dict[str, Any]:
        """Get summary of pull operation"""
        return {
            'completed_entities': len(self.state.completed_entities),
            'failed_entities': len(self.state.failed_entities),
            'failed_details': self.state.get_failed_entities()
        }
    
    def reset_state(self):
        """Reset pull state to start fresh"""
        self.state.reset()
        log_with_extra(self.logger, 'INFO', 'Pull state reset')
    
    def retry_failed_entities(self):
        """Reset only failed entities to retry them"""
        failed_count = len(self.state.failed_entities)
        self.state.reset_failed_entities()
        log_with_extra(self.logger, 'INFO', f'Reset {failed_count} failed entities for retry')
    
    def pull_failed_entities_only(self):
        """Pull only the previously failed entities"""
        failed_entities = list(self.state.failed_entities.keys())
        if not failed_entities:
            log_with_extra(self.logger, 'INFO', 'No failed entities to retry')
            return
            
        log_with_extra(
            self.logger, 'INFO', 'Retrying failed entities only',
            failed_count=len(failed_entities)
        )
        
        # Clear failed state and pull each failed entity directly
        self.state.reset_failed_entities()
        
        for entity_id in failed_entities:
            try:
                # Assume all failed entities are blocks for now
                self._pull_entity_recursive(entity_id, EntityType.BLOCK, self.raw_dir)
            except Exception as e:
                log_with_extra(
                    self.logger, 'ERROR', 'Failed to retry entity',
                    entity_id=entity_id,
                    error=str(e)
                )