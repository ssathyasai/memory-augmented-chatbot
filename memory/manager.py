"""High-level conversation memory orchestration manager.

Process Flow:
1. Manages creation, switching, and tracking of active user session IDs.
2. Adds user and assistant chat messages into session storage (`ConversationStorage`).
3. Fetches recent conversation turns formatted for LLM API prompts or Streamlit UI chat display.
4. Formats string representation of chat context for prompt engineering.
5. Deletes active or historical conversation sessions.
"""

import logging
from typing import List, Dict, Any

from .storage import conversation_storage
from .models import Message

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manage conversation memory."""
    
    def __init__(self, user_id: str):
        """
        Initialize memory manager.
        
        Args:
            user_id: User ID
        """
        self.user_id = user_id
        self.storage = conversation_storage
        self.current_session_id: str = None
    
    def create_session(self) -> str:
        """
        Create new conversation session.
        
        Returns:
            Session ID
        """
        self.current_session_id = self.storage.create_session(self.user_id)
        return self.current_session_id
    
    def set_session(self, session_id: str):
        """
        Set current session.
        
        Args:
            session_id: Session ID
        """
        self.current_session_id = session_id
    
    def add_user_message(self, content: str):
        """
        Add user message to current session.
        
        Args:
            content: Message content
        """
        if not self.current_session_id:
            self.create_session()
        
        self.storage.add_message(
            session_id=self.current_session_id,
            role="user",
            content=content
        )
    
    def add_assistant_message(
        self,
        content: str,
        sources: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Add assistant message to current session.
        
        Args:
            content: Message content
            sources: Source document IDs
            metadata: Additional metadata
        """
        if not self.current_session_id:
            self.create_session()
        
        self.storage.add_message(
            session_id=self.current_session_id,
            role="assistant",
            content=content,
            sources=sources,
            metadata=metadata
        )
    
    def get_conversation_history(self, limit: int = None) -> List[Message]:
        """
        Get conversation history for current session.
        
        Args:
            limit: Maximum number of messages (None for all)
        
        Returns:
            List of messages
        """
        if not self.current_session_id:
            return []
        
        if limit:
            return self.storage.get_recent_messages(self.current_session_id, limit)
        
        conversation = self.storage.get_conversation(self.current_session_id)
        return conversation.messages if conversation else []
    
    def get_conversation_context(self, max_messages: int = 10) -> str:
        """
        Get conversation context as formatted string.
        
        Args:
            max_messages: Maximum number of recent messages
        
        Returns:
            Formatted conversation context
        """
        messages = self.get_conversation_history(limit=max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            role = msg.role.capitalize()
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def get_messages_for_llm(self, max_messages: int = 6) -> List[Dict[str, str]]:
        """
        Get messages formatted for LLM API.
        
        Args:
            max_messages: Maximum number of recent messages
        
        Returns:
            List of message dictionaries
        """
        messages = self.get_conversation_history(limit=max_messages)
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    def clear_session(self):
        """Clear current session."""
        self.current_session_id = None
    
    def delete_session(self):
        """Delete current session from database."""
        if self.current_session_id:
            self.storage.delete_conversation(self.current_session_id, self.user_id)
            self.current_session_id = None
    
    def get_user_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's conversation sessions.
        
        Args:
            limit: Maximum number of sessions
        
        Returns:
            List of session summaries
        """
        conversations = self.storage.get_user_conversations(self.user_id, limit)
        
        return [
            {
                "session_id": conv.session_id,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": conv.message_count,
                "summary": conv.summary or f"{conv.message_count} messages"
            }
            for conv in conversations
        ]
