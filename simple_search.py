"""
Simple script to search for vehicles in Redis.
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis connection
from redis_connection import get_redis_client
from utils import EmbeddingProvider

def main():
    """Main function."""
    print("Simple Vehicle Search")
    print("===================")
    
    # Get Redis client
    redis_client = get_redis_client()
    if redis_client is None:
        print("Error: Redis connection failed.")
        return
    
    # Get all keys
    all_keys = redis_client.keys("*")
    vehicle_keys = [k for k in all_keys if k.startswith(b"vehicle:")]
    
    print(f"Found {len(vehicle_keys)} vehicle keys")
    
    # Get sample vehicle data
    if vehicle_keys:
        sample_key = vehicle_keys[0]
        vehicle_data = redis_client.hgetall(sample_key)
        
        # Convert bytes to strings
        vehicle = {}
        for k, v in vehicle_data.items():
            key_str = k.decode() if isinstance(k, bytes) else k
            value_str = v.decode() if isinstance(v, bytes) else v
            if key_str != "embedding":  # Skip embedding to save space
                vehicle[key_str] = value_str
        
        print("\nSample vehicle data:")
        for k, v in vehicle.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
