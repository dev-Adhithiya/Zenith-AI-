"""
AutoPrep agent for meeting preparation items only.
"""
from __future__ import annotations

from typing import Any


class AutoPrepAgent:
    """Generate meeting prep cards for upcoming meetings."""

    def build_meeting_prep_items(
        self,
        events: list[dict[str, Any]],
        related_emails: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        related_emails = related_emails or []
        items: list[dict[str, Any]] = []

        for event in events:
            status = self._status_for_event(event)
            item = {
                "id": str(event.get("id", "")),
                "type": "meeting_prep",
                "status": status,
                "title": str(event.get("summary") or "Upcoming meeting"),
                "summary": self._summary(event),
                "reason": self._reason(status),
                "prep": self._prep(event, related_emails),
            }
            self._validate_item(item)
            items.append(item)

        return items

    def _status_for_event(self, event: dict[str, Any]) -> str:
        description = str(event.get("description") or "").strip()
        attendees = event.get("attendees") or []
        if description and isinstance(attendees, list) and len(attendees) > 0:
            return "ready"
        return "needs_clarification"

    def _summary(self, event: dict[str, Any]) -> str:
        description = str(event.get("description") or "").strip()
        if description:
            return description[:180]
        return "Agenda or context is missing for this meeting."

    def _reason(self, status: str) -> str:
        if status == "ready":
            return "Meeting details and attendees are available."
        return "Meeting details are incomplete and need clarification."

    def _prep(self, event: dict[str, Any], emails: list[dict[str, Any]]) -> dict[str, Any]:
        title = str(event.get("summary") or "meeting")
        risks = []
        talking_points = []

        if not event.get("description"):
            risks.append("No agenda provided by organizer")
        if not event.get("attendees"):
            risks.append("Attendee list may be incomplete")

        if not risks:
            risks.append("No major risks identified from event metadata")

        talking_points.append(f"Confirm goals for {title}")
        talking_points.append("Review recent related email context before meeting")

        if emails:
            talking_points.append("Address the latest open question from related emails")

        return {"risks": risks, "talking_points": talking_points}

    def _validate_item(self, item: dict[str, Any]) -> None:
        if item.get("type") != "meeting_prep":
            raise ValueError("AutoPrep must only emit meeting_prep items")
        if item.get("status") not in {"ready", "needs_clarification"}:
            raise ValueError("Invalid meeting_prep status")
