"""Document chunk retrieval module.

Process Flow:
1. Receives user query string, `top_k`, and `similarity_threshold` parameters.
2. Converts query text into dense vector embedding using `embedding_generator`.
3. Performs nearest-neighbor vector search in the user's isolated FAISS index (`VectorStore.search`).
4. Filters retrieved document chunks based on `similarity_threshold` to exclude low-relevance noise.
5. Returns sorted list of `(doc_id, chunk_text, similarity_score)` tuples.
"""

import logging
from typing import List, Tuple

from config.settings import settings
from .embeddings import embedding_generator
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieve relevant documents for queries."""
    
    def __init__(self, user_id: str):
        """
        Initialize retriever for a user.
        
        Args:
            user_id: User ID for accessing their vector store
        """
        self.user_id = user_id
        self.vector_store = VectorStore(user_id)
        self.embedding_gen = embedding_generator
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[Tuple[str, str, float]]:
        """
        Retrieve relevant document chunks for a query.
        
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
            # Generate query embedding
            logger.info(f"Generating embedding for query: {query[:100]}...")
            query_embedding = self.embedding_gen.generate_embedding(query)
            
            # Search vector store
            logger.info(f"Searching vector store (top_k={top_k})")
            results = self.vector_store.search(query_embedding, top_k=top_k)
            
            # Filter by similarity threshold
            filtered_results = [
                (doc_id, chunk, score)
                for doc_id, chunk, score in results
                if score >= similarity_threshold
            ]
            
            logger.info(f"Retrieved {len(filtered_results)} relevant chunks")
            return filtered_results
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
