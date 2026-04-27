"""
Inbox Action Engine for Zenith AI.
Classifies emails into a single strict action type and returns UI-ready payloads.
"""
from __future__ import annotations

import re
from typing import Any


ACTION_REPLY = "reply"
ACTION_TASK = "task"
ACTION_MEETING = "meeting"
ACTION_IGNORE = "ignore"
ALLOWED_ACTIONS = {ACTION_REPLY, ACTION_TASK, ACTION_MEETING, ACTION_IGNORE}
UI_ACTIONS_BY_TYPE = {
    ACTION_REPLY: ["Send Reply", "Edit Reply", "Ignore"],
    ACTION_TASK: ["Add Task", "Edit & Add Task", "Ignore"],
    ACTION_MEETING: ["Schedule Meeting", "Edit Details", "Autoprep", "Ignore"],
    ACTION_IGNORE: ["Ignore only"],
}

VERB_PREFIXES = (
    "Update",
    "Review",
    "Send",
    "Prepare",
    "Draft",
    "Fix",
    "Share",
    "Confirm",
    "Schedule",
    "Complete",
)


class InboxActionEngine:
    """Classify email items and build strict action payloads."""

    MEETING_PATTERNS = (
        "meeting",
        "call",
        "zoom",
        "google meet",
        "calendar invite",
        "reschedule",
        "availability",
        "schedule",
    )
    TASK_PATTERNS = (
        "please",
        "can you",
        "could you",
        "need you to",
        "action required",
        "todo",
        "follow up",
        "complete",
        "prepare",
        "submit",
        "review",
    )
    REPLY_PATTERNS = (
        "?",
        "let me know",
        "any update",
        "what is",
        "when will",
        "can you confirm",
    )
    IGNORE_PATTERNS = (
        "newsletter",
        "unsubscribe",
        "promotion",
        "receipt",
        "invoice generated",
        "notification",
    )

    def classify_email(self, email: dict[str, Any]) -> str:
        """Return exactly one action type using strict precedence."""
        text = self._email_text(email)
        lowered = text.lower()

        if self._contains_any(lowered, self.MEETING_PATTERNS):
            return ACTION_MEETING
        if self._is_task_request(lowered):
            return ACTION_TASK
        if self._contains_any(lowered, self.REPLY_PATTERNS):
            return ACTION_REPLY
        if self._contains_any(lowered, self.IGNORE_PATTERNS):
            return ACTION_IGNORE
        return ACTION_IGNORE

    def build_email_action_item(self, email: dict[str, Any]) -> dict[str, Any]:
        """Build a strict UI-ready email action item."""
        action_type = self.classify_email(email)
        base = {
            "id": str(email.get("id", "")),
            "type": "email_action",
            "action_type": action_type,
            "ui_actions": UI_ACTIONS_BY_TYPE[action_type],
            "title": self._title(email),
            "from": email.get("from") or email.get("sender") or "Unknown sender",
            "summary": self._summary(email),
            "reason": self._reason(action_type),
        }

        if action_type == ACTION_REPLY:
            base["draft_reply"] = self._draft_reply(email)
        elif action_type == ACTION_TASK:
            base["task_payload"] = self._task_payload(email)
        elif action_type == ACTION_MEETING:
            base["meeting_payload"] = self._meeting_payload(email)

        self._validate_item(base)
        return base

    def build_email_action_items(self, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert a list of email dicts into strict action items."""
        return [self.build_email_action_item(email) for email in emails]

    def _email_text(self, email: dict[str, Any]) -> str:
        parts = [
            str(email.get("subject", "")),
            str(email.get("snippet", "")),
            str(email.get("body_text", "")),
        ]
        return " ".join(part for part in parts if part).strip()

    def _title(self, email: dict[str, Any]) -> str:
        return str(email.get("subject") or "Email action")

    def _summary(self, email: dict[str, Any]) -> str:
        snippet = str(email.get("snippet") or "").strip()
        if snippet:
            return snippet[:180]
        return "No additional summary available."

    def _reason(self, action_type: str) -> str:
        if action_type == ACTION_MEETING:
            return "Meeting intent detected from email context."
        if action_type == ACTION_TASK:
            return "Explicit work request detected."
        if action_type == ACTION_REPLY:
            return "Direct question or response needed."
        return "No direct action required."

    def _draft_reply(self, email: dict[str, Any]) -> str:
        sender = email.get("from") or email.get("sender") or "there"
        return (
            f"Hi {sender}, thanks for your message. "
            "I have reviewed this and will get back to you shortly."
        )

    def _task_payload(self, email: dict[str, Any]) -> dict[str, Any]:
        summary = self._summary(email)
        title_seed = str(email.get("subject") or "Review email request")
        title = self._ensure_verb_first(title_seed)
        return {
            "title": title,
            "description": summary if summary != "No additional summary available." else None,
            "due": None,
        }

    def _meeting_payload(self, email: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": self._title(email),
            "description": self._summary(email),
            "attendees": [],
            "start_time": None,
            "end_time": None,
        }

    def _ensure_verb_first(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return "Review request"

        first = normalized.split(" ", 1)[0]
        if first.lower() in {verb.lower() for verb in VERB_PREFIXES}:
            return normalized

        clean = normalized[0].lower() + normalized[1:] if len(normalized) > 1 else normalized
        return f"Review {clean}"

    def _validate_item(self, item: dict[str, Any]) -> None:
        action_type = item.get("action_type")
        if action_type not in ALLOWED_ACTIONS:
            raise ValueError("Invalid action_type")

        payload_fields = [
            "draft_reply" in item,
            "task_payload" in item,
            "meeting_payload" in item,
        ]
        payload_count = sum(1 for exists in payload_fields if exists)

        if action_type == ACTION_IGNORE and payload_count != 0:
            raise ValueError("ignore action must not include payloads")
        if action_type in {ACTION_REPLY, ACTION_TASK, ACTION_MEETING} and payload_count != 1:
            raise ValueError("Exactly one payload is allowed for non-ignore actions")

    @staticmethod
    def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _is_task_request(self, text: str) -> bool:
        if self._contains_any(text, self.TASK_PATTERNS):
            return True
        command_patterns = (
            r"\b(update|review|prepare|submit|complete|draft|fix|share)\b\s+\b(the|a|an|our|this|that|my|your)\b",
        )
        return any(re.search(pattern, text) for pattern in command_patterns)
