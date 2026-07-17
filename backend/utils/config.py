
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from the backend directory.
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    # Groq API configuration powers the assistant model.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # MongoDB configuration stores memory, settings, and analytics.
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = "chatbot_db"

    # Neo4j configuration stores the knowledge graph.
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    # Tool configuration uses free public endpoints by default.
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    HN_SEARCH_BASE_URL: str = "https://hn.algolia.com/api/v1/search"
    WIKIPEDIA_SUMMARY_BASE_URL: str = "https://en.wikipedia.org/api/rest_v1/page/summary"

    # Local persistence paths keep the app usable in development if services are unavailable.
    DATABASE_DIR: str = str(BASE_DIR / "database")
    FAISS_DIR: str = str(BASE_DIR / "database" / "faiss_index")
    ANALYTICS_FILE: str = str(BASE_DIR / "database" / "analytics.json")
    DOCUMENT_INDEX_FILE: str = str(BASE_DIR / "database" / "documents.json")
    SETTINGS_FILE: str = str(BASE_DIR / "database" / "settings.json")

    # FastAPI configuration defines application metadata.
    APP_NAME: str = "Memory-Augmented Chatbot"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    class Config:
        env_file = str(BASE_DIR / ".env")
        case_sensitive = True


settings = Settings()
