"""Evaluation page displaying system performance metrics and quality dashboard."""

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

if not db:
    st.error("Database connection unavailable. Please check your MongoDB settings.")
    st.stop()

# Helper function to get color for metric score
def get_score_color(score: float) -> str:
    if score >= 4.0:
        return "green"
    elif score >= 3.0:
        return "blue"
    elif score >= 2.0:
        return "orange"
    else:
        return "red"

# Helper function to render a progress bar with custom color
def render_metric_bar(score: float, label: str):
    color = "#28a745" if score >= 4.0 else ("#007bff" if score >= 3.0 else ("#ffc107" if score >= 2.0 else "#dc3545"))
    percentage = (score / 5.0) * 100
    st.markdown(f"""
        <div style="margin-bottom: 10px;">
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
    
    # Bulk evaluation tool for legacy logs
    unevaluated_chats = [c for c in chats if not c.get("evaluation")]
    if unevaluated_chats:
        st.markdown("---")
        st.subheader("⚙️ Run Bulk Evaluation")
        st.write(f"You have **{len(unevaluated_chats)}** unevaluated chat logs in database history.")
        if st.button("Evaluate Legacy Logs"):
            with st.spinner("Evaluating legacy logs using GROQ API..."):
                from rag.evaluator import RAGEvaluator
                success_count = 0
                for c in unevaluated_chats:
                    try:
                        # Reconstruct context if possible
                        context_str = ""
                        if c.get("sources"):
                            context_str = "\n".join([s.get("chunk", s.get("content", "")) for s in c.get("sources") if isinstance(s, dict)])
                        
                        eval_data = RAGEvaluator.evaluate_query(
                            query=c.get("question", ""),
                            context=context_str,
                            answer=c.get("answer", ""),
                            query_type=c.get("query_type", "direct")
                        )
                        
                        db.chats.update_one(
                            {"_id": c["_id"]},
                            {"$set": {"evaluation": eval_data}}
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Bulk eval error: {e}")
                
                if success_count > 0:
                    st.success(f"Successfully evaluated {success_count} logs!")
                    st.rerun()
                else:
                    st.error("No logs could be evaluated.")
    st.stop()

# ----------------- Analytics Calculations -----------------
total_count = len(evaluated_chats)
sum_faithfulness = 0.0
sum_relevance = 0.0
sum_correctness = 0.0

faithfulness_count = 0
relevance_count = 0
correctness_count = 0

# Group scores by query type
type_scores = {} # query_type -> {metrics}

for chat in evaluated_chats:
    eval_data = chat["evaluation"]
    q_type = chat.get("query_type", "direct")
    
    if q_type not in type_scores:
        type_scores[q_type] = {
            "faithfulness": [],
            "relevance": [],
            "correctness": []
        }
    
    # Calculate RAG specific metrics
    # If faithfulness or relevance is not evaluated (e.g. 5.0 default/neutral for non-RAG), 
    # we filter or average them appropriately
    f_score = eval_data.get("faithfulness", 5.0)
    r_score = eval_data.get("context_relevance", 5.0)
    c_score = eval_data.get("answer_correctness", 5.0)
    
    # Only average non-neutral faithfulness / relevance for contextual queries
    if q_type in ["rag", "kg", "web"]:
        sum_faithfulness += f_score
        faithfulness_count += 1
        sum_relevance += r_score
        relevance_count += 1
        
        type_scores[q_type]["faithfulness"].append(f_score)
        type_scores[q_type]["relevance"].append(r_score)
    
    sum_correctness += c_score
    correctness_count += 1
    type_scores[q_type]["correctness"].append(c_score)

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
    f_delta = f"{avg_faithfulness - 4.0:+.1f}" if avg_faithfulness != 5.0 else None
    st.metric(label="Avg Faithfulness", value=f"{avg_faithfulness:.2f} / 5.0", delta=f_delta)
with col3:
    r_delta = f"{avg_relevance - 4.0:+.1f}" if avg_relevance != 5.0 else None
    st.metric(label="Avg Relevance", value=f"{avg_relevance:.2f} / 5.0", delta=r_delta)
with col4:
    c_delta = f"{avg_correctness - 4.0:+.1f}" if avg_correctness != 5.0 else None
    st.metric(label="Avg Correctness", value=f"{avg_correctness:.2f} / 5.0", delta=c_delta)

st.markdown("---")

# Render metrics visual bars
col_bars1, col_bars2 = st.columns(2)
with col_bars1:
    st.markdown("#### System Scores Breakdown")
    render_metric_bar(avg_faithfulness, "Faithfulness (Groundedness)")
    render_metric_bar(avg_relevance, "Context Relevance")
    render_metric_bar(avg_correctness, "Answer Correctness")

with col_bars2:
    st.markdown("#### Performance Summary")
    if avg_correctness >= 4.0 and avg_faithfulness >= 4.0:
        st.success("🎉 **Excellent System Health!** The chatbot is highly accurate and does not hallucinate facts outside the provided context.")
    elif avg_correctness >= 3.5:
        st.info("ℹ️ **Good System Health.** Responses are generally correct, but context relevance or faithfulness has room for optimization (e.g., adjust chunk overlap).")
    else:
        st.warning("⚠️ **Improvement Required.** Check query routing settings or verify that document chunk size is set correctly on the Settings page.")

st.markdown("---")

# Tabs for detailed analytics
tab_trends, tab_breakdown, tab_log = st.tabs(["📉 Trends over Time", "🧩 Component Performance", "📋 Evaluated Query Log"])

# Tab 1: Trends
with tab_trends:
    st.subheader("Evaluation Score Trends")
    st.write("Chronological display of query evaluations (most recent on the right):")
    
    # Prepare trend line chart data
    trend_chats = list(reversed(evaluated_chats)) # Chronological order
    chart_data = {
        "Faithfulness": [c["evaluation"].get("faithfulness", 5.0) for c in trend_chats],
        "Context Relevance": [c["evaluation"].get("context_relevance", 5.0) for c in trend_chats],
        "Answer Correctness": [c["evaluation"].get("answer_correctness", 5.0) for c in trend_chats]
    }
    
    st.line_chart(chart_data)

# Tab 2: Breakdown
with tab_breakdown:
    st.subheader("Performance by Routing Component")
    st.write("Compare the quality metrics across different query routing targets:")
    
    # Calculate average scores per query type
    breakdown_data = []
    for q_type, scores in type_scores.items():
        avg_f = sum(scores["faithfulness"]) / len(scores["faithfulness"]) if scores["faithfulness"] else 5.0
        avg_r = sum(scores["relevance"]) / len(scores["relevance"]) if scores["relevance"] else 5.0
        avg_c = sum(scores["correctness"]) / len(scores["correctness"]) if scores["correctness"] else 5.0
        breakdown_data.append({
            "Query Type": q_type.upper(),
            "Count": len(scores["correctness"]),
            "Avg Faithfulness": round(avg_f, 2),
            "Avg Relevance": round(avg_r, 2),
            "Avg Correctness": round(avg_c, 2)
        })
    
    st.table(breakdown_data)

# Tab 3: Detailed Log
with tab_log:
    st.subheader("Evaluated Query logs")
    st.write("Browse query runs, retrieved contexts, and detailed explanations of system grading:")
    
    for i, chat in enumerate(evaluated_chats):
        timestamp_str = chat.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if isinstance(chat.get("timestamp"), datetime) else str(chat.get("timestamp"))
        query_type = chat.get("query_type", "direct").upper()
        
        eval_info = chat["evaluation"]
        title = f"Query {i+1}: \"{chat.get('question')[:60]}...\" — {query_type} ({timestamp_str})"
        
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
