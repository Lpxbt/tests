"""
Script to check the data in Redis.
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis connection
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore

def main():
    """Main function."""
    # Get Redis client
    redis_client = get_redis_client()
    if redis_client is None:
        print("Error: Redis connection failed.")
        return
    
    # Get vector store
    vector_store = SimpleVectorStore(index_name="avito_vehicles")
    
    # Get document IDs
    doc_ids = vector_store.redis_client.smembers("index:avito_vehicles:docs")
    print(f"Found {len(doc_ids)} documents")
    
    # Print document details
    for doc_id in list(doc_ids):
        doc = vector_store.redis_client.hgetall(doc_id)
        
        # Convert bytes to strings
        doc_str = {}
        for k, v in doc.items():
            key = k.decode() if isinstance(k, bytes) else k
            value = v.decode() if isinstance(v, bytes) else v
            doc_str[key] = value
        
        print(f"\nDocument {doc_id.decode() if isinstance(doc_id, bytes) else doc_id}:")
        for k, v in doc_str.items():
            if k != "embedding":  # Skip embedding vector
                print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
