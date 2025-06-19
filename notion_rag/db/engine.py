import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import lancedb
import litellm

from notion_rag.config import Config
from notion_rag.utils.logging import log_write, setup_logging


class DBEngine:
    """Shared database engine for LanceDB operations"""

    def __init__(
        self,
        config: Config,
        db_path: Optional[Path] = None,
        table_name: Optional[str] = None,
    ):
        self.config = config
        self.logger = setup_logging(config.log_level)

        # Set up embedding model
        embedding_model = self._setup_embedding_model()
        self.embedding_size = embedding_model["size"]
        self.embedding_model = embedding_model["model"]

        # Set up LanceDB connection
        if db_path:
            self.db_path = db_path
        else:
            # Default database path following same pattern as entity-specific ones
            db_dir = config.data_dir / "databases"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "default.lancedb"
        self.db = lancedb.connect(str(self.db_path))
        self.table_name = table_name if table_name else "notion_pages"

    def _setup_embedding_model(self) -> dict[str, Any]:
        """Setup embedding model based on available API keys"""

        if os.getenv("GEMINI_API_KEY"):
            log_write(self.logger, "INFO", "Using Google Gemini embeddings via LiteLLM")
            return {"model": "gemini/text-embedding-004", "size": 768}
        if os.getenv("OPENAI_API_KEY"):
            log_write(self.logger, "INFO", "Using OpenAI embeddings via LiteLLM")
            return {"model": "text-embedding-3-small", "size": 1536}
        else:
            raise ValueError(
                "Please set either OPENAI_API_KEY or GEMINI_API_KEY environment variable"
            )

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using LiteLLM"""
        try:
            response = litellm.embedding(model=self.embedding_model, input=[text])
            return response.data[0]["embedding"]
        except Exception as e:
            log_write(
                self.logger,
                "ERROR",
                "Failed to get embedding",
                text_length=len(text),
                error=str(e),
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
                return {"exists": False}

            table = self.get_table()
            count = table.count_rows()

            return {
                "exists": True,
                "total_pages": count,
                "table_name": self.table_name,
                "embedding_model": self.embedding_model,
            }

        except Exception as e:
            log_write(self.logger, "ERROR", "Failed to get table stats", error=str(e))
            return {"exists": False, "error": str(e)}

    def search_pages(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the vector database for relevant pages"""
        try:
            if not self.table_exists():
                log_write(self.logger, "WARNING", "Table does not exist")
                return []

            table = self.get_table()
            if not table:
                return []

            # Get query embedding
            query_vector = self.get_embedding(query)

            # Vector search
            results = table.search(query_vector).limit(limit).to_list()

            log_write(
                self.logger,
                "INFO",
                "Search completed",
                query=query,
                results_count=len(results),
            )

            return results

        except Exception as e:
            log_write(self.logger, "ERROR", "Search failed", query=query, error=str(e))
            return []

    def get_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific page by its ID"""
        try:
            if not self.table_exists():
                return None

            table = self.get_table()
            if not table:
                return None

            results = table.search().where(f'id = "{page_id}"').limit(1).to_list()
            return results[0] if results else None

        except Exception as e:
            log_write(
                self.logger,
                "ERROR",
                "Failed to get page by ID",
                page_id=page_id,
                error=str(e),
            )
            return None
