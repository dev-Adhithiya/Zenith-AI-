"""
User Store
Manages user profiles and Google OAuth credentials in Firestore
"""
from copy import deepcopy
from datetime import datetime
from time import monotonic
from typing import Optional
from uuid import uuid4

import structlog

from config import settings
from .firestore_client import FirestoreClient, get_firestore_client

logger = structlog.get_logger()

# Short TTL read-through cache for get_user_by_id to cut repeat Firestore reads per request burst.
_USER_ROW_TTL_SEC = 45.0
_user_row_cache: dict[str, tuple[float, dict]] = {}


def _invalidate_user_cache(user_id: str) -> None:
    _user_row_cache.pop(user_id, None)


class UserStore:
    """
    Manages user data and OAuth credentials.
    Multi-tenant user management for Zenith AI.
    """
    
    def __init__(self, firestore_client: Optional[FirestoreClient] = None):
        self.db = firestore_client or get_firestore_client()
        self.collection = settings.firestore_collection_users
    
    async def create_user(
        self,
        email: str,
        google_user_info: dict,
        credentials: dict
    ) -> dict:
        """
        Create a new user from Google OAuth data.
        
        Args:
            email: User's email address
            google_user_info: User info from Google OAuth
            credentials: OAuth credentials dictionary
            
        Returns:
            Created user document
        """
        user_id = str(uuid4())
        
        user_data = {
            "user_id": user_id,
            "email": email,
            "name": google_user_info.get("name", ""),
            "picture": google_user_info.get("picture", ""),
            "google_id": google_user_info.get("id"),
            "credentials": credentials,
            "settings": {
                "timezone": "Etc/UTC",
                "language": "en",
                "notifications_enabled": True
            },
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat()
        }
        
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data=user_data,
            merge=False
        )
        
        logger.info("Created new user", user_id=user_id, email=email)
        _invalidate_user_cache(user_id)
        return user_data
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by their unique ID."""
        now = monotonic()
        cached = _user_row_cache.get(user_id)
        if cached and (now - cached[0]) < _USER_ROW_TTL_SEC:
            return deepcopy(cached[1])
        user = await self.db.get_document(self.collection, user_id)
        if user:
            _user_row_cache[user_id] = (now, user)
            return deepcopy(user)
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email address."""
        users = await self.db.query_documents(
            collection=self.collection,
            filters=[("email", "==", email)],
            limit=1
        )
        return users[0] if users else None
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[dict]:
        """Get user by Google account ID."""
        users = await self.db.query_documents(
            collection=self.collection,
            filters=[("google_id", "==", google_id)],
            limit=1
        )
        return users[0] if users else None
    
    async def update_user(
        self,
        user_id: str,
        updates: dict
    ) -> dict:
        """Update user data."""
        # Don't allow overwriting critical fields
        protected_fields = ["user_id", "email", "google_id", "created_at"]
        for field in protected_fields:
            updates.pop(field, None)
        
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data=updates,
            merge=True
        )
        
        logger.info("Updated user", user_id=user_id, fields=list(updates.keys()))
        _invalidate_user_cache(user_id)
        return await self.get_user_by_id(user_id)
    
    async def update_credentials(
        self,
        user_id: str,
        credentials: dict
    ) -> None:
        """Update user's OAuth credentials."""
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data={
                "credentials": credentials,
                "credentials_updated_at": datetime.utcnow().isoformat()
            },
            merge=True
        )
        logger.debug("Updated user credentials", user_id=user_id)
        _invalidate_user_cache(user_id)
    
    async def get_credentials(self, user_id: str) -> Optional[dict]:
        """Get user's OAuth credentials."""
        user = await self.get_user_by_id(user_id)
        return user.get("credentials") if user else None
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data={"last_login": datetime.utcnow().isoformat()},
            merge=True
        )
        _invalidate_user_cache(user_id)
    
    async def update_settings(
        self,
        user_id: str,
        settings_updates: dict
    ) -> dict:
        """Update user settings."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        current_settings = user.get("settings", {})
        current_settings.update(settings_updates)
        
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data={"settings": current_settings},
            merge=True
        )
        _invalidate_user_cache(user_id)
        return current_settings
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user and their data.
        Warning: This is destructive and should be used carefully.
        """
        await self.db.delete_document(self.collection, user_id)
        logger.warning("Deleted user", user_id=user_id)
        _invalidate_user_cache(user_id)
        return True
    
    async def get_or_create_user(
        self,
        email: str,
        google_user_info: dict,
        credentials: dict
    ) -> tuple[dict, bool]:
        """
        Get existing user or create new one.
        
        Returns:
            Tuple of (user_data, is_new_user)
        """
        # Try to find by Google ID first
        google_id = google_user_info.get("id")
        existing_user = await self.get_user_by_google_id(google_id)
        
        if existing_user:
            # Update credentials and last login
            await self.update_credentials(existing_user["user_id"], credentials)
            await self.update_last_login(existing_user["user_id"])
            return existing_user, False
        
        # Try by email
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            # Link Google ID and update credentials
            await self.update_user(existing_user["user_id"], {
                "google_id": google_id,
                "credentials": credentials
            })
            await self.update_last_login(existing_user["user_id"])
            return existing_user, False
        
        # Create new user
        new_user = await self.create_user(email, google_user_info, credentials)
        return new_user, True
