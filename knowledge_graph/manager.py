"""Knowledge graph workflow manager module.

Process Flow:
1. Receives raw document text or conversation turn strings for graph indexing.
2. Uses LLM-based extraction (`_extract_graph_via_llm`) with JSON schema enforcement to parse semantic entities and typed relationships (`WORKS_AT`, `KNOWS`, `RELATED_TO`).
3. Falls back to spaCy Named Entity Recognition if LLM extraction is unavailable.
4. Writes entities and relationships to user-isolated Neo4j database using `Neo4jKnowledgeGraph`.
5. Processes chat conversation turns in real-time to continuously expand the user's graph network.
"""

import json
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
    
    def _extract_graph_via_llm(self, text: str) -> Dict[str, Any]:
        """Use Groq to extract semantically rich entities and relationships from text."""
        from rag.llm_client import groq_client
        
        system_prompt = """You are a Knowledge Graph extraction assistant.
Analyze the user's text and extract:
1. Entities: Important people, organizations, locations, products, concepts, or technical terms.
2. Relationships: Directed connections between the extracted entities with a specific, semantic relationship type.

You MUST respond ONLY with a valid JSON object. Do not include any markdown formatting like ```json.

JSON Schema:
{
  "entities": [
    {
      "name": "Entity Name (e.g., Alice)",
      "type": "entity type (e.g., person, organization, location, concept, product)"
    }
  ],
  "relationships": [
    {
      "source": "Source Entity Name",
      "target": "Target Entity Name",
      "type": "RELATIONSHIP_TYPE (use UPPERCASE snake_case, e.g., WORKS_AT, LIVES_IN, KNOWS, RELATED_TO)"
    }
  ]
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Text to extract from:\n{text}"}
        ]
        
        try:
            raw_response = groq_client.client.chat.completions.create(
                model=groq_client.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            response_text = raw_response.choices[0].message.content.strip()
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"LLM graph extraction failure: {e}")
            return {}

    def process_text(self, text: str, session_id: str = None, document_id: str = None) -> Dict[str, Any]:
        """
        Process text and extract knowledge (using LLM for rich relations, falling back to spaCy).
        
        Args:
            text: Text to process
            session_id: Optional chat session ID to associate with relationships
            document_id: Optional document ID to associate with relationships
        
        Returns:
            Dictionary with extraction results
        """
        sample_text = text[:8000].strip() if text else ""
        if not sample_text:
            return {
                "entities_extracted": 0,
                "entities_added": 0,
                "success": True
            }
            
        try:
            # Attempt LLM-based extraction for semantic entities & relations
            extracted_data = self._extract_graph_via_llm(sample_text)
            if extracted_data and (extracted_data.get("entities") or extracted_data.get("relationships")):
                entities = extracted_data.get("entities", [])
                relationships = extracted_data.get("relationships", [])
                
                # Add entities to graph
                entities_added = 0
                for ent in entities:
                    name = ent.get("name", "").strip()
                    ent_type = ent.get("type", "concept").strip().lower()
                    if name:
                        if self.kg.add_entity(entity_name=name, entity_type=ent_type):
                            entities_added += 1
                            
                # Add relationships to graph
                rels_added = 0
                for rel in relationships:
                    src = rel.get("source", "").strip()
                    tgt = rel.get("target", "").strip()
                    rel_type = rel.get("type", "RELATED_TO").strip().upper()
                    if src and tgt and rel_type:
                        # Ensure both entities exist in the graph first
                        self.kg.add_entity(entity_name=src, entity_type="concept")
                        self.kg.add_entity(entity_name=tgt, entity_type="concept")
                        
                        props = {}
                        if session_id:
                            props["session_id"] = session_id
                        if document_id:
                            props["document_id"] = document_id
                            
                        if self.kg.add_relationship(
                            source_entity=src,
                            target_entity=tgt,
                            relationship_type=rel_type,
                            properties=props if props else None
                        ):
                            rels_added += 1
                            
                logger.info(f"LLM KG extraction: {len(entities)} entities ({entities_added} added), {len(relationships)} relationships ({rels_added} added)")
                return {
                    "entities_extracted": len(entities),
                    "entities_added": entities_added,
                    "relationships_added": rels_added,
                    "entities": entities,
                    "success": True
                }
        except Exception as e:
            logger.warning(f"LLM-based KG extraction failed, falling back to spaCy: {e}")
            
        # Fallback to spaCy-based extraction
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
            
            # Add relationships between co-occurring entities in the text
            added_relationships = 0
            if len(entities) > 1:
                for i in range(len(entities) - 1):
                    source = entities[i]["name"]
                    target = entities[i+1]["name"]
                    
                    props = {}
                    if session_id:
                        props["session_id"] = session_id
                    if document_id:
                        props["document_id"] = document_id
                        
                    if self.kg.add_relationship(
                        source_entity=source,
                        target_entity=target,
                        relationship_type="RELATED_TO",
                        properties=props if props else None
                    ):
                        added_relationships += 1
            
            logger.info(f"Processed text (spaCy): {len(entities)} entities ({added_count} added), {added_relationships} relationships added to graph")
            
            return {
                "entities_extracted": len(entities),
                "entities_added": added_count,
                "relationships_added": added_relationships,
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
    
    def process_conversation(self, user_message: str, assistant_message: str, session_id: str = None):
        """
        Process a conversation turn and extract knowledge.
        
        Args:
            user_message: User's message
            assistant_message: Assistant's response
            session_id: Optional session ID associated with this turn
        """
        try:
            # Combine messages
            combined_text = f"{user_message}\n{assistant_message}"
            
            # Process
            self.process_text(combined_text, session_id=session_id)
        
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
