"""
Semantic cache implementation for LLM queries.
"""
import time
import json
import hashlib
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
import uuid

from ..vector_search.vector_store import VectorStore

class SemanticCache:
    """
    Semantic cache for LLM queries.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = None,
        similarity_threshold: float = 0.95,
        ttl: Optional[int] = None,  # Time-to-live in seconds
        index_name: str = "semantic_cache",
        prefix: str = "cache:"
    ):
        """
        Initialize the semantic cache.
        
        Args:
            vector_store: Vector store for cache storage
            embedding_function: Function to generate embeddings for queries
            similarity_threshold: Threshold for semantic similarity (0-1)
            ttl: Time-to-live for cache entries in seconds (None for no expiration)
            index_name: Name of the vector index
            prefix: Prefix for cache keys
        """
        self.vector_store = vector_store or VectorStore(
            index_name=index_name,
            prefix=prefix,
            metadata_fields=["query", "response", "timestamp", "hash"]
        )
        self.embedding_function = embedding_function
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.prefix = prefix
        
    def _compute_hash(self, query: str) -> str:
        """
        Compute a hash for the query.
        
        Args:
            query: Query string
            
        Returns:
            Hash string
        """
        return hashlib.md5(query.encode()).hexdigest()
        
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached response for a query.
        
        Args:
            query: Query string
            
        Returns:
            Cached response or None if not found
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Generate query embedding
        query_embedding = self.embedding_function([query])[0]
        
        # Search for similar queries
        results = self.vector_store.similarity_search(query_embedding, k=1)
        
        # Check if any results were found
        if not results:
            return None
            
        # Get the top result
        top_result = results[0]
        
        # Check similarity threshold
        if top_result["score"] < self.similarity_threshold:
            return None
            
        # Check TTL if set
        if self.ttl is not None:
            timestamp = float(top_result.get("timestamp", 0))
            current_time = time.time()
            
            if current_time - timestamp > self.ttl:
                # Entry expired
                return None
                
        # Return cached response
        return {
            "query": top_result.get("query", ""),
            "response": top_result.get("response", ""),
            "timestamp": float(top_result.get("timestamp", 0)),
            "hash": top_result.get("hash", ""),
            "similarity_score": top_result["score"]
        }
        
    def set(self, query: str, response: str) -> str:
        """
        Set a cached response for a query.
        
        Args:
            query: Query string
            response: Response string
            
        Returns:
            Cache entry ID
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Generate query embedding
        query_embedding = self.embedding_function([query])[0]
        
        # Compute hash
        query_hash = self._compute_hash(query)
        
        # Create metadata
        metadata = {
            "query": query,
            "response": response,
            "timestamp": time.time(),
            "hash": query_hash
        }
        
        # Add to vector store
        ids = self.vector_store.add_texts([query], [query_embedding], [metadata])
        
        return ids[0] if ids else ""
        
    def invalidate(self, query: str) -> bool:
        """
        Invalidate a cached response for a query.
        
        Args:
            query: Query string
            
        Returns:
            True if successful, False otherwise
        """
        if self.embedding_function is None:
            raise ValueError("Embedding function not provided")
            
        # Generate query embedding
        query_embedding = self.embedding_function([query])[0]
        
        # Search for similar queries
        results = self.vector_store.similarity_search(query_embedding, k=1)
        
        # Check if any results were found
        if not results:
            return False
            
        # Get the top result
        top_result = results[0]
        
        # Check similarity threshold
        if top_result["score"] < self.similarity_threshold:
            return False
            
        # Delete the entry
        return self.vector_store.delete([top_result["id"]])
        
    def clear(self) -> bool:
        """
        Clear all cached responses.
        
        Returns:
            True if successful, False otherwise
        """
        return self.vector_store.clear()
        
    def get_or_set(self, query: str, response_fn: Callable[[str], str]) -> Tuple[str, bool]:
        """
        Get a cached response or generate and cache a new one.
        
        Args:
            query: Query string
            response_fn: Function to generate a response if not cached
            
        Returns:
            Tuple of (response, cache_hit)
        """
        # Try to get from cache
        cached = self.get(query)
        
        if cached:
            return cached["response"], True
            
        # Generate new response
        response = response_fn(query)
        
        # Cache the response
        self.set(query, response)
        
        return response, False
