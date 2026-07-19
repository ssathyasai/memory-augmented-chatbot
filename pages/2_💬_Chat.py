"""Streamlit conversational chat interface page.

Process Flow:
1. Enforces user authentication via session check.
2. Initializes user-isolated `MemoryManager`, `RAGPipeline`, and `HybridOrchestrator` instances.
3. Renders sidebar chat configuration (RAG toggle, Top-K source slider, session switching/deletion).
4. Fetches and displays current session conversation history.
5. Captures user prompts, passes query + history + session ID to `HybridOrchestrator`.
6. Renders assistant responses, document sources, and metadata expandable details.
"""

import streamlit as st
import logging
from datetime import datetime

from utils.session import require_auth, init_session_state, get_user_id
from rag.pipeline import RAGPipeline
from memory.manager import MemoryManager
from rag.langgraph_orchestrator import get_hybrid_orchestrator
from errors.handlers import get_user_message
from config.database import get_database

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("💬 Chat")

# Initialize RAG and Memory for user
user_id = get_user_id()

# Initialize memory manager in session state
if "memory_manager" not in st.session_state:
    st.session_state.memory_manager = MemoryManager(user_id)
    # Create or load session
    if not st.session_state.get("current_session_id"):
        session_id = st.session_state.memory_manager.create_session()
        st.session_state.current_session_id = session_id
    else:
        st.session_state.memory_manager.set_session(st.session_state.current_session_id)

# Initialize RAG pipeline in session state
if "rag_pipeline" not in st.session_state:
    st.session_state.rag_pipeline = RAGPipeline(user_id)

# Initialize hybrid orchestrator in session state
if "hybrid_orchestrator" not in st.session_state:
    st.session_state.hybrid_orchestrator = get_hybrid_orchestrator(user_id)

# Database connection
db = get_database()

# Sidebar
with st.sidebar:
    st.subheader("💬 Chat Options")
    
    # RAG settings
    st.markdown("### RAG Settings")
    use_rag = st.checkbox("Use Document Retrieval", value=True, help="Search your documents for answers")
    top_k = st.slider("Number of Sources", 1, 10, 5, help="How many document chunks to retrieve")
    show_sources = st.checkbox("Show Sources", value=True, help="Display source citations")
    
    st.markdown("---")
    
    # Session management
    if st.button("🆕 New Chat", use_container_width=True):
        # Create new session
        new_session_id = st.session_state.memory_manager.create_session()
        st.session_state.current_session_id = new_session_id
        st.session_state.memory_manager.set_session(new_session_id)
        st.success("Started new chat!")
        st.rerun()
    
    if st.button("🗑️ Clear History", use_container_width=True):
        if st.session_state.current_session_id:
            st.session_state.memory_manager.delete_session()
            # Create fresh session
            new_session_id = st.session_state.memory_manager.create_session()
            st.session_state.current_session_id = new_session_id
            st.success("Chat history cleared!")
            st.rerun()
    
    st.markdown("---")
    
    # Recent sessions
    st.markdown("### 📚 Recent Chats")
    sessions = st.session_state.memory_manager.get_user_sessions(limit=10)
    
    if sessions:
        for session in sessions:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                session_label = f"{session['message_count']} msgs"
                if st.button(session_label, key=f"sess_{session['session_id']}", use_container_width=True):
                    st.session_state.current_session_id = session['session_id']
                    st.session_state.memory_manager.set_session(session['session_id'])
                    st.rerun()
            with col2:
                st.caption(session['updated_at'].strftime("%m/%d"))
            with col3:
                if st.button("🗑️", key=f"del_{session['session_id']}", help="Delete this specific chat session"):
                    # Call storage delete directly
                    st.session_state.memory_manager.storage.delete_conversation(session['session_id'], user_id)
                    # Sync deletion: remove session relationships from Neo4j
                    try:
                        from knowledge_graph.manager import KnowledgeGraphManager
                        kg_mgr = KnowledgeGraphManager(user_id)
                        kg_mgr.kg.delete_session_relations(session['session_id'])
                    except Exception as e:
                        logger.error(f"Error deleting Neo4j session relations: {e}")
                    # If this was the current active session, clear session state
                    if st.session_state.current_session_id == session['session_id']:
                        st.session_state.current_session_id = None
                        st.session_state.memory_manager.clear_session()
                    st.success("Session deleted!")
                    st.rerun()
    else:
        st.info("No chat history yet")
    
    st.markdown("---")
    
    # Delete recent chats (MongoDB)
    st.markdown("### 🗑️ Delete Recent Chats")
    if st.button("Delete All Chat History", use_container_width=True, type="primary"):
        if db is not None:
            try:
                result_chats = db.chats.delete_many({"user_id": user_id})
                result_convs = db.conversations.delete_many({"user_id": user_id})
                
                # Sync deletion: clear all graph nodes for the user in Neo4j
                try:
                    from knowledge_graph.manager import KnowledgeGraphManager
                    kg_mgr = KnowledgeGraphManager(user_id)
                    kg_mgr.kg.clear_graph()
                except Exception as e:
                    logger.error(f"Error clearing Neo4j Knowledge Graph: {e}")
                
                # Clear long-term memory facts extracted from past chats
                try:
                    from memory.long_term import LongTermMemoryManager
                    LongTermMemoryManager.clear_user_memories(user_id)
                except Exception as e:
                    logger.error(f"Error clearing long-term memories: {e}")
                
                # Reset orchestrator and session state memory instances
                for key in ["hybrid_orchestrator", "memory_manager", "current_session_id"]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.warning(f"Deleted {result_chats.deleted_count} logs and {result_convs.deleted_count} conversation sessions.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete chat history: {e}")
        else:
            st.error("Database not available")

# Main chat interface
st.markdown("### 💭 Conversation")

# Always sync memory_manager session_id with session state
if st.session_state.current_session_id:
    st.session_state.memory_manager.set_session(st.session_state.current_session_id)

# Load and display conversation history
messages = st.session_state.memory_manager.get_conversation_history()

if not messages:
    st.info("👋 Start a conversation! Ask me anything - I can also answer questions about your uploaded documents.")

# Display messages
for msg in messages:
    with st.chat_message(msg.role):
        st.markdown(msg.content)
        
        # Show sources if available
        if show_sources and msg.sources:
            with st.expander(f"📄 Sources ({len(msg.sources)})"):
                for i, source in enumerate(msg.sources, 1):
                    st.caption(f"**Source {i}:** {source}")

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Save user message
    st.session_state.memory_manager.add_user_message(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Load current session history for short-term memory
                history = st.session_state.memory_manager.get_messages_for_llm()
                
                # Use hybrid orchestrator for all queries, passing current session ID and sidebar settings
                result = st.session_state.hybrid_orchestrator.query(
                    prompt, 
                    chat_history=history,
                    session_id=st.session_state.current_session_id,
                    top_k=top_k,
                    use_rag=use_rag
                )
                
                response = result["answer"]
                sources = result.get("sources", [])
                entities = result.get("entities", [])
                query_type = result.get("query_type", "unknown")
                
                # Display response
                st.markdown(response)
                
                # Show metadata
                with st.expander("🔍 Query Details"):
                    st.caption(f"**Query Type:** {query_type.upper()}")
                    if query_type == "kg":
                        st.caption(f"**Entities Found:** {len(entities)}")
                        for entity in entities[:3]:
                            st.caption(f"- {entity.get('name', '')} ({entity.get('type', '')})")
                    elif query_type == "web":
                        st.caption("**Web data was used for this answer**")
                    
                    # Display evaluations if available
                    eval_data = result.get("evaluation")
                    if eval_data:
                        st.markdown("---")
                        st.markdown("**🤖 RAG Quality Evaluation**")
                        
                        col_f, col_r, col_c = st.columns(3)
                        with col_f:
                            st.metric(
                                label="Faithfulness",
                                value=f"{eval_data.get('faithfulness', 5.0):.1f} / 5.0",
                                help=eval_data.get("faithfulness_explanation", "")
                            )
                        with col_r:
                            st.metric(
                                label="Context Relevance",
                                value=f"{eval_data.get('context_relevance', 5.0):.1f} / 5.0",
                                help=eval_data.get("context_relevance_explanation", "")
                            )
                        with col_c:
                            st.metric(
                                label="Answer Correctness",
                                value=f"{eval_data.get('answer_correctness', 5.0):.1f} / 5.0",
                                help=eval_data.get("answer_correctness_explanation", "")
                            )
                        
                        st.caption(f"**Faithfulness reasoning:** {eval_data.get('faithfulness_explanation', '')}")
                        st.caption(f"**Relevance reasoning:** {eval_data.get('context_relevance_explanation', '')}")
                        st.caption(f"**Correctness reasoning:** {eval_data.get('answer_correctness_explanation', '')}")
                
                # Show sources
                if show_sources and sources:
                    with st.expander(f"📄 Sources ({len(sources)})"):
                        for i, source in enumerate(sources, 1):
                            st.markdown(f"**Source {i}** (Similarity: {source.get('similarity', 'N/A'):.2f})")
                            st.caption(source.get('chunk', source.get('content', '')))
                            st.markdown("---")
                
                # Save assistant message
                st.session_state.memory_manager.add_assistant_message(
                    content=response,
                    sources=[s.get('doc_id', '') for s in sources if s.get('doc_id')],
                    metadata={
                        "query_type": query_type,
                        "evaluation": result.get("evaluation")
                    }
                )
                # DO NOT call st.rerun() here — Streamlit will re-render naturally
                # after st.chat_input processes the submission, preserving messages.
            
            except Exception as e:
                error_msg = get_user_message(e)
                st.error(error_msg)
                logger.error(f"Chat error: {e}")

# Footer stats
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Messages", len(messages))

with col2:
    st.metric("Current Session", st.session_state.current_session_id[:8] if st.session_state.current_session_id else "None")

with col3:
    from rag.vector_store import VectorStore
    try:
        vs = VectorStore(user_id)
        stats = vs.get_stats()
        st.metric("Indexed Docs", stats["total_documents"])
    except:
        st.metric("Indexed Docs", "0")
