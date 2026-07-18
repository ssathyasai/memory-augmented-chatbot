"""Chat page with full RAG integration and recent chats management."""

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
            col1, col2 = st.columns([3, 1])
            with col1:
                session_label = f"{session['message_count']} msgs"
                if st.button(session_label, key=f"sess_{session['session_id']}", use_container_width=True):
                    st.session_state.current_session_id = session['session_id']
                    st.session_state.memory_manager.set_session(session['session_id'])
                    st.rerun()
            with col2:
                st.caption(session['updated_at'].strftime("%m/%d"))
    else:
        st.info("No chat history yet")
    
    st.markdown("---")
    
    # Delete recent chats (MongoDB)
    st.markdown("### 🗑️ Delete Recent Chats")
    if st.button("Delete All Chat History", use_container_width=True, type="primary"):
        if db:
            try:
                result = db.chats.delete_many({"user_id": user_id})
                st.warning(f"Deleted {result.deleted_count} chat messages")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete chat history: {e}")
        else:
            st.error("Database not available")

# Main chat interface
st.markdown("### 💭 Conversation")

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
                # Use hybrid orchestrator for all queries
                result = st.session_state.hybrid_orchestrator.query(prompt)
                
                response = result["answer"]
                sources = result.get("sources", [])
                entities = result.get("entities", [])
                query_type = result.get("query_type", "unknown")
                
                # Display response
                st.markdown(response)
                
                # Show metadata
                with st.expander("🔍 Query Details"):
                    st.caption(f"**Query Type:** {query_type}")
                    if query_type == "kg":
                        st.caption(f"**Entities Found:** {len(entities)}")
                        for entity in entities[:3]:
                            st.caption(f"- {entity.get('name', '')} ({entity.get('type', '')})")
                    elif query_type == "web":
                        st.caption("**Web data was used for this answer**")
                
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
                    sources=[s.get('doc_id', '') for s in sources if s.get('doc_id')]
                )
                
                st.rerun()
            
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
