"""Application settings using Pydantic."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    APP_NAME: str = "Memory-Augmented Chatbot"
    DEBUG: bool = False
    
    # Security
    JWT_SECRET_KEY: str = Field(..., description="Secret key for JWT token generation")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    PASSWORD_MIN_LENGTH: int = 8
    
    # MongoDB
    MONGODB_URI: str = Field(..., description="MongoDB connection string")
    MONGODB_DB_NAME: str = "chatbot_db"
    
    # Neo4j
    NEO4J_URI: str = Field(..., description="Neo4j connection URI")
    NEO4J_USER: str = Field(..., description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")
    
    # GROQ
    GROQ_API_KEY: str = Field(..., description="GROQ API key")
    GROQ_MODEL: str = "mixtral-8x7b-32768"
    GROQ_MAX_TOKENS: int = 32768
    GROQ_TEMPERATURE: float = 0.7
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_CONTEXT_TOKENS: int = 4000
    
    # Vector Store
    VECTOR_STORE_TYPE: str = "faiss"
    VECTOR_STORE_PATH: str = "./vector_stores"
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    
    # Rate Limiting
    MAX_QUERIES_PER_MINUTE: int = 30
    MAX_DOCUMENTS_PER_USER: int = 100
    MAX_STORAGE_MB_PER_USER: int = 500
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
