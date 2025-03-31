"""
Redis connection utility for AI tools.
"""
import os
from typing import Optional
import redis
from redis.client import Redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default Redis connection parameters
DEFAULT_REDIS_URL = "redis://localhost:6379"

# Redis Cloud connection URL (from environment variable)
REDIS_CLOUD_URL = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)

class RedisConnection:
    """
    Singleton class to manage Redis connections.
    """
    _instance = None
    _redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnection, cls).__new__(cls)
            cls._instance._initialize_connection()
        return cls._instance

    def _initialize_connection(self):
        """Initialize the Redis connection using environment variables."""
        redis_url = REDIS_CLOUD_URL
        try:
            # Connect to Redis Cloud
            self._redis_client = redis.from_url(redis_url)
            # Test connection
            self._redis_client.ping()
            print(f"Successfully connected to Redis Cloud at {redis_url.split('@')[1] if '@' in redis_url else redis_url}")
        except redis.ConnectionError as e:
            print(f"Warning: Could not connect to Redis at {redis_url.split('@')[1] if '@' in redis_url else redis_url}. Error: {e}")
            print("Some functionality may be limited without a Redis connection.")
            print("Trying to connect to local Redis instance...")

            # Try connecting to local Redis as fallback
            try:
                self._redis_client = redis.from_url(DEFAULT_REDIS_URL)
                self._redis_client.ping()
                print(f"Successfully connected to local Redis at {DEFAULT_REDIS_URL}")
            except redis.ConnectionError as e:
                print(f"Warning: Could not connect to local Redis either. Error: {e}")
                print("Running in limited functionality mode without Redis.")
                self._redis_client = None

    def get_client(self) -> Optional[Redis]:
        """
        Get the Redis client instance.

        Returns:
            Redis client instance or None if connection failed
        """
        return self._redis_client

    def is_connected(self) -> bool:
        """
        Check if Redis is connected.

        Returns:
            bool: True if connected, False otherwise
        """
        if self._redis_client is None:
            return False

        try:
            self._redis_client.ping()
            return True
        except redis.ConnectionError:
            return False

# Create a global instance
redis_connection = RedisConnection()

def get_redis_client() -> Optional[Redis]:
    """
    Get the Redis client instance.

    Returns:
        Redis client instance or None if connection failed
    """
    return redis_connection.get_client()
