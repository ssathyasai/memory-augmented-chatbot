"""RAG (Retrieval-Augmented Generation) package initialization.

Process Flow:
1. Exports `RAGPipeline` for dense vector & MongoDB fallback retrieval.
2. Exports `HybridOrchestrator` for LangGraph multi-agent hybrid state routing.
3. Exports `WebScraper` for internet search augmentation.
"""

from .pipeline import RAGPipeline
from .langgraph_orchestrator import get_hybrid_orchestrator, HybridOrchestrator
from .web_scraper import web_scraper, WebScraper

__all__ = ["RAGPipeline", "HybridOrchestrator", "get_hybrid_orchestrator", "web_scraper", "WebScraper"]
