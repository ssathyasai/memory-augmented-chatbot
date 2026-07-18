"""Documents page with full processing integration."""

import streamlit as st
import logging

from utils.session import require_auth, init_session_state, get_user_id
from document.processor import document_processor
from rag.pipeline import RAGPipeline
from errors.handlers import get_user_message

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("📄 Document Management")

user_id = get_user_id()

# Upload section
st.markdown("### 📤 Upload Documents")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "txt", "md"],
        help="Upload PDF, DOCX, TXT, or MD files (Max 10MB)"
    )

with col2:
    st.info("""
    **Supported formats:**
    - PDF (.pdf)
    - Word (.docx)
    - Text (.txt)
    - Markdown (.md)
    
    **Max size:** 10 MB
    """)

if uploaded_file:
    st.markdown("---")
    st.markdown("#### 📋 File Details")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filename", uploaded_file.name)
    with col2:
        st.metric("Size", f"{uploaded_file.size / 1024:.2f} KB")
    with col3:
        file_ext = uploaded_file.name.split('.')[-1].upper()
        st.metric("Type", file_ext)
    
    if st.button("🚀 Process & Index Document", type="primary", use_container_width=True):
        with st.spinner("Processing document..."):
            try:
                # Read file bytes
                file_bytes = uploaded_file.read()
                
                # Process document
                st.info("📄 Parsing document...")
                document = document_processor.process_document(
                    file_bytes=file_bytes,
                    filename=uploaded_file.name,
                    user_id=user_id
                )
                
                # Index document in vector store
                st.info("🔍 Indexing document for search...")
                rag_pipeline = RAGPipeline(user_id)
                rag_pipeline.index_document(document.id, document.chunks)
                
                st.success(f"✅ Document processed successfully! Created {document.chunk_count} chunks.")
                st.balloons()
                
                # Clear uploader
                st.rerun()
            
            except Exception as e:
                error_msg = get_user_message(e)
                st.error(f"❌ Error processing document: {error_msg}")
                logger.error(f"Document processing error: {e}")

# Documents list
st.markdown("---")
st.markdown("### 📚 Your Documents")

# Load user documents
try:
    documents = document_processor.get_user_documents(user_id)
    
    if documents:
        # Filter and search
        col1, col2 = st.columns([2, 1])
        with col1:
            search_query = st.text_input("🔍 Search documents", placeholder="Type to filter...")
        with col2:
            status_filter = st.selectbox("Filter by status", ["All", "ready", "processing", "error"])
        
        # Filter documents
        filtered_docs = documents
        if search_query:
            filtered_docs = [d for d in filtered_docs if search_query.lower() in d.filename.lower()]
        if status_filter != "All":
            filtered_docs = [d for d in filtered_docs if d.status == status_filter]
        
        st.markdown(f"**Showing {len(filtered_docs)} of {len(documents)} documents**")
        
        # Display documents
        for doc in filtered_docs:
            with st.expander(f"📄 {doc.filename}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Status", doc.status.upper())
                
                with col2:
                    st.metric("Chunks", doc.chunk_count)
                
                with col3:
                    size_mb = doc.metadata.size_bytes / (1024 * 1024)
                    st.metric("Size", f"{size_mb:.2f} MB")
                
                with col4:
                    st.metric("Type", doc.file_type.upper())
                
                # Document info
                st.caption(f"**Uploaded:** {doc.upload_date.strftime('%Y-%m-%d %H:%M')}")
                st.caption(f"**Document ID:** {doc.id}")
                
                # Show error if any
                if doc.error_message:
                    st.error(f"Error: {doc.error_message}")
                
                # Preview content
                if doc.content and doc.status == "ready":
                    with st.expander("📖 Preview Content"):
                        preview = doc.content[:500] + "..." if len(doc.content) > 500 else doc.content
                        st.text(preview)
                
                # Actions
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🗑️ Delete Document", key=f"del_{doc.id}", type="secondary", use_container_width=True):
                        if document_processor.delete_document(doc.id, user_id):
                            # Also delete from vector store
                            from rag.vector_store import VectorStore
                            vs = VectorStore(user_id)
                            vs.delete_document(doc.id)
                            st.success("Document deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete document")
                
                with col_b:
                    if doc.status == "error" and st.button("🔄 Retry Processing", key=f"retry_{doc.id}", use_container_width=True):
                        st.info("Retry functionality coming soon!")
    
    else:
        st.info("📭 No documents uploaded yet. Upload your first document to get started!")
        st.markdown("""
        **Getting Started:**
        1. Click the file uploader above
        2. Select a PDF, DOCX, TXT, or MD file
        3. Click "Process & Index Document"
        4. Start chatting with your document!
        """)

except Exception as e:
    st.error(f"Error loading documents: {get_user_message(e)}")
    logger.error(f"Error loading documents: {e}")

# Statistics
st.markdown("---")
st.markdown("### 📊 Statistics")

try:
    documents = document_processor.get_user_documents(user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", len(documents))
    
    with col2:
        ready_docs = [d for d in documents if d.status == "ready"]
        st.metric("Ready", len(ready_docs))
    
    with col3:
        total_chunks = sum(d.chunk_count for d in documents)
        st.metric("Total Chunks", total_chunks)
    
    with col4:
        total_size_mb = sum(d.metadata.size_bytes for d in documents) / (1024 * 1024)
        st.metric("Total Size", f"{total_size_mb:.2f} MB")
    
    # Vector store stats
    from rag.vector_store import VectorStore
    vs = VectorStore(user_id)
    vs_stats = vs.get_stats()
    
    st.markdown("#### 🔍 Vector Store")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Indexed Vectors", vs_stats["total_vectors"])
    
    with col2:
        st.metric("Indexed Documents", vs_stats["total_documents"])
    
    with col3:
        st.metric("Index Size", f"{vs_stats['index_size_mb']:.2f} MB")

except Exception as e:
    logger.error(f"Error loading statistics: {e}")
