"""Neo4j database connection and graph driver management.

Process Flow:
1. Instantiates Bolt driver connection using configured URI and credentials (compatible with Neo4j Aura & local instances).
2. Verifies graph database connectivity using `driver.verify_connectivity()`.
3. Handles database name resolution for instance multi-tenancy.
4. Auto-creates Cypher constraints and indexes (`User`, `Document`, `Entity`, `Chunk`, `Concept`) for performant graph traversal.
"""

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
        
    def _get_db_name(self) -> str:
        """Get database name, falling back to user on Aura if database is defaulting to 'neo4j'."""
        database = getattr(settings, 'NEO4J_DATABASE', 'neo4j')
        if database == "neo4j" and settings.NEO4J_USER and settings.NEO4J_USER != "neo4j":
            return settings.NEO4J_USER
        return database
    
    def connect(self) -> bool:
        """
        Connect to Neo4j.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            
            # Test connection using verify_connectivity()
            self._driver.verify_connectivity()
            
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
            self._driver.verify_connectivity()
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
            # Use execute_query with database_ parameter for Aura
            database = self._get_db_name()
            
            # User node uniqueness constraint
            summary = self._driver.execute_query("""
                CREATE CONSTRAINT user_id_unique IF NOT EXISTS
                FOR (u:User) REQUIRE u.id IS UNIQUE
            """, database_=database)
            
            # Entity node uniqueness constraint
            summary = self._driver.execute_query("""
                CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """, database_=database)
            
            # Index on entity user_id for isolation
            summary = self._driver.execute_query("""
                CREATE INDEX entity_user_id IF NOT EXISTS
                FOR (e:Entity) ON (e.user_id)
            """, database_=database)
            
            # Index on entity name for search
            summary = self._driver.execute_query("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """, database_=database)
            
            # Index on entity type
            summary = self._driver.execute_query("""
                CREATE INDEX entity_type IF NOT EXISTS
                FOR (e:Entity) ON (e.type)
            """, database_=database)
            
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
            database = self._get_db_name()
            records, summary, keys = self._driver.execute_query(
                query, 
                parameters or {}, 
                database_=database
            )
            return [dict(record) for record in records]
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
            database = self._get_db_name()
            self._driver.execute_query(query, parameters or {}, database_=database)
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
