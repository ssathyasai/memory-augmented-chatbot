"""Custom exception classes hierarchy for domain-specific error handling.

Process Flow:
1. Defines root base exception `ChatbotException` carrying human-readable messages and HTTP status codes.
2. Derives domain exceptions for Authentication (`401`), Authorization (`403`), Validation (`400`), Document Parsing (`400`), RAG (`500`), Knowledge Graph (`500`), Database (`500`), Not Found (`404`), Rate Limit (`429`), and LLM API (`503`).
"""


class ChatbotException(Exception):
    """Base exception for all chatbot errors."""
    
    def __init__(self, message: str, code: int = 500):
        """
        Initialize exception.
        
        Args:
            message: Error message
            code: HTTP-like error code
        """
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(ChatbotException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code=401)


class AuthorizationError(ChatbotException):
    """Exception raised for authorization failures."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, code=403)


class ValidationError(ChatbotException):
    """Exception raised for validation failures."""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, code=400)


class DocumentProcessingError(ChatbotException):
    """Exception raised for document processing errors."""
    
    def __init__(self, message: str = "Document processing failed"):
        super().__init__(message, code=400)


class RAGError(ChatbotException):
    """Exception raised for RAG pipeline errors."""
    
    def __init__(self, message: str = "RAG operation failed"):
        super().__init__(message, code=500)


class KnowledgeGraphError(ChatbotException):
    """Exception raised for knowledge graph errors."""
    
    def __init__(self, message: str = "Knowledge graph operation failed"):
        super().__init__(message, code=500)


class DatabaseError(ChatbotException):
    """Exception raised for database errors."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, code=500)


class NotFoundError(ChatbotException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code=404)


class RateLimitError(ChatbotException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code=429)


class LLMError(ChatbotException):
    """Exception raised for LLM API errors."""
    
    def __init__(self, message: str = "LLM API error"):
        super().__init__(message, code=503)
