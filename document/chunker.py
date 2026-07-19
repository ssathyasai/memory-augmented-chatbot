"""Text chunking utilities module using LangChain RecursiveCharacterTextSplitter.

Process Flow:
1. Configures target chunk size and character overlap from user settings or defaults.
2. Uses recursive splitting heuristics (`\n\n`, `\n`, `. `, ` `) to preserve paragraph and sentence context.
3. Splits raw extracted document text into clean semantic chunks.
4. Provides a fallback character-based sliding window algorithm if recursive splitting fails.
"""

import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings

logger = logging.getLogger(__name__)


class TextChunker:
    """Split text into chunks with overlap."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Size of each chunk (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        try:
            chunks = self.splitter.split_text(text)
            logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
        
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            # Fallback: simple chunking
            return self._simple_chunk(text)
    
    def _simple_chunk(self, text: str) -> List[str]:
        """
        Simple fallback chunking method.
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        chunks = []
        text_length = len(text)
        
        for i in range(0, text_length, self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
