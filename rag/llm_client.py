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
            self._model = settings.GROQ_MODEL or "openai/gpt-oss-120b"
            self.temperature = settings.GROQ_TEMPERATURE
            self.max_tokens = settings.GROQ_MAX_TOKENS
        except Exception as e:
            logger.warning(f"Warning during GROQ client initialization: {e}")
            self.client = None
            self._model = settings.GROQ_MODEL or "openai/gpt-oss-120b"
            self.temperature = settings.GROQ_TEMPERATURE
            self.max_tokens = settings.GROQ_MAX_TOKENS
    
    @property
    def model(self) -> str:
        """Dynamically get the model name."""
        return self._model or getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b')
    
    @model.setter
    def model(self, value: str):
        self._model = value
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate chat completion with automatic model fallback.
        
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

        if self.client is None or getattr(self.client, "api_key", None) == "placeholder_key":
            self.client = self._create_client(settings.GROQ_API_KEY)

        # Fallback candidate models if the selected model is not available or deprecated on Groq
        fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        current_model = self.model
        models_to_try = [current_model] + [m for m in fallback_models if m != current_model]

        last_error = None
        for m in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if m != current_model:
                    logger.info(f"Groq model '{current_model}' was unavailable. Automatically switched to '{m}'")
                    self.model = m
                    settings.GROQ_MODEL = m
                
                generated_text = response.choices[0].message.content
                logger.info(f"Generated response ({len(generated_text)} chars) with {m}")
                return generated_text

            except Exception as e:
                err_str = str(e)
                if "model_not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                    logger.warning(f"Groq model '{m}' not found: {e}. Trying next candidate...")
                    last_error = e
                    continue
                else:
                    logger.error(f"Error calling GROQ API: {e}")
                    raise LLMError(f"GROQ API error: {str(e)}")

        raise LLMError(f"GROQ API error: {last_error}")
    
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
