"""
Notes Tools for Zenith AI
Provides note-taking and knowledge base capabilities using Firestore
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
import structlog

from config import settings
from memory.firestore_client import FirestoreClient, get_firestore_client

logger = structlog.get_logger()


class NotesTools:
    """
    Notes management system using Firestore.
    Handles note creation, retrieval, and simple knowledge base queries.
    """
    
    def __init__(self, firestore_client: Optional[FirestoreClient] = None):
        self.db = firestore_client or get_firestore_client()
        self.collection = settings.firestore_collection_notes
    
    async def save_note(
        self,
        user_id: str,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Save a new note.
        
        Args:
            user_id: User's unique identifier
            title: Note title
            content: Note content (supports markdown)
            tags: Optional list of tags for categorization
            source: Optional source (e.g., "meeting", "email", "manual")
            metadata: Optional additional metadata
            
        Returns:
            Created note document
        """
        note_id = str(uuid4())
        
        note_data = {
            "note_id": note_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source or "manual",
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # Store lowercase content for simple text search
            "content_lower": content.lower(),
            "title_lower": title.lower()
        }
        
        await self.db.set_document(
            collection=self.collection,
            document_id=note_id,
            data=note_data,
            merge=False
        )
        
        logger.info("Saved note", note_id=note_id, user_id=user_id, title=title)
        
        # Return without internal fields
        return {
            "note_id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source or "manual",
            "created_at": note_data["created_at"]
        }
    
    async def get_note(
        self,
        user_id: str,
        note_id: str
    ) -> Optional[dict]:
        """Get a specific note by ID."""
        note = await self.db.get_document(self.collection, note_id)
        
        if note and note.get("user_id") == user_id:
            return self._format_note(note)
        return None
    
    async def list_notes(
        self,
        user_id: str,
        limit: int = 20,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None
    ) -> list[dict]:
        """
        List user's notes with optional filtering.
        
        Args:
            user_id: User's unique identifier
            limit: Maximum number of notes to return
            tags: Filter by tags (any match)
            source: Filter by source
            
        Returns:
            List of notes
        """
        filters = [("user_id", "==", user_id)]
        
        if source:
            filters.append(("source", "==", source))
        
        notes = await self.db.query_documents(
            collection=self.collection,
            filters=filters,
            order_by="created_at",
            order_direction="DESCENDING",
            limit=limit
        )
        
        # Filter by tags if specified (Firestore doesn't support array-contains-any with other filters well)
        if tags:
            notes = [
                note for note in notes
                if any(tag in note.get("tags", []) for tag in tags)
            ]
        
        return [self._format_note(note) for note in notes]
    
    async def update_note(
        self,
        user_id: str,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Optional[dict]:
        """Update an existing note."""
        # Verify ownership
        existing = await self.db.get_document(self.collection, note_id)
        if not existing or existing.get("user_id") != user_id:
            return None
        
        updates = {"updated_at": datetime.utcnow().isoformat()}
        
        if title is not None:
            updates["title"] = title
            updates["title_lower"] = title.lower()
        
        if content is not None:
            updates["content"] = content
            updates["content_lower"] = content.lower()
        
        if tags is not None:
            updates["tags"] = tags
        
        await self.db.set_document(
            collection=self.collection,
            document_id=note_id,
            data=updates,
            merge=True
        )
        
        logger.info("Updated note", note_id=note_id, user_id=user_id)
        
        return await self.get_note(user_id, note_id)
    
    async def delete_note(
        self,
        user_id: str,
        note_id: str
    ) -> bool:
        """Delete a note."""
        # Verify ownership
        existing = await self.db.get_document(self.collection, note_id)
        if not existing or existing.get("user_id") != user_id:
            return False
        
        await self.db.delete_document(self.collection, note_id)
        logger.info("Deleted note", note_id=note_id, user_id=user_id)
        return True
    
    async def query_knowledge_base(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Search notes by content (simple text search).
        
        For production use with large datasets, consider:
        - Vertex AI Vector Search for semantic search
        - Algolia or Elasticsearch for full-text search
        
        Args:
            user_id: User's unique identifier
            query: Search query
            limit: Maximum results
            
        Returns:
            Matching notes with relevance
        """
        # Get all user's notes (in production, use proper search index)
        notes = await self.db.query_documents(
            collection=self.collection,
            filters=[("user_id", "==", user_id)],
            limit=100  # Fetch more for client-side filtering
        )
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Score and rank results
        scored_results = []
        
        for note in notes:
            score = 0
            title_lower = note.get("title_lower", "")
            content_lower = note.get("content_lower", "")
            
            # Exact phrase match in title (highest priority)
            if query_lower in title_lower:
                score += 10
            
            # Exact phrase match in content
            if query_lower in content_lower:
                score += 5
            
            # Individual term matches
            for term in query_terms:
                if term in title_lower:
                    score += 3
                if term in content_lower:
                    score += 1
            
            # Tag matches
            for tag in note.get("tags", []):
                if query_lower in tag.lower():
                    score += 2
            
            if score > 0:
                scored_results.append((score, note))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results
        results = [
            {
                **self._format_note(note),
                "relevance_score": score
            }
            for score, note in scored_results[:limit]
        ]
        
        logger.info("Queried knowledge base", 
                   user_id=user_id, 
                   query=query,
                   results_count=len(results))
        
        return results
    
    async def get_notes_by_tag(
        self,
        user_id: str,
        tag: str,
        limit: int = 20
    ) -> list[dict]:
        """Get notes with a specific tag."""
        notes = await self.db.query_documents(
            collection=self.collection,
            filters=[
                ("user_id", "==", user_id),
                ("tags", "array_contains", tag)
            ],
            order_by="created_at",
            order_direction="DESCENDING",
            limit=limit
        )
        
        return [self._format_note(note) for note in notes]
    
    async def get_all_tags(
        self,
        user_id: str
    ) -> list[str]:
        """Get all unique tags used by the user."""
        notes = await self.db.query_documents(
            collection=self.collection,
            filters=[("user_id", "==", user_id)],
            limit=500
        )
        
        tags = set()
        for note in notes:
            tags.update(note.get("tags", []))
        
        return sorted(list(tags))
    
    async def save_meeting_notes(
        self,
        user_id: str,
        meeting_title: str,
        meeting_date: datetime,
        summary: str,
        action_items: list[str],
        key_decisions: list[str],
        attendees: Optional[list[str]] = None,
        transcript: Optional[str] = None
    ) -> dict:
        """
        Save structured meeting notes.
        
        Args:
            user_id: User's unique identifier
            meeting_title: Title of the meeting
            meeting_date: When the meeting occurred
            summary: Meeting summary
            action_items: List of action items
            key_decisions: Key decisions made
            attendees: List of attendees
            transcript: Full transcript (if available)
            
        Returns:
            Created note
        """
        # Format the content
        content_parts = [f"# {meeting_title}\n"]
        content_parts.append(f"**Date:** {meeting_date.strftime('%Y-%m-%d %H:%M')}\n")
        
        if attendees:
            content_parts.append(f"**Attendees:** {', '.join(attendees)}\n")
        
        content_parts.append("\n## Summary\n")
        content_parts.append(summary)
        
        if action_items:
            content_parts.append("\n\n## Action Items\n")
            for item in action_items:
                content_parts.append(f"- [ ] {item}\n")
        
        if key_decisions:
            content_parts.append("\n## Key Decisions\n")
            for decision in key_decisions:
                content_parts.append(f"- {decision}\n")
        
        if transcript:
            content_parts.append("\n## Full Transcript\n")
            content_parts.append(f"```\n{transcript}\n```")
        
        content = "".join(content_parts)
        
        return await self.save_note(
            user_id=user_id,
            title=f"Meeting Notes: {meeting_title}",
            content=content,
            tags=["meeting", "notes"],
            source="meeting",
            metadata={
                "meeting_date": meeting_date.isoformat(),
                "attendees": attendees or [],
                "action_items_count": len(action_items),
                "has_transcript": transcript is not None
            }
        )
    
    def _format_note(self, note: dict) -> dict:
        """Format a note for API response."""
        return {
            "note_id": note.get("note_id") or note.get("id"),
            "title": note.get("title"),
            "content": note.get("content"),
            "tags": note.get("tags", []),
            "source": note.get("source"),
            "metadata": note.get("metadata", {}),
            "created_at": note.get("created_at"),
            "updated_at": note.get("updated_at")
        }
