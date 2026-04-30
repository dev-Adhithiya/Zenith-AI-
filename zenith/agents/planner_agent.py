"""
Planner Agent for Zenith AI
Performs LLM-powered reasoning before execution to determine optimal
strategies for multi-step tasks.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import structlog

from .vertex_ai import VertexAIClient, get_vertex_client
from memory.preferences import PreferencesStore

logger = structlog.get_logger()


class PlannerAgent:
    """
    Planner Agent — sits between ContextAgent and Executor.

    Responsibilities:
    - Analyse user intent + gathered context
    - Decide if the request is a simple query or a multi-step task
    - Identify which tools are required and in what order
    - Output a structured plan with goal, steps, risk assessment
    - Incorporate user preferences into planning decisions
    """

    def __init__(self, vertex_client: Optional[VertexAIClient] = None):
        self.llm = vertex_client or get_vertex_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_plan(
        self,
        context: dict,
        user_preferences: Optional[dict] = None,
    ) -> dict:
        """
        Create a structured execution plan from gathered context.

        This is called for Category B (tool-use) requests only.
        Conversational requests bypass the planner entirely.

        Args:
            context: Full context dict from ContextAgent.
            user_preferences: User preference dict from Firestore.

        Returns:
            Structured plan dict:
            {
                "goal": str,
                "complexity": "simple" | "multi_step",
                "steps": [...],
                "requires_confirmation": bool,
                "risk_level": "low" | "medium" | "high",
                "reasoning": str
            }
        """
        intent = context.get("intent", {})
        category = intent.get("category", "A")

        # Skip planner for conversational requests
        if category == "A":
            return {
                "goal": "conversation",
                "complexity": "simple",
                "steps": [],
                "requires_confirmation": False,
                "risk_level": "low",
                "reasoning": "Conversational request — no tool execution needed.",
            }

        return await self._generate_plan(context, user_preferences or {})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _generate_plan(
        self,
        context: dict,
        user_preferences: dict,
    ) -> dict:
        """Use LLM to reason about the optimal execution strategy."""
        import datetime
        import zoneinfo

        user_profile = context.get("user_profile", {})
        timezone_str = user_profile.get("settings", {}).get("timezone", "UTC")
        user_name = user_profile.get("name", "User")
        user_email = user_profile.get("email", "")

        try:
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("Etc/UTC")

        current_dt = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

        # Build preferences context
        pref_text = PreferencesStore.build_prompt_context(user_preferences)
        if pref_text:
            pref_text = "\nUser preferences:\n" + pref_text

        system_instruction = f"""You are a planning agent for Zenith AI, an elite personal assistant.
Your job is to analyse a user request and create an optimal execution plan.

Current date/time: {current_dt}
User: {user_name} ({user_email})
{pref_text}

Available tools:
- calendar.list_events(time_min, time_max, max_results, query)
- calendar.create_event(summary, start_time, end_time, description, attendees, conference_data)
- calendar.quick_add(text)
- calendar.check_availability(time_min, time_max)
- gmail.search_messages(query, max_results)
- gmail.get_thread(thread_id)
- gmail.get_email_details_by_query(query, max_results)
- gmail.summarize_inbox(hours)
- gmail.send_email(to, subject, body)
- tasks.add_task(title, notes, due_date)
- tasks.list_tasks(show_completed)
- tasks.set_reminder(title, remind_at)
- tasks.complete_task(task_id)
- tasks.complete_task_by_title(title, task_list_id)
- notes.save_note(title, content, tags)
- notes.query_knowledge_base(query)
- notes.delete_note(note_id)
- notes.delete_note_by_query(query, delete_all_matches)

Instructions:
1. Determine the user's goal.
2. Decide if this is a "simple" (1 step) or "multi_step" (2+ steps) task.
3. List the steps in optimal execution order.
4. Assess risk: "low" (read-only), "medium" (single write), "high" (bulk write / multi-recipient).
5. Provide brief reasoning for your plan.
6. If the user asks to draft/generate email content, write actual professional content.
7. For dates/times, use ISO format.
8. If the user mentions "meeting", "meet link", "gmeet", "google meet", "video call", or any meeting-related phrase, you MUST use calendar.create_event with conference_data=true. ALWAYS set conference_data=true for meetings — this generates the Google Meet link.
9. NEVER create a task when the user asks for a meeting. Use calendar.create_event instead.

Output ONLY valid JSON in this exact schema:
{{
    "goal": "string describing the goal",
    "complexity": "simple" or "multi_step",
    "steps": [
        {{
            "action": "tool.method",
            "params": {{"param1": "value1"}},
            "description": "what this step does"
        }}
    ],
    "requires_execution": true,
    "risk_level": "low" or "medium" or "high",
    "reasoning": "brief explanation of plan strategy"
}}"""

        # Build prompt with context
        chat_history = context.get("chat_history", [])
        history_str = ""
        if chat_history:
            history_str = "\n\nRecent conversation:\n" + "\n".join(
                [f"{m['role']}: {m['content']}" for m in chat_history[-3:]]
            )

        prompt = f"""User request: {context.get('resolved_message', context.get('original_message', ''))}
{history_str}

Entities extracted: {json.dumps(context.get('entities', {}), default=str)}

Intent classification: {json.dumps(context.get('intent', {}), default=str)}

Create an execution plan:"""

        response = await self.llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2,
            max_tokens=1200,
        )

        plan = self._parse_plan(response)

        # Post-process: force conference_data=true on any calendar.create_event step
        for step in plan.get("steps", []):
            if step.get("action") == "calendar.create_event":
                step.setdefault("params", {})
                step["params"]["conference_data"] = True

        return plan

    @staticmethod
    def _parse_plan(raw: str) -> dict:
        """Parse LLM response into a structured plan dict."""
        raw = raw.strip()

        # Strip markdown code fences
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)

        # Find the outermost JSON object
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("planner_parse_failed", raw_response=raw[:300])
            plan = {
                "goal": "unknown",
                "complexity": "simple",
                "steps": [],
                "requires_execution": False,
                "risk_level": "low",
                "reasoning": "Failed to parse planner output.",
            }

        # Ensure required keys exist with defaults
        plan.setdefault("goal", "unknown")
        plan.setdefault("complexity", "simple")
        plan.setdefault("steps", [])
        
        # If there are steps, we definitely require execution
        if len(plan.get("steps", [])) > 0:
            plan["requires_execution"] = True
        else:
            plan.setdefault("requires_execution", False)
            
        plan.setdefault("risk_level", "low")
        plan.setdefault("reasoning", "")

        return plan
