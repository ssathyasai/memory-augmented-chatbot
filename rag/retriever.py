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

    def _is_similar_content(self, text1: str, text2: str, threshold: float = 0.40) -> bool:
        """
        Check if two chunk text blocks have high body content overlap (ignoring section numbers/headers).
        
        Args:
            text1: First chunk text
            text2: Second chunk text
            threshold: Overlap threshold ratio
            
        Returns:
            True if chunks share duplicate body content
        """
        # Remove common section prefixes like "Section 12:", "Section 5: CVR College" etc.
        t1 = re.sub(r'section\s*\d+:?\s*', '', text1, flags=re.IGNORECASE).lower()
        t2 = re.sub(r'section\s*\d+:?\s*', '', text2, flags=re.IGNORECASE).lower()
        
        words1 = set(w for w in t1.split() if len(w) > 3)
        words2 = set(w for w in t2.split() if len(w) > 3)
        
        if not words1 or not words2:
            return False
            
        intersection = words1.intersection(words2)
        smaller = min(len(words1), len(words2))
        overlap = len(intersection) / smaller if smaller > 0 else 0.0
        return overlap >= threshold

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[Tuple[str, str, float]]:
        """
        Retrieve relevant document chunks using hybrid vector + keyword search, 
        sub-query decomposition, round-robin allocation, and semantic content deduplication.
        
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
            
            # Dynamically ensure top_k accommodates all sub-queries
            effective_top_k = max(top_k, len(sub_queries))
            
            sub_query_candidates: List[List[Tuple[str, str, float]]] = []
            all_raw_candidates: List[Tuple[str, str, float]] = []
            
            for sub_q in sub_queries:
                # 1. Vector Search
                query_embedding = self.embedding_gen.generate_embedding(sub_q)
                vector_results = self.vector_store.search(query_embedding, top_k=max(effective_top_k, 5))
                
                # 2. Sparse Keyword Search
                keyword_results = self._keyword_search(sub_q)
                
                # Combine vector & keyword candidates for sub_q
                candidates_dict: Dict[str, Tuple[str, str, float]] = {}
                for doc_id, chunk, score in vector_results + keyword_results:
                    if score >= similarity_threshold:
                        if chunk not in candidates_dict or score > candidates_dict[chunk][2]:
                            candidates_dict[chunk] = (doc_id, chunk, score)
                            
                sorted_sub_candidates = sorted(candidates_dict.values(), key=lambda x: x[2], reverse=True)
                sub_query_candidates.append(sorted_sub_candidates)
                all_raw_candidates.extend(sorted_sub_candidates)
            
            # Round-Robin Selection with Semantic Content Deduplication
            selected_chunks: List[Tuple[str, str, float]] = []
            
            # Round-Robin across sub-queries first to give every sub-question a fair allocation
            max_rounds = max((len(cands) for cands in sub_query_candidates), default=0)
            for r in range(max_rounds):
                for sub_cands in sub_query_candidates:
                    if r < len(sub_cands):
                        cand = sub_cands[r]
                        # Check semantic deduplication against already selected chunks
                        is_dup = any(self._is_similar_content(cand[1], sel[1]) for sel in selected_chunks)
                        if not is_dup:
                            selected_chunks.append(cand)
                            if len(selected_chunks) >= effective_top_k:
                                break
                if len(selected_chunks) >= effective_top_k:
                    break
            
            # If we still have slots left, fill with remaining non-duplicate raw candidates
            if len(selected_chunks) < effective_top_k:
                all_sorted = sorted(all_raw_candidates, key=lambda x: x[2], reverse=True)
                for cand in all_sorted:
                    is_dup = any(self._is_similar_content(cand[1], sel[1]) for sel in selected_chunks)
                    if not is_dup:
                        selected_chunks.append(cand)
                        if len(selected_chunks) >= effective_top_k:
                            break
            
            logger.info(f"Retrieved {len(selected_chunks)} distinct non-duplicate chunks across {len(sub_queries)} sub-queries")
            return selected_chunks
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

