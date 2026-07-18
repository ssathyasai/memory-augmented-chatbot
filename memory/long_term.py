"""Long-term profile preference memory manager."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from config.database import get_database
from rag.llm_client import groq_client

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """Manages extraction and retrieval of long-term user preferences."""
    
    @staticmethod
    def extract_and_save_preferences(user_id: str, message: str) -> None:
        """
        Analyze user message for persistent preferences and save them to MongoDB.
        
        Args:
            user_id: User ID
            message: User's chat message
        """
        system_prompt = """You are a user profile preference extraction agent. 
Analyze the user's message and determine if it contains any persistent personal facts, preferences, constraints, or technical choices (e.g. "I prefer Python", "I am a frontend developer", "I only work with FastAPI", "I don't like Java").

If it does, extract them as structured key-value statements. Focus only on long-term preferences, not transient questions.

You MUST respond with a valid JSON array of objects. Do not include any markdown styling like ```json or ```, and do not write any introductory or concluding text.

JSON Schema:
[
  {
    "key": "unique_lowercase_preference_name",
    "value": "extracted preference value",
    "explanation": "Brief explanation of why this preference was extracted"
  }
]

If no persistent preferences are found, return an empty JSON array: []"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User message: {message}"}
            ]
            
            # Call LLM to extract preferences
            raw_response = groq_client.client.chat.completions.create(
                model=groq_client.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            response_text = raw_response.choices[0].message.content.strip()
            
            # Parse response
            # Sometimes JSON response format is an object with a key, check list vs object
            extracted = json.loads(response_text)
            
            # Normalize to list of dicts
            preferences = []
            if isinstance(extracted, list):
                preferences = extracted
            elif isinstance(extracted, dict):
                # Check if it has a list key like "preferences"
                for key, val in extracted.items():
                    if isinstance(val, list):
                        preferences = val
                        break
                if not preferences:
                    # Treat it as a single preference dictionary
                    if "key" in extracted and "value" in extracted:
                        preferences = [extracted]
            
            if not preferences:
                return
                
            db = get_database()
            if db is not None:
                for pref in preferences:
                    key = pref.get("key", "").strip().lower()
                    value = pref.get("value", "").strip()
                    explanation = pref.get("explanation", "").strip()
                    
                    if key and value:
                        logger.info(f"Extracted user preference: {key} = {value}")
                        db.user_profile_memories.update_one(
                            {"user_id": user_id, "key": key},
                            {
                                "$set": {
                                    "value": value,
                                    "explanation": explanation,
                                    "timestamp": datetime.utcnow()
                                }
                            },
                            upsert=True
                        )
                        
        except Exception as e:
            logger.error(f"Error extracting user preferences: {e}")
            
    @staticmethod
    def get_user_preferences_context(user_id: str) -> str:
        """
        Retrieve all stored user preferences and format them as system prompt context.
        
        Args:
            user_id: User ID
            
        Returns:
            Formatted string of preferences, or empty string
        """
        try:
            db = get_database()
            if db is None:
                return ""
                
            memories = list(db.user_profile_memories.find({"user_id": user_id}))
            
            if not memories:
                return ""
                
            context_parts = ["\n[USER PROFILE & LONG-TERM MEMORY]"]
            context_parts.append("Keep the following user preferences and profile facts in mind to personalize your response:")
            
            for memory in memories:
                key = memory.get("key", "").replace("_", " ").title()
                value = memory.get("value", "")
                explanation = memory.get("explanation", "")
                context_parts.append(f"- {key}: {value} ({explanation})")
                
            context_parts.append("[END USER PROFILE]\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error retrieving user preferences context: {e}")
            return ""
            
    @staticmethod
    def clear_user_memories(user_id: str) -> None:
        """
        Delete all long-term preferences for a user.
        
        Args:
            user_id: User ID
        """
        try:
            db = get_database()
            if db is not None:
                db.user_profile_memories.delete_many({"user_id": user_id})
                logger.info(f"Cleared all long-term memory for user: {user_id}")
        except Exception as e:
            logger.error(f"Error clearing user memories: {e}")
