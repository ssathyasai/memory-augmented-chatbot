"""Knowledge graph package initialization.

Process Flow:
1. Exports factory function `get_knowledge_graph` for obtaining user-scoped graph instances.
2. Exports `Neo4jKnowledgeGraph` driver manager class.
"""

from .manager import get_knowledge_graph
from .neo4j_manager import Neo4jKnowledgeGraph

__all__ = ["get_knowledge_graph", "Neo4jKnowledgeGraph"]
