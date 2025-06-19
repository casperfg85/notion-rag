import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from notion_rag.api.models import (
    BlockType,
    NotionBlock,
    NotionDatabase,
    NotionPage,
    PropertyValue,
    RichTextObject,
)
from notion_rag.utils.logging import log_write, setup_logging


class NotionParser:
    """Simplified Notion content parser using Pydantic models"""

    def __init__(self, log_level: str = "INFO"):
        self.logger = setup_logging(log_level)

    def extract_text(self, rich_text: List[RichTextObject]) -> str:
        """Extract plain text from rich text objects"""
        return "\n".join([rt.plain_text for rt in rich_text if rt.plain_text])

    def parse_block_content(self, block: NotionBlock) -> Dict[str, Any]:
        """Extract meaningful content from any block type"""
        content: Dict[str, Any] = {
            "id": block.id,
            "type": block.type.value,
            "has_children": block.has_children,
            "text": "",
            "metadata": {},
        }

        # Get the block-specific content using the block type
        block_data = getattr(block, block.type.value, None)
        if not block_data:
            return content

        # Extract text from rich_text fields
        if hasattr(block_data, "rich_text"):
            content["text"] = self.extract_text(block_data.rich_text)

        # Extract special fields based on block type
        if block.type == BlockType.CODE:
            content["metadata"] = {
                "language": block_data.language,
                "caption": self.extract_text(getattr(block_data, "caption", [])),
            }
        elif block.type == BlockType.TO_DO:
            content["metadata"] = {"checked": block_data.checked}
        elif block.type in [
            BlockType.HEADING_1,
            BlockType.HEADING_2,
            BlockType.HEADING_3,
        ]:
            content["metadata"] = {
                "is_toggleable": getattr(block_data, "is_toggleable", False)
            }
        elif block.type in [BlockType.CHILD_PAGE, BlockType.CHILD_DATABASE]:
            content["text"] = block_data.title
        elif block.type == BlockType.TABLE_ROW:
            content["text"] = " | ".join(
                [self.extract_text(cell) for cell in block_data.cells]
            )
        elif block.type == BlockType.SYNCED_BLOCK:
            if block_data.synced_from and block_data.synced_from.block_id:
                content["metadata"] = {
                    "synced_block_id": block_data.synced_from.block_id
                }
        elif hasattr(block_data, "url"):  # File types, links, embeds, etc.
            content["text"] = block_data.url
            content["metadata"] = {"url": block_data.url}
        elif hasattr(block_data, "expression"):  # Equation
            content["text"] = block_data.expression
        elif block.type == BlockType.TABLE_OF_CONTENTS:
            content["text"] = "Table of Contents"  # Default text for TOC blocks

        return content

    def parse_page_properties(
        self, properties: Dict[str, PropertyValue]
    ) -> Dict[str, Any]:
        """Extract meaningful data from page properties"""
        parsed: Dict[str, Any] = {}
        title: str = ""

        for name, prop in properties.items():
            cleaned_name = name.lower().replace(" ", "_").strip()
            prop_type = prop.type.value

            key = f"{prop_type}_{cleaned_name}"
            # Get the property data using the correct field name
            prop_data = getattr(prop, prop_type, None)
            try:
                if prop_type in ["title", "rich_text"]:
                    text = self.extract_text(prop_data) if prop_data else ""

                    if prop_type == "title":
                        if not cleaned_name:
                            # Handle cases where the title property name is an empty string
                            key = "title_missing_title"
                        title = text

                    parsed[key] = text
                elif prop_type in ["select", "status"]:
                    if prop_data:
                        parsed[key] = {"name": prop_data.name, "color": prop_data.color}
                    else:
                        parsed[key] = None
                elif prop_type == "multi_select":
                    if prop_data:
                        parsed[key] = [
                            {"name": opt.name, "color": opt.color} for opt in prop_data
                        ]
                    else:
                        parsed[key] = []
                elif prop_type in ["people"]:
                    if prop_data:
                        parsed[key] = [
                            {"name": person.name, "id": person.id}
                            for person in prop_data
                        ]
                    else:
                        parsed[key] = []
                elif prop_type == "date":
                    if prop_data:
                        parsed[key] = {"start": prop_data.start, "end": prop_data.end}
                    else:
                        parsed[key] = None

            except Exception as e:
                log_write(
                    self.logger,
                    "ERROR",
                    "Failed to parse page property",
                    key=key,
                    prop_data=prop_data,
                    error=str(e),
                )
                raise (e)

        return {"properties": parsed, "title": title}

    def parse_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse any Notion entity into standardized format"""
        try:
            object_type = raw_data.get("object", "")

            if object_type == "block":
                block = NotionBlock(**raw_data)
                content = self.parse_block_content(block)
                return {
                    **content,
                    "object": "block",
                    "parent_id": self._get_parent_id(block.parent),
                    "created_time": block.created_time,
                    "last_edited_time": block.last_edited_time,
                }

            elif object_type == "page":
                page = NotionPage(**raw_data)
                page_data = self.parse_page_properties(page.properties)
                return {
                    "id": page.id,
                    "object": "page",
                    "type": "page",
                    "title": page_data["title"],
                    "url": page.url,
                    "properties": page_data["properties"],
                    "parent_id": self._get_parent_id(page.parent),
                    "created_time": page.created_time,
                    "last_edited_time": page.last_edited_time,
                    "text": page_data["title"],  # For RAG search
                }

            elif object_type == "database":
                database = NotionDatabase(**raw_data)
                return {
                    "id": database.id,
                    "object": "database",
                    "type": "database",
                    "title": self.extract_text(database.title),
                    "url": database.url,
                    "description": self.extract_text(database.description),
                    "parent_id": self._get_parent_id(database.parent),
                    "created_time": database.created_time,
                    "last_edited_time": database.last_edited_time,
                    "text": self.extract_text(database.title),  # For RAG search
                }
            else:
                raise Exception(f"Unknown Object Type - {object_type}")

            # Return minimal structure for unknown object types
            return {
                "id": raw_data.get("id", ""),
                "object": object_type,
                "type": raw_data.get("type", "unknown"),
                "text": "",
            }

        except Exception as e:
            log_write(
                self.logger,
                "ERROR",
                "Failed to parse entity",
                object_id=raw_data.get("id", "unknown"),
                error=str(e),
            )
            # Return minimal fallback structure
            return {
                "id": raw_data.get("id", ""),
                "object": raw_data.get("object", "unknown"),
                "type": raw_data.get("type", "unknown"),
                "text": "",
                "error": str(e),
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
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_write(
                self.logger,
                "WARNING",
                "Failed to load JSON file",
                file_path=str(file_path),
                error=str(e),
            )
            return None
