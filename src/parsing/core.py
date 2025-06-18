from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
from enum import Enum

try:
    from ..api.models import (
        NotionBlock, NotionPage, NotionDatabase, RichTextObject, 
        BlockType, PropertyValue
    )
    from ..utils.logging import setup_logging, log_with_extra
except ImportError:
    from api.models import (
        NotionBlock, NotionPage, NotionDatabase, RichTextObject, 
        BlockType, PropertyValue
    )
    from utils.logging import setup_logging, log_with_extra


class EntityType(str, Enum):
    BLOCK = 'block'
    PAGE = 'page'
    DATABASE = 'database'


class NotionParser:
    """Simplified Notion content parser using Pydantic models"""
    
    def __init__(self, log_level: str = 'INFO'):
        self.logger = setup_logging(log_level)
        self.entity_index: Dict[str, Dict[str, Any]] = {}
    
    def extract_text(self, rich_text: List[RichTextObject]) -> str:
        """Extract plain text from rich text objects"""
        return '\n'.join([rt.plain_text for rt in rich_text if rt.plain_text])
    
    def parse_block_content(self, block: NotionBlock) -> Dict[str, Any]:
        """Extract meaningful content from any block type"""
        content = {
            'id': block.id,
            'type': block.type.value,
            'has_children': block.has_children,
            'text': '',
            'metadata': {}
        }
        
        # Get the block-specific content using the block type
        block_data = getattr(block, block.type.value, None)
        if not block_data:
            return content
            
        # Extract text from rich_text fields
        if hasattr(block_data, 'rich_text'):
            content['text'] = self.extract_text(block_data.rich_text)
            
        # Extract special fields based on block type
        if block.type == BlockType.CODE:
            content['metadata'] = {
                'language': block_data.language,
                'caption': self.extract_text(getattr(block_data, 'caption', []))
            }
        elif block.type == BlockType.TO_DO:
            content['metadata'] = {'checked': block_data.checked}
        elif block.type in [BlockType.HEADING_1, BlockType.HEADING_2, BlockType.HEADING_3]:
            content['metadata'] = {'is_toggleable': getattr(block_data, 'is_toggleable', False)}
        elif block.type in [BlockType.CHILD_PAGE, BlockType.CHILD_DATABASE]:
            content['text'] = block_data.title
        elif block.type == BlockType.TABLE_ROW:
            content['text'] = ' | '.join([self.extract_text(cell) for cell in block_data.cells])
        elif block.type == BlockType.SYNCED_BLOCK:
            if block_data.synced_from and block_data.synced_from.block_id:
                content['metadata'] = {'synced_block_id': block_data.synced_from.block_id}
        elif hasattr(block_data, 'url'):  # File types, links, embeds, etc.
            content['text'] = block_data.url
            content['metadata'] = {'url': block_data.url}
        elif hasattr(block_data, 'expression'):  # Equation
            content['text'] = block_data.expression
        elif block.type == BlockType.TABLE_OF_CONTENTS:
            content['text'] = 'Table of Contents'  # Default text for TOC blocks
            
        return content
    
    def parse_page_properties(self, properties: Dict[str, PropertyValue]) -> Dict[str, Any]:
        """Extract meaningful data from page properties"""
        parsed = {}
        title = ''
        
        for name, prop in properties.items():
            key = name.lower().replace(' ', '_')
            prop_data = getattr(prop, prop.type.value, None)
            
            if prop.type.value in ['title', 'rich_text']:
                text = self.extract_text(prop_data) if prop_data else ''
                parsed[key] = text
                if prop.type.value == 'title':
                    title = text
            elif prop.type.value in ['select', 'status']:
                parsed[key] = {'name': prop_data.name, 'color': prop_data.color} if prop_data else None
            elif prop.type.value == 'multi_select':
                parsed[key] = [{'name': opt.name, 'color': opt.color} for opt in prop_data]
            elif prop.type.value == 'people':
                parsed[key] = [{'name': person.name, 'id': person.id} for person in prop_data]
            elif prop.type.value == 'date':
                parsed[key] = {'start': prop_data.start, 'end': prop_data.end} if prop_data else None
            else:
                parsed[key] = prop_data
                
        return {'properties': parsed, 'title': title}
    
    def parse_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse any Notion entity into standardized format"""
        try:
            object_type = raw_data.get('object', '')
            
            if object_type == 'block':
                block = NotionBlock(**raw_data)
                content = self.parse_block_content(block)
                return {
                    **content,
                    'object': 'block',
                    'parent_id': self._get_parent_id(block.parent),
                    'created_time': block.created_time,
                    'last_edited_time': block.last_edited_time
                }
                
            elif object_type == 'page':
                page = NotionPage(**raw_data)
                page_data = self.parse_page_properties(page.properties)
                return {
                    'id': page.id,
                    'object': 'page',
                    'type': 'page',
                    'title': page_data['title'],
                    'url': page.url,
                    'properties': page_data['properties'],
                    'parent_id': self._get_parent_id(page.parent),
                    'created_time': page.created_time,
                    'last_edited_time': page.last_edited_time,
                    'text': page_data['title']  # For RAG search
                }
                
            elif object_type == 'database':
                database = NotionDatabase(**raw_data)
                return {
                    'id': database.id,
                    'object': 'database',
                    'type': 'database',
                    'title': self.extract_text(database.title),
                    'url': database.url,
                    'description': self.extract_text(database.description),
                    'parent_id': self._get_parent_id(database.parent),
                    'created_time': database.created_time,
                    'last_edited_time': database.last_edited_time,
                    'text': self.extract_text(database.title)  # For RAG search
                }
                
        except Exception as e:
            log_with_extra(
                self.logger, 'ERROR', 'Failed to parse entity',
                object_id=raw_data.get('id', 'unknown'),
                error=str(e)
            )
            # Return minimal fallback structure
            return {
                'id': raw_data.get('id', ''),
                'object': raw_data.get('object', 'unknown'),
                'type': raw_data.get('type', 'unknown'),
                'text': '',
                'error': str(e)
            }
    
    def _get_parent_id(self, parent) -> Optional[str]:
        """Extract parent ID from parent object"""
        if not parent:
            return None
        return parent.page_id or parent.database_id or parent.block_id
    
    def safe_json_load(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Safely load JSON file"""
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_with_extra(
                self.logger, 'WARNING', 'Failed to load JSON file',
                file_path=str(file_path),
                error=str(e)
            )
            return None