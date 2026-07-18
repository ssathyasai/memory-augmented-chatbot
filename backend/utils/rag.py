
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from .config import settings

# The embedding model is intentionally lightweight for local development.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
VECTOR_STORE_PATH = settings.FAISS_DIR

embeddings = None
vector_store = None


def get_embeddings():
    """Lazy load embeddings model only when needed."""
    global embeddings
    if embeddings is None:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    return embeddings


def load_or_initialize_vector_store() -> bool:
    # This loads the persisted FAISS index if it already exists.
    global vector_store
    if Path(VECTOR_STORE_PATH).exists():
        vector_store = FAISS.load_local(
            VECTOR_STORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        return True
    return False


def process_pdf(file_bytes: bytes, filename: str, user_id: str) -> Dict[str, Any]:
    # Each chunk is tagged with the user so retrieval stays isolated.
    global vector_store

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        loader = PyMuPDFLoader(tmp_path)
        documents = loader.load()
        for index, doc in enumerate(documents):
            doc.metadata["source"] = filename
            doc.metadata["user_id"] = user_id
            doc.metadata["page"] = doc.metadata.get("page", index + 1)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = text_splitter.split_documents(documents)

        if vector_store:
            vector_store.add_documents(chunks)
        else:
            vector_store = FAISS.from_documents(chunks, embeddings)

        Path(settings.DATABASE_DIR).mkdir(parents=True, exist_ok=True)
        vector_store.save_local(VECTOR_STORE_PATH)

        return {
            "status": "success",
            "filename": filename,
            "num_documents": len(documents),
            "num_chunks": len(chunks),
            "combined_text": "\n".join(document.page_content for document in documents[:20]),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def query_vector_store(query: str, user_id: str, k: int = 4) -> List[Dict[str, Any]]:
    # FAISS returns top-k chunks, then we filter by user ownership.
    global vector_store
    if not vector_store:
        return []

    # Query FAISS directly with a metadata filter to isolate results by user_id
    results = vector_store.similarity_search_with_score(query, k=k, filter={"user_id": user_id})
    formatted_results: List[Dict[str, Any]] = []
    for doc, score in results:
        formatted_results.append(
            {
                "source": doc.metadata.get("source", "unknown"),
                "content": doc.page_content,
                "score": float(score),
                "page": doc.metadata.get("page"),
            }
        )
    return formatted_results


def count_user_chunks(user_id: str) -> int:
    # Analytics uses a conservative chunk count by inspecting metadata.
    global vector_store
    if not vector_store or vector_store.index.ntotal == 0:
        return 0
    count = 0
    docstore_values = vector_store.docstore._dict.values()
    for document in docstore_values:
        if document.metadata.get("user_id") == user_id:
            count += 1
    return count


def clear_vector_store() -> None:
    # This reset is useful for local development and tests.
    global vector_store
    vector_store = None
    if Path(VECTOR_STORE_PATH).exists():
        shutil.rmtree(VECTOR_STORE_PATH)
