"""Streamlit Knowledge Graph visualization and management UI page.

Process Flow:
1. Connects to `KnowledgeGraphManager` and displays top metrics (Total Entities, Relationships, Entity Types).
2. Provides a control button to re-analyze historical MongoDB chat logs and populate Neo4j graph nodes.
3. Provides a reset button to wipe the user's graph network.
4. Displays tabbed views for entity browsing, relationship inspection, interactive node selection, and graph analytics.
"""

import streamlit as st
import logging

from utils.session import require_auth, init_session_state, get_user_id
from knowledge_graph.manager import KnowledgeGraphManager

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("🧠 Knowledge Graph")

user_id = get_user_id()

# Initialize knowledge graph manager
if "kg_manager" not in st.session_state:
    st.session_state.kg_manager = KnowledgeGraphManager(user_id)

kg_manager = st.session_state.kg_manager

# Get statistics
stats = kg_manager.get_stats()

# Header stats
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📌 Total Entities", stats.get("entities", 0))

with col2:
    st.metric("🔗 Total Relationships", stats.get("relationships", 0))

with col3:
    entity_types = kg_manager.get_entity_types()
    st.metric("🏷️ Entity Types", len(entity_types))

st.markdown("---")

# Graph controls
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔄 Analyze Past Chats & Load Graph", type="primary", use_container_width=True):
        with st.spinner("Analyzing all your past chats to build your Knowledge Graph..."):
            from config.database import get_database
            db = get_database()
            if db is not None:
                # 1. Clear current graph first to avoid duplicates
                kg_manager.kg.clear_graph()
                
                # 2. Find all chats for this user in MongoDB (in chronological order)
                user_chats = list(db.chats.find({"user_id": user_id}).sort("timestamp", 1))
                
                # 3. Re-process each chat to extract relationships
                processed_count = 0
                for chat in user_chats:
                    question = chat.get("question", "")
                    answer = chat.get("answer", "")
                    session_id = chat.get("session_id")
                    if question and answer:
                        kg_manager.process_conversation(question, answer, session_id=session_id)
                        processed_count += 1
                
                st.success(f"✅ Load complete! Successfully analyzed {processed_count} past conversation turns and loaded your Knowledge Graph.")
                st.rerun()
            else:
                st.error("Database connection unavailable.")

with col_btn2:
    if st.button("🗑️ Reset Knowledge Graph", type="secondary", use_container_width=True):
        with st.spinner("Clearing your Knowledge Graph..."):
            kg_manager.kg.clear_graph()
            st.success("✅ Knowledge Graph cleared successfully!")
            st.rerun()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📌 Entities", "🔗 Relationships", "📊 Analytics"])

with tab1:
    st.markdown("### All Entities")
    
    # If an entity is selected, show its connections at the top of Tab 1
    selected_entity = st.session_state.get("selected_entity")
    if selected_entity:
        with st.container(border=True):
            st.markdown(f"### 🔗 Connections for **{selected_entity}**")
            relationships = kg_manager.get_relationships(entity_name=selected_entity)
            if relationships:
                for rel in relationships:
                    col_r1, col_r2, col_r3 = st.columns([2, 1, 2])
                    with col_r1:
                        st.markdown(f"**{rel.get('source', 'Unknown')}**")
                    with col_r2:
                        st.markdown(f"→ *{rel.get('type', 'related')}* →")
                    with col_r3:
                        st.markdown(f"**{rel.get('target', 'Unknown')}**")
            else:
                st.info("No connections found for this entity.")
            if st.button("❌ Close Connections", key="close_connections_tab1"):
                st.session_state.selected_entity = None
                st.rerun()
        st.markdown("---")
    
    # Filter controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_entity = st.text_input("🔍 Search entities", placeholder="Type to filter...")
    
    with col2:
        entity_types_list = list(entity_types.keys()) if entity_types else []
        filter_type = st.selectbox("Filter by type", ["All"] + entity_types_list)
    
    # Get entities
    type_filter = None if filter_type == "All" else filter_type
    entities = kg_manager.get_entities(entity_type=type_filter, limit=100)
    
    # Filter by search
    if search_entity:
        entities = [e for e in entities if search_entity.lower() in e.get("name", "").lower()]
    
    if entities:
        st.markdown(f"**Showing {len(entities)} entities**")
        
        # Display entities in a grid
        for i in range(0, len(entities), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(entities):
                    entity = entities[i + j]
                    with col:
                        with st.container():
                            st.markdown(f"**{entity.get('name', 'Unknown')}**")
                            st.caption(f"Type: {entity.get('type', 'unknown')}")
                            
                            # Show relationships button
                            if st.button("View Connections", key=f"entity_{i}_{j}"):
                                st.session_state.selected_entity = entity.get('name')
                                st.rerun()
    else:
        st.info("No entities found. Extract entities from your conversations or documents.")

with tab2:
    st.markdown("### Relationships")
    
    # Get selected entity if any
    selected_entity = st.session_state.get("selected_entity")
    
    if selected_entity:
        st.info(f"Showing relationships for: **{selected_entity}**")
        if st.button("Clear Selection"):
            st.session_state.selected_entity = None
            st.rerun()
    
    # Get relationships
    relationships = kg_manager.get_relationships(entity_name=selected_entity)
    
    if relationships:
        st.markdown(f"**Found {len(relationships)} relationships**")
        
        for rel in relationships:
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                st.markdown(f"**{rel.get('source', 'Unknown')}**")
            
            with col2:
                rel_type = rel.get('type', 'related')
                st.markdown(f"→ *{rel_type}* →")
            
            with col3:
                st.markdown(f"**{rel.get('target', 'Unknown')}**")
            
            st.markdown("---")
    else:
        if selected_entity:
            st.info(f"No relationships found for {selected_entity}")
        else:
            st.info("No relationships in the knowledge graph yet.")

with tab3:
    st.markdown("### Analytics")
    
    if entity_types:
        st.markdown("#### Entity Type Distribution")
        
        # Sort by count
        sorted_types = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)
        
        # Display as bar chart
        import pandas as pd
        
        df = pd.DataFrame(sorted_types, columns=["Type", "Count"])
        st.bar_chart(df.set_index("Type"))
        
        # Display as table
        st.markdown("#### Detailed Breakdown")
        for entity_type, count in sorted_types:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{entity_type.capitalize()}**")
            with col2:
                st.metric("Count", count)
    else:
        st.info("No entities to analyze yet.")
    
    # Overall stats
    st.markdown("---")
    st.markdown("#### Overall Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Entities", stats.get("entities", 0))
    
    with col2:
        st.metric("Total Relationships", stats.get("relationships", 0))
    
    with col3:
        if stats.get("entities", 0) > 0:
            connectivity = stats.get("relationships", 0) / stats.get("entities", 1)
            st.metric("Avg Connections", f"{connectivity:.2f}")
        else:
            st.metric("Avg Connections", "0.00")

# Help section
st.markdown("---")
with st.expander("ℹ️ About Knowledge Graph"):
    st.markdown("""
    ### What is a Knowledge Graph?
    
    A knowledge graph automatically extracts and connects important information from your documents and conversations.
    
    **Features:**
    - **Entities**: People, organizations, locations, concepts mentioned in your data
    - **Relationships**: How entities are connected to each other
    - **Analytics**: Insights about your knowledge base
    
    **How it works:**
    1. As you chat and upload documents, entities are automatically extracted
    2. Entities are stored in a graph database (Neo4j)
    3. You can explore connections and discover insights
    
    **Use cases:**
    - Discover hidden connections in your documents
    - Track mentions of people, companies, or concepts
    - Visualize your knowledge network
    """)

