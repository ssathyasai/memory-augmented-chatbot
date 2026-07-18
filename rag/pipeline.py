"""Complete RAG pipeline."""

import logging
from typing import List, Tuple, Dict, Any

from config.settings import settings
from .retriever import DocumentRetriever
from .llm_client import groq_client
from .embeddings import embedding_generator
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Complete RAG pipeline for question answering."""
    
    def __init__(self, user_id: str):
        """
        Initialize RAG pipeline for a user.
        
        Args:
            user_id: User ID for document access
        """
        self.user_id = user_id
        self.retriever = DocumentRetriever(user_id)
        self.llm_client = groq_client
    
    def index_document(self, doc_id: str, chunks: List[str]):
        """
        Index document chunks into vector store.
        
        Args:
            doc_id: Document ID
            chunks: List of text chunks
        """
        try:
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = embedding_generator.generate_embeddings(chunks)
            
            # Add to vector store
            vector_store = VectorStore(self.user_id)
            vector_store.add_documents(doc_id, chunks, embeddings)
            
            logger.info(f"Indexed document {doc_id} successfully")
        
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise
    
    def _truncate_history(
        self,
        conversation_history: List[Dict[str, str]],
        max_messages: int = 6,
        max_chars: int = 4000
    ) -> List[Dict[str, str]]:
        """
        Trim conversation history to stay within token budget.

        Args:
            conversation_history: Full history list
            max_messages: Maximum number of recent turns to keep
            max_chars: Rough character budget for all messages combined

        Returns:
            Trimmed history list
        """
        # Keep only the most recent messages
        history = conversation_history[-max_messages:] if conversation_history else []

        # Further trim if combined content still exceeds character budget
        while history and sum(len(m.get("content", "")) for m in history) > max_chars:
            history = history[1:]  # drop oldest

        return history

    def query(
        self,
        question: str,
        top_k: int = None,
        include_sources: bool = True,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG (fall back to direct LLM if no docs).
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            include_sources: Whether to include source citations
            conversation_history: Optional conversation history for direct LLM
        
        Returns:
            Dictionary with answer and sources
        """
        try:
            # Retrieve relevant documents
            logger.info(f"Processing query: {question[:100]}...")
            retrieved_docs = self.retriever.retrieve(question, top_k=top_k)
            
            if retrieved_docs:
                # Build context from retrieved documents
                context = self._build_context(retrieved_docs)
                
                # Generate system prompt
                system_prompt = """You are a helpful AI assistant that answers questions based on the provided context.

Rules:
1. Answer the question using the information from the provided context (if available)
2. If the context doesn't contain enough information, you can still answer using your general knowledge
3. Be concise but complete in your answers
4. Cite specific parts of the context when relevant
5. If you're not sure, acknowledge the uncertainty"""
                
                # Generate response
                logger.info("Generating response with GROQ LLM using RAG")
                answer = self.llm_client.generate_response(
                    system_prompt=system_prompt,
                    user_query=question,
                    context=context
                )
                
                # Prepare sources
                sources = []
                if include_sources:
                    sources = [
                        {
                            "doc_id": doc_id,
                            "chunk": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                            "similarity": score
                        }
                        for doc_id, chunk, score in retrieved_docs
                    ]
                
                return {
                    "answer": answer,
                    "sources": sources,
                    "has_sources": len(sources) > 0,
                    "num_sources": len(sources)
                }
            else:
                # No documents found - use direct LLM
                logger.info("No documents found, using direct LLM")
                if conversation_history is None:
                    conversation_history = []
                truncated = self._truncate_history(conversation_history)
                system_msg = {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Answer the user's questions clearly and concisely."
                }
                messages = [system_msg] + truncated + [{"role": "user", "content": question}]
                answer = self.llm_client.chat_completion(messages)
                
                return {
                    "answer": answer,
                    "sources": [],
                    "has_sources": False
                }
        
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            return {
                "answer": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "has_sources": False,
                "error": str(e)
            }
    
    def _build_context(self, retrieved_docs: List[Tuple[str, str, float]]) -> str:
        """
        Build context string from retrieved documents.
        
        Args:
            retrieved_docs: List of (doc_id, chunk, score) tuples
        
        Returns:
            Formatted context string
        """
        if not retrieved_docs:
            return ""
        
        context_parts = []
        for i, (doc_id, chunk, score) in enumerate(retrieved_docs, 1):
            context_parts.append(f"[Source {i}]\n{chunk}\n")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long (rough token estimate: 4 chars = 1 token)
        max_chars = settings.MAX_CONTEXT_TOKENS * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "\n[Context truncated...]"
        
        return context
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        use_rag: bool = True
    ) -> str:
        """
        Chat with the assistant.
        
        Args:
            messages: Conversation history
            use_rag: Whether to use RAG for retrieval
        
        Returns:
            Assistant's response
        """
        try:
            # Get the last user message
            last_message = messages[-1]["content"] if messages else ""
            
            if use_rag and last_message:
                # Use RAG pipeline
                result = self.query(last_message)
                return result["answer"]
            else:
                # Direct LLM call without retrieval
                truncated = self._truncate_history(messages)
                return self.llm_client.chat_completion(truncated)
        
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I encountered an error: {str(e)}"
