"""
Simple script to test searching for vehicles in Redis.
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis connection
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore
from utils import EmbeddingProvider

def main():
    """Main function."""
    print("Testing search functionality")
    print("===========================")
    
    # Initialize vector store
    vector_store = SimpleVectorStore(index_name="avito_vehicles")
    
    # Initialize embedding provider
    embedding_provider = EmbeddingProvider()
    
    # Search query
    query = "Эвакуатор ГАЗель"
    print(f"\nQuery: {query}")
    
    # Generate query embedding
    query_embedding = embedding_provider.embed([query])[0]
    
    # Search vector store
    results = vector_store.similarity_search(query_embedding, k=2)
    
    if results:
        print(f"Found {len(results)} matching vehicles:")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            
            # Print document ID
            doc_id = result.get("id", "Unknown")
            print(f"Document ID: {doc_id}")
            
            # Print all available fields
            for key, value in result.items():
                if key not in ["embedding", "score", "id"]:
                    if isinstance(value, str) and value.strip():
                        # Limit long values
                        if len(value) > 100:
                            value = value[:100] + "..."
                        print(f"{key}: {value}")
            
            # Print similarity score
            print(f"Similarity Score: {result.get('score', 0):.4f}")
    else:
        print("No matching vehicles found.")

if __name__ == "__main__":
    main()
