
import os
import re
import sys
from typing import List

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Add the backend directory to the import path for local module imports.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph.router import router_graph
from models.schemas import (
    AnalyticsSummary,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    GraphEntity,
    GraphQueryResult,
    GraphRelationshipCreate,
    MemoryCreate,
    MemoryRecord,
    MemoryUpdate,
    PDFProcessResponse,
    RoutingDecision,
    ToolExecution,
    UserSettings,
)
from utils.analytics import (
    get_user_analytics_events,
    get_user_documents,
    get_user_settings,
    record_chat_analytics,
    register_document,
    save_user_settings,
)
from utils.config import settings
from utils.knowledge_graph import (
    add_relationship,
    clear_user_graph,
    connect_to_neo4j,
    get_all_entities,
    get_graph_counts,
    ingest_text_into_graph,
    query_knowledge_graph,
)
from utils.llm import groq_llm
from utils.memory import add_memory, connect_to_mongodb, delete_memory, get_memories, search_memories, update_memory
from utils.rag import count_user_chunks, load_or_initialize_vector_store, process_pdf, query_vector_store
from utils.memory import (
    search_memories as search_memory_records,
)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


def _serialize_memory(memory: dict) -> MemoryRecord:
    # This keeps database storage names separate from API model names.
    return MemoryRecord(
        memory_id=memory["_id"],
        user_id=memory["user_id"],
        type=memory["type"],
        content=memory["content"],
        metadata=memory.get("metadata", {}),
        created_at=memory["created_at"],
        updated_at=memory["updated_at"],
    )


def _extract_preference_memory(user_id: str, text: str) -> None:
    # Simple pattern-based extraction turns user statements into durable preferences.
    patterns = [
        r"my favorite ([a-zA-Z ]+) is ([a-zA-Z0-9\-\+ ]+)",
        r"i like ([a-zA-Z0-9\-\+ ]+)",
        r"i prefer ([a-zA-Z0-9\-\+ ]+)",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            add_memory(
                user_id=user_id,
                memory_type="preference",
                content=text,
                metadata={"captured_from_chat": True},
            )
            break


def _build_system_prompt(
    user_id: str,
    sources: List[Citation],
    memories: List[MemoryRecord],
    graph_results: List[GraphQueryResult],
    tools_used: List[ToolExecution],
) -> str:
    # The final prompt merges outputs from all active subsystems into one coherent context.
    sections: List[str] = [
        "You are a professional AI assistant for a memory-augmented chatbot.",
        "Use the provided context when it is relevant, but do not invent facts.",
        "When document evidence is used, mention the source filename.",
    ]
    if memories:
        sections.append("User Memory:")
        sections.extend(f"- {item.content}" for item in memories)
    if sources:
        sections.append("Retrieved Documents:")
        sections.extend(
            f"- {item.source} page {item.page or 'n/a'}: {item.content[:600]}"
            for item in sources
        )
    if graph_results:
        sections.append("Knowledge Graph Results:")
        for item in graph_results:
            relation_text = ", ".join(
                f"{rel['relation']} -> {rel['entity']}" for rel in item.relations
            ) or "no outgoing relationships"
            sections.append(f"- {item.entity}: {relation_text}")
    if tools_used:
        sections.append("External Tool Results:")
        sections.extend(f"- {tool.tool_name}: {tool.output_summary}" for tool in tools_used)
    return "\n".join(sections)


@app.on_event("startup")
async def startup_event():
    # Startup loads persisted stores so the dashboard has state immediately.
    try:
        load_or_initialize_vector_store()
    except Exception as e:
        print(f"Warning: Could not initialize vector store: {e}")
    
    try:
        connect_to_mongodb()
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
    
    try:
        connect_to_neo4j()
    except Exception as e:
        print(f"Warning: Could not connect to Neo4j: {e}")


@app.get("/")
async def read_root():
    # The frontend is served by FastAPI for a single-command local setup.
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/health")
async def health_check():
    # The health endpoint exposes external dependency availability for debugging.
    return {
        "status": "healthy",
        "message": "API is running",
        "mongodb_connected": connect_to_mongodb(),
        "neo4j_connected": connect_to_neo4j(),
        "groq_configured": bool(settings.GROQ_API_KEY),
    }


@app.get("/api/documents")
async def list_documents(user_id: str = Query(..., min_length=1)):
    # The documents page reloads prior uploads from the local analytics registry.
    return get_user_documents(user_id)


@app.post("/api/upload-pdf", response_model=PDFProcessResponse)
async def upload_pdf(user_id: str = Query(..., min_length=1), file: UploadFile = File(...)):
    # Uploading a PDF updates both FAISS and the knowledge graph.
    try:
        file_bytes = await file.read()
        result = process_pdf(file_bytes, file.filename, user_id)
        graph_stats = ingest_text_into_graph(user_id, result.pop("combined_text", ""))
        register_document(user_id, file.filename, result["num_chunks"])
        return PDFProcessResponse(**result, **graph_stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/api/memories")
async def create_memory(memory_data: MemoryCreate):
    # The memory dashboard writes explicit memory entries here.
    try:
        memory_id = add_memory(
            memory_data.user_id,
            memory_data.type,
            memory_data.content,
            memory_data.metadata,
        )
        return {"memory_id": memory_id, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating memory: {str(e)}")


@app.get("/api/memories", response_model=List[MemoryRecord])
async def list_memories(user_id: str = Query(..., min_length=1), memory_type: str | None = None):
    # This returns a user's stored memories for the memory page.
    try:
        return [_serialize_memory(memory) for memory in get_memories(user_id, memory_type)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching memories: {str(e)}")


@app.get("/api/memories/search", response_model=List[MemoryRecord])
async def search_memory_endpoint(
    query: str,
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
):
    # Search powers both dashboard filtering and chat-time recall.
    try:
        return [_serialize_memory(memory) for memory in search_memories(user_id, query, limit)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memories: {str(e)}")


@app.put("/api/memories/{memory_id}")
async def update_memory_endpoint(memory_id: str, memory_data: MemoryUpdate):
    # Memory entries can be edited inline from the dashboard.
    try:
        success = update_memory(memory_id, memory_data.content, memory_data.metadata)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating memory: {str(e)}")


@app.delete("/api/memories/{memory_id}")
async def delete_memory_endpoint(memory_id: str):
    # Deleting a memory removes it from the active long-term store.
    try:
        success = delete_memory(memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting memory: {str(e)}")


@app.get("/api/graph/entities", response_model=List[GraphEntity])
async def list_graph_entities(user_id: str = Query(..., min_length=1)):
    # The knowledge graph page uses this endpoint to display extracted entities.
    return [GraphEntity(**item) for item in get_all_entities(user_id)]


@app.get("/api/graph/query", response_model=List[GraphQueryResult])
async def query_graph_endpoint(query: str, user_id: str = Query(..., min_length=1)):
    # Graph search lets users inspect stored relationships directly.
    return [GraphQueryResult(**item) for item in query_knowledge_graph(user_id, query)]


@app.post("/api/graph/relationships")
async def create_graph_relationship(payload: GraphRelationshipCreate):
    # Manual graph editing lets the user enrich the graph beyond extracted triples.
    add_relationship(
        user_id=payload.user_id,
        from_entity=payload.from_entity,
        to_entity=payload.to_entity,
        relationship=payload.relationship,
    )
    return {"status": "success"}


@app.delete("/api/graph")
async def clear_graph_endpoint(user_id: str = Query(..., min_length=1)):
    # This clears only the current user's subgraph.
    clear_user_graph(user_id)
    return {"status": "success"}


@app.get("/api/settings/{user_id}", response_model=UserSettings)
async def fetch_user_settings(user_id: str):
    # Settings persist simple dashboard preferences per user.
    return UserSettings(**get_user_settings(user_id))


@app.put("/api/settings/{user_id}", response_model=UserSettings)
async def update_user_settings(user_id: str, payload: UserSettings):
    # The settings page replaces the current user's saved settings.
    if payload.user_id != user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch in settings payload.")
    return UserSettings(**save_user_settings(payload.model_dump()))


@app.get("/api/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(user_id: str = Query(..., min_length=1)):
    # The analytics dashboard combines local document counts with memory and graph metrics.
    documents = get_user_documents(user_id)
    events = get_user_analytics_events(user_id)
    graph_counts = get_graph_counts(user_id)
    total_chats = len(events)
    average_response_time = (
        sum(item["response_time"] for item in events) / total_chats if total_chats else 0.0
    )
    last_route = events[-1]["route"] if events else "none"
    return AnalyticsSummary(
        user_id=user_id,
        uploaded_documents=len(documents),
        total_chunks=count_user_chunks(user_id),
        memory_entries=len(get_memories(user_id)),
        knowledge_graph_nodes=graph_counts["nodes"],
        knowledge_graph_relationships=graph_counts["relationships"],
        total_chats=total_chats,
        average_response_time=average_response_time,
        last_route=last_route,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Chat orchestration merges LangGraph routing, retrieval, memory, graph, tools, and LLM response generation.
    try:
        user_id = request.user_id
        last_user_message = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )

        route_state = await router_graph.ainvoke({"user_id": user_id, "query": last_user_message})
        route = route_state.get("route", "general")

        raw_memories = route_state.get("memories", [])
        raw_sources = route_state.get("sources", [])
        raw_graph_results = route_state.get("graph_results", [])
        raw_tools_used = route_state.get("tools_used", [])

        # Hybrid fallbacks enrich the answer if the primary route returned sparse results.
        if not raw_memories and any(keyword in last_user_message.lower() for keyword in ["favorite", "remember", "like"]):
            raw_memories = search_memory_records(user_id, last_user_message, limit=5)
        if not raw_sources and any(keyword in last_user_message.lower() for keyword in ["document", "pdf", "chapter", "summary", "summarize"]):
            raw_sources = query_vector_store(last_user_message, user_id, k=4)
        if not raw_graph_results and any(keyword in last_user_message.lower() for keyword in ["relationship", "uses", "connected", "framework"]):
            raw_graph_results = query_knowledge_graph(user_id, last_user_message)

        memories = [_serialize_memory(item) for item in raw_memories]
        sources = [Citation(**item) for item in raw_sources]
        graph_results = [GraphQueryResult(**item) for item in raw_graph_results]
        tools_used = [ToolExecution(**item) for item in raw_tools_used]

        system_prompt = _build_system_prompt(
            user_id=user_id,
            sources=sources,
            memories=memories,
            graph_results=graph_results,
            tools_used=tools_used,
        )
        messages_dict = [{"role": "system", "content": system_prompt}] + [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]
        response_text, response_time = groq_llm.generate_response(messages_dict)
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
        )

        if last_user_message:
            add_memory(user_id, "conversation", last_user_message, {"speaker": "user"})
            _extract_preference_memory(user_id, last_user_message)
        add_memory(user_id, "conversation", response_text, {"speaker": "assistant"})

        routing = RoutingDecision(
            route=route,
            used_memory=bool(memories),
            used_rag=bool(sources),
            used_knowledge_graph=bool(graph_results),
            used_tools=bool(tools_used),
        )
        record_chat_analytics(
            user_id=user_id,
            response_time=response_time,
            route=route,
            sources_count=len(sources),
            memories_count=len(memories),
            graph_count=len(graph_results),
            tools_count=len(tools_used),
        )
        return ChatResponse(
            message=assistant_message,
            response_time=response_time,
            sources=sources,
            memories=memories,
            graph_results=graph_results,
            tools_used=tools_used,
            routing=routing,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
