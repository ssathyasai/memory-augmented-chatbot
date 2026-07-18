"""LangGraph hybrid orchestrator for RAG + Knowledge Graph + Tools routing."""

import logging
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .pipeline import RAGPipeline
from knowledge_graph.manager import get_knowledge_graph
from rag.llm_client import groq_client
from rag.embeddings import embedding_generator
from rag.web_scraper import WebScraper
from config.settings import settings

logger = logging.getLogger(__name__)


class HybridOrchestrator:
    """Hybrid RAG + Knowledge Graph + Web + Tools orchestrator using LangGraph."""
    
    def __init__(self, user_id: str):
        """
        Initialize the hybrid orchestrator.
        
        Args:
            user_id: User ID for data access
        """
        self.user_id = user_id
        self.rag_pipeline = RAGPipeline(user_id)
        self.kg_manager = get_knowledge_graph(user_id)
        self.web_scraper = WebScraper()
        self.memory = MemorySaver()
        
        # Build the workflow
        self.graph = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for hybrid RAG."""
        
        def load_recent_chats(state: Dict) -> Dict:
            """Load recent chat history."""
            state['recent_chats'] = self._load_recent_chats()
            return state
        
        def rag_query(state: Dict) -> Dict:
            """Process query through RAG pipeline."""
            question = state['messages'][-1]['content']
            result = self.rag_pipeline.query(question, top_k=settings.TOP_K_RESULTS)
            
            state['answer'] = result['answer']
            state['sources'] = result.get('sources', [])
            state['query_type'] = 'rag'
            return state
        
        def kg_query(state: Dict) -> Dict:
            """Process query through knowledge graph."""
            question = state['messages'][-1]['content']
            
            # Extract entities from the question
            entities = self._extract_entities_from_question(question)
            
            if entities:
                # Query knowledge graph for relationships
                kg_entities = []
                for entity in entities:
                    kg_entities.extend(self.kg_manager.get_entities(entity_type='person'))
                
                # Build KG context
                kg_context = self._build_kg_context(kg_entities, entities)
                
                # Generate answer using KG context
                system_prompt = f"""You are a helpful assistant that answers questions using the provided knowledge graph context.

Knowledge Graph Context:
{kg_context}

Answer the user's question using this structured knowledge."""

                answer = groq_client.generate_response(
                    system_prompt=system_prompt,
                    user_query=question,
                    context=""
                )
                
                state['answer'] = answer
                state['entities'] = kg_entities
                state['query_type'] = 'kg'
            else:
                # Fallback to direct LLM
                state['answer'] = groq_client.chat_completion(state['messages'])
                state['query_type'] = 'direct'
            
            return state
        
        def web_query(state: Dict) -> Dict:
            """Process query using web scraping."""
            question = state['messages'][-1]['content']
            
            # Extract search terms from question
            search_terms = self._extract_search_terms(question)
            
            if search_terms:
                # Scrape web data
                web_results = []
                for term in search_terms[:2]:  # Limit to 2 searches
                    try:
                        results = self.web_scraper.search(term, max_results=2)
                        web_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Web scrape error for '{term}': {e}")
                
                # Build web context
                state['web_data'] = self._format_web_results(web_results)
                
                # Generate answer
                system_prompt = f"""You are a helpful assistant that answers questions using current web data.

Web Data:
{state['web_data']}

Answer the user's question using this up-to-date information."""

                state['answer'] = groq_client.generate_response(
                    system_prompt=system_prompt,
                    user_query=question,
                    context=""
                )
                state['query_type'] = 'web'
            else:
                state['answer'] = groq_client.chat_completion(state['messages'])
                state['query_type'] = 'direct'
            
            return state
        
        def direct_query(state: Dict) -> Dict:
            """Direct LLM query without RAG or KG."""
            state['answer'] = groq_client.chat_completion(state['messages'])
            state['query_type'] = 'direct'
            return state
        
        def save_message(state: Dict) -> Dict:
            """Save the chat message to MongoDB."""
            self._save_chat_message(state['messages'][-1]['content'], state['answer'], state.get('sources', []))
            return state
        
        def update_recent_chats(state: Dict) -> Dict:
            """Update recent chats list."""
            state['recent_chats'] = self._load_recent_chats()
            return state
        
        # Build the workflow
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("load_history", load_recent_chats)
        workflow.add_node("rag", rag_query)
        workflow.add_node("kg", kg_query)
        workflow.add_node("web", web_query)
        workflow.add_node("direct", direct_query)
        workflow.add_node("save", save_message)
        workflow.add_node("update_recent", update_recent_chats)
        
        # Add edges
        workflow.add_edge("__start__", "load_history")
        workflow.add_edge("rag", "save")
        workflow.add_edge("kg", "save")
        workflow.add_edge("web", "save")
        workflow.add_edge("direct", "save")
        workflow.add_edge("save", "update_recent")
        workflow.add_edge("update_recent", END)
        
        # Add conditional edges for routing
        workflow.add_conditional_edges(
            "load_history",
            lambda state: self._route_query(state),
            {
                "rag": "rag",
                "kg": "kg",
                "web": "web",
                "direct": "direct"
            }
        )
        
        return workflow.compile(checkpointer=self.memory)
    
    def _route_query(self, state: Dict) -> str:
        """Determine which path to take based on query analysis."""
        last_message = state['messages'][-1]['content'].lower() if state.get('messages') else ""
        
        # Web-related keywords
        if any(word in last_message for word in ["current", "latest", "real-time", "news", "today", "recent"]):
            return "web"
        
        # Entity/relationship questions
        if any(word in last_message for word in ["who is", "what is", "relationship", "connected", "knows"]):
            return "kg"
        
        # Document-specific questions
        if len(state.get('messages', [])) > 1:
            return "rag"
        
        return "direct"
    
    def _extract_entities_from_question(self, question: str) -> List[str]:
        """Extract entities from a question."""
        import spacy
        
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(question)
            return [ent.text for ent in doc.ents]
        except Exception:
            return []
    
    def _extract_search_terms(self, question: str) -> List[str]:
        """Extract search terms from a question."""
        keywords = ["current", "latest", "news", "today", "recent", "up-to-date"]
        terms = []
        
        for keyword in keywords:
            if keyword in question.lower():
                # Extract terms around the keyword
                words = question.split()
                idx = next((i for i, w in enumerate(words) if keyword in w.lower()), -1)
                if idx > 0:
                    terms.append(" ".join(words[max(0, idx-2):idx+2]))
                    break
        
        if not terms:
            terms.append(question)  # Use full question as fallback
        
        return terms
    
    def _build_kg_context(self, entities: List[Dict], search_entities: List[str]) -> str:
        """Build context string from knowledge graph entities."""
        context_parts = []
        
        for entity in entities:
            context_parts.append(f"Entity: {entity.get('name', 'Unknown')}")
            context_parts.append(f"  Type: {entity.get('type', 'Unknown')}")
            
            # Get relationships
            relationships = self.kg_manager.get_relationships(entity.get('name', ''))
            if relationships:
                context_parts.append("  Relationships:")
                for rel in relationships[:3]:  # Top 3 relationships
                    context_parts.append(f"    - {rel.get('source', '')} -> {rel.get('type', 'related_to')} -> {rel.get('target', '')}")
            
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _format_web_results(self, results: List[Dict]) -> str:
        """Format web search results into context."""
        if not results:
            return "No web data found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}]")
            context_parts.append(f"Title: {result.get('title', 'No title')}")
            context_parts.append(f"URL: {result.get('url', 'No URL')}")
            context_parts.append(f"Content: {result.get('content', 'No content')[:500]}...")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _load_recent_chats(self) -> List[Dict[str, Any]]:
        """Load recent chat history from MongoDB."""
        from config.database import get_database
        
        try:
            db = get_database()
            if db:
                recent = list(db.chats.find(
                    {"user_id": self.user_id}
                ).sort("timestamp", -1).limit(10))
                
                return [
                    {
                        "question": r.get("question", ""),
                        "answer": r.get("answer", ""),
                        "timestamp": r.get("timestamp", "")
                    }
                    for r in recent
                ]
        except Exception as e:
            logger.error(f"Error loading recent chats: {e}")
        
        return []
    
    def _save_chat_message(self, question: str, answer: str, sources: List[Dict]) -> None:
        """Save a chat message to MongoDB."""
        from config.database import get_database
        from datetime import datetime
        
        try:
            db = get_database()
            if db:
                chat_doc = {
                    "user_id": self.user_id,
                    "question": question,
                    "answer": answer,
                    "sources": sources,
                    "query_type": "rag",
                    "timestamp": datetime.utcnow()
                }
                db.chats.insert_one(chat_doc)
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a query through the hybrid system.
        
        Args:
            question: User's question
        
        Returns:
            Dictionary with answer, sources, query type, etc.
        """
        try:
            # Prepare initial state
            state = {
                "messages": [{"role": "user", "content": question}],
                "user_id": self.user_id,
                "recent_chats": [],
                "query_type": ""
            }
            
            # Run the workflow
            result = self.graph.invoke(state, config={"configurable": {"thread_id": self.user_id}})
            
            return {
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "entities": result.get("entities", []),
                "web_data": result.get("web_data", ""),
                "query_type": result.get("query_type", ""),
                "recent_chats": result.get("recent_chats", []),
                "context": result.get("context", ""),
                "kg_context": result.get("kg_context", "")
            }
        
        except Exception as e:
            logger.error(f"Error in hybrid query: {e}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "entities": [],
                "web_data": "",
                "query_type": "error",
                "recent_chats": [],
                "error": str(e)
            }


# Global orchestrator instance
def get_hybrid_orchestrator(user_id: str) -> HybridOrchestrator:
    """Get a hybrid orchestrator instance for a user."""
    return HybridOrchestrator(user_id)
