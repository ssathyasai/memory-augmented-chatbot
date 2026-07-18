"""Error handling package."""

from .exceptions import (
    ChatbotException,
    AuthenticationError,
    DocumentProcessingError,
    RAGError,
    KnowledgeGraphError,
    DatabaseError,
    ValidationError
)
from .handlers import handle_error, log_error

__all__ = [
    "ChatbotException",
    "AuthenticationError",
    "DocumentProcessingError",
    "RAGError",
    "KnowledgeGraphError",
    "DatabaseError",
    "ValidationError",
    "handle_error",
    "log_error"
]
