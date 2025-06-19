from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class NotionPageSchema(BaseModel):
    """Schema for Notion pages in LanceDB"""

    id: str = Field(..., description="Unique identifier for the page")
    title: str = Field(default="", description="Page title")
    text: str = Field(
        default="", description="Combined text content from page and all child blocks"
    )
    url: str = Field(default="", description="Notion URL for the page")

    # Timestamps
    created_time: Optional[datetime] = Field(
        None, description="When the page was created"
    )
    last_edited_time: Optional[datetime] = Field(
        None, description="When the page was last edited"
    )

    # Hierarchy
    parent_id: Optional[str] = Field(None, description="ID of the parent page/database")

    # Properties from Notion page
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Page properties"
    )

    # Vector embedding for semantic search
    vector: Optional[List[float]] = Field(
        None, description="Vector embedding for semantic search"
    )

    @validator("text")
    def validate_text_content(cls, v):
        """Ensure text content is not None"""
        return v or ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LanceDB storage"""
        return self.dict()

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
