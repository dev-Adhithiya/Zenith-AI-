"""
Decomposer Agent for Zenith AI
Phase 2: Task Decomposition - Breaks goals into executable steps
"""
from typing import Optional
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
    "send_email": {
        "name": "Send Email",
        "steps": [
            {"action": "gmail.send_email", "params": ["to", "subject", "body"]}
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
    "save_note": {
        "name": "Save Note",
        "steps": [
            {"action": "notes.save_note", "params": ["title", "content", "tags"]}
        ]
    },
    "search_notes": {
        "name": "Search Notes",
        "steps": [
            {"action": "notes.query_knowledge_base", "params": ["query"]}
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
        category = intent.get("category", "A")
        
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
        tools_needed = intent.get("requires_tools", [])
        entities = context.get("entities", {})
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
        
        logger.info("Decomposed request", 
                   plan_type=plan.get("type"),
                   steps_count=len(plan.get("steps", [])))
        
        return plan
    
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
            "send_email": "send_email",
            "compose_email": "send_email",
            "add_task": "add_task",
            "create_task": "add_task",
            "list_tasks": "list_tasks",
            "show_tasks": "list_tasks",
            "set_reminder": "set_reminder",
            "remind_me": "set_reminder",
            "save_note": "save_note",
            "take_note": "save_note",
            "search_notes": "search_notes",
            "find_notes": "search_notes"
        }
        
        template_key = intent_template_map.get(intent_name.lower())
        
        if not template_key and tools_needed:
            # Try to infer from tools
            if "calendar" in tools_needed:
                template_key = "check_calendar"
            elif "gmail" in tools_needed:
                template_key = "check_email"
            elif "tasks" in tools_needed:
                template_key = "list_tasks"
            elif "notes" in tools_needed:
                template_key = "search_notes"
        
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
                    elif param == "query" and entities.get("search_queries"):
                        step_params[param] = entities["search_queries"][0]
                    elif param == "text" and entities.get("task_descriptions"):
                        step_params[param] = entities["task_descriptions"][0]
                    elif param == "text" and entities.get("meeting_names"):
                        step_params[param] = entities["meeting_names"][0]
                    elif param == "time_min" and entities.get("start_time"):
                        step_params[param] = entities["start_time"]
                    elif param == "time_max" and entities.get("end_time"):
                        step_params[param] = entities["end_time"]
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
                
                # Validation for critical params
                action = step["action"]
                if action == "tasks.add_task" and "title" not in step_params:
                    return None
                if action == "calendar.check_availability" and ("time_min" not in step_params or "time_max" not in step_params):
                    return None
                if action == "gmail.get_thread" and "thread_id" not in step_params:
                    return None
                if action == "gmail.send_email" and ("to" not in step_params or "subject" not in step_params or "body" not in step_params):
                    return None
                if action == "calendar.create_event" and ("summary" not in step_params or "start_time" not in step_params or "end_time" not in step_params):
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
The current date and time is {current_dt}.

Available tools:
- calendar.list_events(time_min, time_max, max_results, query)
- calendar.create_event(summary, start_time, end_time, description, attendees, conference_data)  # Set conference_data=true to generate a Google Meet link. MUST use this for meetings instead of tasks.
- calendar.quick_add(text)
- calendar.check_availability(time_min, time_max)
- gmail.search_messages(query, max_results)  # ALWAYS use first to find messages or thread_ids
- gmail.get_thread(thread_id)  # ONLY use if you ALREADY KNOW the exact hex thread_id string
- gmail.summarize_inbox(hours)
- gmail.send_email(to, subject, body)
- tasks.add_task(title, notes, due_date)
- tasks.list_tasks(show_completed)
- tasks.set_reminder(title, remind_at)
- notes.save_note(title, content, tags)
- notes.query_knowledge_base(query)

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
If the user mentions "meeting", "meet link", or "video call", you MUST output an action for `calendar.create_event` and explicitly set `"conference_data": true` in the parameters instead of adding a task!
For dates/times, use ISO format (YYYY-MM-DDTHH:MM:SS).
Output valid JSON only."""

        prompt = f"""User request: {context.get('resolved_message')}

Entities extracted: {context.get('entities')}

Intent: {context.get('intent')}

Create an execution plan:"""

        response = await self.llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2
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
            "gmail.summarize_inbox", "gmail.send_email",
            "tasks.add_task", "tasks.list_tasks", "tasks.update_task",
            "tasks.complete_task", "tasks.set_reminder",
            "notes.save_note", "notes.query_knowledge_base", "notes.list_notes"
        }
        
        for i, step in enumerate(steps):
            action = step.get("action", "")
            if action not in valid_tools:
                return False, f"Invalid action in step {i + 1}: {action}"
        
        return True, ""
