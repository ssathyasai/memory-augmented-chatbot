"""Streamlit user profile and RAG configuration settings page.

Process Flow:
1. Displays authenticated user profile metadata (email, role, account creation date).
2. Renders password modification form with validation against length and complexity rules.
3. Renders RAG hyperparameter controls (`top_k`, `chunk_size`, `similarity_threshold`, `chunk_overlap`).
4. Saves updated settings to user document in MongoDB (`db.users.update_one`).
5. Displays account storage usage and document quota statistics.
"""

import streamlit as st
import logging

from utils.session import require_auth, init_session_state, get_current_user
from auth.manager import auth_manager
from errors.handlers import get_user_message

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("⚙️ Settings")

user = get_current_user()

# User Profile Section
st.markdown("### 👤 User Profile")

col1, col2 = st.columns(2)

with col1:
    st.text_input("Email", value=user.email, disabled=True, help="Email cannot be changed")
    st.text_input("Role", value=user.role.capitalize(), disabled=True)

with col2:
    st.text_input("User ID", value=user.id, disabled=True)
    member_since = user.created_at.strftime("%Y-%m-%d") if user.created_at else "Unknown"
    st.text_input("Member Since", value=member_since, disabled=True)

# Change Password Section
st.markdown("---")
st.markdown("### 🔒 Change Password")

with st.form("change_password_form"):
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password", help="Min 8 chars, 1 uppercase, 1 lowercase, 1 digit")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    submit = st.form_submit_button("Change Password", type="primary")
    
    if submit:
        if not all([current_password, new_password, confirm_password]):
            st.error("Please fill in all fields")
        elif new_password != confirm_password:
            st.error("New passwords do not match")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long")
        else:
            try:
                success = auth_manager.change_password(
                    user_id=user.id,
                    current_password=current_password,
                    new_password=new_password
                )
                
                if success:
                    st.success("✅ Password changed successfully!")
                else:
                    st.error("Failed to change password")
            
            except Exception as e:
                error_msg = get_user_message(e)
                st.error(error_msg)

# RAG Settings Section
st.markdown("---")
st.markdown("### 🔍 RAG Configuration")

st.info("Adjust these settings to control how documents are retrieved and processed.")

col1, col2 = st.columns(2)

with col1:
    top_k = st.slider(
        "Top K Results",
        min_value=1,
        max_value=20,
        value=user.settings.get("top_k", 8),
        help="Number of document chunks to retrieve"
    )
    
    chunk_size = st.slider(
        "Chunk Size",
        min_value=500,
        max_value=2000,
        value=user.settings.get("chunk_size", 1000),
        step=100,
        help="Size of document chunks in characters"
    )

with col2:
    similarity_threshold = st.slider(
        "Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=user.settings.get("similarity_threshold", 0.25),
        step=0.05,
        help="Minimum similarity score for retrieval"
    )
    
    chunk_overlap = st.slider(
        "Chunk Overlap",
        min_value=0,
        max_value=500,
        value=user.settings.get("chunk_overlap", 200),
        step=50,
        help="Overlap between consecutive chunks"
    )

# User Preferences Section
st.markdown("---")
st.markdown("### 🎨 Preferences")

col1, col2 = st.columns(2)

with col1:
    theme = st.selectbox(
        "Theme",
        ["Light", "Dark", "Auto"],
        index=["light", "dark", "auto"].index(user.settings.get("theme", "light"))
    )

with col2:
    notifications = st.checkbox(
        "Enable Notifications",
        value=user.settings.get("notifications", True)
    )
    
    show_sources = st.checkbox(
        "Show Sources by Default",
        value=user.settings.get("show_sources", True),
        help="Automatically display source citations in chat"
    )

# Save Settings Button
if st.button("💾 Save All Settings", type="primary", use_container_width=True):
    try:
        # Update settings
        new_settings = {
            "theme": theme.lower(),
            "notifications": notifications,
            "show_sources": show_sources,
            "top_k": top_k,
            "chunk_size": chunk_size,
            "similarity_threshold": similarity_threshold,
            "chunk_overlap": chunk_overlap
        }
        # Retain language settings if already present in DB
        if "language" in user.settings:
            new_settings["language"] = user.settings["language"]
        
        success = auth_manager.update_user_settings(user.id, new_settings)
        
        if success:
            st.success("✅ Settings saved successfully!")
            # Update session state
            user.settings = new_settings
            st.rerun()
        else:
            st.error("Failed to save settings")
    
    except Exception as e:
        st.error(f"Error saving settings: {get_user_message(e)}")
        logger.error(f"Error saving settings: {e}")

# Usage Quota Section
st.markdown("---")
st.markdown("### 📊 Usage & Quota")

col1, col2 = st.columns(2)

# Fetch documents once, safely, before the columns
from document.processor import document_processor
try:
    user_docs = document_processor.get_user_documents(user.id)
except Exception:
    user_docs = []

with col1:
    doc_count = len(user_docs)
    max_docs = user.quota.get('documents', 100)
    st.metric("Documents", f"{doc_count} / {max_docs}")
    st.progress(min(doc_count / max_docs, 1.0))

with col2:
    try:
        total_size_mb = sum(d.metadata.size_bytes for d in user_docs) / (1024 * 1024)
    except Exception:
        total_size_mb = 0

    max_storage = user.quota.get('storage_mb', 500)
    st.metric("Storage", f"{total_size_mb:.1f} MB / {max_storage} MB")
    st.progress(min(total_size_mb / max_storage, 1.0))

# Vector Store Stats
st.markdown("---")
st.markdown("### 🗄️ Vector Store")

try:
    from rag.vector_store import VectorStore
    vs = VectorStore(user.id)
    vs_stats = vs.get_stats()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Indexed Vectors", vs_stats["total_vectors"])
    
    with col2:
        st.metric("Indexed Documents", vs_stats["total_documents"])
    
    with col3:
        st.metric("Index Size", f"{vs_stats['index_size_mb']:.2f} MB")

except Exception as e:
    st.warning("Vector store stats unavailable")
    logger.error(f"Error getting vector store stats: {e}")

# Danger Zone
st.markdown("---")
st.markdown("### ⚠️ Danger Zone")

with st.expander("🗑️ Delete All Data"):
    st.warning("**Warning:** This will permanently delete all your documents, conversations, and knowledge graph data. This action cannot be undone!")
    
    confirm_delete = st.text_input("Type 'DELETE' to confirm", key="confirm_delete")
    
    if st.button("Delete All My Data", type="secondary", disabled=confirm_delete != "DELETE"):
        with st.spinner("Deleting all user data..."):
            try:
                from config.database import get_database
                from document.processor import document_processor
                from memory.storage import conversation_storage
                from memory.long_term import LongTermMemoryManager
                from rag.vector_store import VectorStore
                from knowledge_graph.neo4j_manager import Neo4jKnowledgeGraph

                db = get_database()

                # 1. Delete all user documents from MongoDB
                document_processor.delete_all_user_documents(user.id)

                # 2. Delete all user conversations & chat logs
                conversation_storage.delete_all_user_conversations(user.id)
                if db is not None:
                    db.chats.delete_many({"user_id": user.id})

                # 3. Delete long-term profile memories
                LongTermMemoryManager.clear_user_memories(user.id)

                # 4. Clear user vector store
                vs = VectorStore(user.id)
                vs.clear()

                # 5. Clear Neo4j Knowledge Graph
                kg = Neo4jKnowledgeGraph(user.id)
                kg.clear_graph()

                # 6. Reset Streamlit active session state
                st.session_state.current_session_id = None
                st.session_state.messages = []
                st.session_state.uploaded_docs = []
                for key in ["memory_manager", "rag_pipeline", "hybrid_orchestrator"]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("✅ All your data (documents, chat history, vector index, knowledge graph, and profile memories) has been permanently deleted!")
                st.rerun()

            except Exception as e:
                logger.error(f"Error deleting user data: {e}")
                st.error(f"Failed to delete data: {get_user_message(e)}")


# Export Data
with st.expander("📥 Export Data"):
    st.info("Export your data in JSON format")
    
    if st.button("Export My Data"):
        try:
            import json
            from datetime import datetime
            
            # Gather data
            export_data = {
                "user": {
                    "email": user.email,
                    "id": user.id,
                    "created_at": str(user.created_at),
                    "settings": user.settings
                },
                "documents": [
                    {
                        "filename": doc.filename,
                        "upload_date": str(doc.upload_date),
                        "status": doc.status,
                        "chunk_count": doc.chunk_count
                    }
                    for doc in document_processor.get_user_documents(user.id)
                ],
                "export_date": str(datetime.utcnow())
            }
            
            # Create download
            export_json = json.dumps(export_data, indent=2)
            
            st.download_button(
                label="Download JSON",
                data=export_json,
                file_name=f"chatbot_export_{user.id}.json",
                mime="application/json"
            )
        
        except Exception as e:
            st.error(f"Export failed: {get_user_message(e)}")

