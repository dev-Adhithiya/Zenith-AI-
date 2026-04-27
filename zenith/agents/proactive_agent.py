"""
Proactive Agent for Zenith AI
Scans user's Google Workspace data and generates intelligent insights
and actionable suggestions.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

import structlog

from .vertex_ai import VertexAIClient, get_vertex_client
from memory.preferences import PreferencesStore
from tools.calendar import CalendarTools
from tools.gmail import GmailTools
from tools.tasks import TasksTools
from tools.notes import NotesTools

logger = structlog.get_logger()


class ProactiveAgent:
    """
    Proactive Intelligence Agent.

    Capabilities:
    - Scan upcoming calendar events, unread emails, and pending tasks
    - Generate actionable suggestions based on patterns
    - Power the daily-briefing endpoint
    - Detect potential issues (e.g. meetings without prep notes,
      unanswered important emails)
    """

    def __init__(self, vertex_client: Optional[VertexAIClient] = None):
        self.llm = vertex_client or get_vertex_client()
        self.calendar = CalendarTools()
        self.gmail = GmailTools()
        self.tasks = TasksTools()
        self.notes = NotesTools()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_daily_briefing(
        self,
        user_id: str,
        credentials: dict,
        user_preferences: Optional[dict] = None,
    ) -> dict:
        """
        Generate a comprehensive daily briefing with AI insights.

        Returns:
            {
                "status": "success" | "error",
                "meetings": [...],
                "emails": [...],
                "tasks": [...],
                "insights": [...],
                "summary": "AI-generated narrative summary",
                "metadata": {...}
            }
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        tomorrow_end = today_end + timedelta(days=1)

        # --- Fetch data in parallel-ish (sequentially for safety) ---
        meetings = await self._fetch_meetings(credentials, today_start, tomorrow_end)
        emails = await self._fetch_unread_emails(credentials)
        tasks = await self._fetch_pending_tasks(credentials)

        # --- Generate AI insights ---
        insights = await self._generate_insights(
            meetings=meetings,
            emails=emails,
            tasks=tasks,
            user_preferences=user_preferences or {},
        )

        # --- Generate narrative summary ---
        summary = await self._generate_summary(
            meetings=meetings,
            emails=emails,
            tasks=tasks,
            insights=insights,
        )

        return {
            "status": "success",
            "meetings": meetings,
            "emails": emails,
            "tasks": tasks,
            "insights": insights,
            "summary": summary,
            "metadata": {
                "meeting_count": len(meetings),
                "unread_count": len(emails),
                "task_count": len(tasks),
                "insight_count": len(insights),
                "generated_at": now.isoformat(),
            },
        }

    # ------------------------------------------------------------------
    # Data fetchers
    # ------------------------------------------------------------------

    async def _fetch_meetings(
        self, credentials: dict, time_min: datetime, time_max: datetime
    ) -> list[dict]:
        """Fetch calendar events for the date range."""
        try:
            events = await self.calendar.list_events(
                credentials=credentials,
                time_min=time_min,
                time_max=time_max,
                max_results=50,
            )
            return events if isinstance(events, list) else []
        except Exception as exc:
            logger.warning("proactive_calendar_fetch_failed", error=str(exc))
            return []

    async def _fetch_unread_emails(self, credentials: dict) -> list[dict]:
        """Fetch unread emails from the last 48 hours."""
        try:
            cutoff = (datetime.utcnow() - timedelta(hours=48)).strftime("%Y/%m/%d")
            emails = await self.gmail.search_messages(
                credentials=credentials,
                query=f"is:unread after:{cutoff}",
                max_results=20,
            )
            return emails if isinstance(emails, list) else []
        except Exception as exc:
            logger.warning("proactive_email_fetch_failed", error=str(exc))
            return []

    async def _fetch_pending_tasks(self, credentials: dict) -> list[dict]:
        """Fetch all pending (non-completed) tasks."""
        try:
            tasks = await self.tasks.list_tasks(
                credentials=credentials,
                show_completed=False,
                max_results=50,
            )
            return tasks if isinstance(tasks, list) else []
        except Exception as exc:
            logger.warning("proactive_tasks_fetch_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # AI insight generation
    # ------------------------------------------------------------------

    async def _generate_insights(
        self,
        meetings: list[dict],
        emails: list[dict],
        tasks: list[dict],
        user_preferences: dict,
    ) -> list[dict]:
        """
        Generate actionable insights from the user's data.

        Each insight is:
        {
            "type": "warning" | "suggestion" | "reminder",
            "title": "short title",
            "message": "detailed message",
            "priority": "high" | "medium" | "low",
            "related_to": "calendar" | "email" | "tasks"
        }
        """
        system_instruction = """You are an insight-generation engine for a personal assistant.
Analyse the user's calendar events, emails, and tasks, then generate actionable insights.

Output a JSON array of insight objects. Each object must have:
{
    "type": "warning" | "suggestion" | "reminder",
    "title": "short title (max 60 chars)",
    "message": "detailed insight message (max 200 chars)",
    "priority": "high" | "medium" | "low",
    "related_to": "calendar" | "email" | "tasks"
}

Examples of good insights:
- "You have a meeting in 2 hours with no agenda set"
- "3 emails from your manager are unread"
- "Task 'Submit report' is due today"
- "You haven't replied to an email from Jane in 3 days"
- "Tomorrow's meeting conflicts with lunch block"

Rules:
- Generate 2-5 insights maximum
- Focus on actionable, non-obvious observations
- Prioritise urgent items
- Output ONLY a valid JSON array"""

        meetings_text = json.dumps(meetings[:10], default=str)[:2000]
        emails_text = json.dumps(emails[:10], default=str)[:2000]
        tasks_text = json.dumps(tasks[:10], default=str)[:2000]
        preferences_text = PreferencesStore.build_prompt_context(user_preferences) or "None recorded"

        prompt = f"""Analyse this data and generate insights:

USER PREFERENCES:
{preferences_text}

CALENDAR ({len(meetings)} events):
{meetings_text}

EMAILS ({len(emails)} unread):
{emails_text}

TASKS ({len(tasks)} pending):
{tasks_text}

Generate insights:"""

        response = await self.llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.4,
            max_tokens=900,
        )

        return self._parse_insights(response)

    async def _generate_summary(
        self,
        meetings: list[dict],
        emails: list[dict],
        tasks: list[dict],
        insights: list[dict],
    ) -> str:
        """Generate a natural-language narrative summary."""
        system_instruction = """You are Zenith AI, a proactive Chief of Staff.
Generate a concise daily briefing summary (max 200 words).

Format:
✅ TASKS
  • [task items]

📅 CALENDAR
  • [time]: [event]

📧 EMAILS
  [brief summary]

💡 INSIGHTS
  • [key insights]

Rules:
- Use emojis as section markers
- Be concise and scannable
- NO markdown formatting (no **, ##, etc.)
- NO questions or follow-ups
- Mention urgent items first"""

        meetings_brief = "\n".join(
            f"- {e.get('start', '')}: {e.get('summary', '(No title)')}"
            for e in meetings[:10]
        ) or "No events"

        tasks_brief = "\n".join(
            f"- {t.get('title', '(No title)')}" for t in tasks[:10]
        ) or "No pending tasks"

        emails_brief = f"{len(emails)} unread emails" if emails else "No unread emails"

        insights_brief = "\n".join(
            f"- {i.get('message', '')}" for i in insights[:5]
        ) or "No insights"

        prompt = f"""Generate a daily briefing from this data:

TASKS ({len(tasks)} pending):
{tasks_brief}

CALENDAR ({len(meetings)} events):
{meetings_brief}

EMAILS: {emails_brief}

INSIGHTS:
{insights_brief}"""

        summary = await self.llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.6,
            max_tokens=900,
        )

        # Clean any markdown
        summary = (
            summary.replace("**", "")
            .replace("__", "")
            .replace("##", "")
            .replace("- ", "• ")
        )

        return summary

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_insights(raw: str) -> list[dict]:
        """Parse the LLM insight response into structured data."""
        raw = raw.strip()

        if "```" in raw:
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)

        # Find array bounds
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]

        try:
            insights = json.loads(raw)
            if isinstance(insights, list):
                return insights[:5]
        except json.JSONDecodeError:
            logger.warning("insight_parse_failed", raw=raw[:200])

        return []
