"""
Script to search for vehicles in Redis.
"""
import os
import sys
import json
from typing import List, Dict, Any, Optional

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis connection
from redis_connection import get_redis_client
from utils import EmbeddingProvider

def search_vehicles(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for vehicles in Redis.

    Args:
        query: Search query
        k: Number of results to return

    Returns:
        List of vehicle dictionaries
    """
    # Get Redis client
    redis_client = get_redis_client()
    if redis_client is None:
        print("Error: Redis connection failed.")
        return []

    # Initialize embedding provider
    embedding_provider = EmbeddingProvider()

    # Generate query embedding
    query_embedding = embedding_provider.embed([query])[0]

    # Get all keys
    all_keys = redis_client.keys("*")
    vehicle_keys = [k for k in all_keys if k.startswith(b"vehicle:")]

    # Get all vehicle data
    vehicles = []
    for key in vehicle_keys:
        # Get vehicle data
        vehicle_data = redis_client.hgetall(key)

        # Convert bytes to strings
        vehicle = {}
        for k, v in vehicle_data.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            value_str = v.decode() if isinstance(v, bytes) else v
            vehicle[key_str] = value_str

        # Add key to vehicle data
        vehicle["id"] = key.decode() if isinstance(key, bytes) else key

        # Add to vehicles list
        vehicles.append(vehicle)

    # Calculate similarity scores
    results = []
    for vehicle in vehicles:
        # Get embedding
        embedding_str = vehicle.get("embedding")
        if not embedding_str:
            continue

        # Parse embedding
        try:
            embedding = json.loads(embedding_str)
        except json.JSONDecodeError:
            continue

        # Calculate similarity
        import numpy as np
        query_vec = np.array(query_embedding)
        vehicle_vec = np.array(embedding)

        # Normalize vectors
        query_vec = query_vec / np.linalg.norm(query_vec)
        vehicle_vec = vehicle_vec / np.linalg.norm(vehicle_vec)

        # Calculate cosine similarity
        similarity = np.dot(query_vec, vehicle_vec)

        # Add to results
        vehicle_copy = vehicle.copy()
        vehicle_copy.pop("embedding", None)  # Remove embedding to save space
        vehicle_copy["score"] = float(similarity)
        results.append(vehicle_copy)

    # Sort by similarity score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Return top k results
    return results[:min(k, len(results))]

def main():
    """Main function."""
    print("Vehicle Search")
    print("=============")

    # Search queries
    queries = [
        "Самосвал для строительства",
        "Эвакуатор ГАЗель",
        "Зерновоз Volvo"
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        # Search for vehicles
        results = search_vehicles(query, k=2)

        if results:
            print(f"Found {len(results)} matching vehicles:")

            for i, result in enumerate(results):
                print(f"\nResult {i+1}:")

                # Print title and price
                title = result.get("title", "")
                price = result.get("price", "")
                print(f"Title: {title}")
                print(f"Price: {price}")

                # Print description
                description = result.get("description", "")
                if description:
                    # Limit to 200 characters
                    if len(description) > 200:
                        description = description[:200] + "..."
                    print(f"Description: {description}")

                # Print other important fields
                for field in ["brand", "model", "year", "mileage", "engine_type", "transmission", "location"]:
                    value = result.get(field, "")
                    if value:
                        print(f"{field.capitalize()}: {value}")

                # Print URL
                url = result.get("url", "")
                if url:
                    print(f"URL: {url}")

                # Print similarity score
                print(f"Similarity Score: {result.get('score', 0):.4f}")
        else:
            print("No matching vehicles found.")

if __name__ == "__main__":
    main()
