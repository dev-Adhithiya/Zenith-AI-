"""
Context Agent for Zenith AI
Phase 1: Context Gathering - Resolves context from chat history and knowledge base
"""
from typing import Optional
import structlog

from .vertex_ai import VertexAIClient, get_vertex_client
from memory.conversation import ConversationMemory
from memory.preferences import PreferencesStore
from tools.notes import NotesTools

logger = structlog.get_logger()


class ContextAgent:
    """
    Context Agent - Responsible for Phase 1: Context Gathering
    
    Responsibilities:
    - Resolve pronouns and references from chat history
    - Query knowledge base for relevant past context
    - Identify which meeting/email/entity the user is referring to
    """
    
    def __init__(
        self,
        vertex_client: Optional[VertexAIClient] = None,
        conversation_memory: Optional[ConversationMemory] = None,
        notes_tools: Optional[NotesTools] = None
    ):
        self.llm = vertex_client or get_vertex_client()
        self.memory = conversation_memory or ConversationMemory()
        self.notes = notes_tools or NotesTools()
    
    async def gather_context(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        include_knowledge_base: bool = True,
        user_profile: dict = None,
        images: Optional[list[dict]] = None,
        user_preferences: Optional[dict] = None,
        email_draft: Optional[dict] = None
    ) -> dict:
        """
        Gather all relevant context for processing a user message.
        
        Args:
            user_id: User's unique identifier
            session_id: Current conversation session ID
            user_message: The user's message
            include_knowledge_base: Whether to query knowledge base
            user_profile: The user profile dictionary
            images: Optional list of image dicts with 'content' and 'content_type' keys
            
        Returns:
            Context dictionary with resolved message, history, and relevant data
        """
        logger.info("Gathering context", user_id=user_id, session_id=session_id)
        
        if user_profile is None:
            user_profile = {}
        
        # Step 1: Get chat history
        chat_history = await self.memory.get_context_window(
            user_id=user_id,
            session_id=session_id,
            max_messages=8
        )
        chat_history = self._trim_chat_history(chat_history)
        
        # Step 2: Resolve context (pronouns, references)
        resolved_message = await self._resolve_references(
            user_message=user_message,
            chat_history=chat_history
        )

        quick_intent = self._quick_classify_intent(resolved_message)

        if quick_intent and quick_intent.get("category") == "A":
            context = {
                "original_message": user_message,
                "resolved_message": resolved_message,
                "chat_history": chat_history,
                "entities": {},
                "relevant_notes": [],
                "intent": quick_intent,
                "user_id": user_id,
                "session_id": session_id,
                "user_profile": user_profile,
                "user_preferences": user_preferences or {},
                "images": images or [],
                "email_draft": email_draft
            }
            logger.info(
                "Context gathered via fast path",
                intent_category=quick_intent.get("category"),
                intent=quick_intent.get("intent"),
                has_history=len(chat_history) > 0,
            )
            return context
        
        # Step 3: Extract entities mentioned
        entities = await self._extract_entities(resolved_message, user_profile)
        
        # Step 4: Query knowledge base if needed
        relevant_notes = []
        if (
            include_knowledge_base
            and entities.get("search_queries")
            and self._should_query_knowledge_base(quick_intent, resolved_message)
        ):
            for query in entities.get("search_queries", []):
                notes = await self.notes.query_knowledge_base(
                    user_id=user_id,
                    query=query,
                    limit=3
                )
                relevant_notes.extend(notes)
        
        # Step 5: Classify intent
        intent = quick_intent or await self.llm.classify_intent(
            user_message=resolved_message,
            chat_history=chat_history
        )
        
        context = {
            "original_message": user_message,
            "resolved_message": resolved_message,
            "chat_history": chat_history,
            "entities": entities,
            "relevant_notes": relevant_notes,
            "intent": intent,
            "user_id": user_id,
            "session_id": session_id,
            "user_profile": user_profile,
            "user_preferences": user_preferences or {},
            "images": images or [],
            "email_draft": email_draft
        }
        
        logger.info("Context gathered", 
                   intent_category=intent.get("category"),
                   intent=intent.get("intent"),
                   has_history=len(chat_history) > 0)
        
        return context

    @staticmethod
    def _trim_chat_history(chat_history: list[dict], max_chars_per_message: int = 600) -> list[dict]:
        """Keep recent history useful without letting long messages bloat prompts."""
        trimmed: list[dict] = []
        for message in chat_history[-8:]:
            content = (message.get("content") or "").strip()
            if len(content) > max_chars_per_message:
                content = content[: max_chars_per_message - 3].rstrip() + "..."
            trimmed.append({
                "role": message.get("role", "user"),
                "content": content,
            })
        return trimmed

    def _quick_classify_intent(self, user_message: str) -> Optional[dict]:
        """Fast heuristic classifier to avoid extra model hops on obvious requests."""
        message = " ".join(user_message.lower().split())
        if not message:
            return None

        if PreferencesStore.looks_like_preference_statement(message):
            return {
                "category": "A",
                "intent": "preference_update",
                "requires_tools": [],
                "confidence": 0.95,
                "resolved_entities": {},
            }

        email_keywords = ("email", "emails", "mail", "gmail", "inbox", "unread", "sender", "subject")
        calendar_keywords = ("calendar", "meeting", "meet", "schedule", "event", "availability", "gmeet", "google meet", "video call", "conference call")
        task_keywords = ("task", "tasks", "todo", "to-do", "remind", "reminder")
        note_keywords = ("note", "notes", "knowledge base")

        # Check for email-composing intent first (broader match)
        send_email_phrases = (
            "send email", "send mail", "send a mail", "send an email",
            "draft email", "draft mail", "draft a mail", "draft an email",
            "compose email", "compose mail", "compose a mail",
            "write email", "write mail", "write a mail", "write an email",
            "reply to",
        )
        if any(phrase in message for phrase in send_email_phrases):
            return {
                "category": "B",
                "intent": "send_email",
                "requires_tools": ["gmail"],
                "confidence": 0.92,
                "resolved_entities": {},
            }

        # Check for forced intents from UI Tools
        if "[force intent: meeting]" in message:
            return {
                "category": "B",
                "intent": "create_event",
                "requires_tools": ["calendar"],
                "confidence": 1.0,
                "resolved_entities": {},
            }
        elif "[force intent: task]" in message:
            return {
                "category": "B",
                "intent": "add_task",
                "requires_tools": ["tasks"],
                "confidence": 1.0,
                "resolved_entities": {},
            }
        elif "[force intent: notes]" in message:
            return {
                "category": "B",
                "intent": "save_note",
                "requires_tools": ["notes"],
                "confidence": 1.0,
                "resolved_entities": {},
            }
        elif "[force intent: email]" in message:
            return {
                "category": "B",
                "intent": "send_email",
                "requires_tools": ["gmail"],
                "confidence": 1.0,
                "resolved_entities": {},
            }

        # Check for calendar-composing intent explicitly before email keywords
        # to avoid misclassifying "create meeting with user@gmail.com" as an email task.
        meeting_create_phrases = ("create", "schedule", "set up", "book", "invite", "arrange", "organize", "set a", "make a")
        if any(keyword in message for keyword in calendar_keywords) and any(phrase in message for phrase in meeting_create_phrases):
            return {
                "category": "B",
                "intent": "create_event",
                "requires_tools": ["calendar"],
                "confidence": 0.95,
                "resolved_entities": {},
            }

        # Catch standalone meeting-creation phrases even without explicit calendar keywords
        # e.g. "create a meeting tomorrow", "set up a gmeet", "book a video call"
        standalone_meeting_phrases = (
            "create meeting", "create a meeting", "schedule meeting", "schedule a meeting",
            "set up meeting", "set up a meeting", "book meeting", "book a meeting",
            "create gmeet", "create a gmeet", "create google meet",
            "set up a call", "book a call", "schedule a call",
            "create a video call", "schedule video call",
            "invite on meeting", "invite to meeting",
        )
        if any(phrase in message for phrase in standalone_meeting_phrases):
            return {
                "category": "B",
                "intent": "create_event",
                "requires_tools": ["calendar"],
                "confidence": 0.95,
                "resolved_entities": {},
            }

        # Email keyword check — but skip if message is primarily about meetings
        # (avoids misclassifying "invite user@gmail.com to meeting" as email intent)
        if any(keyword in message for keyword in email_keywords) and not any(kw in message for kw in ("meeting", "meet", "calendar", "event", "gmeet")):
            if any(phrase in message for phrase in ("send email", "draft email", "reply to", "compose email")):
                intent_name = "send_email"
            elif any(phrase in message for phrase in ("details", "open that email", "show that email", "tell me about")):
                intent_name = "email_details"
            elif any(phrase in message for phrase in ("summarize", "summary", "inbox summary", "unread")):
                intent_name = "summarize_inbox"
            else:
                intent_name = "check_email"
            return {
                "category": "B",
                "intent": intent_name,
                "requires_tools": ["gmail"],
                "confidence": 0.88,
                "resolved_entities": {},
            }

        if any(keyword in message for keyword in calendar_keywords):
            # create_event is now handled above for stronger phrases
            return {
                "category": "B",
                "intent": "check_calendar",
                "requires_tools": ["calendar"],
                "confidence": 0.88,
                "resolved_entities": {},
            }

        if any(keyword in message for keyword in task_keywords):
            if any(phrase in message for phrase in ("remind", "reminder")):
                intent_name = "set_reminder"
            elif any(phrase in message for phrase in ("complete", "completed", "done", "finished")):
                intent_name = "complete_task"
            elif any(phrase in message for phrase in ("show", "list", "what are my tasks")):
                intent_name = "list_tasks"
            else:
                intent_name = "add_task"
            return {
                "category": "B",
                "intent": intent_name,
                "requires_tools": ["tasks"],
                "confidence": 0.86,
                "resolved_entities": {},
            }

        if any(keyword in message for keyword in note_keywords):
            if any(phrase in message for phrase in ("save", "write down", "take note", "add note")):
                intent_name = "save_note"
            else:
                intent_name = "search_notes"
            return {
                "category": "B",
                "intent": intent_name,
                "requires_tools": ["notes"],
                "confidence": 0.84,
                "resolved_entities": {},
            }

        return {
            "category": "A",
            "intent": "conversation",
            "requires_tools": [],
            "confidence": 0.72,
            "resolved_entities": {},
        }

    @staticmethod
    def _should_query_knowledge_base(intent: Optional[dict], resolved_message: str) -> bool:
        if not intent:
            return False
        if "notes" in intent.get("requires_tools", []):
            return True
        message = resolved_message.lower()
        return any(
            phrase in message
            for phrase in ("knowledge base", "my notes", "saved notes", "remember this note")
        )
    
    async def _resolve_references(
        self,
        user_message: str,
        chat_history: list[dict]
    ) -> str:
        """Resolve pronouns and references using chat history."""
        if not chat_history:
            return user_message
        
        # Check if message likely has unresolved references
        reference_words = ["it", "this", "that", "they", "them", "he", "she", "the"]
        message_lower = user_message.lower()
        
        has_references = any(
            f" {word} " in f" {message_lower} " or 
            message_lower.startswith(f"{word} ") or
            message_lower.endswith(f" {word}")
            for word in reference_words
        )
        
        # Also check for question words that might need context
        question_starters = ["what", "when", "where", "how", "who", "why"]
        is_followup_question = any(
            message_lower.startswith(word) 
            for word in question_starters
        )

        confirmation_starters = ["yes", "yeah", "yep", "sure", "ok", "okay", "go ahead", "please", "uh"]
        detail_markers = ["details", "detail", "more", "open", "show", "provide"]
        is_confirmation_followup = any(
            message_lower.startswith(word)
            for word in confirmation_starters
        ) and any(marker in message_lower for marker in detail_markers)

        is_short_followup = len(message_lower.split()) <= 8 and any(
            token in message_lower for token in ["that", "it", "details", "more"]
        )
        
        if has_references or is_followup_question or is_confirmation_followup or is_short_followup:
            return await self.llm.resolve_context(
                user_message=user_message,
                chat_history=chat_history
            )
        
        return user_message
    
    async def _extract_entities(self, message: str, user_profile: dict = None) -> dict:
        """Extract named entities and search queries from the message."""
        import datetime
        import zoneinfo
        
        timezone_str = user_profile.get("settings", {}).get("timezone", "UTC") if user_profile else "UTC"
        
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
        
        system_instruction = f"""Extract entities from the user message for a personal assistant.
The current date and time is {current_dt}.  Use this as a reference point for relative dates (today, tomorrow, next week).
If the user asks to generate or draft an email, you may invent a professional 'subject' and 'body' in the output arrays rather than using placeholders like 'Generated by AI'.
Output a JSON object with:
{{
    "dates": ["YYYY-MM-DD", ...],  // Any dates mentioned
    "times": ["HH:MM", ...],  // Any times mentioned
    "people": ["name", ...],  // Names of people
    "emails": ["email@example.com", ...],  // Email addresses
    "meeting_names": ["meeting title", ...],  // Meeting/event names
    "task_descriptions": ["task", ...],  // Task descriptions
    "search_queries": ["query", ...],  // Key phrases to search for
    "email_subjects": ["subject", ...], // Email subjects
    "email_bodies": ["message content", ...] // Any text dictated for an email body or drafting content
}}

Only include non-empty arrays. Output valid JSON only."""

        response = await self.llm.generate(
            prompt=f"Message: {message}",
            system_instruction=system_instruction,
            temperature=0.1,
            max_tokens=700,
        )
        
        import json
        import re as _re
        try:
            response = response.strip()
            # Robust JSON extraction: find the first {...} block
            json_match = _re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse entities", response=response)
            return {"search_queries": [message[:100]]}
    
    async def find_relevant_data(
        self,
        user_id: str,
        credentials: dict,
        context: dict
    ) -> dict:
        """
        Find relevant data from user's Google services based on context.
        
        This method is called when we need to look up specific data
        mentioned in the user's request.
        """
        from tools.calendar import CalendarTools
        from tools.gmail import GmailTools
        from datetime import datetime, timedelta
        
        relevant_data = {
            "events": [],
            "emails": [],
            "notes": context.get("relevant_notes", [])
        }
        
        entities = context.get("entities", {})
        intent = context.get("intent", {})
        tools_needed = intent.get("requires_tools", [])
        
        # If we need calendar data
        if "calendar" in tools_needed or entities.get("meeting_names"):
            calendar = CalendarTools()
            
            # Get upcoming events
            events = await calendar.list_events(
                credentials=credentials,
                max_results=5
            )
            relevant_data["events"] = events
            
            # If looking for specific meeting
            meeting_names = entities.get("meeting_names", [])
            for name in meeting_names:
                matching = [e for e in events if name.lower() in e.get("summary", "").lower()]
                if matching:
                    relevant_data["target_event"] = matching[0]
        
        # If we need email data
        if "gmail" in tools_needed or entities.get("emails"):
            gmail = GmailTools()
            
            # Get recent emails
            emails = await gmail.search_messages(
                credentials=credentials,
                max_results=5,
                label_ids=["INBOX"]
            )
            relevant_data["emails"] = emails
        
        return relevant_data
