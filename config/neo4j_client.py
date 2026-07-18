"""Neo4j database connection and management."""

import logging
from typing import Optional, Dict, List, Any
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

from .settings import settings

logger = logging.getLogger(__name__)


class Neo4jManager:
    """Manage Neo4j connections and operations."""
    
    def __init__(self):
        """Initialize Neo4j manager."""
        self._driver: Optional[Driver] = None
    
    def connect(self) -> bool:
        """
        Connect to Neo4j.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600
            )
            
            # Test connection
            with self._driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            
            logger.info("Connected to Neo4j")
            return True
            
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._driver = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            self._driver = None
            return False
    
    def get_driver(self) -> Optional[Driver]:
        """
        Get Neo4j driver instance.
        
        Returns:
            Driver or None if not connected
        """
        if self._driver is None:
            logger.warning("Neo4j not connected. Attempting to connect...")
            self.connect()
        return self._driver
    
    def is_connected(self) -> bool:
        """
        Check if Neo4j is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if self._driver is None:
            return False
        
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            return True
        except Exception:
            return False
    
    def disconnect(self):
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Disconnected from Neo4j")
            self._driver = None
    
    def create_constraints_and_indexes(self):
        """Create necessary constraints and indexes."""
        if self._driver is None:
            logger.error("Cannot create constraints: driver not connected")
            return
        
        try:
            with self._driver.session() as session:
                # User node uniqueness constraint
                session.run("""
                    CREATE CONSTRAINT user_id_unique IF NOT EXISTS
                    FOR (u:User) REQUIRE u.id IS UNIQUE
                """)
                
                # Entity node uniqueness constraint
                session.run("""
                    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                    FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """)
                
                # Index on entity user_id for isolation
                session.run("""
                    CREATE INDEX entity_user_id IF NOT EXISTS
                    FOR (e:Entity) ON (e.user_id)
                """)
                
                # Index on entity name for search
                session.run("""
                    CREATE INDEX entity_name IF NOT EXISTS
                    FOR (e:Entity) ON (e.name)
                """)
                
                # Index on entity type
                session.run("""
                    CREATE INDEX entity_type IF NOT EXISTS
                    FOR (e:Entity) ON (e.type)
                """)
                
                logger.info("Neo4j constraints and indexes created successfully")
                
        except Exception as e:
            logger.error(f"Error creating constraints/indexes: {e}")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
        
        Returns:
            List of result records as dictionaries
        """
        if self._driver is None:
            logger.error("Cannot execute query: driver not connected")
            return []
        
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    def execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute a write query (CREATE, UPDATE, DELETE).
        
        Args:
            query: Cypher query string
            parameters: Query parameters
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self._driver is None:
            logger.error("Cannot execute write query: driver not connected")
            return False
        
        try:
            with self._driver.session() as session:
                session.run(query, parameters or {})
            return True
        except Exception as e:
            logger.error(f"Error executing write query: {e}")
            return False


# Global Neo4j manager instance
neo4j_manager = Neo4jManager()


def get_neo4j_driver() -> Optional[Driver]:
    """
    Get Neo4j driver instance.
    
    Returns:
        Driver or None if not connected
    """
    return neo4j_manager.get_driver()
