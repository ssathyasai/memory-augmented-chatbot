from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from utils.knowledge_graph import query_knowledge_graph
from utils.memory import search_memories
from utils.rag import query_vector_store
from utils.tools_runtime import execute_tools


class RouterState(TypedDict, total=False):
    # Shared state passed between LangGraph nodes.
    user_id: str
    query: str
    route: str
    tool_names: List[str]
    memories: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    graph_results: List[Dict[str, Any]]
    tools_used: List[Dict[str, str]]


def classify_route(state: RouterState) -> RouterState:
    # The router uses explicit heuristics so behavior stays interview-friendly and explainable.
    query = state["query"].lower()
    route = "general"
    tool_names: List[str] = []
    if any(keyword in query for keyword in ["weather", "temperature", "forecast"]):
        route = "tool"
        tool_names = ["weather"]
    elif "news" in query or "headline" in query:
        route = "tool"
        tool_names = ["news"]
    elif any(keyword in query for keyword in ["wikipedia", "who is", "what is"]):
        route = "hybrid"
        tool_names = ["wikipedia"]
    elif any(keyword in query for keyword in ["relationship", "connected", "uses", "depends on", "graph"]):
        route = "knowledge_graph"
    elif any(keyword in query for keyword in ["remember", "preference", "favorite", "like", "told you"]):
        route = "memory"
    elif any(keyword in query for keyword in ["document", "pdf", "chapter", "summarize", "uploaded"]):
        route = "rag"

    return {"route": route, "tool_names": tool_names}


def memory_node(state: RouterState) -> RouterState:
    # Memory retrieval recalls user-specific long-term context.
    memories = search_memories(state["user_id"], state["query"], limit=5)
    return {"memories": memories}


def rag_node(state: RouterState) -> RouterState:
    # RAG fetches top chunks from FAISS for document-grounded answers.
    sources = query_vector_store(state["query"], state["user_id"], k=4)
    return {"sources": sources}


def knowledge_graph_node(state: RouterState) -> RouterState:
    # Knowledge graph queries capture structured relationships between concepts.
    graph_results = query_knowledge_graph(state["user_id"], state["query"])
    return {"graph_results": graph_results}


async def tools_node(state: RouterState) -> RouterState:
    # Tool execution fetches fresh external data.
    tools_used = await execute_tools(state.get("tool_names", []), state["query"])
    return {"tools_used": tools_used}


def route_after_classifier(state: RouterState) -> str:
    # This branch controls which specialist node runs first.
    return state.get("route", "general")


def build_router():
    # The graph is intentionally compact: classify, then consult specialized sources.
    workflow = StateGraph(RouterState)
    workflow.add_node("classify", classify_route)
    workflow.add_node("memory", memory_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("knowledge_graph", knowledge_graph_node)
    workflow.add_node("tool", tools_node)

    workflow.set_entry_point("classify")
    workflow.add_conditional_edges(
        "classify",
        route_after_classifier,
        {
            "memory": "memory",
            "rag": "rag",
            "knowledge_graph": "knowledge_graph",
            "tool": "tool",
            "hybrid": "memory",
            "general": END,
        },
    )
    workflow.add_edge("memory", END)
    workflow.add_edge("rag", END)
    workflow.add_edge("knowledge_graph", END)
    workflow.add_edge("tool", END)
    return workflow.compile()


router_graph = build_router()
