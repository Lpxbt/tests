"""
Document processing utilities for RAG.
"""
import os
import re
from typing import List, Dict, Any, Optional, Callable, Union
import uuid

class Document:
    """
    Document class for storing text and metadata.
    """
    
    def __init__(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize a document.
        
        Args:
            text: Document text
            metadata: Document metadata
            doc_id: Document ID
        """
        self.text = text
        self.metadata = metadata or {}
        self.doc_id = doc_id or str(uuid.uuid4())
        
    def __repr__(self) -> str:
        return f"Document(id={self.doc_id}, text={self.text[:50]}..., metadata={self.metadata})"


class TextSplitter:
    """
    Text splitter for chunking documents.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n"
    ):
        """
        Initialize a text splitter.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            separator: Separator for splitting text
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        
    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Split text by separator
        splits = text.split(self.separator)
        
        # Initialize chunks
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Process each split
        for split in splits:
            # Skip empty splits
            if not split.strip():
                continue
                
            # If adding this split would exceed chunk size, save current chunk and start a new one
            if current_length + len(split) > self.chunk_size and current_chunk:
                chunks.append(self.separator.join(current_chunk))
                
                # Keep overlap from previous chunk
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk) + len(self.separator) * (len(current_chunk) - 1)
                
            # Add split to current chunk
            current_chunk.append(split)
            current_length += len(split) + len(self.separator)
            
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
            
        return chunks
        
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of chunked documents
        """
        chunked_documents = []
        
        for doc in documents:
            # Split text
            chunks = self.split_text(doc.text)
            
            # Create new documents for each chunk
            for i, chunk in enumerate(chunks):
                # Create metadata with chunk info
                metadata = doc.metadata.copy()
                metadata["chunk"] = i
                metadata["source"] = metadata.get("source", doc.doc_id)
                metadata["parent_id"] = doc.doc_id
                
                # Create new document
                chunked_doc = Document(
                    text=chunk,
                    metadata=metadata,
                    doc_id=f"{doc.doc_id}_chunk_{i}"
                )
                
                chunked_documents.append(chunked_doc)
                
        return chunked_documents


class DocumentProcessor:
    """
    Document processor for RAG.
    """
    
    def __init__(
        self,
        text_splitter: Optional[TextSplitter] = None,
        embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = None
    ):
        """
        Initialize a document processor.
        
        Args:
            text_splitter: Text splitter for chunking documents
            embedding_function: Function to generate embeddings for text
        """
        self.text_splitter = text_splitter or TextSplitter()
        self.embedding_function = embedding_function
        
    def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Process text into documents.
        
        Args:
            text: Text to process
            metadata: Metadata for the document
            
        Returns:
            List of processed documents
        """
        # Create document
        doc = Document(text=text, metadata=metadata or {})
        
        # Split document
        return self.text_splitter.split_documents([doc])
        
    def process_file(self, file_path: str) -> List[Document]:
        """
        Process a file into documents.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of processed documents
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        # Create metadata
        metadata = {
            "source": file_path,
            "filename": os.path.basename(file_path)
        }
        
        # Process text
        return self.process_text(text, metadata)
        
    def generate_embeddings(self, documents: List[Document]) -> List[List[float]]:
        """
        Generate embeddings for documents.
        
        Args:
            documents: List of documents
            
        Returns:
            List of embeddings
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Extract text from documents
        texts = [doc.text for doc in documents]
        
        # Generate embeddings
        return self.embedding_function(texts)
