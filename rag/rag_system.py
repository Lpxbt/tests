"""
RAG (Retrieval Augmented Generation) system implementation.
"""
import os
from typing import List, Dict, Any, Optional, Union, Callable
import uuid

from .document_processor import Document, DocumentProcessor
from ..vector_search.vector_store import VectorStore

class RAGSystem:
    """
    RAG (Retrieval Augmented Generation) system.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        document_processor: Optional[DocumentProcessor] = None,
        embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = None,
        llm_function: Optional[Callable[[str], str]] = None,
        top_k: int = 4
    ):
        """
        Initialize the RAG system.
        
        Args:
            vector_store: Vector store for document retrieval
            document_processor: Document processor for text processing
            embedding_function: Function to generate embeddings for text
            llm_function: Function to generate text from a prompt
            top_k: Number of documents to retrieve
        """
        self.vector_store = vector_store or VectorStore()
        self.document_processor = document_processor or DocumentProcessor(embedding_function=embedding_function)
        self.embedding_function = embedding_function
        self.llm_function = llm_function
        self.top_k = top_k
        
        # Set embedding function for document processor if not already set
        if self.document_processor.embedding_function is None:
            self.document_processor.embedding_function = self.embedding_function
            
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the RAG system.
        
        Args:
            documents: List of documents to add
            
        Returns:
            List of document IDs
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Generate embeddings
        embeddings = self.document_processor.generate_embeddings(documents)
        
        # Extract text and metadata
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [doc.doc_id for doc in documents]
        
        # Add to vector store
        return self.vector_store.add_texts(texts, embeddings, metadatas, ids)
        
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add texts to the RAG system.
        
        Args:
            texts: List of texts to add
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            List of document IDs
        """
        # Create documents
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            doc = Document(text=text, metadata=metadata)
            documents.append(doc)
            
        # Process documents
        processed_docs = []
        for doc in documents:
            processed_docs.extend(self.document_processor.process_text(doc.text, doc.metadata))
            
        # Add documents
        return self.add_documents(processed_docs)
        
    def add_file(self, file_path: str) -> List[str]:
        """
        Add a file to the RAG system.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of document IDs
        """
        # Process file
        documents = self.document_processor.process_file(file_path)
        
        # Add documents
        return self.add_documents(documents)
        
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        """
        Retrieve documents relevant to the query.
        
        Args:
            query: Query string
            top_k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Generate query embedding
        query_embedding = self.embedding_function([query])[0]
        
        # Retrieve documents
        k = top_k or self.top_k
        results = self.vector_store.similarity_search(query_embedding, k=k)
        
        # Convert to documents
        documents = []
        for result in results:
            doc = Document(
                text=result["text"],
                metadata={**result, "score": result["score"]},
                doc_id=result["id"]
            )
            documents.append(doc)
            
        return documents
        
    def generate(self, query: str, context_docs: List[Document]) -> str:
        """
        Generate a response based on the query and context documents.
        
        Args:
            query: Query string
            context_docs: List of context documents
            
        Returns:
            Generated response
        """
        if self.llm_function is None:
            raise ValueError("LLM function not provided")
            
        # Prepare context
        context = "\n\n".join([doc.text for doc in context_docs])
        
        # Create prompt
        prompt = f"""Answer the question based on the following context:

Context:
{context}

Question: {query}

Answer:"""
        
        # Generate response
        return self.llm_function(prompt)
        
    def query(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            query: Query string
            top_k: Number of documents to retrieve
            
        Returns:
            Dictionary with query results
        """
        # Retrieve documents
        retrieved_docs = self.retrieve(query, top_k=top_k)
        
        # Generate response
        response = self.generate(query, retrieved_docs)
        
        # Return results
        return {
            "query": query,
            "response": response,
            "source_documents": retrieved_docs
        }
