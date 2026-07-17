
# Memory-Augmented Chatbot with Knowledge Graph and Hybrid RAG System

## Overview
This project is a full-stack AI assistant built with a fixed architecture:

Frontend  
↓  
FastAPI  
↓  
LangGraph Router  
↓  
RAG + Memory + Knowledge Graph + Tools  
↓  
Groq LLM  
↓  
Final Response

The application now includes:
- Chat UI with markdown rendering, typing animation, dark mode, and responsive layout
- Multi-document PDF upload with PyMuPDF extraction, chunking, embeddings, and FAISS retrieval
- Long-term memory with MongoDB-first storage and local fallback for development
- Knowledge graph with Neo4j-first storage and local fallback for development
- LangGraph routing across memory, RAG, knowledge graph, and live tools
- Dynamic tools for weather, news, and Wikipedia
- Analytics dashboard with routing, chunk, memory, graph, and latency metrics
- Settings page for per-user display name, theme, and transparency

## Project Structure
```text
chatbot_project/
├── backend/
│   ├── api/
│   ├── database/
│   ├── knowledge_graph/
│   ├── langgraph/
│   │   └── router.py
│   ├── memory/
│   ├── models/
│   │   └── schemas.py
│   ├── rag/
│   ├── tools/
│   ├── utils/
│   │   ├── analytics.py
│   │   ├── config.py
│   │   ├── knowledge_graph.py
│   │   ├── llm.py
│   │   ├── memory.py
│   │   ├── rag.py
│   │   └── tools_runtime.py
│   ├── .env
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── css/
│   │   └── style.css
│   ├── images/
│   ├── js/
│   │   └── app.js
│   └── index.html
└── README.md
```

## File Explanation
- `backend/main.py`: Central FastAPI app, API endpoints, startup hooks, chat orchestration, and analytics logging
- `backend/langgraph/router.py`: LangGraph decision graph for memory, RAG, graph, and tool routing
- `backend/utils/llm.py`: Groq model client and response generation wrapper
- `backend/utils/rag.py`: PDF extraction, chunking, embeddings, FAISS persistence, and retrieval
- `backend/utils/memory.py`: MongoDB-backed memory storage with safe local fallback
- `backend/utils/knowledge_graph.py`: Neo4j-backed graph storage, extraction heuristics, querying, and fallback
- `backend/utils/tools_runtime.py`: External tools for weather, news, and Wikipedia
- `backend/utils/analytics.py`: Local analytics, uploaded document registry, and user settings persistence
- `backend/models/schemas.py`: Typed API contracts for chat, memory, graph, analytics, and settings
- `frontend/index.html`: Dashboard pages for chat, documents, graph, memory, analytics, and settings
- `frontend/css/style.css`: Dark-themed dashboard styling and reusable cards/forms
- `frontend/js/app.js`: Frontend state manager, API calls, rendering, transparency traces, and user settings

## Setup
### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment variables
Update `backend/.env` with real values:

```env
GROQ_API_KEY=your_real_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
MONGODB_URI=your_real_mongodb_atlas_uri
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_real_neo4j_password
```

Notes:
- Groq is required for chat generation.
- MongoDB and Neo4j are optional for local boot because the app falls back to local storage when they are unavailable.
- For final submission and interviews, use real MongoDB Atlas and Neo4j instances.

### 3. Run the backend
```bash
cd backend
python -m uvicorn main:app --reload
```

### 4. Open the app
Visit `http://127.0.0.1:8000`.

## API Summary
- `GET /`: Serves the frontend dashboard
- `GET /health`: Health summary for Groq, MongoDB, and Neo4j
- `GET /api/documents?user_id=...`: Lists uploaded documents for a user
- `POST /api/upload-pdf?user_id=...`: Uploads and processes a PDF into FAISS and the knowledge graph
- `POST /api/chat`: Runs the LangGraph-routed chat pipeline
- `GET /api/memories?user_id=...`: Lists user memories
- `POST /api/memories`: Creates a memory
- `GET /api/memories/search?...`: Searches user memories
- `PUT /api/memories/{memory_id}`: Updates a memory
- `DELETE /api/memories/{memory_id}`: Deletes a memory
- `GET /api/graph/entities?user_id=...`: Lists graph entities
- `GET /api/graph/query?...`: Searches the knowledge graph
- `POST /api/graph/relationships`: Adds a manual graph relationship
- `DELETE /api/graph?user_id=...`: Clears the current user graph
- `GET /api/analytics/summary?user_id=...`: Returns dashboard metrics
- `GET /api/settings/{user_id}`: Returns saved user settings
- `PUT /api/settings/{user_id}`: Saves user settings

## Phase Coverage
### Phase 1
- FastAPI backend
- HTML, CSS, and JavaScript frontend
- Chat UI
- Groq integration
- Dark mode
- Responsive UI
- Typing animation
- Markdown support
- Conversation API

### Phase 2
- PDF upload
- Text extraction with PyMuPDF
- Chunking
- Embeddings with sentence-transformers
- FAISS vector search
- Context injection
- Source citations
- Multi-document support

### Phase 3
- MongoDB Atlas-ready memory layer
- Memory create, retrieve, search, update, delete
- Conversation memory capture
- Preference extraction from chat
- User-level isolation through `user_id`

### Phase 4
- Neo4j-ready knowledge graph layer
- Entity extraction heuristics
- Relationship extraction heuristics
- Graph construction
- Graph query endpoints
- Dashboard graph inspection

### Phase 5
- LangGraph router
- Conditional routing to memory, RAG, graph, and tools
- Hybrid enrichment when route results are sparse

### Phase 6
- Weather tool via Open-Meteo
- News tool via Hacker News search
- Wikipedia summary tool

### Phase 7
- Analytics summary endpoint
- Dashboard metrics for documents, chunks, memory, graph, chat count, latency, and route

## Manual Testing
### Core tests
1. Open the dashboard and verify all sidebar pages render.
2. Save a new user in Settings and confirm dashboard state reloads for that user.
3. Add a memory from the Memory page and confirm it appears immediately.
4. Add a graph relationship from the Knowledge Graph page and confirm the entity cards update.
5. Upload a PDF and confirm the document appears in the Documents page.
6. Ask a document question and confirm source traces appear under the answer.
7. Ask a memory question like `What is my favorite language?` after storing a preference.
8. Ask a graph question like `Which framework uses LLM?` after creating a relationship.
9. Ask a live question like `What is the weather in Hyderabad?`.
10. Open Analytics and confirm counters increase after interactions.

### Expected outputs
- Health endpoint returns service availability instead of crashing.
- Documents list is isolated per `user_id`.
- Memory list only shows the active user’s items.
- Graph entities only show the active user’s nodes.
- Chat responses include route and transparency pills when enabled.

### Edge cases
- Empty chat message is ignored.
- Missing MongoDB or Neo4j should not crash the UI.
- Missing Groq API key should only affect chat generation, not dashboard pages.
- Graph search with no matches returns an empty result list.

### Common bugs and fixes
- `GROQ_API_KEY` invalid: chat returns a server error until a real key is configured.
- MongoDB DNS/auth errors: memory falls back locally, but Atlas persistence will not be active.
- Neo4j connection refused: graph falls back locally, but Neo4j persistence will not be active.
- First FAISS/embedding load is slow: sentence-transformer model download happens on first run.

## Interview Explanation
### Architecture explanation
- The frontend is a single dashboard shell that talks only to FastAPI.
- FastAPI delegates query understanding to LangGraph.
- LangGraph decides whether to retrieve memory, documents, graph data, tools, or a mix.
- The LLM receives one final grounded prompt and returns a single coherent answer.

### Flow explanation
1. User sends a message.
2. LangGraph classifies the route.
3. Memory, RAG, graph, and tool nodes gather context.
4. FastAPI builds a final prompt.
5. Groq generates the answer.
6. Analytics and memory are updated.

### Sample interview questions
- Why use LangGraph instead of hardcoded if-else routing?
- Why combine FAISS and Neo4j?
- How is user isolation enforced?
- What happens when MongoDB or Neo4j is unavailable?
- Why are citations and route traces shown in the UI?

### Sample answers
- LangGraph keeps routing explicit, extensible, and easier to debug than scattered conditionals.
- FAISS is strong for semantic similarity, while Neo4j is strong for relationship traversal.
- Every persistent record is keyed by `user_id`, and every query is filtered by that user.
- The app degrades gracefully with local fallbacks for development, but production should use the real services.
- Transparency improves trust, debugging, and interview demonstration value.

## Deployment
### Backend on Render
1. Push the repo to GitHub.
2. Create a new Web Service on Render.
3. Set the root to `backend`.
4. Use build command: `pip install -r requirements.txt`
5. Use start command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables in Render.

### Frontend on Vercel
This project currently serves the frontend from FastAPI. For Vercel deployment, either:
- keep a static export of `frontend/` and point it to the Render backend URL, or
- continue serving frontend and backend together from the backend deployment for simplicity.

## Git Commit Message
```bash
git add .
git commit -m "Build hybrid chatbot with RAG, memory, knowledge graph, LangGraph routing, tools, and analytics"
```
