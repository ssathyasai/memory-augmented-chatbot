"""Streamlit RAG evaluation dashboard and quality analytics UI page.

Process Flow:
1. Fetches evaluated chat logs from MongoDB `chats` collection for the authenticated user.
2. Computes aggregate performance metrics: Faithfulness, Context Relevance, and Answer Correctness.
3. Renders score progress bars and detailed log of evaluated user queries.
"""

import streamlit as st
import logging
from datetime import datetime
from config.database import get_database
from utils.session import require_auth, init_session_state, get_user_id

logger = logging.getLogger(__name__)

# Initialize session
init_session_state()

# Require authentication
require_auth()

# Page config
st.title("📊 RAG Evaluation Dashboard")

user_id = get_user_id()
db = get_database()

if db is None:
    st.error("Database connection unavailable. Please check your MongoDB settings.")
    st.stop()


# Helper function to render a progress bar with custom color
def render_metric_bar(score: float, label: str):
    color = "#28a745" if score >= 4.0 else ("#007bff" if score >= 3.0 else ("#ffc107" if score >= 2.0 else "#dc3545"))
    percentage = (score / 5.0) * 100
    st.markdown(f"""
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span style="font-weight: 500; font-size: 0.9rem;">{label}</span>
                <span style="font-weight: bold; font-size: 0.9rem; color: {color};">{score:.2f} / 5.00</span>
            </div>
            <div style="background-color: #e9ecef; border-radius: 4px; height: 8px; width: 100%;">
                <div style="background-color: {color}; border-radius: 4px; height: 8px; width: {percentage}%;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Fetch evaluated chats for current user
try:
    chats = list(db.chats.find({"user_id": user_id}).sort("timestamp", -1))
except Exception as e:
    st.error(f"Failed to fetch evaluations: {e}")
    chats = []

# Filter chats that have evaluation metrics
evaluated_chats = [c for c in chats if c.get("evaluation") and c["evaluation"].get("answer_correctness") is not None]

# Check if there are no evaluated queries
if not evaluated_chats:
    st.info("👋 No evaluation data available yet. Please go to the **Chat** page and start asking questions to populate quality metrics!")
    st.stop()

# ----------------- Analytics Calculations -----------------
total_count = len(evaluated_chats)
sum_faithfulness = 0.0
sum_relevance = 0.0
sum_correctness = 0.0

faithfulness_count = 0
relevance_count = 0
correctness_count = 0

for chat in evaluated_chats:
    eval_data = chat["evaluation"]
    q_type = chat.get("query_type", "direct")
    
    f_score = eval_data.get("faithfulness", 5.0)
    r_score = eval_data.get("context_relevance", 5.0)
    c_score = eval_data.get("answer_correctness", 5.0)
    
    # Only average non-neutral faithfulness / relevance for contextual queries
    if q_type in ["rag", "kg", "web"]:
        sum_faithfulness += f_score
        faithfulness_count += 1
        sum_relevance += r_score
        relevance_count += 1
    
    sum_correctness += c_score
    correctness_count += 1

# Overall Averages
avg_faithfulness = (sum_faithfulness / faithfulness_count) if faithfulness_count > 0 else 5.0
avg_relevance = (sum_relevance / relevance_count) if relevance_count > 0 else 5.0
avg_correctness = (sum_correctness / correctness_count) if correctness_count > 0 else 5.0

# ----------------- Dashboard Layout -----------------
st.markdown("### 📈 Quality Metrics Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total Evaluated Queries", value=total_count)
with col2:
    st.metric(label="Avg Faithfulness", value=f"{avg_faithfulness:.2f} / 5.0")
with col3:
    st.metric(label="Avg Relevance", value=f"{avg_relevance:.2f} / 5.0")
with col4:
    st.metric(label="Avg Correctness", value=f"{avg_correctness:.2f} / 5.0")

st.markdown("---")

# Render metrics visual bars
st.markdown("#### System Performance Scores")
render_metric_bar(avg_faithfulness, "Faithfulness (Groundedness)")
render_metric_bar(avg_relevance, "Context Relevance")
render_metric_bar(avg_correctness, "Answer Correctness")

st.markdown("---")

# Render list of recent query evaluations
st.markdown("### 📋 Recent Evaluated Queries")
for i, chat in enumerate(evaluated_chats):
    timestamp_str = chat.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if isinstance(chat.get("timestamp"), datetime) else str(chat.get("timestamp"))
    query_type = chat.get("query_type", "direct").upper()
    
    eval_info = chat["evaluation"]
    title = f"\"{chat.get('question')[:80]}...\" — {query_type} ({timestamp_str})"
    
    with st.expander(title):
        st.markdown(f"**Question:** {chat.get('question')}")
        st.markdown(f"**Answer:** {chat.get('answer')}")
        
        st.markdown("---")
        st.markdown("**Metric Evaluation Summary:**")
        
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            st.write(f"**Faithfulness:** {eval_info.get('faithfulness', 5.0):.1f} / 5.0")
            st.caption(eval_info.get('faithfulness_explanation', ''))
        with col_e2:
            st.write(f"**Context Relevance:** {eval_info.get('context_relevance', 5.0):.1f} / 5.0")
            st.caption(eval_info.get('context_relevance_explanation', ''))
        with col_e3:
            st.write(f"**Answer Correctness:** {eval_info.get('answer_correctness', 5.0):.1f} / 5.0")
            st.caption(eval_info.get('answer_correctness_explanation', ''))
        
        if chat.get("sources"):
            st.markdown("---")
            st.markdown("**Retrieved Sources:**")
            for s_idx, source in enumerate(chat.get("sources"), 1):
                doc_name = source.get("doc_id", "Unknown Document")
                similarity = source.get("similarity", 0.0)
                chunk_text = source.get("chunk", source.get("content", ""))
                st.caption(f"**{s_idx}. {doc_name}** (Similarity: {similarity:.2f})")
                st.text(chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text)
