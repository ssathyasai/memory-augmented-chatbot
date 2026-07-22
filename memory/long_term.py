"""Long-term profile preference memory manager module.

Process Flow:
1. Analyzes user chat turns using GROQ LLM to extract persistent user preferences, constraints, or technology choices.
2. Formats extracted preferences as key-value pairs and upserts them into `user_profile_memories` collection in MongoDB.
3. Retrieves stored profile memories and formats them as a system prompt block (`[USER PROFILE & LONG-TERM MEMORY]`) to personalize future LLM answers.
4. Provides clearing methods to wipe long-term memories upon user request.
"""

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
Analyze the user's message and determine if it contains any persistent personal facts, profile details, preferences, constraints, or technical choices.

If it does, extract them as structured key-value statements. Focus only on long-term personal facts and preferences, not transient questions.

You MUST map each extracted fact or preference to one of these standard keys if applicable:
- 'name': The user's name
- 'roll_number': The user's roll number/student ID
- 'department': The user's department, branch, or field of study
- 'institution': The user's college, university, or educational institution
- 'education_level': The user's current degree, year, or grade of study (e.g., "B.Tech 4th year")
- 'programming_languages': Preferred programming languages or technical stacks
- 'technical_interests': Technical focus areas or interest fields
If a preference does not fit any of the above standard keys, you may use a custom, descriptive, lowercase key name.

Crucially:
- If the user explicitly mentions a change of state (e.g., "changed my college from X to Y", "my new department is Z", "changed my name to A"), make sure to output the correct standard key with the new value so that it overwrites the previous entry in the database.

You MUST respond with a valid JSON array of objects. Do not include any markdown styling like ```json or ```, and do not write any introductory or concluding text.

JSON Schema:
[
  {
    "key": "standard_or_custom_lowercase_key",
    "value": "extracted fact or preference value",
    "explanation": "Brief explanation of why this fact/preference was extracted"
  }
]

If no persistent facts or preferences are found, return an empty JSON array: []"""

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
            
            # Translate potential key aliases to standard keys immediately
            key_mapping = {
                "current_institution": "institution",
                "college": "institution",
                "school": "institution",
                "university": "institution",
                "degree": "education_level",
                "academic_year": "education_level",
                "year_of_study": "education_level",
                "branch": "department",
                "field_of_study": "department",
                "roll_no": "roll_number",
                "student_id": "roll_number",
            }
            
            response_text = raw_response.choices[0].message.content.strip()
            
            # Parse response
            extracted = json.loads(response_text)
            
            # Recursively find all dictionaries containing both "key" and "value" keys
            def find_key_value_dicts(obj) -> List[Dict[str, Any]]:
                results = []
                if isinstance(obj, dict):
                    if "key" in obj and "value" in obj:
                        results.append(obj)
                    else:
                        for k, v in obj.items():
                            results.extend(find_key_value_dicts(v))
                elif isinstance(obj, list):
                    for item in obj:
                        results.extend(find_key_value_dicts(item))
                return results

            preferences = find_key_value_dicts(extracted)
            
            if not preferences:
                return
                
            db = get_database()
            if db is not None:
                for pref in preferences:
                    key = pref.get("key", "").strip().lower()
                    # Apply standardization mapping
                    key = key_mapping.get(key, key)
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
                
            # Perform reconciliation to standardize legacy/conflicting keys in the database
            try:
                key_mapping = {
                    "current_institution": "institution",
                    "college": "institution",
                    "school": "institution",
                    "university": "institution",
                    "degree": "education_level",
                    "academic_year": "education_level",
                    "year_of_study": "education_level",
                    "branch": "department",
                    "field_of_study": "department",
                    "roll_no": "roll_number",
                    "student_id": "roll_number",
                }
                
                memories = list(db.user_profile_memories.find({"user_id": user_id}))
                mem_dict = {m["key"]: m for m in memories}
                
                for key, target_key in key_mapping.items():
                    if key in mem_dict:
                        m_old = mem_dict[key]
                        if target_key in mem_dict:
                            m_new = mem_dict[target_key]
                            # Compare timestamps to keep the latest one
                            t_old = m_old.get("timestamp") or datetime.min
                            t_new = m_new.get("timestamp") or datetime.min
                            if t_old > t_new:
                                # Overwrite new with old's value
                                db.user_profile_memories.update_one(
                                    {"_id": m_new["_id"]},
                                    {"$set": {
                                        "value": m_old["value"],
                                        "explanation": m_old.get("explanation", ""),
                                        "timestamp": t_old
                                    }}
                                )
                            # Delete the obsolete legacy key
                            db.user_profile_memories.delete_one({"_id": m_old["_id"]})
                        else:
                            # Standardize key name in database
                            db.user_profile_memories.update_one(
                                {"_id": m_old["_id"]},
                                {"$set": {"key": target_key}}
                            )
                        # Remove from local dict to avoid reprocessing
                        if key in mem_dict:
                            del mem_dict[key]
            except Exception as re_err:
                logger.error(f"Error reconciling user memories: {re_err}")
                
            # Reload memories after reconciliation
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
