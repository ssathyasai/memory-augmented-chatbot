"""Main Streamlit application entry point.

Process Flow:
1. Configures logging handlers to stream logs and save them to 'chatbot.log'.
2. Sets Streamlit page configuration (title, layout, sidebar state).
3. Injects custom CSS styles for clean UI components.
4. Checks and initializes backend connections (MongoDB for storage, Neo4j for Knowledge Graph).
5. Manages session authentication state; displays the authentication page if unauthenticated.
6. Renders the main dashboard landing view when authenticated.
"""

import streamlit as st
import logging
from pathlib import Path

from config.database import mongodb_manager
from config.neo4j_client import neo4j_manager
from utils.session import init_session_state, is_authenticated
from components.auth import show_auth_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Memory-Augmented Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)


def initialize_connections():
    """Initialize database connections."""
    # Initialize MongoDB
    if not mongodb_manager.is_connected():
        logger.info("Connecting to MongoDB...")
        if mongodb_manager.connect():
            mongodb_manager.create_indexes()
            logger.info("MongoDB connected and indexed")
        else:
            logger.warning("MongoDB connection failed - some features may not work")
    
    # Initialize Neo4j
    if not neo4j_manager.is_connected():
        logger.info("Connecting to Neo4j...")
        try:
            if neo4j_manager.connect():
                neo4j_manager.create_constraints_and_indexes()
                logger.info("Neo4j connected and indexed")
            else:
                logger.warning("Neo4j connection failed - knowledge graph features disabled")
        except Exception as e:
            logger.error(f"Error during Neo4j connection: {e}")
            logger.warning("Neo4j connection failed - knowledge graph features disabled")


def main():
    """Main application function."""
    # Initialize session state
    init_session_state()
    
    # Initialize database connections
    initialize_connections()
    
    # Display connection status in sidebar
    st.sidebar.markdown("### Connection Status")
    
    mongodb_connected = mongodb_manager.is_connected()
    if mongodb_connected:
        st.sidebar.success("✅ MongoDB Connected")
    else:
        st.sidebar.error("❌ MongoDB Disconnected")
    
    neo4j_connected = neo4j_manager.is_connected()
    if neo4j_connected:
        st.sidebar.success("✅ Neo4j Connected")
    else:
        st.sidebar.warning("⚠️ Neo4j Disconnected (KG features disabled)")
    
    st.sidebar.markdown("---")
    
    # Check authentication
    if not is_authenticated():
        # Show login/register page
        show_auth_page()
    else:
        # Show main application
        st.sidebar.success(f"Logged in as: {st.session_state.user.email}")
        
        if st.sidebar.button("Logout"):
            from utils.session import clear_session
            clear_session()
            st.rerun()
        
        # Main content
        st.markdown('<div class="main-header">🤖 Memory-Augmented Chatbot</div>', unsafe_allow_html=True)
        
        st.info("👈 Use the sidebar to navigate between pages")
        
        st.markdown("## Welcome to Your Intelligent Assistant")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("### 💬 Chat")
            st.write("Have conversations with AI that remembers context")
            if st.button("Go to Chat", key="nav_chat"):
                st.switch_page("pages/2_💬_Chat.py")
        
        with col2:
            st.markdown("### 📄 Documents")
            st.write("Upload and manage your documents")
            if st.button("Go to Documents", key="nav_docs"):
                st.switch_page("pages/3_📄_Documents.py")
        
        with col3:
            st.markdown("### 🧠 Knowledge Graph")
            st.write("Explore extracted knowledge")
            if st.button("Go to Knowledge Graph", key="nav_kg"):
                st.switch_page("pages/4_🧠_Knowledge_Graph.py")
                
        with col4:
            st.markdown("### 📊 Evaluation")
            st.write("View quality and accuracy metrics")
            if st.button("Go to Evaluation", key="nav_eval"):
                st.switch_page("pages/6_📊_Evaluation.py")
        
        # Stats
        st.markdown("---")
        st.markdown("### Your Stats")
        
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("Documents", len(st.session_state.get("uploaded_docs", [])))
        
        with stats_col2:
            st.metric("Conversations", "0")  # TODO: Implement
        
        with stats_col3:
            st.metric("Messages", len(st.session_state.get("messages", [])))
        
        with stats_col4:
            st.metric("Knowledge Entities", "0")  # TODO: Implement
        
        # Quick start guide
        with st.expander("📖 Quick Start Guide"):
            st.markdown("""
            ### Getting Started
            
            1. **Upload Documents** 📄
               - Go to the Documents page
               - Upload PDF, DOCX, TXT, or MD files
               - Wait for processing to complete
            
            2. **Start Chatting** 💬
               - Go to the Chat page
               - Ask questions about your uploaded documents
               - View source citations for answers
            
            3. **Explore Knowledge** 🧠
               - Go to the Knowledge Graph page
               - See entities and relationships extracted from your conversations
               - Discover connections in your data
            
            4. **Customize Settings** ⚙️
               - Go to Settings page
               - Configure RAG parameters
               - Update your preferences
            
            5. **Track Performance & Accuracy** 📊
               - Go to the Evaluation page
               - View real-time accuracy and performance graphs
               - Inspect automated metrics (Faithfulness, Relevance, Correctness) for each query
            """)


if __name__ == "__main__":
    main()
