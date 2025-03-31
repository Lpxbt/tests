"""
LLM Session Manager for maintaining conversation context.
"""
import time
import json
import uuid
from typing import List, Dict, Any, Optional, Union

from ..redis_connection import get_redis_client

class Message:
    """
    Message class for storing conversation messages.
    """
    
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[float] = None,
        message_id: Optional[str] = None
    ):
        """
        Initialize a message.
        
        Args:
            role: Message role (e.g., "user", "assistant", "system")
            content: Message content
            timestamp: Message timestamp
            message_id: Message ID
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
        self.message_id = message_id or str(uuid.uuid4())
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        Create message from dictionary.
        
        Args:
            data: Dictionary representation of the message
            
        Returns:
            Message instance
        """
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data["message_id"]
        )
        
    def __repr__(self) -> str:
        return f"Message(role={self.role}, content={self.content[:50]}..., timestamp={self.timestamp})"


class Session:
    """
    Session class for storing conversation sessions.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        messages: Optional[List[Message]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None
    ):
        """
        Initialize a session.
        
        Args:
            session_id: Session ID
            messages: List of messages
            metadata: Session metadata
            created_at: Session creation timestamp
            updated_at: Session update timestamp
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.messages = messages or []
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        
    def add_message(self, message: Message) -> None:
        """
        Add a message to the session.
        
        Args:
            message: Message to add
        """
        self.messages.append(message)
        self.updated_at = time.time()
        
    def add_user_message(self, content: str) -> Message:
        """
        Add a user message to the session.
        
        Args:
            content: Message content
            
        Returns:
            Added message
        """
        message = Message(role="user", content=content)
        self.add_message(message)
        return message
        
    def add_assistant_message(self, content: str) -> Message:
        """
        Add an assistant message to the session.
        
        Args:
            content: Message content
            
        Returns:
            Added message
        """
        message = Message(role="assistant", content=content)
        self.add_message(message)
        return message
        
    def add_system_message(self, content: str) -> Message:
        """
        Add a system message to the session.
        
        Args:
            content: Message content
            
        Returns:
            Added message
        """
        message = Message(role="system", content=content)
        self.add_message(message)
        return message
        
    def get_messages(self, limit: Optional[int] = None, roles: Optional[List[str]] = None) -> List[Message]:
        """
        Get messages from the session.
        
        Args:
            limit: Maximum number of messages to return
            roles: Filter messages by roles
            
        Returns:
            List of messages
        """
        messages = self.messages
        
        # Filter by roles
        if roles:
            messages = [m for m in messages if m.role in roles]
            
        # Apply limit
        if limit is not None:
            messages = messages[-limit:]
            
        return messages
        
    def get_message_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get message history in a format suitable for LLM context.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        messages = self.get_messages(limit=limit)
        return [{"role": m.role, "content": m.content} for m in messages]
        
    def clear_messages(self) -> None:
        """Clear all messages from the session."""
        self.messages = []
        self.updated_at = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary.
        
        Returns:
            Dictionary representation of the session
        """
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """
        Create session from dictionary.
        
        Args:
            data: Dictionary representation of the session
            
        Returns:
            Session instance
        """
        return cls(
            session_id=data["session_id"],
            messages=[Message.from_dict(m) for m in data["messages"]],
            metadata=data["metadata"],
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
        
    def __repr__(self) -> str:
        return f"Session(id={self.session_id}, messages={len(self.messages)}, updated={self.updated_at})"


class SessionManager:
    """
    Session manager for LLM conversations.
    """
    
    def __init__(
        self,
        prefix: str = "session:",
        ttl: Optional[int] = None  # Time-to-live in seconds
    ):
        """
        Initialize the session manager.
        
        Args:
            prefix: Prefix for session keys
            ttl: Time-to-live for sessions in seconds (None for no expiration)
        """
        self.prefix = prefix
        self.ttl = ttl
        self.redis_client = get_redis_client()
        
    def _get_key(self, session_id: str) -> str:
        """
        Get Redis key for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Redis key
        """
        return f"{self.prefix}{session_id}"
        
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Create a new session.
        
        Args:
            metadata: Session metadata
            
        Returns:
            New session
        """
        session = Session(metadata=metadata)
        
        # Save session
        self.save_session(session)
        
        return session
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session or None if not found
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot get session.")
            return None
            
        # Get session data
        key = self._get_key(session_id)
        data = self.redis_client.get(key)
        
        if data is None:
            return None
            
        # Parse session data
        try:
            session_dict = json.loads(data)
            return Session.from_dict(session_dict)
        except Exception as e:
            print(f"Error parsing session data: {e}")
            return None
            
    def save_session(self, session: Session) -> bool:
        """
        Save a session.
        
        Args:
            session: Session to save
            
        Returns:
            True if successful, False otherwise
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot save session.")
            return False
            
        # Convert session to JSON
        session_json = json.dumps(session.to_dict())
        
        # Save session
        key = self._get_key(session.session_id)
        
        if self.ttl is not None:
            return bool(self.redis_client.setex(key, self.ttl, session_json))
        else:
            return bool(self.redis_client.set(key, session_json))
            
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot delete session.")
            return False
            
        # Delete session
        key = self._get_key(session_id)
        return bool(self.redis_client.delete(key))
        
    def list_sessions(self) -> List[str]:
        """
        List all session IDs.
        
        Returns:
            List of session IDs
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot list sessions.")
            return []
            
        # Get all session keys
        keys = self.redis_client.keys(f"{self.prefix}*")
        
        # Extract session IDs
        return [key.decode().replace(self.prefix, "") for key in keys]
        
    def add_message(self, session_id: str, message: Message) -> bool:
        """
        Add a message to a session.
        
        Args:
            session_id: Session ID
            message: Message to add
            
        Returns:
            True if successful, False otherwise
        """
        # Get session
        session = self.get_session(session_id)
        
        if session is None:
            return False
            
        # Add message
        session.add_message(message)
        
        # Save session
        return self.save_session(session)
        
    def add_user_message(self, session_id: str, content: str) -> Optional[Message]:
        """
        Add a user message to a session.
        
        Args:
            session_id: Session ID
            content: Message content
            
        Returns:
            Added message or None if failed
        """
        # Get session
        session = self.get_session(session_id)
        
        if session is None:
            return None
            
        # Add message
        message = session.add_user_message(content)
        
        # Save session
        if self.save_session(session):
            return message
        else:
            return None
            
    def add_assistant_message(self, session_id: str, content: str) -> Optional[Message]:
        """
        Add an assistant message to a session.
        
        Args:
            session_id: Session ID
            content: Message content
            
        Returns:
            Added message or None if failed
        """
        # Get session
        session = self.get_session(session_id)
        
        if session is None:
            return None
            
        # Add message
        message = session.add_assistant_message(content)
        
        # Save session
        if self.save_session(session):
            return message
        else:
            return None
            
    def get_message_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get message history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        # Get session
        session = self.get_session(session_id)
        
        if session is None:
            return []
            
        # Get message history
        return session.get_message_history(limit=limit)
