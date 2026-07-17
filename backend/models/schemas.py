
# This file defines the API request and response models.
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    # Each message in the conversation carries a role and message content.
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="Role of the message sender.",
    )
    content: str = Field(..., min_length=1, description="Message body.")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp for the message.",
    )


class ChatRequest(BaseModel):
    # The active user is passed explicitly to keep data isolated across users.
    user_id: str = Field(..., min_length=1, description="Current user identifier.")
    messages: List[ChatMessage] = Field(
        ...,
        min_length=1,
        description="Conversation history sent to the backend.",
    )


class Citation(BaseModel):
    # Retrieved document chunk returned to the frontend for transparency.
    source: str = Field(..., description="Document filename.")
    content: str = Field(..., description="Retrieved chunk content.")
    score: float = Field(..., description="Similarity score from FAISS.")
    page: Optional[int] = Field(default=None, description="Source page number if known.")


class MemoryRecord(BaseModel):
    # Memory records are persisted per user for long-term recall.
    memory_id: str = Field(..., description="Unique memory identifier.")
    user_id: str = Field(..., description="Owner of the memory.")
    type: Literal["preference", "fact", "conversation"] = Field(
        ...,
        description="Memory category.",
    )
    content: str = Field(..., description="Stored memory content.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured memory attributes.",
    )
    created_at: datetime = Field(..., description="Creation time.")
    updated_at: datetime = Field(..., description="Last modification time.")


class MemoryCreate(BaseModel):
    # Memory creation payload used by the dashboard and chat pipeline.
    user_id: str = Field(..., min_length=1, description="Current user identifier.")
    type: Literal["preference", "fact", "conversation"] = Field(
        ...,
        description="Memory category.",
    )
    content: str = Field(..., min_length=1, description="Memory content.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional memory metadata.",
    )


class MemoryUpdate(BaseModel):
    # Memory update allows partial edits from the dashboard.
    content: Optional[str] = Field(default=None, description="Updated memory content.")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated metadata object.",
    )


class PDFProcessResponse(BaseModel):
    # PDF processing returns counts used by the upload dashboard.
    status: str = Field(..., description="Processing result.")
    filename: str = Field(..., description="Uploaded filename.")
    num_documents: int = Field(..., description="Number of extracted document pages.")
    num_chunks: int = Field(..., description="Number of generated chunks.")
    entities_extracted: int = Field(
        default=0,
        description="Number of knowledge graph entities extracted from the file.",
    )
    relationships_extracted: int = Field(
        default=0,
        description="Number of relationships extracted from the file.",
    )


class GraphRelationshipCreate(BaseModel):
    # Manual graph updates are supported from the dashboard.
    user_id: str = Field(..., min_length=1, description="Current user identifier.")
    from_entity: str = Field(..., min_length=1, description="Source entity label.")
    to_entity: str = Field(..., min_length=1, description="Target entity label.")
    relationship: str = Field(..., min_length=1, description="Relationship type.")


class GraphEntity(BaseModel):
    # Graph entity card displayed in the knowledge graph page.
    entity_id: str = Field(..., description="Entity identifier.")
    name: str = Field(..., description="Entity name.")
    entity_type: str = Field(..., description="Entity type.")
    relation_count: int = Field(..., description="Connected relationship count.")


class GraphQueryResult(BaseModel):
    # Query results summarize entity relationships matched for a user query.
    entity: str = Field(..., description="Matched entity.")
    entity_type: str = Field(..., description="Matched entity type.")
    relations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relationships connected to the matched entity.",
    )


class ToolExecution(BaseModel):
    # Tool traces explain which external data source was used.
    tool_name: str = Field(..., description="Tool name.")
    input_query: str = Field(..., description="Query passed to the tool.")
    output_summary: str = Field(..., description="Short tool result summary.")


class RoutingDecision(BaseModel):
    # The router returns the selected execution path for transparency.
    route: str = Field(..., description="Primary route chosen by the router.")
    used_memory: bool = Field(default=False, description="Whether memory was consulted.")
    used_rag: bool = Field(default=False, description="Whether RAG was consulted.")
    used_knowledge_graph: bool = Field(
        default=False,
        description="Whether the knowledge graph was consulted.",
    )
    used_tools: bool = Field(default=False, description="Whether any external tool ran.")


class ChatResponse(BaseModel):
    # Chat responses include traces for analytics and explanation.
    message: ChatMessage = Field(..., description="Assistant reply.")
    response_time: float = Field(..., description="End-to-end latency in seconds.")
    sources: List[Citation] = Field(
        default_factory=list,
        description="Document chunks used for the answer.",
    )
    memories: List[MemoryRecord] = Field(
        default_factory=list,
        description="Memories used to answer the request.",
    )
    graph_results: List[GraphQueryResult] = Field(
        default_factory=list,
        description="Knowledge graph results used by the answer.",
    )
    tools_used: List[ToolExecution] = Field(
        default_factory=list,
        description="Tool executions used by the answer.",
    )
    routing: RoutingDecision = Field(..., description="Router decision metadata.")


class AnalyticsSummary(BaseModel):
    # Analytics aggregates dashboard-level metrics for the current user.
    user_id: str = Field(..., description="Current user identifier.")
    uploaded_documents: int = Field(..., description="Total uploaded documents.")
    total_chunks: int = Field(..., description="Total stored chunks.")
    memory_entries: int = Field(..., description="Total memory records.")
    knowledge_graph_nodes: int = Field(..., description="Total graph nodes.")
    knowledge_graph_relationships: int = Field(
        ...,
        description="Total graph relationships.",
    )
    total_chats: int = Field(..., description="Total completed chat turns.")
    average_response_time: float = Field(..., description="Average response latency.")
    last_route: str = Field(..., description="Most recent selected route.")


class UserSettings(BaseModel):
    # Settings are persisted per user and surfaced in the settings page.
    user_id: str = Field(..., min_length=1, description="Current user identifier.")
    display_name: str = Field(..., min_length=1, description="User display name.")
    preferred_theme: Literal["dark", "light"] = Field(
        default="dark",
        description="UI theme preference.",
    )
    transparency_enabled: bool = Field(
        default=True,
        description="Whether traces are shown in the UI.",
    )
