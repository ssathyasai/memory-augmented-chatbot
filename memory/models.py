"""Memory and conversation Pydantic data models.

Process Flow:
1. Defines `Message` model tracking role (`user`, `assistant`, `system`), timestamp, sources, and metadata.
2. Defines `Conversation` model for session grouping, message arrays, session timestamps, and total message counts.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message model."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation session model."""
    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = Field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def message_count(self) -> int:
        """Get message count."""
        return len(self.messages)
