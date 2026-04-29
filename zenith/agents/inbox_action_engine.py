"""
Inbox Action Engine for Zenith AI.
Classifies emails into a single strict action type and returns UI-ready payloads.

Uses weighted scoring across all categories instead of first-match-wins
to improve classification accuracy for ambiguous emails.
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

ACTION_REPLY = "reply"
ACTION_TASK = "task"
ACTION_MEETING = "meeting"
ACTION_IGNORE = "ignore"
ALLOWED_ACTIONS = {ACTION_REPLY, ACTION_TASK, ACTION_MEETING, ACTION_IGNORE}
UI_ACTIONS_BY_TYPE = {
    ACTION_REPLY: ["Send Reply", "Edit Reply", "Ignore"],
    ACTION_TASK: ["Add Task", "Edit & Add Task", "Help", "Ignore"],
    ACTION_MEETING: ["Schedule Meeting", "Edit Details", "Autoprep", "Ignore"],
    ACTION_IGNORE: ["Ignore"],
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

# ── Weighted keyword lists ─────────────────────────────────────────────
# Each match against these patterns adds +1 to the category score.
# The category with the highest total score wins.

MEETING_KEYWORDS: tuple[str, ...] = (
    "meeting",
    "call",
    "zoom",
    "google meet",
    "teams meeting",
    "calendar invite",
    "reschedule",
    "availability",
    "standup",
    "sync up",
    "sync-up",
    "huddle",
    "conference call",
    "video call",
    "dial in",
    "webinar",
    "book a time",
    "meet at",
    "let's meet",
    "catch up call",
    "schedule a meeting",
    "schedule a call",
    "schedule meeting",
    "schedule call",
)

TASK_KEYWORDS: tuple[str, ...] = (
    "please",
    "can you",
    "could you",
    "need you to",
    "action required",
    "action needed",
    "todo",
    "to-do",
    "follow up",
    "follow-up",
    "complete",
    "prepare",
    "submit",
    "review",
    "deadline",
    "urgent",
    "asap",
    "by eod",
    "by end of day",
    "by tomorrow",
    "assigned to you",
    "your task",
    "deliverable",
    "approval needed",
    "sign off",
    "take care of",
)

REPLY_KEYWORDS: tuple[str, ...] = (
    "let me know",
    "any update",
    "any updates",
    "what is",
    "when will",
    "can you confirm",
    "thoughts on",
    "your thoughts",
    "what do you think",
    "please respond",
    "please reply",
    "waiting for your",
    "get back to me",
    "looking forward to hearing",
    "could you clarify",
    "need your input",
    "your opinion",
    "feedback on",
    "are you available",
)

IGNORE_KEYWORDS: tuple[str, ...] = (
    "newsletter",
    "unsubscribe",
    "promotion",
    "receipt",
    "invoice generated",
    "notification",
    "no-reply",
    "noreply",
    "donotreply",
    "do-not-reply",
    "automated message",
    "marketing",
    "subscription",
    "verify your email",
    "account statement",
    "privacy policy",
    "terms of service",
)

# Regex patterns that give a +2 (strong signal) bonus
TASK_REGEX_PATTERNS: tuple[str, ...] = (
    r"\b(update|review|prepare|submit|complete|draft|fix|share)\b\s+\b(the|a|an|our|this|that|my|your)\b",
    r"\b(can you|could you|need you to)\b\s+\w+",
    r"\bdeadline\s*(is|:)",
    r"\bdue\s+(by|on|date)",
    r"\bassigned\s+to\s+you\b",
)

MEETING_REGEX_PATTERNS: tuple[str, ...] = (
    r"\b(schedule|book|set up)\s+(a\s+)?(meeting|call|session|sync)\b",
    r"\b(join|attend)\s+(the\s+)?(meeting|call|standup|huddle)\b",
    r"\bmeeting\s+(at|on|from)\s+\d",
)

REPLY_REGEX_PATTERNS: tuple[str, ...] = (
    r"\bplease\s+(respond|reply|confirm|advise)\b",
    r"\bwhat\s+(are|is|was|were|do|did|should|would|could)\b",
    r"\bhow\s+(do|can|should|would)\b",
)


class InboxActionEngine:
    """Classify email items and build strict action payloads using weighted scoring."""

    # Keyword weight per match
    _KEYWORD_WEIGHT = 1
    # Regex weight per match (stronger signal)
    _REGEX_WEIGHT = 2

    def classify_email(self, email: dict[str, Any]) -> str:
        """Return exactly one action type using weighted scoring across all categories."""
        text = self._email_text(email)
        lowered = text.lower()

        # Check ignore first — if strong ignore signals, skip scoring
        ignore_score = self._count_matches(lowered, IGNORE_KEYWORDS) * self._KEYWORD_WEIGHT
        if ignore_score >= 2:
            return ACTION_IGNORE

        # Score all categories
        scores: dict[str, int] = {
            ACTION_MEETING: 0,
            ACTION_TASK: 0,
            ACTION_REPLY: 0,
            ACTION_IGNORE: ignore_score,
        }

        # Keyword scoring
        scores[ACTION_MEETING] += self._count_matches(lowered, MEETING_KEYWORDS) * self._KEYWORD_WEIGHT
        scores[ACTION_TASK] += self._count_matches(lowered, TASK_KEYWORDS) * self._KEYWORD_WEIGHT
        scores[ACTION_REPLY] += self._count_matches(lowered, REPLY_KEYWORDS) * self._KEYWORD_WEIGHT

        # Regex scoring (stronger signal)
        scores[ACTION_MEETING] += self._count_regex_matches(lowered, MEETING_REGEX_PATTERNS) * self._REGEX_WEIGHT
        scores[ACTION_TASK] += self._count_regex_matches(lowered, TASK_REGEX_PATTERNS) * self._REGEX_WEIGHT
        scores[ACTION_REPLY] += self._count_regex_matches(lowered, REPLY_REGEX_PATTERNS) * self._REGEX_WEIGHT

        # Find the winner — ties broken by precedence: meeting > task > reply > ignore
        precedence = [ACTION_MEETING, ACTION_TASK, ACTION_REPLY, ACTION_IGNORE]
        best_action = ACTION_IGNORE
        best_score = 0
        for action in precedence:
            if scores[action] > best_score:
                best_score = scores[action]
                best_action = action

        return best_action

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
        items: list[dict[str, Any]] = []
        for email in emails:
            try:
                items.append(self.build_email_action_item(email))
            except Exception:
                logger.warning(
                    "Skipped email during classification",
                    extra={"email_id": email.get("id", "unknown")},
                )
        return items

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
    def _count_matches(text: str, patterns: tuple[str, ...]) -> int:
        """Count how many patterns appear in the text."""
        return sum(1 for pattern in patterns if pattern in text)

    @staticmethod
    def _count_regex_matches(text: str, patterns: tuple[str, ...]) -> int:
        """Count how many regex patterns match in the text."""
        return sum(1 for pattern in patterns if re.search(pattern, text))
