"""Error handling and logging utilities."""

import logging
import traceback
from typing import Dict, Any

from .exceptions import (
    ChatbotException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    DocumentProcessingError,
    RAGError,
    KnowledgeGraphError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
    LLMError
)

logger = logging.getLogger(__name__)


def log_error(error: Exception, context: Dict[str, Any] = None):
    """
    Log error with context and stack trace.
    
    Args:
        error: Exception to log
        context: Additional context information
    """
    context_str = f" Context: {context}" if context else ""
    
    if isinstance(error, ChatbotException):
        logger.error(f"{error.__class__.__name__}: {error.message}{context_str}")
    else:
        logger.error(f"{error.__class__.__name__}: {str(error)}{context_str}")
    
    # Log stack trace for non-user errors
    if not isinstance(error, (ValidationError, AuthenticationError, NotFoundError)):
        logger.debug(traceback.format_exc())


def handle_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Handle error and return user-friendly response.
    
    Args:
        error: Exception to handle
        context: Additional context information
    
    Returns:
        Dictionary with error information
    """
    log_error(error, context)
    
    if isinstance(error, AuthenticationError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "authentication_error"
        }
    
    elif isinstance(error, AuthorizationError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "authorization_error"
        }
    
    elif isinstance(error, ValidationError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "validation_error"
        }
    
    elif isinstance(error, NotFoundError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "not_found_error"
        }
    
    elif isinstance(error, RateLimitError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "rate_limit_error"
        }
    
    elif isinstance(error, DocumentProcessingError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "document_error"
        }
    
    elif isinstance(error, RAGError):
        return {
            "success": False,
            "error": "Unable to process your request. Please try again.",
            "code": error.code,
            "type": "rag_error"
        }
    
    elif isinstance(error, KnowledgeGraphError):
        return {
            "success": False,
            "error": "Knowledge graph operation failed. Please try again.",
            "code": error.code,
            "type": "kg_error"
        }
    
    elif isinstance(error, DatabaseError):
        return {
            "success": False,
            "error": "Database error occurred. Please try again later.",
            "code": error.code,
            "type": "database_error"
        }
    
    elif isinstance(error, LLMError):
        return {
            "success": False,
            "error": "AI service temporarily unavailable. Please try again.",
            "code": error.code,
            "type": "llm_error"
        }
    
    elif isinstance(error, ChatbotException):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "type": "chatbot_error"
        }
    
    else:
        # Unexpected error
        return {
            "success": False,
            "error": "An unexpected error occurred. Please try again.",
            "code": 500,
            "type": "internal_error"
        }


def get_user_message(error: Exception) -> str:
    """
    Get user-friendly error message.
    
    Args:
        error: Exception
    
    Returns:
        User-friendly error message
    """
    if isinstance(error, AuthenticationError):
        return "Authentication failed. Please check your credentials."
    
    elif isinstance(error, AuthorizationError):
        return "You don't have permission to perform this action."
    
    elif isinstance(error, ValidationError):
        return f"Validation error: {error.message}"
    
    elif isinstance(error, NotFoundError):
        return error.message
    
    elif isinstance(error, RateLimitError):
        return "You've made too many requests. Please wait a moment and try again."
    
    elif isinstance(error, DocumentProcessingError):
        return f"Document processing failed: {error.message}"
    
    elif isinstance(error, (RAGError, LLMError)):
        return "Unable to generate response. Please try again."
    
    elif isinstance(error, KnowledgeGraphError):
        return "Knowledge graph operation failed. This won't affect your chat."
    
    elif isinstance(error, DatabaseError):
        return "Database error. Please try again later."
    
    elif isinstance(error, ChatbotException):
        return error.message
    
    else:
        return "An unexpected error occurred. Please try again."
