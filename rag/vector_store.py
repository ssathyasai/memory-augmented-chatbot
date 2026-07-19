"""FAISS-based vector store with user isolation."""

import logging
import os
import json
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import faiss

from config.settings import settings
from errors.exceptions import RAGError

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS vector store for document embeddings."""
    
    def __init__(self, user_id: str):
        """
        Initialize vector store for a user.
        
        Args:
            user_id: User ID for isolation
        """
        self.user_id = user_id
        self.vector_store_path = settings.VECTOR_STORE_PATH
        self.index_path = os.path.join(self.vector_store_path, f"index_user_{user_id}.faiss")
        self.metadata_path = os.path.join(self.vector_store_path, f"metadata_user_{user_id}.json")
        
        # Create directory if needed
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        self.index: Optional[faiss.IndexFlatL2] = None
        self.metadata: Dict[str, Any] = {}
        
        self._load_or_create()
    
    def _load_or_create(self):
        """Load existing index or create new one."""
        try:
            if os.path.exists(self.index_path):
                # Load existing index
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded existing FAISS index for user {self.user_id}")
                
                # Load metadata
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
            else:
                # Create new index
                dimension = settings.EMBEDDING_DIMENSION
                self.index = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index for user {self.user_id}")
                self._save()
        
        except Exception as e:
            logger.error(f"Error loading/creating index: {e}")
            raise RAGError(f"Failed to initialize vector store: {str(e)}")
    
    def add_documents(self, doc_id: str, chunks: List[str], embeddings: List[np.ndarray]):
        """
        Add document chunks to vector store.
        
        Args:
            doc_id: Document ID
            chunks: List of text chunks
            embeddings: List of embedding vectors
        """
        try:
            if not chunks or not embeddings:
                logger.warning(f"Empty chunks or embeddings for document {doc_id}")
                return
            
            if len(chunks) != len(embeddings):
                raise RAGError("Mismatch between chunks and embeddings count")
            
            # Convert embeddings to numpy array
            embeddings_array = np.array(embeddings).astype('float32')
            
            # Get starting index
            start_idx = self.index.ntotal
            
            # Add to FAISS index
            self.index.add(embeddings_array)
            
            # Store metadata
            if doc_id not in self.metadata:
                self.metadata[doc_id] = {
                    "chunk_indices": [],
                    "chunks": [],
                    "metadata": {}
                }
            
            for i, chunk in enumerate(chunks):
                chunk_idx = start_idx + i
                self.metadata[doc_id]["chunk_indices"].append(chunk_idx)
                self.metadata[doc_id]["chunks"].append(chunk)
            
            # Save
            self._save()
            
            logger.info(f"Added {len(chunks)} chunks for document {doc_id}")
        
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise RAGError(f"Failed to add documents: {str(e)}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
        
        Returns:
            List of (doc_id, chunk_text, similarity_score) tuples
        """
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector store is empty")
                return []
            
            # Ensure query embedding is 2D array
            query_array = np.array([query_embedding]).astype('float32')
            
            # Search
            distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
            
            # Convert results
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                # Find document and chunk
                doc_id, chunk_text = self._get_chunk_by_index(int(idx))
                if doc_id and chunk_text:
                    # Convert L2 distance to similarity score (inverse)
                    similarity = 1.0 / (1.0 + float(distance))
                    results.append((doc_id, chunk_text, similarity))
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def _get_chunk_by_index(self, chunk_idx: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Get chunk text by index.
        
        Args:
            chunk_idx: Chunk index in FAISS
        
        Returns:
            Tuple of (doc_id, chunk_text) or (None, None)
        """
        for doc_id, doc_meta in self.metadata.items():
            if chunk_idx in doc_meta["chunk_indices"]:
                local_idx = doc_meta["chunk_indices"].index(chunk_idx)
                chunk_text = doc_meta["chunks"][local_idx]
                return doc_id, chunk_text
        
        return None, None
    
    def delete_document(self, doc_id: str):
        """
        Delete document from vector store.
        
        Args:
            doc_id: Document ID
        """
        try:
            if doc_id in self.metadata:
                del self.metadata[doc_id]
                self._rebuild_index()
                self._save()
                logger.info(f"Removed metadata and rebuilt FAISS index for document {doc_id}")
        
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {e}")

    def _rebuild_index(self):
        """Rebuild FAISS index from remaining document metadata."""
        try:
            dimension = settings.EMBEDDING_DIMENSION
            new_index = faiss.IndexFlatL2(dimension)
            
            all_chunks = []
            doc_chunk_map = {}
            for d_id, d_meta in list(self.metadata.items()):
                chunks = d_meta.get("chunks", [])
                doc_chunk_map[d_id] = len(chunks)
                all_chunks.extend(chunks)
            
            if all_chunks:
                from rag.embeddings import embedding_generator
                embeddings = embedding_generator.generate_embeddings(all_chunks)
                embeddings_array = np.array(embeddings).astype('float32')
                new_index.add(embeddings_array)
                
                # Update chunk indices in metadata
                start_idx = 0
                for d_id, count in doc_chunk_map.items():
                    self.metadata[d_id]["chunk_indices"] = list(range(start_idx, start_idx + count))
                    start_idx += count
            
            self.index = new_index
            logger.info(f"Rebuilt FAISS index with {self.index.ntotal} total vectors.")
        
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
    
    def _save(self):
        """Save index and metadata to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise RAGError(f"Failed to save vector store: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "total_documents": len(self.metadata),
            "index_size_mb": os.path.getsize(self.index_path) / (1024 * 1024) if os.path.exists(self.index_path) else 0
        }
