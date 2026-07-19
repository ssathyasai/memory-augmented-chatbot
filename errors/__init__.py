"""Error handling package initialization.

Process Flow:
1. Exports custom exception hierarchy classes.
2. Exports central error handling and logging functions (`handle_error`, `log_error`).
"""

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
