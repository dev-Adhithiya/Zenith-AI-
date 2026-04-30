"""
Vertex AI Integration for Zenith AI
Provides LLM inference using Google's Vertex AI platform
"""
from typing import Optional, AsyncIterator
from functools import lru_cache
import structlog

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Content,
    Part,
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold
)
import base64
from io import BytesIO

from config import settings

logger = structlog.get_logger()

# Map finish reasons to human-readable messages
FINISH_REASON_MESSAGES = {
    0: "FINISH_REASON_UNSPECIFIED",
    1: "STOP - natural completion",
    2: "MAX_TOKENS - token limit reached",
    3: "SAFETY - blocked by safety filters",
    4: "RECITATION - blocked for recitation",
    5: "OTHER - other reason"
}


class VertexAIClient:
    """
    Vertex AI Generative Model client.
    Handles all LLM inference for Zenith AI.
    """
    
    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location
        )
        
        self.model_name = settings.vertex_ai_model
        self.model = GenerativeModel(self.model_name)
        
        # Default generation config values (stored as dict to avoid SDK attribute issues)
        self.default_generation_params = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,
        }
        
        # Minimal safety settings - disabled to prevent blocking
        self.safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_NONE
            ),
        ]
        
        logger.info("Initialized Vertex AI client", model=self.model_name)
    
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[list[dict]] = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user's prompt
            system_instruction: System instruction for the model
            chat_history: Previous conversation messages
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            images: List of image dicts with 'content' (bytes) and 'content_type' keys
            
        Returns:
            Generated text response
        """
        # Build generation config
        config = GenerationConfig(
            temperature=temperature or self.default_generation_params["temperature"],
            top_p=self.default_generation_params["top_p"],
            top_k=self.default_generation_params["top_k"],
            max_output_tokens=max_tokens or self.default_generation_params["max_output_tokens"],
        )
        
        # Build model with system instruction if provided
        if system_instruction:
            model = GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
        else:
            model = self.model
        
        # Build contents
        contents = []
        
        if chat_history:
            for msg in chat_history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(Content(
                    role=role,
                    parts=[Part.from_text(msg.get("content", ""))]
                ))
        
        # Add current prompt with images if provided
        parts = [Part.from_text(prompt)]
        
        if images:
            for img in images:
                try:
                    content = img.get('content')
                    content_type = img.get('content_type', 'image/jpeg')
                    
                    if isinstance(content, bytes):
                        # Use from_data for binary image data
                        parts.append(Part.from_data(
                            data=content,
                            mime_type=content_type
                        ))
                    elif isinstance(content, str):
                        # If it's base64 encoded string, decode first
                        try:
                            decoded = base64.b64decode(content)
                            parts.append(Part.from_data(
                                data=decoded,
                                mime_type=content_type
                            ))
                        except:
                            logger.warning(f"Failed to decode base64 image")
                except Exception as e:
                    logger.warning(f"Failed to process image: {str(e)}")
        
        contents.append(Content(
            role="user",
            parts=parts
        ))
        
        try:
            response = await model.generate_content_async(
                contents,
                generation_config=config,
                safety_settings=self.safety_settings
            )
            
            # Check if response was blocked or truncated
            if not response.candidates or not response.candidates[0]:
                # Check if blocked by safety
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    block_reason = getattr(response.prompt_feedback, 'block_reason', 'Unknown')
                    logger.warning("Response blocked by safety filters", reason=block_reason)
                    return "I apologize, but I couldn't process that request. Please try rephrasing your question."
                logger.error("No response candidates returned - API issue detected", 
                           response_obj=str(response))
                return "I apologize, but I couldn't generate a response. Please try again."
            
            candidate = response.candidates[0]
            
            # If no content parts at all, retry or give user-friendly error
            if not hasattr(candidate, 'content') or not candidate.content or not candidate.content.parts:
                logger.warning("Response has no content parts", 
                              finish_reason=getattr(candidate, 'finish_reason', 'unknown'))
                return "I received an empty response from the API. Please try your question again."
            
            # Get finish reason - handle both int and enum types
            finish_reason = candidate.finish_reason
            finish_reason_int = finish_reason if isinstance(finish_reason, int) else getattr(finish_reason, 'value', finish_reason)
            finish_reason_str = FINISH_REASON_MESSAGES.get(finish_reason_int, str(finish_reason))
            
            # Handle different finish reasons
            if finish_reason_int == 3:  # SAFETY
                logger.warning("Response blocked by safety filters", finish_reason=finish_reason_str)
                return "I apologize, but I couldn't generate a response for that request. Please try rephrasing your question."
            
            if finish_reason_int == 4:  # RECITATION
                logger.warning("Response blocked for recitation", finish_reason=finish_reason_str)
                return "I apologize, but I couldn't complete that response. Please try a different approach."
            
            if finish_reason_int == 2:  # MAX_TOKENS
                logger.warning("Response truncated due to MAX_TOKENS limit.")
                # Still return partial response if we have text
                if candidate.content and candidate.content.parts:
                    partial_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
                    if partial_text:
                        return partial_text + "\n\n[Response truncated]"
                return "The response was too long. Please try a more specific question."
            
            # Check if content has parts
            if not candidate.content or not candidate.content.parts:
                logger.warning("No content in response", finish_reason=finish_reason_str)
                return "I couldn't generate a response. Please try again with a different question."
            
            # Extract text from parts
            response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
            
            if not response_text:
                logger.warning("Empty text in response parts", finish_reason=finish_reason_str)
                return "I received an empty response. Please try again."
            
            logger.debug("Generated response", 
                        prompt_length=len(prompt),
                        response_length=len(response_text),
                        finish_reason=finish_reason_str)
            
            return response_text
            
        except Exception as e:
            logger.error("Generation failed", error=str(e))
            # Return a user-friendly error message instead of raising
            return f"I encountered an issue while processing your request. Please try again. (Error: {str(e)[:100]})"
    
    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.
        
        Yields:
            Text chunks as they're generated
        """
        config = GenerationConfig(
            temperature=temperature or self.default_generation_params["temperature"],
            top_p=self.default_generation_params["top_p"],
            top_k=self.default_generation_params["top_k"],
            max_output_tokens=self.default_generation_params["max_output_tokens"],
        )
        
        if system_instruction:
            model = GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
        else:
            model = self.model
        
        contents = []
        
        if chat_history:
            for msg in chat_history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(Content(
                    role=role,
                    parts=[Part.from_text(msg.get("content", ""))]
                ))
        
        contents.append(Content(
            role="user",
            parts=[Part.from_text(prompt)]
        ))
        
        try:
            response = await model.generate_content_async(
                contents,
                generation_config=config,
                safety_settings=self.safety_settings,
                stream=True
            )
            
            has_content = False
            async for chunk in response:
                # Handle both text and other part types
                if hasattr(chunk, 'text') and chunk.text:
                    has_content = True
                    yield chunk.text
                elif hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'finish_reason'):
                            finish_reason = candidate.finish_reason
                            finish_reason_int = finish_reason if isinstance(finish_reason, int) else getattr(finish_reason, 'value', 3)
                            if finish_reason_int == 3:  # SAFETY blocked
                                logger.warning("Stream response blocked by safety filters", finish_reason=finish_reason_int)
                                yield "\n\nI apologize, but I couldn't complete that response. Please try rephrasing your question."
                                return
                        if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    has_content = True
                                    yield part.text
            
            if not has_content:
                yield "I apologize, but I couldn't generate a response. Please try again."
                    
        except Exception as e:
            logger.error("Streaming generation failed", error=str(e))
            yield f"An error occurred: {str(e)[:100]}"
    
    async def classify_intent(
        self,
        user_message: str,
        chat_history: Optional[list[dict]] = None
    ) -> dict:
        """
        Classify the intent of a user message.
        
        Returns:
            Dict with intent category and confidence
        """
        system_instruction = """You are an intent classifier for a personal assistant AI.
Analyze the user's message and classify it into one of these categories:

CATEGORY A (General Knowledge & Conversation):
- Answering general questions
- Follow-up questions about previously retrieved data
- Casual conversation
- Clarification requests

CATEGORY B (Personal Management & Tool Use):
- Calendar operations (list, create, check meetings)
- Email operations (search, read, send, summarize)
- Task management (add, list, complete tasks)
- Note-taking and knowledge base queries
- Setting reminders

Output a JSON object with:
{
    "category": "A" or "B",
    "intent": "specific intent name",
    "requires_tools": ["tool1", "tool2"] or [],
    "confidence": 0.0-1.0,
    "resolved_entities": {"key": "value"} 
}

For resolved_entities, extract any specific values mentioned:
- dates/times
- email addresses
- meeting names
- task descriptions
- search queries"""

        prompt = f"User message: {user_message}"
        
        if chat_history:
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in chat_history[-5:]
            ])
            prompt = f"Recent conversation:\n{context}\n\nCurrent message: {user_message}"
        
        response = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.1,  # Low temperature for classification
            max_tokens=350,
        )
        
        # Parse JSON response
        import json
        import re as _re
        try:
            # Extract JSON from response (may have markdown code blocks)
            response = response.strip()
            # Robust JSON extraction: find the first {...} block
            json_match = _re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse intent classification", response=response)
            return {
                "category": "A",
                "intent": "unknown",
                "requires_tools": [],
                "confidence": 0.5,
                "resolved_entities": {}
            }
    
    async def resolve_context(
        self,
        user_message: str,
        chat_history: list[dict]
    ) -> str:
        """
        Resolve pronouns and context from chat history.
        
        Takes a message like "what's the prize?" and resolves it to
        "what's the prize for the hackathon mentioned in the email?"
        """
        if not chat_history:
            return user_message
        
        system_instruction = """You are a context resolution assistant.
Given a user message and chat history, rewrite the message to be fully self-contained.

Rules:
1. Replace pronouns (it, they, he, she, this, that) with their referents
2. Include relevant context from recent messages
3. Keep the rewritten message concise but complete
4. If no context resolution is needed, return the original message
5. Output ONLY the resolved message, nothing else"""

        context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in chat_history[-5:]
        ])
        
        prompt = f"""Chat history:
{context}

User's new message: {user_message}

Resolved message:"""
        
        resolved = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.1,
            max_tokens=220,
        )
        
        return resolved.strip()


@lru_cache()
def get_vertex_client() -> VertexAIClient:
    """Get cached Vertex AI client instance."""
    return VertexAIClient()
