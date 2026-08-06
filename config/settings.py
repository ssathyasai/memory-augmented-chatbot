"""Application environment configuration settings using Pydantic BaseSettings.

Process Flow:
1. Automatically reads variables from `.env` file or system environment.
2. Validates type safety and required parameters (GROQ API key, MongoDB URI, Neo4j credentials, JWT Secret).
3. Provides default fallbacks for RAG hyperparameters (chunk size, similarity threshold, top_k, embedding model).
4. Exports a singleton `settings` object used across the application architecture.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Any


def _get_secret_or_env(key: str, default: str = "") -> str:
    """Helper to fetch configuration value from os.environ or streamlit.secrets."""
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets and st.secrets[key]:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    APP_NAME: str = "Memory-Augmented Chatbot"
    DEBUG: bool = False
    
    # Security
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: _get_secret_or_env("JWT_SECRET_KEY", "dev-secret-key-change-in-production"),
        description="Secret key for JWT token generation"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    PASSWORD_MIN_LENGTH: int = 8
    
    # MongoDB
    MONGODB_URI: str = Field(
        default_factory=lambda: _get_secret_or_env("MONGODB_URI", "mongodb://localhost:27017"),
        description="MongoDB connection string"
    )
    MONGODB_DB_NAME: str = Field(
        default_factory=lambda: _get_secret_or_env("MONGODB_DB_NAME", "chatbot_db"),
        description="MongoDB database name"
    )
    
    # Neo4j
    NEO4J_URI: str = Field(
        default_factory=lambda: _get_secret_or_env("NEO4J_URI", "bolt://localhost:7687"),
        description="Neo4j connection URI"
    )
    NEO4J_USER: str = Field(
        default_factory=lambda: _get_secret_or_env("NEO4J_USER", "neo4j"),
        description="Neo4j username (for Aura, use instance ID)"
    )
    NEO4J_PASSWORD: str = Field(
        default_factory=lambda: _get_secret_or_env("NEO4J_PASSWORD", ""),
        description="Neo4j password"
    )
    NEO4J_DATABASE: str = Field(
        default_factory=lambda: _get_secret_or_env("NEO4J_DATABASE", "neo4j"),
        description="Neo4j database name (for Aura, use instance ID)"
    )
    
    # GROQ
    GROQ_API_KEY: str = Field(
        default_factory=lambda: _get_secret_or_env("GROQ_API_KEY", ""),
        description="GROQ API key"
    )
    GROQ_MODEL: str = Field(
        default_factory=lambda: _get_secret_or_env("GROQ_MODEL", "llama-3.1-8b-instant"),
        description="GROQ model name"
    )
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.7
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 8
    SIMILARITY_THRESHOLD: float = 0.40
    MAX_CONTEXT_TOKENS: int = 4000
    
    # Vector Store
    VECTOR_STORE_TYPE: str = "faiss"
    VECTOR_STORE_PATH: str = "./vector_stores"
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt,.md"
    
    # Rate Limiting
    MAX_QUERIES_PER_MINUTE: int = 30
    MAX_DOCUMENTS_PER_USER: int = 100
    MAX_STORAGE_MB_PER_USER: int = 500
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
