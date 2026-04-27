"""
Zenith Core - The main orchestrator for the Zenith AI assistant
Coordinates all agents and executes the upgraded 4-phase pipeline:
  Context → Planner → Executor → Synthesizer
"""
from __future__ import annotations

import json
import time
from typing import Optional, AsyncIterator

import structlog

from .context_agent import ContextAgent
from .decomposer import DecomposerAgent
from .synthesizer import SynthesizerAgent
from .planner_agent import PlannerAgent
from .inbox_action_engine import InboxActionEngine
from .autoprep_agent import AutoPrepAgent
from .priority_feed import PriorityFeedBuilder
from .vertex_ai import VertexAIClient, get_vertex_client
from memory.conversation import ConversationMemory
from memory.user_store import UserStore
from memory.preferences import PreferencesStore
from core.executor import PlanExecutor
from tools.calendar import CalendarTools
from tools.gmail import GmailTools
from tools.tasks import TasksTools
from tools.notes import NotesTools

logger = structlog.get_logger()


class ZenithCore:
    """
    Zenith Core Orchestrator — upgraded pipeline.

    4-phase execution:
    1. Context Gathering   (ContextAgent)
    2. Planning            (PlannerAgent)   ← NEW
    3. Execution           (PlanExecutor)   ← NEW
    4. Synthesis & Response (SynthesizerAgent)

    The PlannerAgent is skipped for trivial/conversational requests
    (Category A). For Category B, it produces a structured plan that
    the PlanExecutor runs step-by-step.
    """

    WRITE_ACTION_KEYWORDS = [
        "create", "quick_add", "add", "send", "update",
        "delete", "complete", "uncomplete", "set",
    ]

    def __init__(
        self,
        vertex_client: Optional[VertexAIClient] = None,
        user_store: Optional[UserStore] = None,
        conversation_memory: Optional[ConversationMemory] = None,
    ):
        self.llm = vertex_client or get_vertex_client()
        self.user_store = user_store or UserStore()
        self.memory = conversation_memory or ConversationMemory()
        self.preferences_store = PreferencesStore()

        # Agents
        self.context_agent = ContextAgent(vertex_client=self.llm)
        self.planner = PlannerAgent(vertex_client=self.llm)
        self.decomposer = DecomposerAgent(vertex_client=self.llm)
        self.synthesizer = SynthesizerAgent(vertex_client=self.llm)

        # Executor
        self.executor = PlanExecutor()

        # Direct tool references (still used by briefing endpoint)
        self.calendar = CalendarTools()
        self.gmail = GmailTools()
        self.tasks = TasksTools()
        self.notes = NotesTools()
        self.inbox_action_engine = InboxActionEngine()
        self.autoprep_agent = AutoPrepAgent()
        self.priority_feed = PriorityFeedBuilder(
            gmail=self.gmail,
            calendar=self.calendar,
            inbox_engine=self.inbox_action_engine,
            autoprep_agent=self.autoprep_agent,
        )

        logger.info("Initialized Zenith Core (upgraded pipeline)")

    # ------------------------------------------------------------------
    # Preference extraction (was previously a nested method causing a bug)
    # ------------------------------------------------------------------

    async def _extract_preferences_from_message(self, message: str) -> dict:
        """
        Extract long-lived conversational preferences from a message.

        Prefer fast local heuristics for common statements like
        "I don't like strawberry". Fall back to the LLM only for
        ambiguous preference-like messages.
        """
        heuristic_updates = self.preferences_store.extract_memory_updates_from_text(message)
        if heuristic_updates:
            return {"memory_profile": heuristic_updates}

        if not self.preferences_store.looks_like_preference_statement(message):
            return {}

        system_instruction = (
            "Extract durable user preferences from the message.\n"
            "Output valid JSON only.\n"
            "Use this exact schema and include only non-empty arrays:\n"
            "{\n"
            '  "memory_profile": {\n'
            '    "likes": [],\n'
            '    "dislikes": [],\n'
            '    "avoid": [],\n'
            '    "preferences": [],\n'
            '    "notes": []\n'
            "  }\n"
            "}\n"
            "Examples:\n"
            '- "I do not like strawberry" -> {"memory_profile":{"dislikes":["strawberry"]}}\n'
            '- "I prefer email over calls" -> {"memory_profile":{"preferences":["email over calls"]}}\n'
            '- "Please avoid suggesting spicy food" -> {"memory_profile":{"avoid":["spicy food"]}}\n'
            "If nothing should be remembered, return {}."
        )
        response = await self.llm.generate(
            prompt=f"Message: {message}",
            system_instruction=system_instruction,
            temperature=0.1,
            max_tokens=300,
        )

        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```", 1)[-1]
                if response.startswith("json"):
                    response = response[4:]
            prefs = json.loads(response)
            if isinstance(prefs, dict):
                memory_profile = self.preferences_store._normalize_memory_profile(
                    prefs.get("memory_profile")
                )
                if any(memory_profile.values()):
                    return {"memory_profile": memory_profile}
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        images: Optional[list[dict]] = None,
        user_preferences: Optional[dict] = None,
        debug: bool = False,
    ) -> dict:
        """
        Process a user message through the full upgraded pipeline.

        Args:
            user_id: User's unique identifier
            session_id: Conversation session ID
            message: The user's message
            images: Optional image attachments
            user_preferences: Pre-loaded preferences (or fetched here)
            debug: If True, include debug/observability data in response

        Returns:
            Response dictionary with text, metadata, and optional debug info
        """
        pipeline_start = time.monotonic()
        debug_info: dict = {} if debug else None

        logger.info("Processing message", user_id=user_id, session_id=session_id)

        # --- Auth check ---
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return {
                "response": "I don't recognize you. Please authenticate first.",
                "error": "user_not_found",
                "requires_auth": True,
            }

        credentials = user.get("credentials")
        if not credentials:
            return {
                "response": "Your session has expired. Please re-authenticate.",
                "error": "no_credentials",
                "requires_auth": True,
            }

        # Save user message to conversation history
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
        )

        # --- Preference extraction (fire-and-forget style) ---
        preference_updates: dict = {}
        try:
            preference_updates = await self._extract_preferences_from_message(message)
            memory_profile_update = preference_updates.get("memory_profile")
            if memory_profile_update:
                user_preferences = await self.preferences_store.update_memory_profile(
                    user_id,
                    memory_profile_update,
                )
        except Exception:
            pass  # Non-critical

        # Load stored preferences if not provided
        if not user_preferences:
            try:
                user_preferences = await self.preferences_store.get_all_preferences(user_id)
            except Exception:
                user_preferences = {}

        try:
            # ── Check for pending plan confirmation ──
            recent = await self.memory.get_recent_messages(user_id, session_id, limit=2)
            pending_plan = None
            if len(recent) >= 2 and recent[-2].get("role") == "assistant":
                prev_metadata = recent[-2].get("metadata", {})
                if (
                    prev_metadata
                    and prev_metadata.get("requires_confirmation")
                    and prev_metadata.get("pending_plan")
                ):
                    pending_plan = prev_metadata.get("pending_plan")

            if pending_plan:
                msg_lower = message.strip().lower()
                if msg_lower in [
                    "approve", "yes", "do it", "send", "send it",
                    "go ahead", "confirm",
                ]:
                    return await self._execute_confirmed_plan(
                        plan=pending_plan,
                        credentials=credentials,
                        user_id=user_id,
                        session_id=session_id,
                        debug_info=debug_info,
                        pipeline_start=pipeline_start,
                    )
                elif msg_lower == "cancel":
                    response_text = "Okay, I've cancelled the action."
                    await self.memory.add_message(
                        user_id=user_id,
                        session_id=session_id,
                        role="assistant",
                        content=response_text,
                    )
                    return {
                        "response": response_text,
                        "suggestions": ["What else can I help you with?"],
                        "intent": {"action": "cancel"},
                    }
                elif msg_lower == "edit":
                    pass  # Fall through to normal pipeline

            # ══════════════════════════════════════════════
            # PHASE 1: Context Gathering
            # ══════════════════════════════════════════════
            context = await self.context_agent.gather_context(
                user_id=user_id,
                session_id=session_id,
                user_message=message,
                user_profile=user,
                images=images,
                user_preferences=user_preferences,
            )
            if preference_updates:
                context["preference_updates"] = preference_updates

            # ══════════════════════════════════════════════
            # PHASE 2: Planning (NEW — Decomposer fallback)
            # ══════════════════════════════════════════════
            intent = context.get("intent", {})
            category = intent.get("category", "A")

            plan = None
            planner_used = False

            if category == "B":
                # Try planner first for richer reasoning
                plan = await self.planner.create_plan(
                    context=context,
                    user_preferences=user_preferences,
                )
                planner_used = True

                # If planner produced no steps, fall back to decomposer
                if not plan.get("steps"):
                    plan = await self.decomposer.decompose(context)
                    planner_used = False
            else:
                # Category A → decomposer handles it (returns conversation plan)
                plan = await self.decomposer.decompose(context)

            if debug_info is not None:
                debug_info["plan"] = plan
                debug_info["planner_used"] = planner_used
                debug_info["planner_reasoning"] = plan.get("reasoning", "")

            # Validate plan
            is_valid, error = self.decomposer.validate_plan(plan)
            if not is_valid:
                logger.warning("Invalid plan", error=error)

            # ══════════════════════════════════════════════
            # PHASE 3: Execution (via PlanExecutor)
            # ══════════════════════════════════════════════
            execution_results = None
            requires_confirmation = False

            if plan.get("requires_execution"):
                if is_valid:
                    execution_results = await self.executor.execute_plan(
                        plan=plan,
                        credentials=credentials,
                        user_id=user_id,
                    )
                    # Check if executor is requesting confirmation
                    if execution_results.get("requires_confirmation"):
                        requires_confirmation = True
                else:
                    execution_results = {
                        "success": False,
                        "error": f"Failed to create a valid execution plan: {error}",
                    }

            if debug_info is not None:
                debug_info["steps_executed"] = (
                    execution_results.get("step_results", [])
                    if execution_results
                    else []
                )
                debug_info["risk_level"] = (
                    execution_results.get("risk_level", "low")
                    if execution_results
                    else "low"
                )
                debug_info["tools_used"] = [
                    s.get("action") for s in plan.get("steps", [])
                ]

            # ══════════════════════════════════════════════
            # PHASE 4: Synthesis
            # ══════════════════════════════════════════════
            response_text = await self.synthesizer.synthesize(
                context=context,
                execution_results=execution_results,
            )

            # Generate follow-up suggestions
            suggestions: list[str] = []
            if execution_results:
                suggestions = await self.synthesizer.generate_followup_suggestions(
                    context=context,
                    execution_results=execution_results,
                )

            # Save assistant response to conversation history
            metadata = {
                "plan": plan.get("name", plan.get("goal", "")),
                "tools_used": [s.get("action") for s in plan.get("steps", [])],
            }
            if requires_confirmation:
                metadata["requires_confirmation"] = True
                metadata["pending_plan"] = plan

            await self.memory.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata=metadata,
            )

            # Build response
            total_latency = (time.monotonic() - pipeline_start) * 1000
            if debug_info is not None:
                debug_info["latency_ms"] = round(total_latency, 1)

            result = {
                "response": response_text,
                "suggestions": suggestions,
                "intent": context.get("intent", {}),
                "execution_success": (
                    execution_results.get("success")
                    if execution_results
                    else None
                ),
                "requires_confirmation": requires_confirmation,
                "pending_plan": plan if requires_confirmation else None,
            }
            if debug_info is not None:
                result["debug"] = debug_info

            return result

        except Exception as e:
            logger.error("Error processing message", error=str(e))

            error_response = f"I encountered an error: {str(e)}. Please try again."

            await self.memory.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=error_response,
                metadata={"error": str(e)},
            )

            return {"response": error_response, "error": str(e)}

    # ------------------------------------------------------------------
    # Confirmed plan execution
    # ------------------------------------------------------------------

    async def _execute_confirmed_plan(
        self,
        plan: dict,
        credentials: dict,
        user_id: str,
        session_id: str,
        debug_info: Optional[dict],
        pipeline_start: float,
    ) -> dict:
        """Execute a plan that was previously awaiting user confirmation."""
        context = {"intent": {"action": "execute_pending_plan"}}

        is_valid, error = self.decomposer.validate_plan(plan)
        execution_results = None

        if is_valid:
            execution_results = await self.executor.execute_plan(
                plan=plan,
                credentials=credentials,
                user_id=user_id,
                skip_confirmation=True,
            )
        else:
            execution_results = {
                "success": False,
                "error": f"Failed to create a valid execution plan: {error}",
            }

        response_text = await self.synthesizer.synthesize(
            context=context,
            execution_results=execution_results,
        )
        suggestions = await self.synthesizer.generate_followup_suggestions(
            context=context,
            execution_results=execution_results,
        )

        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response_text,
            metadata={
                "plan": plan.get("name", plan.get("goal", "")),
                "tools_used": [s.get("action") for s in plan.get("steps", [])],
            },
        )

        result = {
            "response": response_text,
            "suggestions": suggestions,
            "intent": context.get("intent", {}),
            "execution_success": (
                execution_results.get("success") if execution_results else None
            ),
        }

        if debug_info is not None:
            total_latency = (time.monotonic() - pipeline_start) * 1000
            debug_info.update(
                {
                    "plan": plan,
                    "steps_executed": execution_results.get("step_results", []),
                    "latency_ms": round(total_latency, 1),
                    "tools_used": [
                        s.get("action") for s in plan.get("steps", [])
                    ],
                }
            )
            result["debug"] = debug_info

        return result

    # ------------------------------------------------------------------
    # Streaming (preserved from original)
    # ------------------------------------------------------------------

    async def process_message_stream(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict]:
        """
        Process a user message with streaming response.

        Yields:
            Chunks of the response as they're generated
        """
        # Get user and credentials
        user = await self.user_store.get_user_by_id(user_id)
        if not user or not user.get("credentials"):
            yield {
                "type": "error",
                "content": "Please authenticate first.",
                "requires_auth": True,
            }
            return

        credentials = user["credentials"]

        # Save user message
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
        )

        # Phase 1: Context
        yield {"type": "status", "content": "Understanding your request..."}

        context = await self.context_agent.gather_context(
            user_id=user_id,
            session_id=session_id,
            user_message=message,
        )

        # Phase 2: Plan + Decompose
        yield {"type": "status", "content": "Planning..."}

        intent = context.get("intent", {})
        category = intent.get("category", "A")

        if category == "B":
            plan = await self.planner.create_plan(context=context)
            if not plan.get("steps"):
                plan = await self.decomposer.decompose(context)
        else:
            plan = await self.decomposer.decompose(context)

        # Phase 3: Execute if needed
        execution_results = None
        if plan.get("requires_execution"):
            yield {"type": "status", "content": "Working on it..."}

            is_valid, error = self.decomposer.validate_plan(plan)
            if is_valid:
                execution_results = await self.executor.execute_plan(
                    plan=plan,
                    credentials=credentials,
                    user_id=user_id,
                )
            else:
                execution_results = {
                    "success": False,
                    "error": f"Failed to create a valid execution plan: {error}",
                }

        # Phase 4: Synthesise + stream
        yield {"type": "status", "content": "Generating response..."}

        full_response = await self.synthesizer.synthesize(
            context=context,
            execution_results=execution_results,
        )

        chunk_size = 50
        for i in range(0, len(full_response), chunk_size):
            yield {
                "type": "content",
                "content": full_response[i : i + chunk_size],
            }

        # Save response
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=full_response,
        )

        # Yield suggestions
        suggestions = await self.synthesizer.generate_followup_suggestions(
            context=context,
            execution_results=execution_results,
        )

        yield {"type": "complete", "suggestions": suggestions}
