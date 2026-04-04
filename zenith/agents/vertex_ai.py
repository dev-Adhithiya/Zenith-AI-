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

from config import settings

logger = structlog.get_logger()


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
            "max_output_tokens": 2048,
        }
        
        # Safety settings
        self.safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
        ]
        
        logger.info("Initialized Vertex AI client", model=self.model_name)
    
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user's prompt
            system_instruction: System instruction for the model
            chat_history: Previous conversation messages
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            
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
        
        # Add current prompt
        contents.append(Content(
            role="user",
            parts=[Part.from_text(prompt)]
        ))
        
        try:
            response = await model.generate_content_async(
                contents,
                generation_config=config,
                safety_settings=self.safety_settings
            )
            
            logger.debug("Generated response", 
                        prompt_length=len(prompt),
                        response_length=len(response.text))
            
            return response.text
            
        except Exception as e:
            logger.error("Generation failed", error=str(e))
            raise
    
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
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error("Streaming generation failed", error=str(e))
            raise
    
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
            temperature=0.1  # Low temperature for classification
        )
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response (may have markdown code blocks)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
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
            temperature=0.1
        )
        
        return resolved.strip()


@lru_cache()
def get_vertex_client() -> VertexAIClient:
    """Get cached Vertex AI client instance."""
    return VertexAIClient()
