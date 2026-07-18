# Memory-Augmented Chatbot - Architecture

## Overview

This project implements a hybrid intelligent chatbot system with:
- **Static Knowledge Layer (RAG)** - Document-based retrieval
- **Knowledge Graph Layer (Neo4j)** - Structured entity relationships  
- **Dynamic Intelligence Layer (LangGraph)** - Query routing with web search

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Interface (Streamlit)                 │
├─────────────────────────────────────────────────────────────────┤
│  Chat Interface  │  Recent Chats  │  Documents  │  Knowledge KG │
├─────────────────────────────────────────────────────────────────┤
│                     Hybrid Orchestrator (LangGraph)             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Query Router → [RAG] → [KG] → [Web] → [Direct LLM]    │   │
│  │  Decision based on query analysis & keywords             │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                   Memory & Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  MongoDB     │  │  Neo4j       │  │  FAISS       │          │
│  │  - Chats     │  │  - Graph     │  │  - Vectors   │          │
│  │  - Documents │  │  - Entities  │  │  - Indexes   │          │
│  │  - Users     │  │  - Rel'ships │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Static Knowledge Layer (RAG)

**Files:** `rag/pipeline.py`, `rag/retriever.py`, `rag/llm_client.py`

**Functionality:**
- Document ingestion (PDF, DOCX, TXT, MD)
- Text chunking with overlap (1000 chars, 200 overlap)
- Embedding generation (Sentence Transformers)
- Vector storage in FAISS
- Semantic similarity search
- LLM response generation (Groq)

**Workflow:**
```
Upload Document → Parse → Chunk → Embed → Store in FAISS
                      ↓
User Question → Embed → Search → Retrieve Top-K → LLM Answer
```

### 2. Knowledge Graph Layer

**Files:** `knowledge_graph/manager.py`, `knowledge_graph/neo4j_manager.py`

**Functionality:**
- Entity extraction (spaCy NER)
- Relationship mapping
- Graph storage in Neo4j
- Structured queries for relationships

**Entities:**
- PERSON, ORGANIZATION, LOCATION
- TECHNICAL TERM, CONCEPT
- DATE, NUMBER

**Example Graph:**
```
(Alice)-[:WORKS_AT]->(Google)
(Alice)-[:KNOWS]->(Bob)
(Google)-[:USES]->(Python)
```

### 3. Dynamic Intelligence Layer (LangGraph)

**Files:** `rag/langgraph_orchestrator.py`, `rag/web_scraper.py`

**Functionality:**
- Query analysis and routing
- Context-aware decision making
- Web scraping for current data
- Multi-source answer synthesis

**Routing Logic:**
```
Question Analysis:
├─ Web keywords? → Web Scraper (current/latest/news/today)
├─ Entity questions? → Knowledge Graph (who is/what is/relationship)
├─ Has chat history? → RAG (document-specific)
└─ Fallback → Direct LLM (general knowledge)
```

**Web Scraping:**
- Google search integration
- Content extraction with BeautifulSoup
- Date/time extraction
- Multiple source aggregation

## Chat Interface Features

### Recent Chats Section
- Display last 10 conversations
- Click to restore previous sessions
- Delete all chat history button
- Timestamp and message count

### Document Upload
- Multiple format support
- Automatic chunking and embedding
- Progress tracking
- Source citation display

### Knowledge Graph Page
- Visual entity display
- Relationship exploration
- Custom text extraction
- Statistics and analytics

## Database Schema

### MongoDB Collections

**users:**
```json
{
  "_id": ObjectId,
  "email": String (unique),
  "hashed_password": String,
  "created_at": DateTime,
  "preferences": Object
}
```

**documents:**
```json
{
  "_id": ObjectId,
  "user_id": String,
  "filename": String,
  "content": String,
  "chunks": [String],
  "status": "ready|processing|error",
  "upload_date": DateTime
}
```

**chats:**
```json
{
  "_id": ObjectId,
  "user_id": String,
  "question": String,
  "answer": String,
  "sources": [Object],
  "query_type": "rag|kg|web|direct",
  "timestamp": DateTime
}
```

### Neo4j Schema

**Nodes:**
```
:Entity {
  id: String (unique),
  name: String,
  type: String (PERSON, ORG, LOC, etc.),
  user_id: String
}
```

**Relationships:**
```
(:Entity)-[:RELATED {type: "knows|works_at|uses"}]->(:Entity)
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| LLM | Groq (Mixtral-8x7b) |
| Orchestration | LangGraph |
| Embeddings | Sentence Transformers |
| Vector Store | FAISS |
| Graph DB | Neo4j Aura |
| Document DB | MongoDB Atlas |
| NLP | spaCy |
| Web Scraping | BeautifulSoup |

## Configuration

**Environment Variables (.env):**
```env
NEO4J_URI=neo4j+s://139ecc32.databases.neo4j.io
NEO4J_USER=139ecc32
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=139ecc32
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
GROQ_API_KEY=gsk_...
```

## Usage Examples

### 1. Document Chat
```
1. Upload PDF about "Machine Learning"
2. Ask: "What is a neural network?"
3. RAG retrieves relevant chunks
4. LLM generates answer with citations
```

### 2. Knowledge Graph Query
```
1. Ask: "Who is Alan Turing?"
2. KG extracts entity "Alan Turing"
3. Queries relationships from Neo4j
4. Returns biographical info with connections
```

### 3. Web Search Query
```
1. Ask: "What's the latest news about AI?"
2. Web scraper searches current data
3. Aggregates results from multiple sources
4. Returns up-to-date information
```

### 4. Direct LLM Query
```
1. Ask: "What is Python?"
2. No documents found, no entities
3. Direct LLM response
4. Answer from general knowledge
```

## Performance Metrics

- **Response Time:** < 3 seconds for typical queries
- **Document Processing:** ~10-30 seconds per document
- **Vector Search:** < 500ms latency
- **Concurrent Users:** Tested with 10+ simultaneous users

## Security Features

- JWT authentication with 24-hour expiration
- User ID isolation in all database queries
- Password hashing with bcrypt
- Input validation with Pydantic
- File type and size restrictions

## Future Enhancements

- Voice input support
- Multi-language support
- Advanced visualization
- API endpoints
- Plugin system
- Collaborative features
- Document versioning

---

**Built with ❤️ using modern AI technologies**