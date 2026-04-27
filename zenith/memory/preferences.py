"""
User Preferences Store for Zenith AI
Manages user behavioral patterns and preference data in Firestore.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Optional

import structlog

from .firestore_client import FirestoreClient, get_firestore_client

logger = structlog.get_logger()

# Firestore collection name
PREFERENCES_COLLECTION = "user_preferences"

# Default preference schema
DEFAULT_PREFERENCES: dict[str, Any] = {
    "preferred_meeting_times": [],      # e.g. ["09:00-12:00", "14:00-16:00"]
    "frequent_contacts": [],             # e.g. ["john@example.com"]
    "email_tone": "professional",        # "formal" | "casual" | "professional"
    "custom_rules": [],                  # Array of user-defined constraints/preferences
    "working_hours": {
        "start": "09:00",
        "end": "17:00",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    },
    "timezone": "Etc/UTC",
    "notification_preferences": {
        "daily_briefing": True,
        "email_alerts": True,
        "task_reminders": True,
    },
    "memory_profile": {
        "likes": [],
        "dislikes": [],
        "avoid": [],
        "preferences": [],
        "notes": [],
    },
}


class PreferencesStore:
    """
    Manages user preferences and behavioral patterns in Firestore.

    Preferences are stored in a dedicated top-level collection
    `user_preferences` with the user_id as the document ID.
    """

    def __init__(self, firestore_client: Optional[FirestoreClient] = None):
        self.db = firestore_client or get_firestore_client()
        self.collection = PREFERENCES_COLLECTION

    # ------------------------------------------------------------------
    # Normalization / prompt helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _unique_text_list(values: list[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result

    @classmethod
    def _normalize_memory_profile(cls, profile: Optional[dict]) -> dict[str, list[str]]:
        base = dict(DEFAULT_PREFERENCES["memory_profile"])
        profile = profile or {}
        normalized: dict[str, list[str]] = {}
        for key, default_value in base.items():
            raw_value = profile.get(key, default_value)
            if isinstance(raw_value, list):
                normalized[key] = cls._unique_text_list(raw_value)
            elif raw_value:
                normalized[key] = cls._unique_text_list([raw_value])
            else:
                normalized[key] = []
        return normalized

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(base)
        for key, value in updates.items():
            base_value = merged.get(key)
            if isinstance(base_value, dict) and isinstance(value, dict):
                merged[key] = cls._deep_merge(base_value, value)
            else:
                merged[key] = value
        return merged

    @classmethod
    def _normalize_preferences(cls, prefs: Optional[dict[str, Any]]) -> dict[str, Any]:
        merged = cls._deep_merge(dict(DEFAULT_PREFERENCES), prefs or {})
        merged["preferred_meeting_times"] = cls._unique_text_list(
            merged.get("preferred_meeting_times", [])
        )
        merged["frequent_contacts"] = cls._unique_text_list(
            merged.get("frequent_contacts", [])
        )
        merged["custom_rules"] = cls._unique_text_list(
            merged.get("custom_rules", [])
        )
        merged["memory_profile"] = cls._normalize_memory_profile(
            merged.get("memory_profile")
        )
        return merged

    @staticmethod
    def looks_like_preference_statement(message: str) -> bool:
        message_lower = message.lower()
        cues = (
            "i like",
            "i love",
            "i enjoy",
            "i dislike",
            "i don't like",
            "i do not like",
            "i hate",
            "i prefer",
            "i'd prefer",
            "i would prefer",
            "i would rather",
            "my favorite",
            "please remember that",
            "remember that i",
            "don't suggest",
            "do not suggest",
            "avoid ",
            "i am allergic to",
            "i'm allergic to",
        )
        return any(cue in message_lower for cue in cues)

    @staticmethod
    def _clean_memory_fragment(fragment: str) -> str:
        cleaned = fragment.strip(" \t\r\n.,!?;:")
        cleaned = re.split(
            r"\b(?:because|since|but|except|when|whenever|although|though|so that)\b",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" \t\r\n.,!?;:")
        cleaned = re.sub(r"^(?:the|a|an|any|some|all)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned

    @classmethod
    def _split_memory_items(cls, fragment: str) -> list[str]:
        cleaned = cls._clean_memory_fragment(fragment)
        if not cleaned:
            return []
        parts = re.split(r",|/|\band\b|\bor\b", cleaned, flags=re.IGNORECASE)
        items = [cls._clean_memory_fragment(part) for part in parts]
        return cls._unique_text_list([item for item in items if item])

    @classmethod
    def extract_memory_updates_from_text(cls, message: str) -> dict[str, list[str]]:
        message_clean = " ".join(message.strip().split())
        if not message_clean:
            return {}

        updates: dict[str, list[str]] = {
            "likes": [],
            "dislikes": [],
            "avoid": [],
            "preferences": [],
            "notes": [],
        }
        patterns = [
            (
                "avoid",
                r"(?:i am allergic to|i'm allergic to|please avoid|avoid|don't suggest|do not suggest)\s+(.+?)(?:[.!?]|$)",
            ),
            (
                "dislikes",
                r"(?:i don't like|i do not like|i dislike|i hate|i can't stand)\s+(.+?)(?:[.!?]|$)",
            ),
            (
                "likes",
                r"(?:i like|i love|i enjoy)\s+(.+?)(?:[.!?]|$)",
            ),
            (
                "preferences",
                r"(?:i prefer|i'd prefer|i would prefer|i would rather)\s+(.+?)(?:[.!?]|$)",
            ),
            (
                "preferences",
                r"(?:my favorite\s+.+?\s+is)\s+(.+?)(?:[.!?]|$)",
            ),
        ]

        for bucket, pattern in patterns:
            for match in re.finditer(pattern, message_clean, flags=re.IGNORECASE):
                fragment = match.group(1).strip()
                if bucket == "preferences":
                    normalized = cls._clean_memory_fragment(fragment)
                    if normalized:
                        updates[bucket].append(normalized)
                else:
                    updates[bucket].extend(cls._split_memory_items(fragment))

        normalized_updates = cls._normalize_memory_profile(updates)
        if any(normalized_updates.values()):
            return normalized_updates
        return {}

    @classmethod
    def build_prompt_context(
        cls,
        preferences: Optional[dict[str, Any]],
        max_items_per_list: int = 4,
    ) -> str:
        prefs = cls._normalize_preferences(preferences)
        lines: list[str] = []

        if prefs.get("email_tone") and prefs.get("email_tone") != DEFAULT_PREFERENCES["email_tone"]:
            lines.append(f"- Email tone: {prefs['email_tone']}")
        if prefs.get("preferred_meeting_times"):
            slots = ", ".join(prefs["preferred_meeting_times"][:max_items_per_list])
            lines.append(f"- Preferred meeting windows: {slots}")
        if prefs.get("custom_rules"):
            rules = "; ".join(prefs["custom_rules"][:max_items_per_list])
            lines.append(f"- Custom rules: {rules}")

        memory_profile = prefs.get("memory_profile", {})
        for label, key in (
            ("Likes", "likes"),
            ("Dislikes", "dislikes"),
            ("Avoid", "avoid"),
            ("Personal preferences", "preferences"),
            ("Remembered notes", "notes"),
        ):
            values = memory_profile.get(key, [])
            if values:
                lines.append(f"- {label}: {', '.join(values[:max_items_per_list])}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get_all_preferences(self, user_id: str) -> dict:
        """
        Get all preferences for a user.
        Returns default preferences merged with stored values.
        """
        doc = await self.db.get_document(self.collection, user_id)
        if doc:
            doc.pop("id", None)
            return self._normalize_preferences(doc)
        return self._normalize_preferences({})

    async def get_preference(self, user_id: str, key: str) -> Any:
        """Get a single preference value."""
        prefs = await self.get_all_preferences(user_id)
        return prefs.get(key)

    async def save_preference(self, user_id: str, key: str, value: Any) -> None:
        """Save a single preference."""
        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data={
                key: value,
                "updated_at": datetime.utcnow().isoformat(),
            },
            merge=True,
        )
        logger.info("preference_saved", user_id=user_id, key=key)

    async def update_preferences(self, user_id: str, prefs: dict) -> dict:
        """
        Batch-update multiple preferences.

        Args:
            user_id: User identifier.
            prefs: Dict of key-value preference pairs to update.

        Returns:
            The full updated preferences dict.
        """
        safe_prefs = {
            k: v for k, v in prefs.items() if k not in ("id", "user_id", "created_at")
        }
        current = await self.get_all_preferences(user_id)
        merged = self._deep_merge(current, safe_prefs)
        merged = self._normalize_preferences(merged)
        merged["updated_at"] = datetime.utcnow().isoformat()

        await self.db.set_document(
            collection=self.collection,
            document_id=user_id,
            data=merged,
            merge=True,
        )
        logger.info("preferences_updated", user_id=user_id, keys=list(safe_prefs.keys()))
        return await self.get_all_preferences(user_id)

    async def update_memory_profile(self, user_id: str, memory_updates: dict) -> dict:
        """Merge conversational memory updates into the stored memory profile."""
        normalized_updates = self._normalize_memory_profile(memory_updates)
        if not any(normalized_updates.values()):
            return await self.get_all_preferences(user_id)

        current = await self.get_all_preferences(user_id)
        current_profile = self._normalize_memory_profile(current.get("memory_profile"))

        merged_profile: dict[str, list[str]] = {}
        for key in current_profile:
            merged_profile[key] = self._unique_text_list(
                current_profile.get(key, []) + normalized_updates.get(key, [])
            )

        return await self.update_preferences(
            user_id,
            {"memory_profile": merged_profile},
        )

    async def delete_preferences(self, user_id: str) -> bool:
        """Delete all preferences for a user."""
        return await self.db.delete_document(self.collection, user_id)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def get_working_hours(self, user_id: str) -> dict:
        """Get user's working hours configuration."""
        prefs = await self.get_all_preferences(user_id)
        return prefs.get("working_hours", DEFAULT_PREFERENCES["working_hours"])

    async def get_email_tone(self, user_id: str) -> str:
        """Get user's preferred email tone."""
        prefs = await self.get_all_preferences(user_id)
        return prefs.get("email_tone", "professional")

    async def get_frequent_contacts(self, user_id: str) -> list[str]:
        """Get user's frequent contacts list."""
        prefs = await self.get_all_preferences(user_id)
        return prefs.get("frequent_contacts", [])

    async def add_frequent_contact(self, user_id: str, email: str) -> None:
        """Add an email to the frequent contacts list."""
        contacts = await self.get_frequent_contacts(user_id)
        if email not in contacts:
            contacts.append(email)
            await self.save_preference(user_id, "frequent_contacts", contacts)
