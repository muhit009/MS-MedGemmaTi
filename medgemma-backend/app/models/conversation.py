"""
Conversation data models.
Represents AI consultation sessions and messages.
"""

from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from uuid import UUID
from enum import Enum


class MessageSender(str, Enum):
    """Message sender types."""
    USER = "user"
    AI = "ai"


@dataclass
class MessageContext:
    """
    Message context entity.
    Tracks which images/notes were attached to a message.
    """
    id: UUID
    message_id: UUID
    attached_image_id: Optional[UUID] = None
    attached_note_id: Optional[UUID] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "MessageContext":
        """Create a MessageContext from a dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            message_id=UUID(data["message_id"]) if isinstance(data["message_id"], str) else data["message_id"],
            attached_image_id=UUID(data["attached_image_id"]) if data.get("attached_image_id") else None,
            attached_note_id=UUID(data["attached_note_id"]) if data.get("attached_note_id") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
            "attached_image_id": str(self.attached_image_id) if self.attached_image_id else None,
            "attached_note_id": str(self.attached_note_id) if self.attached_note_id else None
        }


@dataclass
class Message:
    """
    Message entity.
    Represents a single message in a conversation.
    """
    id: UUID
    conversation_id: UUID
    sender: MessageSender
    content: str
    created_at: Optional[datetime] = None
    
    # Related data
    context: List[MessageContext] = field(default_factory=list)
    
    @property
    def timestamp(self) -> Optional[str]:
        """Get timestamp as ISO string."""
        if self.created_at:
            return self.created_at.isoformat()
        return None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create a Message from a dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            conversation_id=UUID(data["conversation_id"]) if isinstance(data["conversation_id"], str) else data["conversation_id"],
            sender=MessageSender(data.get("sender", "user")),
            content=data.get("content", ""),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "sender": self.sender.value,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class Conversation:
    """
    Conversation entity.
    Represents an AI consultation session.
    """
    id: UUID
    patient_id: UUID
    title: Optional[str] = None
    started_at: Optional[datetime] = None
    
    # Related data
    messages: List[Message] = field(default_factory=list)
    
    @property
    def date_display(self) -> str:
        """Format date for display (relative)."""
        if not self.started_at:
            return ""
        
        now = datetime.now(self.started_at.tzinfo) if self.started_at.tzinfo else datetime.utcnow()
        diff = now.date() - self.started_at.date()
        
        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return self.started_at.strftime("%Y-%m-%d")
    
    @property
    def snippet(self) -> str:
        """Get a snippet from the first message."""
        if self.messages:
            content = self.messages[0].content
            return content[:100] + "..." if len(content) > 100 else content
        return ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Create a Conversation from a dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            patient_id=UUID(data["patient_id"]) if isinstance(data["patient_id"], str) else data["patient_id"],
            title=data.get("title"),
            started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")) if data.get("started_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "title": self.title,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


@dataclass
class ConversationCreate:
    """
    Data model for creating a new conversation.
    """
    patient_id: UUID
    title: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "patient_id": str(self.patient_id),
            "title": self.title,
            "started_at": datetime.utcnow().isoformat()
        }


@dataclass
class MessageCreate:
    """
    Data model for creating a new message.
    """
    conversation_id: UUID
    sender: MessageSender
    content: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "conversation_id": str(self.conversation_id),
            "sender": self.sender.value,
            "content": self.content,
            "created_at": datetime.utcnow().isoformat()
        }