"""
Decomposer Agent for Zenith AI
Phase 2: Task Decomposition - Breaks goals into executable steps
"""
from typing import Optional
import re
import structlog

from .vertex_ai import VertexAIClient, get_vertex_client

logger = structlog.get_logger()


# Execution plan templates for common tasks
PLAN_TEMPLATES = {
    "check_calendar": {
        "name": "Check Calendar",
        "steps": [
            {"action": "calendar.list_events", "params": ["time_range", "query"]}
        ]
    },
    "create_meeting": {
        "name": "Create Meeting",
        "steps": [
            {"action": "calendar.create_event", "params": ["summary", "start_time", "end_time", "attendees", "conference_data", "description"]}
        ]
    },
    "quick_add_event": {
        "name": "Quick Add Event",
        "steps": [
            {"action": "calendar.quick_add", "params": ["text"]}
        ]
    },
    "check_email": {
        "name": "Check Email",
        "steps": [
            {"action": "gmail.search_messages", "params": ["query", "max_results"]}
        ]
    },
    "summarize_inbox": {
        "name": "Summarize Inbox",
        "steps": [
            {"action": "gmail.summarize_inbox", "params": ["hours"]}
        ]
    },
    "read_email": {
        "name": "Read Email",
        "steps": [
            {"action": "gmail.get_thread", "params": ["thread_id"]}
        ]
    },
    "email_details": {
        "name": "Email Details",
        "steps": [
            {"action": "gmail.get_email_details_by_query", "params": ["query"]}
        ]
    },
    "add_task": {
        "name": "Add Task",
        "steps": [
            {"action": "tasks.add_task", "params": ["title", "notes", "due_date"]}
        ]
    },
    "list_tasks": {
        "name": "List Tasks",
        "steps": [
            {"action": "tasks.list_tasks", "params": ["show_completed"]}
        ]
    },
    "set_reminder": {
        "name": "Set Reminder",
        "steps": [
            {"action": "tasks.set_reminder", "params": ["title", "remind_at"]}
        ]
    },
    "complete_task": {
        "name": "Complete Task",
        "steps": [
            {"action": "tasks.complete_task_by_title", "params": ["title"]}
        ]
    },
    "delete_note": {
        "name": "Delete Note",
        "steps": [
            {"action": "notes.delete_note_by_query", "params": ["query"]}
        ]
    },
    "search_notes": {
        "name": "Search Notes",
        "steps": [
            {"action": "notes.query_knowledge_base", "params": ["query"]}
        ]
    },
    "detailed_breakdown": {
        "name": "Detailed Breakdown",
        "steps": [
            {"action": "calendar.list_events", "params": ["max_results"]},
            {"action": "gmail.summarize_inbox", "params": ["hours"]},
            {"action": "tasks.list_tasks", "params": ["show_completed"]}
        ]
    }
}


class DecomposerAgent:
    """
    Decomposer Agent - Responsible for Phase 2: Task Decomposition
    
    Responsibilities:
    - Break complex goals into step-by-step execution plans
    - Select appropriate tools for each step
    - Extract parameters from context
    """
    
    def __init__(self, vertex_client: Optional[VertexAIClient] = None):
        self.llm = vertex_client or get_vertex_client()
    
    async def decompose(self, context: dict) -> dict:
        """
        Decompose a user request into an execution plan.
        
        Args:
            context: Context dictionary from ContextAgent
            
        Returns:
            Execution plan with steps and parameters
        """
        intent = context.get("intent", {})
        entities = dict(context.get("entities", {}))
        resolved_message = (context.get("resolved_message") or context.get("original_message") or "").lower()
        chat_history = context.get("chat_history", [])
        category = intent.get("category", "A")

        last_assistant_message = ""
        last_user_message = ""
        for msg in reversed(chat_history):
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "assistant" and not last_assistant_message:
                last_assistant_message = content
            if role == "user" and content.strip().lower() != resolved_message.strip() and not last_user_message:
                last_user_message = content
            if last_assistant_message and last_user_message:
                break

        last_assistant_lower = last_assistant_message.lower()

        confirmation_starters = ["yes", "yeah", "yep", "sure", "ok", "okay", "go ahead", "please"]
        detail_markers = ["details", "provide", "open", "show", "tell me"]
        email_markers = ["email", "mail", "inbox", "sender", "subject", "hackathon"]

        is_confirmation_followup = any(
            resolved_message.startswith(starter)
            for starter in confirmation_starters
        )

        was_prompted_for_email_details = (
            "open that email" in last_assistant_lower
            or "provide you with its details" in last_assistant_lower
            or "top senders" in last_assistant_lower
        )

        wants_email_details = (
            (any(marker in resolved_message for marker in detail_markers)
             and any(marker in resolved_message for marker in email_markers))
            or (is_confirmation_followup and was_prompted_for_email_details)
            or ("tell me about" in resolved_message and "hackathon" in resolved_message)
        )

        if wants_email_details and not entities.get("search_queries"):
            quoted_phrases = re.findall(r'"([^"]+)"', last_assistant_message)
            if quoted_phrases:
                entities["search_queries"] = [quoted_phrases[0]]
            elif last_user_message:
                entities["search_queries"] = [last_user_message[:120]]

        if wants_email_details:
            intent = {
                **intent,
                "category": "B",
                "intent": "email_details",
                "requires_tools": ["gmail"]
            }
            category = "B"

        wants_breakdown = (
            "expand on the executive summary" in resolved_message
            or "detailed breakdown" in resolved_message
            or "daily briefing" in resolved_message
            or "executive summary" in resolved_message
            or (
                ("schedule" in resolved_message or "calendar" in resolved_message)
                and ("email" in resolved_message or "inbox" in resolved_message)
                and "task" in resolved_message
            )
        )

        if wants_breakdown:
            intent = {
                **intent,
                "category": "B",
                "intent": "detailed_breakdown",
                "requires_tools": ["calendar", "gmail", "tasks"]
            }
            category = "B"

        # Heuristic recovery when classifier misses actionable task/note intents.
        if category == "A":
            completion_markers = ["completed", "complete", "done", "finished", "mark", "check off", "checked off"]
            deletion_markers = ["delete", "remove", "erase"]

            if entities.get("task_descriptions") and any(marker in resolved_message for marker in completion_markers):
                intent = {
                    **intent,
                    "category": "B",
                    "intent": "complete_task",
                    "requires_tools": ["tasks"]
                }
                category = "B"
            elif "note" in resolved_message and any(marker in resolved_message for marker in deletion_markers):
                intent = {
                    **intent,
                    "category": "B",
                    "intent": "delete_note",
                    "requires_tools": ["notes"]
                }
                category = "B"
            else:
                # Catch meeting-creation phrases that the classifier missed
                meeting_create_phrases = (
                    "create meeting", "create a meeting", "schedule meeting",
                    "schedule a meeting", "set up meeting", "set up a meeting",
                    "book meeting", "book a meeting", "gmeet", "google meet",
                    "video call", "meet link", "invite on meeting",
                    "invite to meeting", "create a call", "schedule a call",
                )
                if any(phrase in resolved_message for phrase in meeting_create_phrases):
                    intent = {
                        **intent,
                        "category": "B",
                        "intent": "create_event",
                        "requires_tools": ["calendar"]
                    }
                    category = "B"
        
        # Category A: General conversation - no tool execution needed
        if category == "A":
            return {
                "type": "conversation",
                "requires_execution": False,
                "response_mode": "direct",
                "context_for_response": context
            }
        
        # Category B: Tool execution needed
        intent_name = intent.get("intent", "unknown")
        
        # send_email: Don't execute tools — let the Synthesizer generate
        # the draft via <email_draft> XML. The user sends from the Console.
        if intent_name in ("send_email", "compose_email", "draft_email"):
            return {
                "type": "conversation",
                "requires_execution": False,
                "response_mode": "email_draft",
                "context_for_response": context,
                "goal": "Draft an email based on the user's request",
            }
        
        tools_needed = intent.get("requires_tools", [])
        resolved_entities = intent.get("resolved_entities", {})
        
        # Merge entities
        all_entities = {**entities, **resolved_entities}
        
        # Pass user_profile into plan generation
        user_profile = context.get("user_profile", {})
        
        # Try to match to a template first
        plan = await self._match_template(intent_name, tools_needed, all_entities)
        
        if not plan:
            # Generate custom plan with LLM
            plan = await self._generate_plan(context)
        
        # Post-process: ensure conference_data=true on any calendar.create_event step
        for step in plan.get("steps", []):
            if step.get("action") == "calendar.create_event":
                step.setdefault("params", {})
                step["params"]["conference_data"] = True
        
        logger.info("Decomposed request", 
                   plan_type=plan.get("type"),
                   steps_count=len(plan.get("steps", [])))
        
        return plan
    
    @staticmethod
    def _build_datetime(entities: dict) -> tuple[str | None, str | None]:
        """Combine separate date and time entities into ISO datetime strings.

        The entity extractor often returns dates and times as separate
        arrays (e.g. dates=["2026-05-01"], times=["15:00"]).  This helper
        merges them into start_time/end_time ISO strings that the Calendar
        API can accept.
        """
        # If the entities already have explicit start_time / end_time, use them.
        if entities.get("start_time") and entities.get("end_time"):
            return entities["start_time"], entities["end_time"]

        from datetime import datetime as _dt, timedelta as _td

        dates = entities.get("dates", [])
        times = entities.get("times", [])

        base_date = dates[0] if dates else None
        start_time_str = times[0] if times else None
        end_time_str = times[1] if len(times) > 1 else None

        start_iso: str | None = None
        end_iso: str | None = None

        if base_date and start_time_str:
            try:
                start_iso = f"{base_date}T{start_time_str}:00"
                if end_time_str:
                    end_iso = f"{base_date}T{end_time_str}:00"
                else:
                    # Default meeting duration: 1 hour
                    from dateutil.parser import isoparse
                    end_iso = (isoparse(start_iso) + _td(hours=1)).isoformat()
            except Exception:
                pass
        elif base_date:
            # Date but no time — default to 09:00-10:00
            start_iso = f"{base_date}T09:00:00"
            end_iso = f"{base_date}T10:00:00"
        elif start_time_str:
            # Time but no date — assume today
            today = _dt.utcnow().strftime("%Y-%m-%d")
            start_iso = f"{today}T{start_time_str}:00"
            if end_time_str:
                end_iso = f"{today}T{end_time_str}:00"
            else:
                from dateutil.parser import isoparse
                end_iso = (isoparse(start_iso) + _td(hours=1)).isoformat()

        # Also check for the direct keys the LLM entity extractor
        # sometimes provides.
        if not start_iso and entities.get("start_time"):
            start_iso = entities["start_time"]
        if not end_iso and entities.get("end_time"):
            end_iso = entities["end_time"]

        return start_iso, end_iso

    async def _match_template(
        self,
        intent_name: str,
        tools_needed: list[str],
        entities: dict
    ) -> Optional[dict]:
        """Match the intent to a predefined template."""
        
        # Map intents to templates
        intent_template_map = {
            "list_events": "check_calendar",
            "check_calendar": "check_calendar",
            "check_meetings": "check_calendar",
            "view_schedule": "check_calendar",
            "create_event": "create_meeting",
            "schedule_meeting": "create_meeting",
            "create_meeting": "create_meeting",
            "quick_add": "quick_add_event",
            "check_email": "check_email",
            "search_email": "check_email",
            "summarize_inbox": "summarize_inbox",
            "inbox_summary": "summarize_inbox",
            "read_email": "read_email",
            "get_email": "read_email",
            "email_details": "email_details",
            "open_email": "email_details",
            "email_detail": "email_details",
            "send_email": "send_email",
            "compose_email": "send_email",
            "add_task": "add_task",
            "create_task": "add_task",
            "list_tasks": "list_tasks",
            "show_tasks": "list_tasks",
            "set_reminder": "set_reminder",
            "remind_me": "set_reminder",
            "complete_task": "complete_task",
            "mark_task_done": "complete_task",
            "mark_task_complete": "complete_task",
            "task_done": "complete_task",
            "task_completed": "complete_task",
            "finish_task": "complete_task",
            "delete_note": "delete_note",
            "remove_note": "delete_note",
            "delete_notes": "delete_note",
            "remove_notes": "delete_note",
            "detailed_breakdown": "detailed_breakdown",
            "expand_executive_summary": "detailed_breakdown",
            "daily_briefing": "detailed_breakdown",
            "briefing": "detailed_breakdown",
            "save_note": "save_note",
            "take_note": "save_note",
            "search_notes": "search_notes",
            "find_notes": "search_notes"
        }
        
        template_key = intent_template_map.get(intent_name.lower())
        
        if not template_key and tools_needed:
            # Try to infer from tools
            if all(tool in tools_needed for tool in ["calendar", "gmail", "tasks"]):
                template_key = "detailed_breakdown"
            elif "calendar" in tools_needed:
                template_key = "check_calendar"
            elif "gmail" in tools_needed:
                template_key = "check_email"

        # For meeting creation, pre-compute start/end from entity fragments
        if template_key == "create_meeting":
            start_iso, end_iso = self._build_datetime(entities)
            if start_iso:
                entities["start_time"] = start_iso
            if end_iso:
                entities["end_time"] = end_iso
        
        if template_key and template_key in PLAN_TEMPLATES:
            template = PLAN_TEMPLATES[template_key]
            
            # Build execution plan from template
            steps = []
            for step in template["steps"]:
                step_params = {}
                for param in step["params"]:
                    if param in entities:
                        step_params[param] = entities[param]
                    elif param == "title" and entities.get("task_descriptions"):
                        step_params[param] = entities["task_descriptions"][0]
                    elif param == "title" and entities.get("meeting_names"):
                        step_params[param] = entities["meeting_names"][0]
                    elif param == "summary" and entities.get("meeting_names"):
                        step_params[param] = entities["meeting_names"][0]
                    elif param == "summary" and entities.get("task_descriptions"):
                        step_params[param] = entities["task_descriptions"][0]
                    elif param == "query" and entities.get("search_queries"):
                        step_params[param] = entities["search_queries"][0]
                    elif param == "query" and entities.get("email_subjects"):
                        step_params[param] = entities["email_subjects"][0]
                    elif param == "query" and entities.get("task_descriptions"):
                        step_params[param] = entities["task_descriptions"][0]
                    elif param == "text" and entities.get("task_descriptions"):
                        step_params[param] = entities["task_descriptions"][0]
                    elif param == "text" and entities.get("meeting_names"):
                        step_params[param] = entities["meeting_names"][0]
                    elif param == "time_min" and entities.get("start_time"):
                        step_params[param] = entities["start_time"]
                    elif param == "time_max" and entities.get("end_time"):
                        step_params[param] = entities["end_time"]
                    elif param == "start_time" and entities.get("start_time"):
                        step_params[param] = entities["start_time"]
                    elif param == "end_time" and entities.get("end_time"):
                        step_params[param] = entities["end_time"]
                    elif param == "attendees" and entities.get("emails"):
                        step_params[param] = entities["emails"]
                    elif param == "attendees" and entities.get("people"):
                        step_params[param] = entities["people"]
                    elif param == "conference_data":
                        # Default to True for meetings — users expect a Meet link
                        step_params[param] = True
                    elif param == "hours":
                        step_params[param] = 24
                    elif param == "show_completed":
                        step_params[param] = False
                    elif param == "max_results":
                        step_params[param] = 20
                    elif param == "to" and entities.get("emails"):
                        step_params[param] = entities["emails"]
                    elif param == "subject":
                        if entities.get("email_subjects"):
                            step_params[param] = entities["email_subjects"][0]
                        elif entities.get("task_descriptions"):
                            step_params[param] = entities["task_descriptions"][0]
                    elif param == "body":
                        if entities.get("email_bodies"):
                            step_params[param] = entities["email_bodies"][0]
                        elif entities.get("task_descriptions") and len(entities["task_descriptions"]) > 1:
                            step_params[param] = entities["task_descriptions"][-1]
                    
                    # If param is thread_id, we need to defer to _generate_plan if missing
                    if param == "thread_id" and "thread_id" not in step_params:
                        return None
                
                # Validation for critical params — return None to fall through
                # to the LLM-based _generate_plan which can infer missing data.
                action = step["action"]
                if action == "tasks.add_task" and "title" not in step_params:
                    return None
                if action == "calendar.check_availability" and ("time_min" not in step_params or "time_max" not in step_params):
                    return None
                if action == "gmail.get_thread" and "thread_id" not in step_params:
                    return None
                if action == "gmail.get_email_details_by_query" and "query" not in step_params:
                    return None
                if action == "gmail.send_email" and ("to" not in step_params or "subject" not in step_params or "body" not in step_params):
                    return None
                if action == "calendar.create_event" and ("summary" not in step_params or "start_time" not in step_params or "end_time" not in step_params):
                    # Missing date/time info — let LLM figure it out
                    return None
                if action == "tasks.set_reminder" and ("title" not in step_params or "remind_at" not in step_params):
                    return None
                if action == "tasks.complete_task_by_title" and "title" not in step_params:
                    return None
                if action == "notes.save_note" and ("title" not in step_params or "content" not in step_params):
                    return None
                if action == "notes.delete_note_by_query" and "query" not in step_params:
                    return None

                steps.append({
                    "action": step["action"],
                    "params": step_params,
                    "status": "pending"
                })
            
            return {
                "type": "tool_execution",
                "requires_execution": True,
                "template": template_key,
                "name": template["name"],
                "steps": steps,
                "entities": entities
            }
        
        return None
    
    async def _generate_plan(self, context: dict) -> dict:
        """Generate a custom execution plan using LLM."""
        import datetime
        import zoneinfo
        
        user_profile = context.get("user_profile", {})
        timezone_str = user_profile.get("settings", {}).get("timezone", "UTC")
        user_name = user_profile.get("name", "User")
        user_email = user_profile.get("email", "")
        
        tz = None
        try:
            # Try to load the timezone from zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            try:
                # Fallback to standard IANA timezone if provided
                tz = zoneinfo.ZoneInfo("Etc/UTC")
            except Exception:
                # Last resort: use datetime.timezone.utc
                tz = datetime.timezone.utc
            
        current_dt = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        system_instruction = f"""You are a task decomposition agent for a personal assistant.
Given a user request and context, create an execution plan.
The user's name is {user_name} ({user_email}). When drafting emails, ensure you use the user's name ({user_name}) as the sender and choose an appropriate contextual subject.
IMPORTANT: If the user asks you to draft or generate an email subject and body, you MUST write the complete, natural-sounding, and professional email content directly into the 'subject' and 'body' parameters of the `gmail.send_email` action. DO NOT use generic placeholders like "Generated by AI", "[Subject here]", or "[Body here]". Generate the actual final text.
The current date and time is {current_dt}.

Available tools:
- calendar.list_events(time_min, time_max, max_results, query)
- calendar.create_event(summary, start_time, end_time, description, attendees, conference_data)  # Set conference_data=true to generate a Google Meet link. MUST use this for meetings instead of tasks.
- calendar.quick_add(text)
- calendar.check_availability(time_min, time_max)
- gmail.search_messages(query, max_results)  # ALWAYS use first to find messages or thread_ids
- gmail.get_thread(thread_id)  # ONLY use if you ALREADY KNOW the exact hex thread_id string
- gmail.get_email_details_by_query(query, max_results)  # PREFERRED for follow-ups like "tell me about that email" or "yes, provide details"
- gmail.summarize_inbox(hours)
- gmail.send_email(to, subject, body)
- tasks.add_task(title, notes, due_date)
- tasks.list_tasks(show_completed)
- tasks.set_reminder(title, remind_at)
- tasks.complete_task(task_id) # ONLY use if you ALREADY KNOW the exact task_id string, otherwise run tasks.list_tasks first
- tasks.complete_task_by_title(title, task_list_id) # PREFERRED for user commands like "I completed <task name>"
- notes.save_note(title, content, tags)
- notes.query_knowledge_base(query)
- notes.delete_note(note_id) # ONLY use if you ALREADY KNOW the exact note_id string, otherwise run notes.query_knowledge_base first
- notes.delete_note_by_query(query, delete_all_matches) # PREFERRED for commands like "delete my <note topic> notes"

Output a JSON execution plan:
{{
    "type": "tool_execution",
    "requires_execution": true,
    "name": "Plan Name",
    "steps": [
        {{
            "action": "tool.method",
            "params": {{"param1": "value1"}},
            "description": "What this step does"
        }}
    ]
}}

Extract parameter values from the context when available.
If the user asks you to draft or generate content (like an email body or event description), you MUST write/generate that content yourself and include it in the parameters.
If the user asks to save a note from the previous conversation (e.g. "add that to my notes"), you MUST extract the actual detailed content from the Recent Conversation history and place it entirely into the 'content' parameter. DO NOT just put the title into the content.
If the user mentions "meeting", "meet link", "gmeet", "google meet", "video call", or any meeting-related phrase, you MUST output an action for `calendar.create_event` and ALWAYS set `"conference_data": true` in the parameters instead of adding a task! EVERY meeting MUST have conference_data=true to generate a Google Meet link.
For dates/times, use ISO format (YYYY-MM-DDTHH:MM:SS).
Output valid JSON only."""

        # Extract chat history to give context for requests like "add it to notes" 
        chat_history = context.get('chat_history', [])
        chat_history_str = ""
        if chat_history:
            chat_history_str = "\nRecent Conversation:\n" + "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-3:]])

        prompt = f"""User request: {context.get('resolved_message')}{chat_history_str}

Entities extracted: {context.get('entities')}

Intent: {context.get('intent')}

Create an execution plan:"""

        response = await self.llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2,
            max_tokens=1200,
        )
        
        import json
        import re
        try:
            response = response.strip()
            # Try to extract content between triple backticks if present
            if "```" in response:
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    response = match.group(1)
            # Find the first '{' and last '}' to handle any conversational wrapper
            start_idx = response.find("{")
            end_idx = response.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx+1]
                
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse execution plan", response=response)
            return {
                "type": "tool_execution",
                "requires_execution": True,
                "name": "Custom Plan",
                "steps": [],
                "error": "Could not parse execution plan"
            }
    
    def validate_plan(self, plan: dict) -> tuple[bool, str]:
        """
        Validate an execution plan before execution.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not plan:
            return False, "Empty plan"
        
        if plan.get("type") == "conversation":
            return True, ""
        
        steps = plan.get("steps", [])
        if not steps:
            return False, "No steps in plan"
        
        # Validate each step
        valid_tools = {
            "calendar.list_events", "calendar.create_event", "calendar.quick_add",
            "calendar.check_availability", "calendar.update_event", "calendar.delete_event",
            "gmail.search_messages", "gmail.get_thread", "gmail.get_message",
            "gmail.get_email_details_by_query", "gmail.summarize_inbox", "gmail.send_email",
            "tasks.add_task", "tasks.list_tasks", "tasks.update_task",
            "tasks.complete_task", "tasks.complete_task_by_title", "tasks.set_reminder",
            "notes.save_note", "notes.query_knowledge_base", "notes.list_notes", "notes.delete_note", "notes.delete_note_by_query"
        }

        for i, step in enumerate(steps):
            action = step.get("action", "")
            if action not in valid_tools:
                return False, f"Invalid action in step {i + 1}: {action}"
        
        return True, ""
