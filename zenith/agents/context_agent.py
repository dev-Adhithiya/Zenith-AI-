"""
Context Agent for Zenith AI
Phase 1: Context Gathering - Resolves context from chat history and knowledge base
"""
from typing import Optional
import structlog

from .vertex_ai import VertexAIClient, get_vertex_client
from memory.conversation import ConversationMemory
from memory.user_store import UserStore
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
        include_knowledge_base: bool = True
    ) -> dict:
        """
        Gather all relevant context for processing a user message.
        
        Args:
            user_id: User's unique identifier
            session_id: Current conversation session ID
            user_message: The user's message
            include_knowledge_base: Whether to query knowledge base
            
        Returns:
            Context dictionary with resolved message, history, and relevant data
        """
        logger.info("Gathering context", user_id=user_id, session_id=session_id)
        
        # Step 1: Get chat history
        chat_history = await self.memory.get_context_window(
            user_id=user_id,
            session_id=session_id,
            max_messages=10
        )
        
        # Step 2: Resolve context (pronouns, references)
        resolved_message = await self._resolve_references(
            user_message=user_message,
            chat_history=chat_history
        )
        
        # Step 3: Extract entities mentioned
        entities = await self._extract_entities(resolved_message)
        
        # Step 4: Query knowledge base if needed
        relevant_notes = []
        if include_knowledge_base and entities.get("search_queries"):
            for query in entities.get("search_queries", []):
                notes = await self.notes.query_knowledge_base(
                    user_id=user_id,
                    query=query,
                    limit=3
                )
                relevant_notes.extend(notes)
        
        # Step 5: Classify intent
        intent = await self.llm.classify_intent(
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
            "session_id": session_id
        }
        
        logger.info("Context gathered", 
                   intent_category=intent.get("category"),
                   intent=intent.get("intent"),
                   has_history=len(chat_history) > 0)
        
        return context
    
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
        
        if has_references or is_followup_question:
            return await self.llm.resolve_context(
                user_message=user_message,
                chat_history=chat_history
            )
        
        return user_message
    
    async def _extract_entities(self, message: str) -> dict:
        """Extract named entities and search queries from the message."""
        system_instruction = """Extract entities from the user message for a personal assistant.
Output a JSON object with:
{
    "dates": ["YYYY-MM-DD", ...],  // Any dates mentioned
    "times": ["HH:MM", ...],  // Any times mentioned
    "people": ["name", ...],  // Names of people
    "emails": ["email@example.com", ...],  // Email addresses
    "meeting_names": ["meeting title", ...],  // Meeting/event names
    "task_descriptions": ["task", ...],  // Task descriptions
    "search_queries": ["query", ...]  // Key phrases to search for
}

Only include non-empty arrays. Output valid JSON only."""

        response = await self.llm.generate(
            prompt=f"Message: {message}",
            system_instruction=system_instruction,
            temperature=0.1
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
