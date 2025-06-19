from typing import Any, Dict, Optional
import time

from notion_client import Client

from notion_rag.config import Config
from notion_rag.utils.logging import log_write, setup_logging


class NotionAPIClient:
    """Wrapper around notion_client with retry logic and rate limiting"""

    def __init__(self, config: Config):
        self.config = config
        self.client = Client(auth=config.notion_token)
        self.logger = setup_logging(config.log_level)

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                time.sleep(self.config.api_delay)
                result = func(*args, **kwargs)

                log_write(
                    self.logger,
                    "DEBUG",
                    "API call successful",
                    function=func.__name__,
                    attempt=attempt + 1,
                )
                return result

            except Exception as e:
                wait_time = self.config.api_delay * (
                    self.config.backoff_factor**attempt
                )

                log_write(
                    self.logger,
                    "WARNING",
                    "API call failed, retrying",
                    function=func.__name__,
                    attempt=attempt + 1,
                    error=str(e),
                    wait_time=wait_time,
                )

                if attempt == self.config.max_retries - 1:
                    log_write(
                        self.logger,
                        "ERROR",
                        "API call failed permanently",
                        function=func.__name__,
                        error=str(e),
                    )
                    raise

                time.sleep(wait_time)

    def get_block(self, block_id: str) -> Dict[str, Any]:
        """Get block with retry logic"""
        return self._retry_with_backoff(self.client.blocks.retrieve, block_id=block_id)

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page with retry logic"""
        return self._retry_with_backoff(self.client.pages.retrieve, page_id=page_id)

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database with retry logic"""
        return self._retry_with_backoff(
            self.client.databases.retrieve, database_id=database_id
        )

    def get_block_children(
        self, block_id: str, start_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get block children with retry logic"""
        kwargs = {"block_id": block_id}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        return self._retry_with_backoff(self.client.blocks.children.list, **kwargs)

    def query_database(
        self, database_id: str, start_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query database with retry logic"""
        kwargs = {"database_id": database_id}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        return self._retry_with_backoff(self.client.databases.query, **kwargs)
