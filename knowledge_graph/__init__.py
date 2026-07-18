"""Knowledge graph package."""

from .manager import get_knowledge_graph
from .neo4j_manager import Neo4jKnowledgeGraph

__all__ = ["get_knowledge_graph", "Neo4jKnowledgeGraph"]
