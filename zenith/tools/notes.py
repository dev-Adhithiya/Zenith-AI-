"""
Notes Tools for Zenith AI
Provides note-taking and knowledge base capabilities using Firestore with Google Drive sync
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
import structlog
import json
import re

from config import settings
from memory.firestore_client import FirestoreClient, get_firestore_client
from auth.google_oauth import GoogleOAuthManager, get_oauth_manager

logger = structlog.get_logger()


class NotesTools:
    """
    Notes management system using Firestore with Google Drive sync.
    Handles note creation, retrieval, and synchronization with Google Drive.
    """
    
    def __init__(
        self,
        firestore_client: Optional[FirestoreClient] = None,
        oauth_manager: Optional[GoogleOAuthManager] = None
    ):
        self.db = firestore_client or get_firestore_client()
        self.oauth = oauth_manager or get_oauth_manager()
        self.collection = settings.firestore_collection_notes
        self.drive_folder_name = "Zenith Notes"  # Folder in Google Drive
    
    def _get_drive_service(self, credentials_dict: dict):
        """Get Google Drive API service."""
        return self.oauth.build_service("drive", "v3", credentials_dict)

    def _normalize_text(self, value: str) -> str:
        """Normalize text for lenient matching."""
        if not value:
            return ""
        cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
        return " ".join(cleaned.split())
    
    async def _ensure_notes_folder(self, credentials: dict) -> str:
        """
        Ensure a 'Zenith Notes' folder exists in Google Drive.
        Returns the folder ID.
        """
        service = self._get_drive_service(credentials)
        
        try:
            # Search for existing folder
            results = service.files().list(
                q=f"name='{self.drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            files = results.get("files", [])
            if files:
                folder_id = files[0]["id"]
                logger.info("Found existing Zenith Notes folder", folder_id=folder_id)
                return folder_id
            
            # Create folder if it doesn't exist
            file_metadata = {
                "name": self.drive_folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = service.files().create(body=file_metadata, fields="id").execute()
            folder_id = folder.get("id")
            logger.info("Created Zenith Notes folder", folder_id=folder_id)
            return folder_id
            
        except Exception as e:
            logger.error("Failed to ensure notes folder", error=str(e))
            return None
    
    async def _sync_note_to_drive(
        self,
        note_id: str,
        title: str,
        content: str,
        credentials: dict,
        drive_file_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Sync a note to Google Drive.
        Returns the Drive file ID.
        """
        service = self._get_drive_service(credentials)
        folder_id = await self._ensure_notes_folder(credentials)
        
        if not folder_id:
            logger.warning("Could not sync note to Drive - folder creation failed", note_id=note_id)
            return None
        
        try:
            # Prepare note content as text file
            file_metadata = {
                "name": f"{title}.txt",
                "mimeType": "text/plain",
                "parents": [folder_id]
            }
            
            # Add metadata as comment at the top
            full_content = f"""[Zenith AI Note]
ID: {note_id}
Synced: {datetime.utcnow().isoformat()}

---

{content}"""
            
            if drive_file_id:
                # Update existing file
                result = service.files().update(
                    fileId=drive_file_id,
                    body=file_metadata,
                    media_body=full_content.encode(),
                    fields="id"
                ).execute()
                logger.info("Updated note in Google Drive", note_id=note_id, drive_file_id=drive_file_id)
            else:
                # Create new file
                result = service.files().create(
                    body=file_metadata,
                    media_body=full_content.encode(),
                    fields="id"
                ).execute()
                drive_file_id = result.get("id")
                logger.info("Synced note to Google Drive", note_id=note_id, drive_file_id=drive_file_id)
            
            return drive_file_id
            
        except Exception as e:
            logger.error("Failed to sync note to Drive", note_id=note_id, error=str(e))
            return None
    
    async def save_note(
        self,
        user_id: str,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
        credentials: Optional[dict] = None
    ) -> dict:
        """
        Save a new note and sync to Google Drive if credentials provided.
        
        Args:
            user_id: User's unique identifier
            title: Note title
            content: Note content (supports markdown)
            tags: Optional list of tags for categorization
            source: Optional source (e.g., "meeting", "email", "manual")
            metadata: Optional additional metadata
            credentials: Optional OAuth credentials for Google Drive sync
            
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
            "title_lower": title.lower(),
            "sync_status": "pending"
        }
        
        await self.db.set_document(
            collection=self.collection,
            document_id=note_id,
            data=note_data,
            merge=False
        )
        
        logger.info("Saved note", note_id=note_id, user_id=user_id, title=title)
        
        # Attempt to sync to Google Drive
        if credentials:
            drive_file_id = await self._sync_note_to_drive(
                note_id=note_id,
                title=title,
                content=content,
                credentials=credentials
            )
            
            if drive_file_id:
                # Update sync status
                await self.db.set_document(
                    collection=self.collection,
                    document_id=note_id,
                    data={
                        "sync_status": "synced",
                        "drive_file_id": drive_file_id,
                        "last_sync": datetime.utcnow().isoformat()
                    },
                    merge=True
                )
        
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
        tags: Optional[list[str]] = None,
        credentials: Optional[dict] = None
    ) -> Optional[dict]:
        """Update an existing note and sync to Google Drive if changed."""
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
        
        # Sync updated note to Google Drive
        if credentials and (content is not None or title is not None):
            drive_file_id = existing.get("drive_file_id")
            updated_title = title or existing.get("title")
            updated_content = content or existing.get("content")
            
            new_drive_id = await self._sync_note_to_drive(
                note_id=note_id,
                title=updated_title,
                content=updated_content,
                credentials=credentials,
                drive_file_id=drive_file_id
            )
            
            if new_drive_id:
                await self.db.set_document(
                    collection=self.collection,
                    document_id=note_id,
                    data={
                        "sync_status": "synced",
                        "drive_file_id": new_drive_id,
                        "last_sync": datetime.utcnow().isoformat()
                    },
                    merge=True
                )
        
        return await self.get_note(user_id, note_id)
    
    async def delete_note(
        self,
        user_id: str,
        note_id: str,
        credentials: Optional[dict] = None
    ) -> bool:
        """Delete a note from Firestore and Google Drive."""
        # Verify ownership
        existing = await self.db.get_document(self.collection, note_id)
        if not existing or existing.get("user_id") != user_id:
            return False
        
        # Delete from Google Drive if synced
        drive_file_id = existing.get("drive_file_id")
        if drive_file_id and credentials:
            try:
                service = self._get_drive_service(credentials)
                service.files().delete(fileId=drive_file_id).execute()
                logger.info("Deleted note from Google Drive", drive_file_id=drive_file_id)
            except Exception as e:
                logger.warning("Failed to delete from Drive, continuing with local delete", 
                              error=str(e), note_id=note_id)
        
        # Delete from Firestore
        await self.db.delete_document(self.collection, note_id)
        logger.info("Deleted note", note_id=note_id, user_id=user_id)
        return True

    async def delete_note_by_query(
        self,
        user_id: str,
        query: str,
        delete_all_matches: bool = False,
        credentials: Optional[dict] = None
    ) -> dict:
        """
        Delete note(s) by semantic query rather than note ID.

        This is intended for natural-language commands where users reference
        a note by title/topic instead of internal note_id.
        """
        if not query or not query.strip():
            raise ValueError("Query is required to delete notes")

        candidates = await self.query_knowledge_base(
            user_id=user_id,
            query=query,
            limit=10
        )

        if not candidates:
            raise ValueError(f"No notes found matching '{query}'")

        normalized_query = self._normalize_text(query)
        if normalized_query:
            title_matches = [
                note for note in candidates
                if normalized_query in self._normalize_text(note.get("title", ""))
            ]
            if title_matches:
                title_match_ids = {note.get("note_id") for note in title_matches}
                non_title_matches = [
                    note for note in candidates
                    if note.get("note_id") not in title_match_ids
                ]
                candidates = title_matches + non_title_matches

        if delete_all_matches:
            deleted_notes = []
            for note in candidates:
                note_id = note.get("note_id")
                if not note_id:
                    continue
                deleted = await self.delete_note(
                    user_id=user_id,
                    note_id=note_id,
                    credentials=credentials
                )
                if deleted:
                    deleted_notes.append({
                        "note_id": note_id,
                        "title": note.get("title")
                    })

            return {
                "query": query,
                "deleted_count": len(deleted_notes),
                "deleted_notes": deleted_notes
            }

        # Delete the highest-relevance result.
        best_match = candidates[0]
        deleted = await self.delete_note(
            user_id=user_id,
            note_id=best_match.get("note_id"),
            credentials=credentials
        )

        if not deleted:
            raise ValueError(f"Failed to delete note matching '{query}'")

        return {
            "query": query,
            "deleted_count": 1,
            "deleted_notes": [{
                "note_id": best_match.get("note_id"),
                "title": best_match.get("title")
            }]
        }
    
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
    
    async def import_notes_from_drive(
        self,
        user_id: str,
        credentials: dict
    ) -> dict:
        """
        Import all notes from Google Drive's Zenith Notes folder.
        Creates local copies in Firestore.
        
        Returns:
            Dict with imported_count, skipped_count, errors
        """
        service = self._get_drive_service(credentials)
        folder_id = await self._ensure_notes_folder(credentials)
        
        if not folder_id:
            logger.error("Could not import notes - folder not found")
            return {"imported_count": 0, "skipped_count": 0, "errors": []}
        
        imported = 0
        skipped = 0
        errors = []
        
        try:
            # Get all files in Zenith Notes folder
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=100,
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            files = results.get("files", [])
            
            for file in files:
                try:
                    file_id = file.get("id")
                    file_name = file.get("name", "Untitled")
                    
                    # Download file content
                    request = service.files().get_media(fileId=file_id)
                    file_content = request.execute()
                    
                    # Parse content
                    if isinstance(file_content, bytes):
                        content_str = file_content.decode('utf-8')
                    else:
                        content_str = file_content
                    
                    # Extract note ID if it exists in the metadata header
                    lines = content_str.split("\n")
                    note_id = None
                    content_start = 0
                    
                    for i, line in enumerate(lines):
                        if line.startswith("ID: "):
                            note_id = line.replace("ID: ", "").strip()
                        elif line.startswith("---"):
                            content_start = i + 1
                            break
                    
                    if not note_id:
                        note_id = str(uuid4())
                    
                    # Extract actual content
                    actual_content = "\n".join(lines[content_start:]).strip()
                    title = file_name.replace(".txt", "")
                    
                    # Check if note already exists to avoid duplicates
                    existing = await self.db.get_document(self.collection, note_id)
                    
                    if existing and existing.get("user_id") == user_id:
                        skipped += 1
                        logger.info("Note already exists, skipping", note_id=note_id)
                        continue
                    
                    # Save to Firestore
                    note_data = {
                        "note_id": note_id,
                        "user_id": user_id,
                        "title": title,
                        "content": actual_content,
                        "tags": ["imported_from_drive"],
                        "source": "drive",
                        "drive_file_id": file_id,
                        "metadata": {"original_file_id": file_id},
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "content_lower": actual_content.lower(),
                        "title_lower": title.lower(),
                        "sync_status": "synced"
                    }
                    
                    await self.db.set_document(
                        collection=self.collection,
                        document_id=note_id,
                        data=note_data,
                        merge=False
                    )
                    
                    imported += 1
                    logger.info("Imported note from Drive", note_id=note_id, file_id=file_id)
                    
                except Exception as e:
                    error_msg = f"Failed to import file {file.get('name')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error("Failed to import from Drive", file_id=file.get("id"), error=str(e))
            
            logger.info("Completed Drive import", imported=imported, skipped=skipped, errors=len(errors))
            
        except Exception as e:
            logger.error("Failed to list Drive files", error=str(e))
            errors.append(f"Failed to access Drive folder: {str(e)}")
        
        return {
            "imported_count": imported,
            "skipped_count": skipped,
            "errors": errors
        }
    
    async def get_sync_status(
        self,
        user_id: str,
        note_id: str
    ) -> Optional[dict]:
        """Get sync status of a note with Google Drive."""
        note = await self.db.get_document(self.collection, note_id)
        
        if not note or note.get("user_id") != user_id:
            return None
        
        return {
            "note_id": note_id,
            "sync_status": note.get("sync_status", "not_synced"),
            "drive_file_id": note.get("drive_file_id"),
            "last_sync": note.get("last_sync")
        }
    
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
