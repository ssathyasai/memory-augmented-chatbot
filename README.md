# 🧠 Memory-Augmented Chatbot

An intelligent, production-ready conversational AI platform featuring **Hybrid RAG**, **Neo4j Knowledge Graph**, **LangGraph Orchestration**, and **RAG Quality Analytics**.

🚀 **Live Deployment Link:** [https://memory-augmented-c.streamlit.app/](https://memory-augmented-c.streamlit.app/)

---

## ✨ Key Features

- 📄 **Hybrid RAG Retrieval Engine**  
  Combines FAISS dense vector search with sparse keyword matching. Supports sub-query decomposition, semantic content deduplication, and dynamic Top-K scaling for complex multi-part questions.

- 🧠 **Neo4j Knowledge Graph Integration**  
  Automatically extracts entities (People, Organizations, Concepts) and relationships from documents and conversations, offering interactive graph analytics and visualization.

- 🔀 **LangGraph Intelligent Query Routing**  
  Dynamically routes user prompts across RAG document search, Knowledge Graph entity lookup, Web Search, and direct LLM chat based on intent.

- 📊 **RAG Quality Evaluation Dashboard**  
  Computes real-time evaluation metrics for Faithfulness, Context Relevance, and Answer Correctness with bulk evaluation support for historical logs.

- 🔒 **Multi-User Isolation & Auth**  
  JWT-based authentication, user-isolated FAISS vector indices, isolated MongoDB document/chat storage, and user profile memory management.

- ⚙️ **User Data Control & Danger Zone**  
  Configurable RAG hyperparameters (Top-K, similarity threshold, chunk size), JSON data export, and complete **Delete All Data** functionality across MongoDB, FAISS, and Neo4j.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **LLM Engine:** GROQ API (`llama-3.1-8b-instant`)
- **Orchestration:** LangGraph
- **Embeddings:** HuggingFace `sentence-transformers/all-MiniLM-L6-v2`
- **Vector Store:** FAISS (Facebook AI Similarity Search)
- **Databases:** MongoDB (Documents, Conversations, Evaluations), Neo4j (Knowledge Graph)
- **NLP & NER:** spaCy (`en_core_web_sm`)
- **Web Search:** BeautifulSoup & Web Scraper

---

## ⚡ Quick Start

### 1. Clone Repository & Install Dependencies

```bash
git clone https://github.com/ssathyasai/memory-augmented-chatbot.git
cd memory-augmented-chatbot

python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
JWT_SECRET_KEY="your-secret-key-min-32-chars"
MONGODB_URI="mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
NEO4J_URI="neo4j+s://<instance-id>.databases.neo4j.io"
NEO4J_USER="<instance-id>"
NEO4J_PASSWORD="your-neo4j-password"
NEO4J_DATABASE="<instance-id>"
GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxx"
```

### 3. Run Locally

```bash
streamlit run app.py
```

---

## 🌐 Live Application

Access the live app hosted on Streamlit Cloud:  
🔗 **[https://memory-augmented-c.streamlit.app/](https://memory-augmented-c.streamlit.app/)**

---

## 📝 License

Distributed under the MIT License.