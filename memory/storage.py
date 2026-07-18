"""Conversation storage in MongoDB."""

import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
import uuid

from config.database import get_database
from errors.exceptions import DatabaseError
from .models import Message, Conversation

logger = logging.getLogger(__name__)


class ConversationStorage:
    """Store and retrieve conversations."""
    
    def __init__(self):
        """Initialize conversation storage."""
        self.db = get_database()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            self.db = get_database()
            if self.db is None:
                raise DatabaseError("Database connection not available")
    
    def create_session(self, user_id: str) -> str:
        """
        Create new conversation session.
        
        Args:
            user_id: User ID
        
        Returns:
            Session ID
        """
        self._ensure_db()
        
        try:
            session_id = str(uuid.uuid4())
            
            session_doc = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": [],
                "summary": None,
                "metadata": {
                    "message_count": 0,
                    "token_count": 0
                }
            }
            
            self.db.conversations.insert_one(session_doc)
            logger.info(f"Created conversation session: {session_id}")
            
            return session_id
        
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise DatabaseError(f"Failed to create session: {str(e)}")
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: List[str] = None,
        metadata: dict = None
    ):
        """
        Add message to conversation.
        
        Args:
            session_id: Session ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            sources: Source document IDs
            metadata: Additional metadata
        """
        self._ensure_db()
        
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "sources": sources or [],
                "metadata": metadata or {}
            }
            
            self.db.conversations.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"metadata.message_count": 1}
                }
            )
            
            logger.debug(f"Added {role} message to session {session_id}")
        
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise DatabaseError(f"Failed to add message: {str(e)}")
    
    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """
        Get conversation by session ID.
        
        Args:
            session_id: Session ID
        
        Returns:
            Conversation object or None
        """
        self._ensure_db()
        
        try:
            conv_doc = self.db.conversations.find_one({"session_id": session_id})
            
            if not conv_doc:
                return None
            
            messages = [
                Message(**msg) for msg in conv_doc.get("messages", [])
            ]
            
            conversation = Conversation(
                session_id=conv_doc["session_id"],
                user_id=conv_doc["user_id"],
                created_at=conv_doc["created_at"],
                updated_at=conv_doc["updated_at"],
                messages=messages,
                summary=conv_doc.get("summary"),
                metadata=conv_doc.get("metadata", {})
            )
            
            return conversation
        
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Conversation]:
        """
        Get user's conversations.
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations
        
        Returns:
            List of conversations
        """
        self._ensure_db()
        
        try:
            conv_docs = self.db.conversations.find(
                {"user_id": user_id}
            ).sort("updated_at", -1).limit(limit)
            
            conversations = []
            for conv_doc in conv_docs:
                messages = [
                    Message(**msg) for msg in conv_doc.get("messages", [])
                ]
                
                conversations.append(Conversation(
                    session_id=conv_doc["session_id"],
                    user_id=conv_doc["user_id"],
                    created_at=conv_doc["created_at"],
                    updated_at=conv_doc["updated_at"],
                    messages=messages,
                    summary=conv_doc.get("summary"),
                    metadata=conv_doc.get("metadata", {})
                ))
            
            return conversations
        
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            return []
    
    def delete_conversation(self, session_id: str, user_id: str) -> bool:
        """
        Delete conversation.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
        
        Returns:
            True if deleted
        """
        self._ensure_db()
        
        try:
            result = self.db.conversations.delete_one({
                "session_id": session_id,
                "user_id": user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Deleted conversation: {session_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    def get_recent_messages(self, session_id: str, limit: int = 10) -> List[Message]:
        """
        Get recent messages from conversation.
        
        Args:
            session_id: Session ID
            limit: Number of recent messages
        
        Returns:
            List of recent messages
        """
        conversation = self.get_conversation(session_id)
        
        if not conversation:
            return []
        
        return conversation.messages[-limit:] if conversation.messages else []


# Global conversation storage instance
conversation_storage = ConversationStorage()
