"""Chat page with full RAG integration."""

import streamlit as st
import logging

from utils.session import require_auth, init_session_state, get_user_id
from rag.pipeline import RAGPipeline
from memory.manager import MemoryManager
from errors.handlers import get_user_message

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("💬 Chat with Your Documents")

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
    sessions = st.session_state.memory_manager.get_user_sessions(limit=5)
    
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

# Main chat interface
st.markdown("### 💭 Conversation")

# Load and display conversation history
messages = st.session_state.memory_manager.get_conversation_history()

if not messages:
    st.info("👋 Start a conversation! Ask me anything about your uploaded documents.")

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
if prompt := st.chat_input("Ask me anything about your documents..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Save user message
    st.session_state.memory_manager.add_user_message(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if use_rag:
                    # Use RAG pipeline
                    result = st.session_state.rag_pipeline.query(
                        question=prompt,
                        top_k=top_k,
                        include_sources=show_sources
                    )
                    
                    response = result["answer"]
                    sources = [s["doc_id"] for s in result.get("sources", [])]
                    
                    # Display response
                    st.markdown(response)
                    
                    # Show sources
                    if show_sources and result.get("sources"):
                        with st.expander(f"📄 Sources ({len(result['sources'])})"):
                            for i, source in enumerate(result['sources'], 1):
                                st.markdown(f"**Source {i}** (Similarity: {source['similarity']:.2f})")
                                st.caption(source['chunk'])
                                st.markdown("---")
                    
                    # Save assistant message
                    st.session_state.memory_manager.add_assistant_message(
                        content=response,
                        sources=sources
                    )
                else:
                    # Direct LLM without RAG
                    llm_messages = st.session_state.memory_manager.get_messages_for_llm()
                    llm_messages.append({"role": "user", "content": prompt})
                    
                    from rag.llm_client import groq_client
                    response = groq_client.chat_completion(llm_messages)
                    
                    # Display and save
                    st.markdown(response)
                    st.session_state.memory_manager.add_assistant_message(response)
                
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
