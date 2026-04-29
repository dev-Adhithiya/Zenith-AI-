"""
Synthesizer Agent for Zenith AI
Phase 3: Synthesis & Response - Generates natural language responses
"""
from typing import Optional
import structlog

from .vertex_ai import VertexAIClient, get_vertex_client
from memory.preferences import PreferencesStore

logger = structlog.get_logger()


class SynthesizerAgent:
    """
    Synthesizer Agent - Responsible for Phase 3: Synthesis & Response
    
    Responsibilities:
    - Generate natural language responses
    - Summarize tool execution results
    - Maintain conversational tone
    """
    
    def __init__(self, vertex_client: Optional[VertexAIClient] = None):
        self.llm = vertex_client or get_vertex_client()
        
        self.system_instruction = """You are Zenith, an elite, highly intelligent Personal Assistant AI.
Your tone is proactive, concise, warm, and highly competent.

Guidelines:
- Be conversational and natural, not robotic
- Keep responses concise but informative
- Proactively offer helpful follow-up actions
- When presenting data (emails, events, tasks), format it clearly
- Use appropriate emoji sparingly for warmth 📅✉️✅
- If something failed, explain clearly and suggest alternatives
- Remember context from the conversation
- NEVER hallucinate or arbitrarily invent URLs, meeting links, or facts. Only mention links or details if they are explicitly present in the provided execution results.

When presenting lists:
- Use bullet points for clarity
- Include key details (dates, times, people)
- Highlight what's important or urgent"""
    
    async def synthesize(
        self,
        context: dict,
        execution_results: Optional[dict] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a natural language response.
        
        Args:
            context: Context dictionary from ContextAgent
            execution_results: Results from tool execution (if any)
            custom_prompt: Optional custom prompt to override default behavior
            
        Returns:
            Natural language response
        """
        user_message = context.get("original_message", "")
        resolved_message = context.get("resolved_message", user_message)
        chat_history = context.get("chat_history", [])
        intent = context.get("intent", {})
        dynamic_system_instruction = self._build_system_instruction(
            user_preferences=context.get("user_preferences"),
            email_draft=context.get("email_draft")
        )
        
        # Use custom prompt if provided
        if custom_prompt:
            prompt = custom_prompt
        # Build prompt based on whether we have execution results
        elif execution_results:
            prompt = await self._build_results_prompt(
                user_message=resolved_message,
                results=execution_results
            )
        else:
            prompt = self._build_conversation_prompt(
                resolved_message=resolved_message,
                preference_updates=context.get("preference_updates"),
            )
        
        response = await self.llm.generate(
            prompt=prompt,
            system_instruction=dynamic_system_instruction,
            chat_history=chat_history,
            temperature=0.65 if execution_results is None else 0.45,
            max_tokens=1200 if execution_results is None else 900,
            images=context.get("images")
        )
        
        logger.info("Synthesized response", response_length=len(response))
        
        return response

    def _build_system_instruction(
        self, 
        user_preferences: Optional[dict],
        email_draft: Optional[dict] = None
    ) -> str:
        preferences_text = PreferencesStore.build_prompt_context(user_preferences)
        base_instruction = self.system_instruction
        
        if preferences_text:
            base_instruction = (
                f"{self.system_instruction}\n\n"
                "Known user preferences and long-term memory:\n"
                f"{preferences_text}\n"
                "Use these preferences when they are relevant, even across new chats. "
                "Do not mention them unless they help answer the request."
            )
            
        if email_draft:
            base_instruction += (
                "\n\nCRITICAL CONSTRAINTS FOR EMAIL DRAFTING:\n"
                "The user is currently composing an email in the split-screen console.\n"
                f"Current Draft State:\n"
                f"- To: {email_draft.get('to', '')}\n"
                f"- Subject: {email_draft.get('subject', '')}\n"
                f"- Body: {email_draft.get('body', '')}\n\n"
                "When responding, if the user asks to update or write the email, you MUST update the draft state by appending an XML block at the very end of your response exactly like this:\n"
                "<email_draft>\n"
                "{\n"
                '  "to": "recipient@example.com",\n'
                '  "subject": "Email Subject",\n'
                '  "body": "The full updated email body here."\n'
                "}\n"
                "</email_draft>\n"
                "Strictly preserve all content from the current draft that the user did not ask to change. Output ONLY valid JSON inside the XML block."
            )
            
        return base_instruction

    def _build_conversation_prompt(
        self,
        resolved_message: str,
        preference_updates: Optional[dict] = None,
    ) -> str:
        if not preference_updates:
            return resolved_message

        memory_profile = preference_updates.get("memory_profile", {})
        lines: list[str] = []
        for label, key in (
            ("likes", "likes"),
            ("dislikes", "dislikes"),
            ("avoid", "avoid"),
            ("preferences", "preferences"),
            ("notes", "notes"),
        ):
            values = memory_profile.get(key, [])
            if values:
                lines.append(f"- {label}: {', '.join(values)}")

        if not lines:
            return resolved_message

        memory_lines = "\n".join(lines)
        return (
            "The user just shared a durable personal preference or memory.\n"
            "Acknowledge briefly that you will remember it for future chats, then respond naturally.\n"
            "Captured memory:\n"
            f"{memory_lines}\n\n"
            f"User message: {resolved_message}"
        )
    
    async def _build_results_prompt(
        self,
        user_message: str,
        results: dict
    ) -> str:
        """Build a prompt that includes execution results."""
        
        prompt_parts = [f"User asked: {user_message}\n"]
        
        if results.get("pending_confirmation"):
            prompt_parts.append("I have prepared the requested actions but I need the user's confirmation before executing them.")
            for step in results.get("pending_steps", []):
                prompt_parts.append(f"- Will execute: {step.get('action')} with params {step.get('params')}")
            prompt_parts.append("Tell the user what you have drafted/prepared based on the pending parameters, and ask them if they would like to approve or edit.")
        elif not results.get("success"):
            # ERROR CASE: Execution failed
            prompt_parts.append(f"There was an error: {results.get('error', 'Unknown error')}\n")
        else:
            # SUCCESS CASE: Include the tool execution results
            prompt_parts.append("Tool execution was successful. Here are the results:\n")
            for step_result in results.get("step_results", []):
                action = step_result.get("action", "unknown")
                if step_result.get("success"):
                    data = step_result.get("data")
                    formatted_data = self._format_result_data(action, data)
                    prompt_parts.append(f"\n{action}:\n{formatted_data}")
                else:
                    error = step_result.get("error", "Unknown error")
                    prompt_parts.append(f"\n{action}: Failed - {error}")
        
        prompt_parts.append("\nGenerate a concise, informative response based on these results.")
        prompt_parts.append("Keep it brief and factual. No questions or follow-up suggestions.")
        
        return "\n".join(prompt_parts)
    
    def _format_result_data(self, action: str, data) -> str:
        """Format result data for the LLM prompt."""
        import json

        if action == "gmail.get_email_details_by_query":
            return self._format_email_details(data)
        
        if isinstance(data, list):
            if len(data) == 0:
                return "No results found.\n"
            
            # Format based on action type
            if "event" in action or "calendar" in action:
                return self._format_events(data)
            elif "message" in action or "email" in action or "gmail" in action:
                return self._format_emails(data)
            elif "task" in action:
                return self._format_tasks(data)
            elif "note" in action:
                return self._format_notes(data)
        
        elif isinstance(data, dict):
            # Single item or summary
            if "messages" in data:
                # Inbox summary
                return self._format_inbox_summary(data)
            elif "summary" in data:
                # Event
                return self._format_events([data])
            elif "subject" in data:
                # Email
                return self._format_emails([data])
        
        # Fallback to JSON
        return json.dumps(data, indent=2, default=str)[:1000]

    def _format_email_details(self, details: dict) -> str:
        """Format resolved email details for clear assistant output."""
        if not isinstance(details, dict):
            return "No email details available.\n"

        message = details.get("message") if isinstance(details.get("message"), dict) else details

        subject = message.get("subject", "(No subject)")
        sender = message.get("from", "Unknown sender")
        date = message.get("date", "")
        snippet = message.get("snippet", "")
        body_text = (message.get("body_text") or "").strip()
        thread_count = details.get("thread_message_count")

        lines = [
            f"Subject: {subject}",
            f"From: {sender}"
        ]

        if date:
            lines.append(f"Date: {date}")

        if thread_count:
            lines.append(f"Thread messages: {thread_count}")

        if snippet:
            lines.append(f"Snippet: {snippet}")

        if body_text:
            lines.append("Body:")
            lines.append(body_text[:1500])

        return "\n".join(lines) + "\n"
    
    def _format_events(self, events: list) -> str:
        """Format calendar events."""
        lines = []
        for event in events[:10]:
            start = event.get("start", "")
            summary = event.get("summary", "(No title)")
            location = event.get("location", "")
            meet_link = event.get("meet_link", "")
            html_link = event.get("html_link", "")
            
            line = f"- {summary} at {start}"
            if location:
                line += f" ({location})"
            if meet_link:
                line += f" [Meet link: {meet_link}]"
            elif html_link:
                line += f" [Event link: {html_link}]"
            lines.append(line)
        
        return "\n".join(lines) + "\n"
    
    def _format_emails(self, emails: list) -> str:
        """Format email messages."""
        lines = []
        for email in emails[:10]:
            subject = email.get("subject", "(No subject)")
            sender = email.get("from", "Unknown")
            snippet = email.get("snippet", "")[:100]
            is_unread = "🔵 " if email.get("is_unread") else ""
            
            lines.append(f"- {is_unread}{subject} from {sender}")
            if snippet:
                lines.append(f"  {snippet}...")
        
        return "\n".join(lines) + "\n"
    
    def _format_tasks(self, tasks: list) -> str:
        """Format tasks."""
        lines = []
        for task in tasks[:10]:
            title = task.get("title", "(No title)")
            due = task.get("due", "")
            status = "✅" if task.get("is_completed") else "⬜"
            
            line = f"- {status} {title}"
            if due:
                line += f" (due: {due})"
            lines.append(line)
        
        return "\n".join(lines) + "\n"
    
    def _format_notes(self, notes: list) -> str:
        """Format notes."""
        lines = []
        for note in notes[:5]:
            title = note.get("title", "(Untitled)")
            tags = note.get("tags", [])
            snippet = note.get("content", "")[:100]
            
            tag_str = " ".join([f"#{t}" for t in tags]) if tags else ""
            lines.append(f"- {title} {tag_str}")
            if snippet:
                lines.append(f"  {snippet}...")
        
        return "\n".join(lines) + "\n"
    
    def _format_inbox_summary(self, summary: dict) -> str:
        """Format inbox summary."""
        lines = [
            f"Total messages: {summary.get('total_count', 0)}",
            f"Unread: {summary.get('unread_count', 0)}",
            f"Important: {summary.get('important_count', 0)}",
            "",
            "Top senders:"
        ]
        
        senders = summary.get("senders", {})
        for sender, count in sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"- {sender}: {count} messages")
        
        return "\n".join(lines) + "\n"
    
    async def generate_followup_suggestions(
        self,
        context: dict,
        execution_results: Optional[dict] = None
    ) -> list[str]:
        """Generate relevant follow-up action suggestions."""
        if not execution_results:
            return []
        
        system_instruction = """Based on the conversation and results, suggest 2-3 relevant follow-up actions.
Output as a JSON array of short action phrases.
Examples: ["Schedule a follow-up meeting", "Reply to John's email", "Add this to my tasks"]
Output valid JSON array only."""
        
        prompt_parts = [f"User asked: {context.get('resolved_message', '')}"]
        
        if execution_results and execution_results.get("success"):
            prompt_parts.append(f"Results: {str(execution_results)[:500]}")
        
        prompt_parts.append("\nSuggest relevant follow-up actions:")
        
        response = await self.llm.generate(
            prompt="\n".join(prompt_parts),
            system_instruction=system_instruction,
            temperature=0.5,
            max_tokens=256
        )
        
        import json
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            return []
