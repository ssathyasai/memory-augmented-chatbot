"""Main document processing and lifecycle manager module.

Process Flow:
1. Validates uploaded file size and extension against allowed application limits.
2. Creates initial document record with `processing` status in MongoDB.
3. Invokes `DocumentParser` to extract raw text content from uploaded bytes.
4. Uses `TextChunker` with user-specific chunk size and overlap parameters to generate chunk lists.
5. Updates MongoDB document record to `ready` status containing extracted text and chunks.
6. Passes text to `KnowledgeGraphManager` to populate Neo4j graph entities and relationships.
7. Deletes document records from MongoDB and syncs relationship removal in Neo4j upon user request.
"""

import logging
from datetime import datetime
from typing import Optional
from bson import ObjectId

from config.database import get_database
from config.settings import settings
from errors.exceptions import DocumentProcessingError, ValidationError
from .models import Document, DocumentMetadata
from .parsers import DocumentParser
from .chunker import TextChunker

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and store documents."""
    
    def __init__(self):
        """Initialize document processor."""
        self.db = get_database()
        self.parser = DocumentParser()
        self.chunker = TextChunker()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            self.db = get_database()
            if self.db is None:
                raise DocumentProcessingError("Database connection not available")
    
    def validate_file(self, filename: str, file_size: int) -> None:
        """
        Validate file before processing.
        
        Args:
            filename: Name of the file
            file_size: Size of file in bytes
        
        Raises:
            ValidationError: If validation fails
        """
        # Check file extension
        file_ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        allowed_extensions = [ext.strip() for ext in settings.ALLOWED_EXTENSIONS.split(',')]
        if file_ext not in allowed_extensions:
            raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
        
        # Check file size
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValidationError(f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB} MB")
    
    def process_document(self, file_bytes: bytes, filename: str, user_id: str) -> Document:
        """
        Process uploaded document.
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename
            user_id: User ID who uploaded
        
        Returns:
            Processed Document object
        
        Raises:
            DocumentProcessingError: If processing fails
        """
        self._ensure_db()
        
        try:
            # Validate file
            self.validate_file(filename, len(file_bytes))
            
            # Extract file type
            file_type = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
            
            # Create initial document record
            doc_id = str(ObjectId())
            doc_dict = {
                "_id": ObjectId(doc_id),
                "user_id": user_id,
                "filename": filename,
                "file_type": file_type,
                "content": "",
                "chunks": [],
                "chunk_count": 0,
                "metadata": {
                    "size_bytes": len(file_bytes),
                    "page_count": None,
                    "language": "en"
                },
                "upload_date": datetime.utcnow(),
                "status": "processing",
                "error_message": None
            }
            
            self.db.documents.insert_one(doc_dict)
            logger.info(f"Created document record: {doc_id}")
            
            # Parse document
            logger.info(f"Parsing document: {filename}")
            content = self.parser.parse(file_bytes, file_type)
            
            # Load user settings for chunk size and overlap
            user_doc = self.db.users.find_one({"_id": ObjectId(user_id)})
            user_settings = user_doc.get("settings", {}) if user_doc else {}
            chunk_size = user_settings.get("chunk_size", settings.CHUNK_SIZE)
            chunk_overlap = user_settings.get("chunk_overlap", settings.CHUNK_OVERLAP)
            
            # Chunk text using user-specific settings
            logger.info(f"Chunking document: {filename} with size={chunk_size}, overlap={chunk_overlap}")
            custom_chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = custom_chunker.chunk_text(content)
            
            # Update document
            self.db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {
                    "content": content,
                    "chunks": chunks,
                    "chunk_count": len(chunks),
                    "status": "ready"
                }}
            )
            
            # Extract entities and relationships for the Knowledge Graph
            try:
                from knowledge_graph.manager import KnowledgeGraphManager
                logger.info(f"Extracting KG entities and relationships from document: {filename}")
                kg_mgr = KnowledgeGraphManager(user_id)
                # Process the first 15,000 characters to build graph entities, passing document_id
                kg_mgr.process_text(content[:15000], document_id=doc_id)
            except Exception as e:
                logger.error(f"Error building Knowledge Graph for document {filename}: {e}")
                
            logger.info(f"Document processed: {doc_id}, {len(chunks)} chunks")
            
            # Create Document object
            document = Document(
                id=doc_id,
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                content=content,
                chunks=chunks,
                chunk_count=len(chunks),
                metadata=DocumentMetadata(
                    size_bytes=len(file_bytes),
                    language="en"
                ),
                upload_date=datetime.utcnow(),
                status="ready"
            )
            
            return document
        
        except (ValidationError, DocumentProcessingError) as e:
            # Update document status
            if 'doc_id' in locals():
                self.db.documents.update_one(
                    {"_id": ObjectId(doc_id)},
                    {"$set": {"status": "error", "error_message": str(e)}}
                )
            raise
        
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            # Update document status
            if 'doc_id' in locals():
                self.db.documents.update_one(
                    {"_id": ObjectId(doc_id)},
                    {"$set": {"status": "error", "error_message": str(e)}}
                )
            raise DocumentProcessingError(f"Failed to process document: {str(e)}")
    
    def get_user_documents(self, user_id: str) -> list[Document]:
        """
        Get all documents for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of documents
        """
        self._ensure_db()
        
        try:
            docs = self.db.documents.find({"user_id": user_id}).sort("upload_date", -1)
            
            documents = []
            for doc in docs:
                documents.append(Document(
                    id=str(doc["_id"]),
                    user_id=doc["user_id"],
                    filename=doc["filename"],
                    file_type=doc["file_type"],
                    content=doc.get("content", ""),
                    chunks=doc.get("chunks", []),
                    chunk_count=doc.get("chunk_count", 0),
                    metadata=DocumentMetadata(**doc.get("metadata", {"size_bytes": 0})),
                    upload_date=doc["upload_date"],
                    status=doc.get("status", "unknown"),
                    error_message=doc.get("error_message")
                ))
            
            return documents
        
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return []
    
    def delete_document(self, doc_id: str, user_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID
            user_id: User ID (for authorization)
        
        Returns:
            True if deleted, False otherwise
        """
        self._ensure_db()
        
        try:
            result = self.db.documents.delete_one({
                "_id": ObjectId(doc_id),
                "user_id": user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Document deleted: {doc_id}")
                
                # Sync deletion: remove document relationships from Neo4j
                try:
                    from knowledge_graph.manager import KnowledgeGraphManager
                    kg_mgr = KnowledgeGraphManager(user_id)
                    kg_mgr.kg.delete_document_relations(doc_id)
                except Exception as e:
                    logger.error(f"Error deleting Neo4j document relations: {e}")
                    
                # Sync deletion: remove document from FAISS Vector Store
                try:
                    from rag.vector_store import VectorStore
                    vs = VectorStore(user_id)
                    vs.delete_document(doc_id)
                except Exception as e:
                    logger.error(f"Error deleting vector store document: {e}")
                    
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    def delete_all_user_documents(self, user_id: str) -> bool:
        """
        Delete all documents for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        self._ensure_db()
        
        try:
            result = self.db.documents.delete_many({"user_id": user_id})
            logger.info(f"Deleted {result.deleted_count} documents for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting all user documents: {e}")
            return False


# Global document processor instance
document_processor = DocumentProcessor()

