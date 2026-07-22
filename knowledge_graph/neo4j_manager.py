"""Neo4j Cypher query execution and graph database storage.

Process Flow:
1. Executes Cypher `MERGE` queries to upsert user-isolated `Entity` nodes with property dictionaries.
2. Executes Cypher `MATCH`/`MERGE` queries to create directed `RELATED` edges between entities.
3. Queries graph entities, relationship types, and node connection counts for visualization and graph analytics.
4. Executes Cypher deletion statements for document-specific, session-specific, or full-user graph wipe requests.
"""

import logging
from typing import List, Dict, Any, Optional

from config.neo4j_client import neo4j_manager
from config.settings import settings
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
        self.database = getattr(settings, 'NEO4J_DATABASE', 'neo4j')
        if self.database == "neo4j" and settings.NEO4J_USER and settings.NEO4J_USER != "neo4j":
            self.database = settings.NEO4J_USER
    
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
            
            with self.driver.session(database=self.database) as session:
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
            
            with self.driver.session(database=self.database) as session:
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
            
            with self.driver.session(database=self.database) as session:
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
                MATCH (s:Entity {user_id: $user_id, name: $entity_name})-[r:RELATED]->(t:Entity {user_id: $user_id})
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                UNION
                MATCH (s:Entity {user_id: $user_id})-[r:RELATED]->(t:Entity {user_id: $user_id, name: $entity_name})
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                """
                params = {"user_id": self.user_id, "entity_name": entity_name}
            else:
                query = """
                MATCH (s:Entity {user_id: $user_id})-[r:RELATED]->(t:Entity {user_id: $user_id})
                RETURN s.name AS source, t.name AS target, r.type AS type, properties(r) AS properties
                LIMIT 100
                """
                params = {"user_id": self.user_id}
            
            with self.driver.session(database=self.database) as session:
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
            with self.driver.session(database=self.database) as session:
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
            
    def delete_session_relations(self, session_id: str) -> bool:
        """
        Delete all relationships and orphan entities associated with a specific session ID.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if successful
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return False
            
        try:
            with self.driver.session(database=self.database) as session:
                # 1. Delete relationships matching user_id and session_id
                session.run(
                    "MATCH (s:Entity {user_id: $user_id})-[r:RELATED {session_id: $session_id}]->(t:Entity) DELETE r",
                    user_id=self.user_id,
                    session_id=session_id
                )
                # 2. Delete orphan entities with no relationships left
                session.run(
                    "MATCH (e:Entity {user_id: $user_id}) WHERE NOT (e)-[]-() DELETE e",
                    user_id=self.user_id
                )
            logger.info(f"Deleted relationships and clean up orphans for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session relationships: {e}")
            return False
            
    def delete_document_relations(self, document_id: str) -> bool:
        """
        Delete all relationships and orphan entities associated with a specific document ID.
        
        Args:
            document_id: The document ID to delete
            
        Returns:
            True if successful
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return False
            
        try:
            with self.driver.session(database=self.database) as session:
                # 1. Delete relationships matching user_id and document_id
                session.run(
                    "MATCH (s:Entity {user_id: $user_id})-[r:RELATED {document_id: $document_id}]->(t:Entity) DELETE r",
                    user_id=self.user_id,
                    document_id=document_id
                )
                # 2. Delete orphan entities with no relationships left
                session.run(
                    "MATCH (e:Entity {user_id: $user_id}) WHERE NOT (e)-[]-() DELETE e",
                    user_id=self.user_id
                )
            logger.info(f"Deleted relationships and clean up orphans for document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document relationships: {e}")
    def get_subgraph_around_entities(self, names: List[str]) -> Dict[str, Any]:
        """
        Retrieve nodes and relationships within 2 hops of the given entity names.
        
        Args:
            names: List of starting entity names
            
        Returns:
            Dictionary with 'entities' (list of node dicts) and 'relationships' (list of rel dicts)
        """
        if not self.driver or not names:
            return {"entities": [], "relationships": []}
            
        try:
            names_lower = [n.lower() for n in names]
            
            # 1. Fetch relationships within 2 hops
            query_rels = """
            MATCH (e:Entity {user_id: $user_id})
            WHERE toLower(e.name) IN $names_lower
            MATCH path = (e)-[r:RELATED*1..2]-(neighbor:Entity {user_id: $user_id})
            UNWIND relationships(path) AS rel
            RETURN DISTINCT startNode(rel).name AS source, endNode(rel).name AS target, rel.type AS type, properties(rel) AS properties
            """
            
            with self.driver.session(database=self.database) as session:
                result_rels = session.run(query_rels, user_id=self.user_id, names_lower=names_lower)
                relationships = [dict(record) for record in result_rels]
                
                # Collect all involved entity names
                all_entity_names = set(names)
                for rel in relationships:
                    all_entity_names.add(rel["source"])
                    all_entity_names.add(rel["target"])
                
                # 2. Fetch all involved entities
                query_entities = """
                MATCH (e:Entity {user_id: $user_id})
                WHERE toLower(e.name) IN $all_names_lower
                RETURN e.name AS name, e.type AS type, properties(e) AS properties
                """
                all_names_lower = [n.lower() for n in all_entity_names]
                result_entities = session.run(query_entities, user_id=self.user_id, all_names_lower=all_names_lower)
                entities = [dict(record) for record in result_entities]
                
            return {
                "entities": entities,
                "relationships": relationships
            }
        except Exception as e:
            logger.error(f"Error getting subgraph around entities: {e}")
            return {"entities": [], "relationships": []}

    def clear_graph(self) -> bool:
        """
        Clear all entities and relationships associated with the user.
        
        Returns:
            True if successful
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return False
            
        try:
            with self.driver.session(database=self.database) as session:
                session.run(
                    "MATCH (e:Entity {user_id: $user_id}) DETACH DELETE e",
                    user_id=self.user_id
                )
            logger.info(f"Cleared entire Knowledge Graph for user: {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing user graph: {e}")
            return False


# Create knowledge graph instance
def get_knowledge_graph(user_id: str) -> Neo4jKnowledgeGraph:
    """Get knowledge graph for user."""
    return Neo4jKnowledgeGraph(user_id)
