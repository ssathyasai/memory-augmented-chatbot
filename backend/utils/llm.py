
import time
from typing import Dict, List, Tuple

from groq import Groq

from .config import settings


class GroqLLM:
    def __init__(self, model_name: str = "llama3-8b-8192"):
        # The client is created lazily so local development still starts without a key.
        self.model_name = model_name
        self._client: Groq | None = None

    def _get_client(self) -> Groq:
        # Fail only when the model is actually invoked, not at import time.
        if not settings.GROQ_API_KEY:
            raise ValueError("Missing GROQ_API_KEY in backend/.env.")
        if self._client is None:
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def generate_response(self, messages: List[Dict[str, str]]) -> Tuple[str, float]:
        # The chat endpoint passes a normalized message list directly to Groq.
        start_time = time.time()
        client = self._get_client()
        completion = client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            temperature=0.2,
        )
        response_text = completion.choices[0].message.content or ""
        end_time = time.time()
        return response_text, end_time - start_time


groq_llm = GroqLLM(model_name=settings.GROQ_MODEL)
