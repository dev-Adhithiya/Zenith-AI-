"""
Priority feed merger for Zenith AI.
Combines strict email actions with meeting prep items.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .autoprep_agent import AutoPrepAgent
from .inbox_action_engine import InboxActionEngine
from tools.calendar import CalendarTools
from tools.gmail import GmailTools


class PriorityFeedBuilder:
    """Build a UI-ready priority feed from Gmail + Calendar."""

    def __init__(
        self,
        gmail: GmailTools | None = None,
        calendar: CalendarTools | None = None,
        inbox_engine: InboxActionEngine | None = None,
        autoprep_agent: AutoPrepAgent | None = None,
    ):
        self.gmail = gmail or GmailTools()
        self.calendar = calendar or CalendarTools()
        self.inbox_engine = inbox_engine or InboxActionEngine()
        self.autoprep = autoprep_agent or AutoPrepAgent()

    async def build(self, credentials: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow()
        start = now
        end = now + timedelta(hours=24)
        cutoff = (now - timedelta(hours=48)).strftime("%Y/%m/%d")

        emails = await self.gmail.search_messages(
            credentials=credentials,
            query=f"in:inbox after:{cutoff}",
            max_results=20,
        )
        events = await self.calendar.list_events(
            credentials=credentials,
            time_min=start,
            time_max=end,
            max_results=20,
        )

        email_items = self.inbox_engine.build_email_action_items(emails if isinstance(emails, list) else [])
        meeting_prep_items = self.autoprep.build_meeting_prep_items(
            events=events if isinstance(events, list) else [],
            related_emails=emails if isinstance(emails, list) else [],
        )

        items = [*email_items, *meeting_prep_items]
        valid_items: list[dict[str, Any]] = []
        for item in items:
            try:
                self._validate_ui_contract(item)
                valid_items.append(item)
            except ValueError:
                pass  # skip malformed items silently

        return {
            "status": "success",
            "items": valid_items,
            "metadata": {
                "email_action_count": len(email_items),
                "meeting_prep_count": len(meeting_prep_items),
                "generated_at": now.isoformat(),
                "execution_hooks": {
                    "task_add": "/tasks",
                    "task_edit": "/tasks/edit",
                    "reply_send": "/gmail/send",
                    "meeting_schedule": "/calendar",
                },
            },
        }

    def _validate_ui_contract(self, item: dict[str, Any]) -> None:
        if item.get("type") == "email_action":
            action_type = item.get("action_type")
            expected_ui = {
                "reply": ["Send Reply", "Edit Reply", "Ignore"],
                "task": ["Add Task", "Edit & Add Task", "Help", "Ignore"],
                "meeting": ["Schedule Meeting", "Edit Details", "Autoprep", "Ignore"],
                "ignore": ["Ignore"],
            }
            if item.get("ui_actions") != expected_ui.get(action_type):
                raise ValueError("ui_actions mismatch for action_type")
            if action_type == "reply" and "draft_reply" not in item:
                raise ValueError("reply action requires draft_reply")
            if action_type == "task" and "task_payload" not in item:
                raise ValueError("task action requires task_payload")
            if action_type == "meeting" and "meeting_payload" not in item:
                raise ValueError("meeting action requires meeting_payload")
            if action_type == "ignore":
                if any(key in item for key in ("draft_reply", "task_payload", "meeting_payload")):
                    raise ValueError("ignore action must not include payloads")
        elif item.get("type") == "meeting_prep":
            if item.get("status") not in {"ready", "needs_clarification"}:
                raise ValueError("Invalid meeting_prep status")
        else:
            raise ValueError("Unsupported item type in priority feed")