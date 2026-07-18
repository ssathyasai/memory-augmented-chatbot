"""MongoDB database connection and management."""

import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .settings import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manage MongoDB connections."""
    
    def __init__(self):
        """Initialize MongoDB manager."""
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
    
    def connect(self) -> bool:
        """
        Connect to MongoDB.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            
            # Test connection
            self._client.admin.command('ping')
            self._db = self._client[settings.MONGODB_DB_NAME]
            
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._client = None
            self._db = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self._client = None
            self._db = None
            return False
    
    def get_database(self) -> Optional[Database]:
        """
        Get MongoDB database instance.
        
        Returns:
            Database or None if not connected
        """
        if self._db is None:
            logger.warning("MongoDB not connected. Attempting to connect...")
            self.connect()
        return self._db
    
    def is_connected(self) -> bool:
        """
        Check if MongoDB is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if self._client is None:
            return False
        
        try:
            self._client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("Disconnected from MongoDB")
            self._client = None
            self._db = None
    
    def create_indexes(self):
        """Create necessary database indexes for performance."""
        if self._db is None:
            logger.error("Cannot create indexes: database not connected")
            return
        
        try:
            # Users collection indexes
            self._db.users.create_index("email", unique=True)
            self._db.users.create_index("created_at")
            
            # Documents collection indexes
            self._db.documents.create_index([("user_id", 1), ("filename", 1)])
            self._db.documents.create_index("upload_date")
            self._db.documents.create_index("status")
            
            # Conversations collection indexes
            self._db.conversations.create_index("session_id", unique=True)
            self._db.conversations.create_index([("user_id", 1), ("created_at", -1)])
            self._db.conversations.create_index("updated_at")
            
            # Chats collection indexes (for hybrid orchestrator)
            self._db.chats.create_index([("user_id", 1), ("timestamp", -1)])
            self._db.chats.create_index("query_type")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")


# Global MongoDB manager instance
mongodb_manager = MongoDBManager()


def get_database() -> Optional[Database]:
    """
    Get MongoDB database instance.
    
    Returns:
        Database or None if not connected
    """
    return mongodb_manager.get_database()
