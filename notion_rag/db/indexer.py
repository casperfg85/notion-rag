import json

from pathlib import Path
from typing import Any, Dict, Optional

from notion_rag.config import Config
from notion_rag.utils.logging import log_write, setup_logging

from notion_rag.db.engine import DBEngine
from notion_rag.db.models import NotionPageSchema


class NotionIndexer:
    """LanceDB indexer for Notion content - focused only on indexing operations"""

    def __init__(
        self,
        config: Config,
        entity_data_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        entity_id: Optional[str] = None,
    ):
        self.config = config
        self.logger = setup_logging(config.log_level)
        self.entity_data_dir = entity_data_dir if entity_data_dir else config.data_dir
        self.db_path = db_path
        self.entity_id = entity_id
        self.db_engine = DBEngine(config=config, db_path=db_path)

    def create_index(self, recreate: bool = False) -> Dict[str, Any]:
        """Create vector index from parsed content"""
        log_write(self.logger, "INFO", "Starting index creation", recreate=recreate)

        try:
            # Check if parsed data exists
            parsed_file = self.entity_data_dir / "parsed" / "parsed_pages.json"
            if not parsed_file.exists():
                raise FileNotFoundError(f"Parsed pages file not found: {parsed_file}")

            # Load parsed data
            with open(parsed_file, "r") as f:
                pages_data = json.load(f)

            if not pages_data:
                raise ValueError("No pages data found")

            # Convert to Pydantic models and add embeddings
            log_write(
                self.logger,
                "INFO",
                "Converting to schema and generating embeddings",
                total_pages=len(pages_data),
            )

            validated_pages = []
            for i, page_data in enumerate(pages_data):
                if i % 10 == 0:
                    log_write(
                        self.logger, "INFO", f"Processing page {i+1}/{len(pages_data)}"
                    )

                try:
                    # Convert to Pydantic model for validation
                    page_schema = NotionPageSchema(**page_data)

                    # Generate embedding for the text content
                    if page_schema.text:
                        embedding = self.db_engine.get_embedding(page_schema.text)
                        page_schema.vector = self.ensure_embedding(
                            embedding, self.db_engine.embedding_size
                        )
                    else:
                        page_schema.vector = self.ensure_embedding(
                            None, self.db_engine.embedding_size
                        )

                    validated_pages.append(page_schema.to_dict())

                except Exception as e:
                    log_write(
                        self.logger,
                        "WARNING",
                        "Failed to validate page",
                        page_id=page_data.get("id", "unknown"),
                        error=str(e),
                    )

            pages_data = validated_pages

            # Drop existing table if recreating
            if recreate and self.db_engine.table_exists():
                self.db_engine.db.drop_table(self.db_engine.table_name)
                log_write(self.logger, "INFO", "Dropped existing table")

            # Create or get table
            if not self.db_engine.table_exists():
                # Create new table
                table = self.db_engine.db.create_table(
                    self.db_engine.table_name, data=pages_data
                )
                log_write(self.logger, "INFO", "Created new table")
            else:
                # Add to existing table
                table = self.db_engine.get_table()
                table.add(pages_data)
                log_write(self.logger, "INFO", "Added data to existing table")

            # Get stats
            stats = self._get_index_stats()

            log_write(self.logger, "INFO", "Index creation completed", **stats)

            return stats

        except Exception as e:
            log_write(self.logger, "ERROR", "Index creation failed", error=str(e))
            raise

    def _get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        stats = self.db_engine.get_table_stats()
        if stats.get("exists"):
            return {
                "indexed_documents": stats["total_pages"],
                "table_name": stats["table_name"],
                "embedding_model": stats["embedding_model"],
            }
        else:
            return {
                "indexed_documents": "unknown",
                "table_name": self.db_engine.table_name,
                "embedding_model": self.db_engine.embedding_model,
            }

    def get_table(self):
        """Get the LanceDB table for direct access"""
        return self.db_engine.get_table()

    def ensure_embedding(self, embedding, size=1536):
        if isinstance(embedding, list) and len(embedding) == size:
            return embedding
        return [0.0] * size
