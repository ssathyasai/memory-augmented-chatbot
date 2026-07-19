"""Document chunk retrieval module with sub-query decomposition and hybrid search.

Process Flow:
1. Receives user query string, `top_k`, and `similarity_threshold` parameters.
2. Decomposes multi-question prompts into focused sub-queries.
3. Performs dense vector search (FAISS) and sparse keyword matching for each sub-query.
4. Aggregates, deduplicates, and ranks chunks to ensure multi-topic coverage.
5. Filters retrieved document chunks based on `similarity_threshold`.
6. Returns sorted list of `(doc_id, chunk_text, similarity_score)` tuples.
"""

import logging
import re
from typing import List, Tuple, Dict, Any

from config.settings import settings
from .embeddings import embedding_generator
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieve relevant documents for queries with hybrid search & query decomposition."""
    
    def __init__(self, user_id: str):
        """
        Initialize retriever for a user.
        
        Args:
            user_id: User ID for accessing their vector store
        """
        self.user_id = user_id
        self.vector_store = VectorStore(user_id)
        self.embedding_gen = embedding_generator
    
    def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose multi-part question prompts into focused sub-queries.
        
        Args:
            query: Raw user query string
            
        Returns:
            List of sub-query strings
        """
        # Split by question marks, newlines, or numbered lists (1., 2., etc.)
        parts = [p.strip() for p in re.split(r'\?|\n|\d+\.\s*', query) if p.strip()]
        
        sub_queries = []
        for p in parts:
            if len(p) > 3:
                sub_q = p if p.endswith('?') else f"{p}?"
                sub_queries.append(sub_q)
        
        # Include original full query if it contains multiple topics
        if len(sub_queries) > 1 and query not in sub_queries:
            sub_queries.append(query)
            
        return sub_queries if sub_queries else [query]

    def _keyword_search(self, sub_query: str) -> List[Tuple[str, str, float]]:
        """
        Sparse keyword search across indexed chunks in vector store metadata.
        
        Args:
            sub_query: Sub-query string
            
        Returns:
            List of (doc_id, chunk_text, similarity_score)
        """
        stop_words = {
            "the", "is", "was", "are", "in", "of", "a", "an", "what", "which",
            "who", "when", "where", "how", "does", "do", "did", "and", "or",
            "to", "for", "on", "at", "by", "with", "this", "that", "it", "should", "pay"
        }
        words = [w.strip("?,.:;!\"'").lower() for w in sub_query.split()]
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        if not keywords:
            return []
        
        results = []
        if hasattr(self.vector_store, 'metadata') and self.vector_store.metadata:
            for doc_id, doc_data in self.vector_store.metadata.items():
                chunks = doc_data.get("chunks", [])
                for chunk in chunks:
                    chunk_lower = chunk.lower()
                    matches = sum(1 for kw in keywords if kw in chunk_lower)
                    if matches > 0:
                        # Score proportional to keyword coverage (0.3 to 0.8 scale)
                        score = 0.3 + 0.5 * (matches / max(len(keywords), 1))
                        results.append((doc_id, chunk, min(score, 0.9)))
                        
        return results

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[Tuple[str, str, float]]:
        """
        Retrieve relevant document chunks using hybrid vector + keyword search and sub-query decomposition.
        
        Args:
            query: Search query
            top_k: Number of results to return (default from settings)
            similarity_threshold: Minimum similarity score (default from settings)
        
        Returns:
            List of (doc_id, chunk_text, similarity_score) tuples
        """
        top_k = top_k or settings.TOP_K_RESULTS
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD
        
        try:
            sub_queries = self._decompose_query(query)
            logger.info(f"Retriever processing {len(sub_queries)} sub-queries for: {query[:80]}...")
            
            chunk_scores: Dict[str, Tuple[str, str, float]] = {}  # chunk_text -> (doc_id, chunk_text, max_score)
            
            for sub_q in sub_queries:
                # 1. Vector Search
                query_embedding = self.embedding_gen.generate_embedding(sub_q)
                vector_results = self.vector_store.search(query_embedding, top_k=max(top_k, 5))
                
                # 2. Sparse Keyword Search
                keyword_results = self._keyword_search(sub_q)
                
                # Combine results for this sub-query
                for doc_id, chunk, score in vector_results + keyword_results:
                    if chunk not in chunk_scores or score > chunk_scores[chunk][2]:
                        chunk_scores[chunk] = (doc_id, chunk, score)
            
            # Sort all unique retrieved chunks by score descending
            all_candidates = sorted(chunk_scores.values(), key=lambda x: x[2], reverse=True)
            
            # Filter by similarity threshold
            filtered_results = [
                (doc_id, chunk, score)
                for doc_id, chunk, score in all_candidates
                if score >= similarity_threshold
            ]
            
            # Limit to top_k results
            final_results = filtered_results[:top_k]
            logger.info(f"Retrieved {len(final_results)} relevant chunks across {len(sub_queries)} sub-queries")
            return final_results
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

