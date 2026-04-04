"""
Conversation Memory Manager
Stores and retrieves chat history for context-aware responses
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog

from config import settings
from .firestore_client import FirestoreClient, get_firestore_client

logger = structlog.get_logger()


class ConversationMemory:
    """
    Manages conversation history for multi-turn interactions.
    Stores messages in Firestore per user with session grouping.
    """
    
    def __init__(self, firestore_client: Optional[FirestoreClient] = None):
        self.db = firestore_client or get_firestore_client()
        self.collection = settings.firestore_collection_conversations
    
    async def create_session(self, user_id: str, metadata: Optional[dict] = None) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_id: User's unique identifier
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        session_id = str(uuid4())
        
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "messages": [],
            "metadata": metadata or {},
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        await self.db.set_document(
            collection=self.collection,
            document_id=f"{user_id}_{session_id}",
            data=session_data,
            merge=False
        )
        
        logger.info("Created conversation session", user_id=user_id, session_id=session_id)
        return session_id
    
    async def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Add a message to the conversation.
        
        Args:
            user_id: User's unique identifier
            session_id: Conversation session ID
            role: "user", "assistant", or "system"
            content: Message content
            metadata: Optional message metadata (tool calls, etc.)
            
        Returns:
            The added message
        """
        message = {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        doc_id = f"{user_id}_{session_id}"
        session = await self.db.get_document(self.collection, doc_id)
        
        if not session:
            # Auto-create session if it doesn't exist
            await self.create_session(user_id)
            session = {"messages": []}
        
        messages = session.get("messages", [])
        messages.append(message)
        
        await self.db.set_document(
            collection=self.collection,
            document_id=doc_id,
            data={
                "messages": messages,
                "last_activity": datetime.utcnow().isoformat()
            },
            merge=True
        )
        
        logger.debug("Added message to conversation", 
                     user_id=user_id, session_id=session_id, role=role)
        return message
    
    async def get_recent_messages(
        self,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Get recent messages from a conversation.
        
        Args:
            user_id: User's unique identifier
            session_id: Conversation session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages (most recent last)
        """
        doc_id = f"{user_id}_{session_id}"
        session = await self.db.get_document(self.collection, doc_id)
        
        if not session:
            return []
        
        messages = session.get("messages", [])
        return messages[-limit:] if len(messages) > limit else messages
    
    async def get_context_window(
        self,
        user_id: str,
        session_id: str,
        max_messages: int = 10
    ) -> list[dict]:
        """
        Get messages formatted for LLM context.
        
        Returns messages in the format expected by most LLMs:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        messages = await self.get_recent_messages(user_id, session_id, limit=max_messages)
        
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> list[dict]:
        """Get user's recent conversation sessions."""
        sessions = await self.db.query_documents(
            collection=self.collection,
            filters=[("user_id", "==", user_id)],
            order_by="last_activity",
            order_direction="DESCENDING",
            limit=limit
        )
        
        return [
            {
                "session_id": s.get("session_id"),
                "started_at": s.get("started_at"),
                "last_activity": s.get("last_activity"),
                "message_count": len(s.get("messages", []))
            }
            for s in sessions
        ]
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Search through conversation history.
        Note: For more advanced search, consider Vertex AI Vector Search.
        
        Args:
            user_id: User's unique identifier
            query: Search query
            limit: Maximum results
            
        Returns:
            Matching messages with context
        """
        sessions = await self.db.query_documents(
            collection=self.collection,
            filters=[("user_id", "==", user_id)],
            limit=50  # Search through recent sessions
        )
        
        results = []
        query_lower = query.lower()
        
        for session in sessions:
            for msg in session.get("messages", []):
                if query_lower in msg.get("content", "").lower():
                    results.append({
                        "session_id": session.get("session_id"),
                        "message": msg,
                        "timestamp": msg.get("timestamp")
                    })
                    
                    if len(results) >= limit:
                        return results
        
        return results
    
    async def clear_session(self, user_id: str, session_id: str) -> bool:
        """Clear all messages from a session."""
        doc_id = f"{user_id}_{session_id}"
        
        await self.db.set_document(
            collection=self.collection,
            document_id=doc_id,
            data={"messages": []},
            merge=True
        )
        
        logger.info("Cleared conversation session", user_id=user_id, session_id=session_id)
        return True
