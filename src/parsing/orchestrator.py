from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

try:
    from .core import NotionParser
    from ..api.models import NotionBlock, NotionPage, NotionDatabase
    from ..config import Config
    from ..utils.logging import setup_logging, log_with_extra
    from ..utils.persistence import save_json
    from ..db.models import NotionPageSchema
except ImportError:
    from parsing.core import NotionParser
    from api.models import NotionBlock, NotionPage, NotionDatabase
    from config import Config
    from utils.logging import setup_logging, log_with_extra
    from utils.persistence import save_json
    from db.models import NotionPageSchema


class ParseOrchestrator:
    """Direct parser from Pydantic models to flat LanceDB format"""
    
    def __init__(self, config: Config, entity_data_dir: Optional[Path] = None):
        self.config = config
        self.parser = NotionParser(config.log_level)
        self.logger = setup_logging(config.log_level)
        
        # Use entity-specific data directory if provided, otherwise use config default
        data_dir = entity_data_dir if entity_data_dir else config.data_dir
        self.raw_dir = data_dir / 'raw'
        self.parsed_dir = data_dir / 'parsed'
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_all_entities(self) -> List[Dict[str, Any]]:
        """Collect all entities from API directory and parse to flat format"""
        flat_entities = []
        
        # Walk through all JSON files in raw directory
        for json_file in self.raw_dir.rglob('*.json'):
            try:
                raw_data = self.parser.safe_json_load(json_file)
                if not raw_data:
                    continue
                
                # Parse into Pydantic model and extract flat content
                flat_entity = self.parse_to_flat_format(raw_data)
                if flat_entity and flat_entity.get('text', '').strip():
                    flat_entities.append(flat_entity)
                    
            except Exception as e:
                log_with_extra(
                    self.logger, 'WARNING', 'Failed to parse entity file',
                    file_path=str(json_file), error=str(e)
                )
        
        return flat_entities
    
    def parse_to_flat_format(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw JSON directly to flat format using NotionParser"""
        try:
            # Use the existing parser's parse_entity method
            parsed = self.parser.parse_entity(raw_data)
            
            # Convert to flat format with additional fields for LanceDB
            flat_entity = {
                'id': parsed['id'],
                'type': parsed['object'],
                'text': parsed['text'],
                'created_time': parsed.get('created_time'),
                'last_edited_time': parsed.get('last_edited_time'),
                'parent_id': parsed.get('parent_id')
            }
            
            # Add type-specific fields
            if parsed['object'] == 'page':
                flat_entity.update({
                    'title': parsed.get('title', ''),
                    'url': parsed.get('url', ''),
                    'properties': parsed.get('properties', {})
                })
            elif parsed['object'] == 'database':
                flat_entity.update({
                    'title': parsed.get('title', ''),
                    'url': parsed.get('url', ''),
                    'description': parsed.get('description', ''),
                    'is_inline': parsed.get('is_inline', False)
                })
            elif parsed['object'] == 'block':
                flat_entity.update({
                    'block_type': parsed.get('type', ''),
                    'url': parsed.get('metadata', {}).get('url'),
                    'metadata': parsed.get('metadata', {})
                })
            
            return flat_entity
                
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Failed to parse to flat format',
                object_id=raw_data.get('id', 'unknown'), error=str(e)
            )
            
        return None
    
    def build_page_hierarchy(self, flat_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical page content by combining related entities"""
        pages_map = {}
        blocks_by_parent = {}
        
        # Organize entities by type and parent
        for entity in flat_entities:
            if entity['type'] == 'page':
                pages_map[entity['id']] = entity
            elif entity['type'] == 'block' and entity.get('parent_id'):
                parent_id = entity['parent_id']
                if parent_id not in blocks_by_parent:
                    blocks_by_parent[parent_id] = []
                blocks_by_parent[parent_id].append(entity)
        
        # Combine pages with their block content
        enhanced_pages = []
        for page_id, page in pages_map.items():
            # Collect all text content from child blocks
            child_blocks = blocks_by_parent.get(page_id, [])
            
            # Build combined text content
            combined_text = page['title'] + '\n\n'
            
            # Add property text
            for prop_value in page.get('properties', {}).values():
                if isinstance(prop_value, str) and prop_value.strip():
                    combined_text += f"{prop_value}\n"
            
            # Add block content
            for block in child_blocks:
                if block.get('text', '').strip():
                    combined_text += f"{block['text']}\n"
            
            # Create enhanced page using Pydantic model
            enhanced_page = NotionPageSchema(
                id=page_id,
                title=page['title'],
                text=combined_text.strip(),
                url=page['url'],
                parent_id=page.get('parent_id'),
                created_time=page.get('created_time'),
                last_edited_time=page.get('last_edited_time'),
                properties=page.get('properties', {})
            ).to_dict()
            
            enhanced_pages.append(enhanced_page)
        
        return enhanced_pages
    
    def parse_all(self) -> Dict[str, Any]:
        """Parse all content to flat format ready for LanceDB"""
        log_with_extra(self.logger, 'INFO', 'Starting flat parsing operation')
        
        try:
            # Collect all entities in flat format
            flat_entities = self.collect_all_entities()
            
            # Build hierarchical pages
            pages = self.build_page_hierarchy(flat_entities)
            
            # Save results
            save_json(flat_entities, self.parsed_dir / 'flat_entities.json')
            save_json(pages, self.parsed_dir / 'parsed_pages.json')
            
            log_with_extra(
                self.logger, 'INFO', 'Flat parsing completed',
                total_entities=len(flat_entities),
                total_pages=len(pages)
            )
            
            return {
                'flat_entities': flat_entities,
                'pages': pages
            }
            
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Flat parsing failed', error=str(e)
            )
            raise