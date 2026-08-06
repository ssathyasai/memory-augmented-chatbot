"""GROQ LLM client wrapper module.

Process Flow:
1. Initializes `Groq` client using `GROQ_API_KEY`, model selection (`llama-3.1-8b-instant`), temperature, and max token limits.
2. Performs chat completion requests with system, context, and user role message arrays.
3. Provides `generate_response` helper method to inject RAG/KG context blocks into prompt payloads.
4. Catches API connection and rate limit errors, wrapping them in `LLMError`.
"""

import logging
from typing import List, Dict
import httpx
from groq import Groq

from config.settings import settings
from errors.exceptions import LLMError

logger = logging.getLogger(__name__)


class GroqClient:
    """Client for GROQ LLM API."""
    
    def _create_client(self, api_key: str) -> Groq:
        """Create Groq client using httpx.Client to prevent httpx proxies kwargs incompatibility."""
        try:
            return Groq(api_key=api_key, http_client=httpx.Client())
        except Exception:
            return Groq(api_key=api_key)

    def __init__(self):
        """Initialize GROQ client."""
        try:
            api_key = settings.GROQ_API_KEY or "placeholder_key"
            self.client = self._create_client(api_key)
            self.model = settings.GROQ_MODEL
            self.temperature = settings.GROQ_TEMPERATURE
            self.max_tokens = settings.GROQ_MAX_TOKENS
        except Exception as e:
            logger.warning(f"Warning during GROQ client initialization: {e}")
            self.client = None
            self.model = settings.GROQ_MODEL
            self.temperature = settings.GROQ_TEMPERATURE
            self.max_tokens = settings.GROQ_MAX_TOKENS
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (default from settings)
            max_tokens: Maximum tokens to generate (default from settings)
        
        Returns:
            Generated response text
        
        Raises:
            LLMError: If API call fails
        """
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        if not settings.GROQ_API_KEY:
            raise LLMError("GROQ API Key is missing. Please set GROQ_API_KEY in your environment variables or Streamlit secrets.")

        try:
            if self.client is None or getattr(self.client, "api_key", None) == "placeholder_key":
                self.client = self._create_client(settings.GROQ_API_KEY)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            generated_text = response.choices[0].message.content
            logger.info(f"Generated response ({len(generated_text)} chars)")
            
            return generated_text
        
        except Exception as e:
            logger.error(f"Error calling GROQ API: {e}")
            raise LLMError(f"GROQ API error: {str(e)}")
    
    def generate_response(
        self,
        system_prompt: str,
        user_query: str,
        context: str = "",
        temperature: float = None
    ) -> str:
        """
        Generate response with system prompt and context.
        
        Args:
            system_prompt: System instructions
            user_query: User's question
            context: Additional context (e.g., from RAG)
            temperature: Sampling temperature
        
        Returns:
            Generated response
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({
                "role": "system",
                "content": f"Context information:\n{context}"
            })
        
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        return self.chat_completion(messages, temperature=temperature)


# Global GROQ client instance
groq_client = GroqClient()
