"""Entity extraction from text using spaCy."""

import logging
from typing import List, Dict, Any
import spacy

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract named entities from text."""
    
    _nlp = None
    
    @classmethod
    def _load_model(cls):
        """Lazy load spaCy model."""
        if cls._nlp is None:
            try:
                logger.info("Loading spaCy model...")
                cls._nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded")
            except Exception as e:
                logger.error(f"Error loading spaCy model: {e}")
                raise RuntimeError(
                    "spaCy model 'en_core_web_sm' is not installed. "
                    "Run: python -m spacy download en_core_web_sm"
                ) from e
    
    @classmethod
    def extract_entities(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            List of entity dictionaries
        """
        cls._load_model()
        
        try:
            # Process text
            doc = cls._nlp(text[:1000000])  # Limit to 1M chars
            
            entities = []
            seen = set()
            
            for ent in doc.ents:
                # Normalize entity text
                entity_text = ent.text.strip()
                
                # Skip duplicates and very short entities
                if entity_text in seen or len(entity_text) < 2:
                    continue
                
                seen.add(entity_text)
                
                # Map spaCy labels to our types
                entity_type = cls._map_entity_type(ent.label_)
                
                entities.append({
                    "name": entity_text,
                    "type": entity_type,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            
            logger.info(f"Extracted {len(entities)} entities")
            return entities
        
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    @staticmethod
    def _map_entity_type(spacy_label: str) -> str:
        """
        Map spaCy entity labels to simplified types.
        
        Args:
            spacy_label: spaCy NER label
        
        Returns:
            Simplified entity type
        """
        mapping = {
            "PERSON": "person",
            "ORG": "organization",
            "GPE": "location",
            "LOC": "location",
            "FAC": "facility",
            "PRODUCT": "product",
            "EVENT": "event",
            "WORK_OF_ART": "work",
            "LAW": "law",
            "LANGUAGE": "language",
            "DATE": "date",
            "TIME": "time",
            "MONEY": "money",
            "QUANTITY": "quantity",
            "ORDINAL": "number",
            "CARDINAL": "number"
        }
        
        return mapping.get(spacy_label, "concept")


# Global entity extractor
entity_extractor = EntityExtractor()
