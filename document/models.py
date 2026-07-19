"""Document data structures and Pydantic models.

Process Flow:
1. Defines `DocumentMetadata` for file size, page count, language, and author tracking.
2. Defines `DocumentChunk` schema for storing indexed chunk content with positional indexes.
3. Defines top-level `Document` model tracking upload status (`pending`, `processing`, `ready`, `error`), total chunks, and raw content.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata."""
    size_bytes: int
    page_count: Optional[int] = None
    language: str = "en"
    author: Optional[str] = None


class DocumentChunk(BaseModel):
    """Document chunk model."""
    chunk_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Document model."""
    id: str
    user_id: str
    filename: str
    file_type: str
    content: str
    chunks: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    metadata: DocumentMetadata
    upload_date: datetime
    status: str = "pending"  # pending, processing, ready, error
    error_message: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "filename": "document.pdf",
                "file_type": "pdf",
                "content": "Document text content...",
                "chunks": ["chunk1", "chunk2"],
                "chunk_count": 2,
                "metadata": {
                    "size_bytes": 1024000,
                    "page_count": 10,
                    "language": "en"
                },
                "upload_date": "2024-01-01T00:00:00",
                "status": "ready"
            }
        }
