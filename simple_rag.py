"""
Simple RAG implementation without external dependencies.
"""
import os
import sys
import numpy as np
from typing import List, Dict, Any, Optional

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis tools
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore
from utils import EmbeddingProvider, LLMProvider

class Document:
    """Simple document class."""

    def __init__(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Initialize a document."""
        self.text = text
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"Document(text={self.text[:50]}..., metadata={self.metadata})"

class SimpleRAG:
    """
    Simple RAG implementation without external dependencies.
    """

    def __init__(
        self,
        index_name: str = "vehicle_knowledge",
        vector_dimensions: int = 384
    ):
        """
        Initialize the SimpleRAG.

        Args:
            index_name: Name of the vector index
            vector_dimensions: Dimensions of the vector embeddings
        """
        # Initialize components
        self.embedding_provider = EmbeddingProvider()
        self.llm_provider = LLMProvider()

        # Initialize vector store
        self.vector_store = SimpleVectorStore(
            index_name=index_name,
            vector_dimensions=vector_dimensions
        )

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add texts to the vector store.

        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dictionaries

        Returns:
            List of document IDs
        """
        # Generate embeddings
        embeddings = self.embedding_provider.embed(texts)

        # Add to vector store
        return self.vector_store.add_texts(texts, embeddings, metadatas)

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of Document objects

        Returns:
            List of document IDs
        """
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        return self.add_texts(texts, metadatas)

    def retrieve(self, query: str, k: int = 4) -> List[Document]:
        """
        Retrieve documents relevant to the query.

        Args:
            query: Query string
            k: Number of documents to retrieve

        Returns:
            List of retrieved documents
        """
        # Generate query embedding
        query_embedding = self.embedding_provider.embed([query])[0]

        # Search vector store
        results = self.vector_store.similarity_search(query_embedding, k=k)

        # Convert to documents
        documents = []
        for result in results:
            metadata = {k: v for k, v in result.items() if k not in ["text", "id"]}
            doc = Document(text=result["text"], metadata=metadata)
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
        # Prepare context
        context = "\n\n".join([doc.text for doc in context_docs])

        # Create prompt
        prompt = f"""Answer the question based on the following context:

Context:
{context}

Question: {query}

Answer:"""

        # Generate response
        return self.llm_provider.generate(prompt)

    def query(self, query: str, k: int = 4) -> Dict[str, Any]:
        """
        Query the RAG system.

        Args:
            query: Query string
            k: Number of documents to retrieve

        Returns:
            Dictionary with query results
        """
        # Retrieve documents
        retrieved_docs = self.retrieve(query, k=k)

        # Generate response
        response = self.generate(query, retrieved_docs)

        # Return results
        return {
            "query": query,
            "response": response,
            "source_documents": retrieved_docs
        }

def search_avito_vehicles():
    """Search for vehicles in the avito_vehicles index."""
    print("\n=== Searching Avito Vehicles ===\n")

    # Initialize vector store
    vector_store = SimpleVectorStore(index_name="avito_vehicles")

    # Initialize embedding provider
    embedding_provider = EmbeddingProvider()

    # Search queries
    queries = [
        "Самосвал для строительства",
        "Эвакуатор ГАЗель",
        "Зерновоз Volvo"
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        # Generate query embedding
        query_embedding = embedding_provider.embed([query])[0]

        # Search vector store
        results = vector_store.similarity_search(query_embedding, k=2)

        if results:
            print(f"Found {len(results)} matching vehicles:")

            for i, result in enumerate(results):
                print(f"\nResult {i+1}:")

                # Print all available fields
                print("Available fields:")
                for key, value in result.items():
                    if key != "embedding" and key != "score":
                        if isinstance(value, str) and value.strip():
                            # Limit long values
                            if len(value) > 100:
                                value = value[:100] + "..."
                            print(f"  {key}: {value}")

                # Print similarity score
                print(f"Similarity Score: {result.get('score', 0):.4f}")
        else:
            print("No matching vehicles found.")

def main():
    """Main function."""
    # Initialize RAG system
    rag = SimpleRAG()

    # Add sample texts
    texts = [
        "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
        "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях: фургон, бортовой, микроавтобус.",
        "MAN TGX - это седельный тягач премиум-класса, отличается высокой надежностью и экономичностью.",
        "Mercedes-Benz Sprinter - это универсальный микроавтобус, который может использоваться как для пассажирских перевозок, так и в качестве фургона.",
        "Volvo FH - это флагманский седельный тягач Volvo, предназначенный для дальних перевозок."
    ]

    print("Adding texts to RAG system...")
    rag.add_texts(texts)

    # Query the RAG system with multiple queries
    queries = [
        "Какой грузовик лучше для строительных работ?",
        "Расскажи о ГАЗель NEXT",
        "Какой тягач самый надежный?",
        "Самосвал для перевозки грузов",
        "Эвакуатор ГАЗель"
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        result = rag.query(query)
        print(f"Response: {result['response']}")

        print("Source Documents:")
        for doc in result["source_documents"]:
            print(f"- {doc.text}")

        print("---")

if __name__ == "__main__":
    main()
    # Search for vehicles in the avito_vehicles index
    search_avito_vehicles()
