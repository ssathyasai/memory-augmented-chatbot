"""Neo4j knowledge graph operations."""

import logging
from typing import List, Dict, Any, Optional

from config.neo4j_client import neo4j_manager
from errors.exceptions import KnowledgeGraphError

logger = logging.getLogger(__name__)


class Neo4jKnowledgeGraph:
    """Manage knowledge graph in Neo4j."""
    
    def __init__(self, user_id: str):
        """
        Initialize knowledge graph for user.
        
        Args:
            user_id: User ID for data isolation
        """
        self.user_id = user_id
        self.driver = neo4j_manager.get_driver()
    
    def add_entity(
        self,
        entity_name: str,
        entity_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """
        Add entity to knowledge graph.
        
        Args:
            entity_name: Entity name
            entity_type: Entity type
            properties: Additional properties
        
        Returns:
            True if successful
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return False
        
        try:
            props = properties or {}
            props.update({
                "user_id": self.user_id,
                "name": entity_name,
                "type": entity_type
            })
            
            # Convert properties to Cypher format
            props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
            
            query = f"""
            MERGE (e:Entity {{user_id: $user_id, name: $name}})
            SET e += {{{props_str}}}
            RETURN e
            """
            
            with self.driver.session() as session:
                session.run(query, **props)
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding entity: {e}")
            return False
    
    def add_relationship(
        self,
        source_entity: str,
        target_entity: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """
        Add relationship between entities.
        
        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            relationship_type: Relationship type
            properties: Additional properties
        
        Returns:
            True if successful
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return False
        
        try:
            props = properties or {}
            props["type"] = relationship_type
            
            query = """
            MATCH (s:Entity {user_id: $user_id, name: $source})
            MATCH (t:Entity {user_id: $user_id, name: $target})
            MERGE (s)-[r:RELATED {type: $rel_type}]->(t)
            SET r += $properties
            RETURN r
            """
            
            with self.driver.session() as session:
                session.run(
                    query,
                    user_id=self.user_id,
                    source=source_entity,
                    target=target_entity,
                    rel_type=relationship_type,
                    properties=props
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            return False
    
    def get_entities(self, entity_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get entities from knowledge graph.
        
        Args:
            entity_type: Filter by entity type (None for all)
            limit: Maximum number of entities
        
        Returns:
            List of entities
        """
        if not self.driver:
            return []
        
        try:
            if entity_type:
                query = """
                MATCH (e:Entity {user_id: $user_id, type: $entity_type})
                RETURN e.name AS name, e.type AS type, properties(e) AS properties
                LIMIT $limit
                """
                params = {"user_id": self.user_id, "entity_type": entity_type, "limit": limit}
            else:
                query = """
                MATCH (e:Entity {user_id: $user_id})
                RETURN e.name AS name, e.type AS type, properties(e) AS properties
                LIMIT $limit
                """
                params = {"user_id": self.user_id, "limit": limit}
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                entities = [dict(record) for record in result]
            
            return entities
        
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []
    
    def get_relationships(self, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get relationships from knowledge graph.
        
        Args:
            entity_name: Filter by entity name (None for all)
        
        Returns:
            List of relationships
        """
        if not self.driver:
            return []
        
        try:
            if entity_name:
                query = """
                MATCH (s:Entity {user_id: $user_id, name: $entity_name})-[r:RELATED]->(t:Entity)
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                UNION
                MATCH (s:Entity)-[r:RELATED]->(t:Entity {user_id: $user_id, name: $entity_name})
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                """
                params = {"user_id": self.user_id, "entity_name": entity_name}
            else:
                query = """
                MATCH (s:Entity {user_id: $user_id})-[r:RELATED]->(t:Entity)
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                LIMIT 100
                """
                params = {"user_id": self.user_id}
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                relationships = [dict(record) for record in result]
            
            return relationships
        
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get knowledge graph statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.driver:
            return {"entities": 0, "relationships": 0}
        
        try:
            with self.driver.session() as session:
                # Count entities
                result = session.run(
                    "MATCH (e:Entity {user_id: $user_id}) RETURN count(e) AS count",
                    user_id=self.user_id
                )
                entity_count = result.single()["count"]
                
                # Count relationships
                result = session.run(
                    "MATCH (s:Entity {user_id: $user_id})-[r:RELATED]->() RETURN count(r) AS count",
                    user_id=self.user_id
                )
                rel_count = result.single()["count"]
            
            return {
                "entities": entity_count,
                "relationships": rel_count
            }
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"entities": 0, "relationships": 0}


# Create knowledge graph instance
def get_knowledge_graph(user_id: str) -> Neo4jKnowledgeGraph:
    """Get knowledge graph for user."""
    return Neo4jKnowledgeGraph(user_id)
