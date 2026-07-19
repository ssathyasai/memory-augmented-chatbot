"""Document processing package initialization.

Process Flow:
1. Exports high-level `DocumentProcessor` entry point.
2. Exports `Document` and `DocumentChunk` data model classes.
"""

from .processor import DocumentProcessor
from .models import Document, DocumentChunk

__all__ = ["DocumentProcessor", "Document", "DocumentChunk"]
