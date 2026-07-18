"""Knowledge graph manager."""

import logging
from typing import List, Dict, Any

from .entity_extractor import entity_extractor
from .neo4j_manager import get_knowledge_graph

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Manage knowledge graph operations."""
    
    def __init__(self, user_id: str):
        """
        Initialize knowledge graph manager.
        
        Args:
            user_id: User ID for data isolation
        """
        self.user_id = user_id
        self.kg = get_knowledge_graph(user_id)
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """
        Process text and extract knowledge.
        
        Args:
            text: Text to process
        
        Returns:
            Dictionary with extraction results
        """
        try:
            # Extract entities
            entities = entity_extractor.extract_entities(text)
            
            if not entities:
                return {
                    "entities_extracted": 0,
                    "entities_added": 0,
                    "success": True
                }
            
            # Add entities to knowledge graph
            added_count = 0
            for entity in entities:
                if self.kg.add_entity(
                    entity_name=entity["name"],
                    entity_type=entity["type"],
                    properties={"label": entity.get("label", "")}
                ):
                    added_count += 1
            
            logger.info(f"Processed text: {len(entities)} entities, {added_count} added to graph")
            
            return {
                "entities_extracted": len(entities),
                "entities_added": added_count,
                "entities": entities,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error processing text for knowledge graph: {e}")
            return {
                "entities_extracted": 0,
                "entities_added": 0,
                "success": False,
                "error": str(e)
            }
    
    def process_conversation(self, user_message: str, assistant_message: str):
        """
        Process a conversation turn and extract knowledge.
        
        Args:
            user_message: User's message
            assistant_message: Assistant's response
        """
        try:
            # Combine messages
            combined_text = f"{user_message}\n{assistant_message}"
            
            # Process
            self.process_text(combined_text)
        
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
    
    def get_entities(self, entity_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get entities from knowledge graph.
        
        Args:
            entity_type: Filter by type
            limit: Maximum results
        
        Returns:
            List of entities
        """
        return self.kg.get_entities(entity_type, limit)
    
    def get_relationships(self, entity_name: str = None) -> List[Dict[str, Any]]:
        """
        Get relationships from knowledge graph.
        
        Args:
            entity_name: Filter by entity
        
        Returns:
            List of relationships
        """
        return self.kg.get_relationships(entity_name)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get knowledge graph statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.kg.get_stats()
    
    def get_entity_types(self) -> Dict[str, int]:
        """
        Get entity type distribution.
        
        Returns:
            Dictionary of type counts
        """
        try:
            entities = self.kg.get_entities(limit=1000)
            type_counts = {}
            
            for entity in entities:
                entity_type = entity.get("type", "unknown")
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            
            return type_counts
        
        except Exception as e:
            logger.error(f"Error getting entity types: {e}")
            return {}
