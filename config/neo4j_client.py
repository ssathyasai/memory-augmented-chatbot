"""Neo4j database connection and graph driver management.

Process Flow:
1. Instantiates Bolt driver connection using configured URI and credentials (compatible with Neo4j Aura & local instances).
2. Verifies graph database connectivity using `driver.verify_connectivity()`.
3. Handles database name resolution (defaulting cleanly to 'neo4j' without erroneous overrides).
4. Auto-creates Cypher constraints and indexes (`User`, `Entity`) for performant graph traversal.
5. Provides diagnostic status inspection and fault-tolerant query execution.
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
        self._connection_attempted: bool = False
        self._last_error: Optional[str] = None
        
    def _get_db_name(self) -> str:
        """
        Get database name.
        
        Ensures it defaults cleanly to 'neo4j' and prevents erroneous overrides 
        (e.g., using an Aura instance ID as the database name).
        """
        database = getattr(settings, 'NEO4J_DATABASE', 'neo4j')
        if not database:
            return "neo4j"
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        uri = getattr(settings, 'NEO4J_URI', '')
        # If database was set to the Aura instance ID (e.g. fc54b344) instead of 'neo4j'
        if database != "neo4j" and (database == user or (uri and database in uri)):
            return "neo4j"
        return database

    def _get_user(self) -> str:
        """
        Get Neo4j username.
        
        Defaults to 'neo4j'. If an Aura instance ID was erroneously entered as the username,
        automatically falls back to 'neo4j' since Aura usernames are always 'neo4j'.
        """
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        if not user:
            return "neo4j"
        uri = getattr(settings, 'NEO4J_URI', '')
        if user != "neo4j" and uri and user in uri:
            return "neo4j"
        return user
    
    def connect(self, force: bool = False) -> bool:
        """
        Connect to Neo4j.
        
        Args:
            force: Re-attempt connection even if previously attempted.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if self._connection_attempted and not force and self._driver is None:
            return False

        self._connection_attempted = True
        self._last_error = None

        if not settings.NEO4J_PASSWORD or not settings.NEO4J_URI:
            self._last_error = "Neo4j credentials (NEO4J_PASSWORD or NEO4J_URI) not configured in environment or .env."
            logger.info("Neo4j credentials not configured. Skipping connection.")
            return False

        user = self._get_user()
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(user, settings.NEO4J_PASSWORD)
            )
            
            # Test connection using verify_connectivity()
            self._driver.verify_connectivity()
            
            logger.info(f"Connected to Neo4j at {settings.NEO4J_URI} as user '{user}'")
            return True
            
        except AuthError as e:
            self._last_error = f"Authentication failed for user '{user}': {e}"
            logger.error(self._last_error)
            if self._driver:
                try:
                    self._driver.close()
                except Exception:
                    pass
            self._driver = None
            return False
        except ServiceUnavailable as e:
            self._last_error = f"Neo4j service unavailable at {settings.NEO4J_URI}: {e}"
            logger.error(self._last_error)
            if self._driver:
                try:
                    self._driver.close()
                except Exception:
                    pass
            self._driver = None
            return False
        except Exception as e:
            self._last_error = f"Unexpected error connecting to Neo4j: {e}"
            logger.error(self._last_error)
            if self._driver:
                try:
                    self._driver.close()
                except Exception:
                    pass
            self._driver = None
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get diagnostic status information about the Neo4j connection."""
        connected = self.is_connected()
        return {
            "connected": connected,
            "uri": settings.NEO4J_URI,
            "user": self._get_user(),
            "database": self._get_db_name(),
            "has_password": bool(settings.NEO4J_PASSWORD),
            "last_error": self._last_error if not connected else None
        }

    def get_driver(self) -> Optional[Driver]:
        """
        Get Neo4j driver instance.
        
        Returns:
            Driver or None if not connected
        """
        if self._driver is None:
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
        except Exception as e:
            self._last_error = str(e)
            return False
    
    def disconnect(self):
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Disconnected from Neo4j")
            self._driver = None
    
    def create_constraints_and_indexes(self):
        """Create necessary constraints and indexes with individual error isolation."""
        driver = self.get_driver()
        if driver is None:
            logger.error("Cannot create constraints: driver not connected")
            return
        
        database = self._get_db_name()
        
        statements = [
            ("user_id_unique constraint", """
                CREATE CONSTRAINT user_id_unique IF NOT EXISTS
                FOR (u:User) REQUIRE u.id IS UNIQUE
            """),
            ("entity_user_id index", """
                CREATE INDEX entity_user_id IF NOT EXISTS
                FOR (e:Entity) ON (e.user_id)
            """),
            ("entity_name index", """
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """),
            ("entity_user_name index", """
                CREATE INDEX entity_user_name IF NOT EXISTS
                FOR (e:Entity) ON (e.user_id, e.name)
            """),
            ("entity_type index", """
                CREATE INDEX entity_type IF NOT EXISTS
                FOR (e:Entity) ON (e.type)
            """),
        ]
        
        for name, stmt in statements:
            try:
                try:
                    driver.execute_query(stmt, database_=database)
                except Exception:
                    driver.execute_query(stmt)
                logger.info(f"Neo4j {name} verified/created.")
            except Exception as e:
                logger.warning(f"Could not create Neo4j {name}: {e}")
        
        logger.info("Neo4j constraints and indexes processed successfully")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
        
        Returns:
            List of result records as dictionaries
        """
        driver = self.get_driver()
        if driver is None:
            logger.error("Cannot execute query: driver not connected")
            return []
        
        database = self._get_db_name()
        try:
            try:
                records, summary, keys = driver.execute_query(
                    query, 
                    parameters or {}, 
                    database_=database
                )
            except Exception as db_err:
                if database != "neo4j":
                    records, summary, keys = driver.execute_query(
                        query, 
                        parameters or {}, 
                        database_="neo4j"
                    )
                else:
                    raise db_err
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
        driver = self.get_driver()
        if driver is None:
            logger.error("Cannot execute write query: driver not connected")
            return False
        
        database = self._get_db_name()
        try:
            try:
                driver.execute_query(query, parameters or {}, database_=database)
            except Exception as db_err:
                if database != "neo4j":
                    driver.execute_query(query, parameters or {}, database_="neo4j")
                else:
                    raise db_err
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
