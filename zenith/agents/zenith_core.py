"""
Zenith Core - The main orchestrator for the Zenith AI assistant
Coordinates all agents and executes the 3-phase pipeline
"""
from typing import Optional, AsyncIterator
import structlog

from .context_agent import ContextAgent
from .decomposer import DecomposerAgent
from .synthesizer import SynthesizerAgent
from .vertex_ai import VertexAIClient, get_vertex_client
from memory.conversation import ConversationMemory
from memory.user_store import UserStore
from tools.calendar import CalendarTools
from tools.gmail import GmailTools
from tools.tasks import TasksTools
from tools.notes import NotesTools

logger = structlog.get_logger()


class ZenithCore:
    """
    Zenith Core Orchestrator
    
    Coordinates the 3-phase execution pipeline:
    1. Context Gathering (ContextAgent)
    2. Task Decomposition (DecomposerAgent)
    3. Synthesis & Response (SynthesizerAgent)
    """
    
    def __init__(
        self,
        vertex_client: Optional[VertexAIClient] = None,
        user_store: Optional[UserStore] = None,
        conversation_memory: Optional[ConversationMemory] = None
    ):
        self.llm = vertex_client or get_vertex_client()
        self.user_store = user_store or UserStore()
        self.memory = conversation_memory or ConversationMemory()
        
        # Initialize agents
        self.context_agent = ContextAgent(vertex_client=self.llm)
        self.decomposer = DecomposerAgent(vertex_client=self.llm)
        self.synthesizer = SynthesizerAgent(vertex_client=self.llm)
        
        # Initialize tools
        self.calendar = CalendarTools()
        self.gmail = GmailTools()
        self.tasks = TasksTools()
        self.notes = NotesTools()
        
        logger.info("Initialized Zenith Core")
    
    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str
    ) -> dict:
        """
        Process a user message through the full pipeline.
        
        Args:
            user_id: User's unique identifier
            session_id: Conversation session ID
            message: The user's message
            
        Returns:
            Response dictionary with text and metadata
        """
        logger.info("Processing message", user_id=user_id, session_id=session_id)
        
        # Get user credentials
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return {
                "response": "I don't recognize you. Please authenticate first.",
                "error": "user_not_found",
                "requires_auth": True
            }
        
        credentials = user.get("credentials")
        if not credentials:
            return {
                "response": "Your session has expired. Please re-authenticate.",
                "error": "no_credentials",
                "requires_auth": True
            }
        
        # Save user message to conversation history
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message
        )
        
        try:
            # PHASE 1: Context Gathering
            context = await self.context_agent.gather_context(
                user_id=user_id,
                session_id=session_id,
                user_message=message,
                user_profile=user
            )
            
            # PHASE 2: Task Decomposition
            plan = await self.decomposer.decompose(context)
            
            # Validate plan
            is_valid, error = self.decomposer.validate_plan(plan)
            if not is_valid:
                logger.warning("Invalid plan", error=error)
            
            # Execute plan if needed
            execution_results = None
            if plan.get("requires_execution"):
                if is_valid:
                    execution_results = await self._execute_plan(
                        plan=plan,
                        credentials=credentials,
                        user_id=user_id
                    )
                else:
                    execution_results = {
                        "success": False,
                        "error": f"Failed to create a valid execution plan: {error}"
                    }
            
            # PHASE 3: Synthesis
            response_text = await self.synthesizer.synthesize(
                context=context,
                execution_results=execution_results
            )
            
            # Generate follow-up suggestions
            suggestions = await self.synthesizer.generate_followup_suggestions(
                context=context,
                execution_results=execution_results
            )
            
            # Save assistant response to conversation history
            await self.memory.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata={
                    "plan": plan.get("name"),
                    "tools_used": [s.get("action") for s in plan.get("steps", [])]
                }
            )
            
            return {
                "response": response_text,
                "suggestions": suggestions,
                "intent": context.get("intent", {}),
                "execution_success": execution_results.get("success") if execution_results else None
            }
            
        except Exception as e:
            logger.error("Error processing message", error=str(e))
            
            error_response = f"I encountered an error: {str(e)}. Please try again."
            
            await self.memory.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=error_response,
                metadata={"error": str(e)}
            )
            
            return {
                "response": error_response,
                "error": str(e)
            }
    
    async def _execute_plan(
        self,
        plan: dict,
        credentials: dict,
        user_id: str
    ) -> dict:
        """Execute a decomposed plan."""
        results = {
            "success": True,
            "step_results": [],
            "error": None
        }
        
        for step in plan.get("steps", []):
            action = step.get("action", "")
            params = step.get("params", {})
            
            try:
                step_result = await self._execute_step(
                    action=action,
                    params=params,
                    credentials=credentials,
                    user_id=user_id
                )
                
                results["step_results"].append({
                    "action": action,
                    "success": True,
                    "data": step_result
                })
                
            except Exception as e:
                logger.error("Step execution failed", action=action, error=str(e))
                results["step_results"].append({
                    "action": action,
                    "success": False,
                    "error": str(e)
                })
                results["success"] = False
                results["error"] = str(e)
                break  # Stop on first error
        
        return results
    
    async def _execute_step(
        self,
        action: str,
        params: dict,
        credentials: dict,
        user_id: str
    ):
        """Execute a single step from the plan."""
        tool_name, method_name = action.split(".")
        
        # Get the appropriate tool
        tool_map = {
            "calendar": self.calendar,
            "gmail": self.gmail,
            "tasks": self.tasks,
            "notes": self.notes
        }
        
        tool = tool_map.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        method = getattr(tool, method_name, None)
        if not method:
            raise ValueError(f"Unknown method: {method_name} on {tool_name}")
        
        # Execute the method
        if tool_name == "notes":
            # Notes tools use user_id instead of credentials
            return await method(user_id=user_id, **params)
        else:
            # Google API tools use credentials
            return await method(credentials=credentials, **params)
    
    async def process_message_stream(
        self,
        user_id: str,
        session_id: str,
        message: str
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
                "requires_auth": True
            }
            return
        
        credentials = user["credentials"]
        
        # Save user message
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message
        )
        
        # Phase 1 & 2
        yield {"type": "status", "content": "Understanding your request..."}
        
        context = await self.context_agent.gather_context(
            user_id=user_id,
            session_id=session_id,
            user_message=message
        )
        
        plan = await self.decomposer.decompose(context)
        
        # Execute if needed
        execution_results = None
        if plan.get("requires_execution"):
            yield {"type": "status", "content": "Working on it..."}
            
            is_valid, error = self.decomposer.validate_plan(plan)
            if is_valid:
                execution_results = await self._execute_plan(
                    plan=plan,
                    credentials=credentials,
                    user_id=user_id
                )
            else:
                execution_results = {
                    "success": False,
                    "error": f"Failed to create a valid execution plan: {error}"
                }
        
        # Phase 3: Stream the response
        yield {"type": "status", "content": "Generating response..."}
        
        full_response = await self.synthesizer.synthesize(
            context=context,
            execution_results=execution_results
        )
        
        # Yield the response in chunks for streaming effect
        chunk_size = 50
        for i in range(0, len(full_response), chunk_size):
            yield {
                "type": "content",
                "content": full_response[i:i + chunk_size]
            }
        
        # Save response
        await self.memory.add_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=full_response
        )
        
        # Yield suggestions
        suggestions = await self.synthesizer.generate_followup_suggestions(
            context=context,
            execution_results=execution_results
        )
        
        yield {
            "type": "complete",
            "suggestions": suggestions
        }
