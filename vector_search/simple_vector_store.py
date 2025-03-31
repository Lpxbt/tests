"""
Simple Vector Store implementation using Redis without RedisVL dependency.
"""
import os
import sys
import uuid
import json
import numpy as np
from typing import List, Dict, Any, Optional, Union

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Redis connection
from redis_connection import get_redis_client

class SimpleVectorStore:
    """
    Simple vector store implementation using Redis without RedisVL dependency.
    """

    def __init__(
        self,
        index_name: str = "default_vector_index",
        vector_field_name: str = "embedding",
        vector_dimensions: int = 768,
        distance_metric: str = "COSINE",
        prefix: str = "doc:",
        metadata_fields: List[str] = None,
        text_field: str = "text"
    ):
        """
        Initialize the vector store.

        Args:
            index_name: Name of the Redis index
            vector_field_name: Name of the vector field
            vector_dimensions: Dimensions of the vector embeddings
            distance_metric: Distance metric for similarity search (COSINE, IP, L2)
            prefix: Prefix for Redis keys
            metadata_fields: List of metadata fields to index
            text_field: Name of the text field
        """
        self.index_name = index_name
        self.vector_field_name = vector_field_name
        self.vector_dimensions = vector_dimensions
        self.distance_metric = distance_metric
        self.prefix = prefix
        self.metadata_fields = metadata_fields or []
        self.text_field = text_field

        # Get Redis client
        self.redis_client = get_redis_client()
        if self.redis_client is None:
            print("Warning: Redis connection failed. Vector search functionality will be limited.")

        # Create index key
        self.index_key = f"index:{self.index_name}"

        # Initialize index
        self._initialize_index()

    def _initialize_index(self) -> None:
        """Initialize the index in Redis."""
        if self.redis_client is None:
            return

        try:
            # Check if index exists
            if not self.redis_client.exists(self.index_key):
                # Create index metadata
                index_metadata = {
                    "name": self.index_name,
                    "prefix": self.prefix,
                    "vector_field": self.vector_field_name,
                    "dimensions": str(self.vector_dimensions),
                    "distance_metric": self.distance_metric,
                    "metadata_fields": json.dumps(self.metadata_fields),
                    "text_field": self.text_field,
                    "created_at": str(uuid.uuid4())
                }

                # Save index metadata
                self.redis_client.hset(self.index_key, mapping=index_metadata)
                print(f"Created vector index '{self.index_name}'")
            else:
                print(f"Using existing vector index '{self.index_name}'")

        except Exception as e:
            print(f"Error initializing index: {e}")

    def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add texts and their embeddings to the vector store.

        Args:
            texts: List of text strings
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs

        Returns:
            List of IDs for the added documents
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot add texts.")
            return []

        if len(texts) != len(embeddings):
            raise ValueError("Number of texts and embeddings must match")

        if metadatas is not None and len(texts) != len(metadatas):
            raise ValueError("Number of texts and metadatas must match")

        # Generate IDs if not provided
        if ids is None:
            ids = [f"{self.prefix}{str(uuid.uuid4())}" for _ in range(len(texts))]
        else:
            # Add prefix if not already present
            ids = [
                f"{self.prefix}{id_}" if not id_.startswith(self.prefix) else id_
                for id_ in ids
            ]

        # Add documents to Redis
        try:
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                # Create document
                doc = {
                    self.text_field: text,
                    self.vector_field_name: json.dumps(embedding)  # Store embedding as JSON string
                }

                # Add metadata if available
                if metadatas is not None:
                    for key, value in metadatas[i].items():
                        if key in self.metadata_fields:
                            doc[key] = value

                # Add document to Redis
                self.redis_client.hset(ids[i], mapping=doc)

                # Add to index
                self.redis_client.sadd(f"{self.index_key}:docs", ids[i])

            return ids
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            return []

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 4,
        filter_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using the query embedding.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_str: Optional filter string (not used in this simple implementation)

        Returns:
            List of documents with their scores and metadata
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot perform search.")
            return []

        try:
            # Get all document IDs in the index
            doc_ids = self.redis_client.smembers(f"{self.index_key}:docs")

            if not doc_ids:
                return []

            # Convert to list of strings
            doc_ids = [doc_id.decode('utf-8') if isinstance(doc_id, bytes) else doc_id for doc_id in doc_ids]

            # Calculate similarity for each document
            results = []

            for doc_id in doc_ids:
                # Get document
                doc = self.redis_client.hgetall(doc_id)

                if not doc:
                    continue

                # Convert bytes to strings
                doc = {k.decode('utf-8') if isinstance(k, bytes) else k:
                       v.decode('utf-8') if isinstance(v, bytes) else v
                       for k, v in doc.items()}

                # Get embedding
                embedding_str = doc.get(self.vector_field_name)
                if not embedding_str:
                    continue

                # Parse embedding
                try:
                    embedding = json.loads(embedding_str)
                except json.JSONDecodeError:
                    continue

                # Calculate similarity
                score = self._calculate_similarity(query_embedding, embedding)

                # Add to results
                result = {
                    "id": doc_id,
                    "text": doc.get(self.text_field, ""),
                    "score": score
                }

                # Add metadata
                for field in self.metadata_fields:
                    if field in doc:
                        result[field] = doc[field]

                results.append(result)

            # Sort by score (descending)
            results.sort(key=lambda x: x["score"], reverse=True)

            # Return top k results
            return results[:k]

        except Exception as e:
            print(f"Error performing similarity search: {e}")
            return []

    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score
        """
        # Convert to numpy arrays
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        # Calculate similarity based on distance metric
        if self.distance_metric == "COSINE":
            # Cosine similarity
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return np.dot(vec1, vec2) / (norm1 * norm2)

        elif self.distance_metric == "IP":
            # Inner product
            return np.dot(vec1, vec2)

        elif self.distance_metric == "L2":
            # Euclidean distance (converted to similarity)
            dist = np.linalg.norm(vec1 - vec2)
            return 1.0 / (1.0 + dist)

        else:
            # Default to cosine similarity
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return np.dot(vec1, vec2) / (norm1 * norm2)

    def delete(self, ids: List[str]) -> bool:
        """
        Delete documents from the vector store.

        Args:
            ids: List of document IDs to delete

        Returns:
            True if successful, False otherwise
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot delete documents.")
            return False

        try:
            # Add prefix if not already present
            ids = [
                f"{self.prefix}{id_}" if not id_.startswith(self.prefix) else id_
                for id_ in ids
            ]

            # Delete documents
            for doc_id in ids:
                # Remove from index
                self.redis_client.srem(f"{self.index_key}:docs", doc_id)

                # Delete document
                self.redis_client.delete(doc_id)

            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all documents from the vector store.

        Returns:
            True if successful, False otherwise
        """
        if self.redis_client is None:
            print("Warning: Redis connection not available. Cannot clear vector store.")
            return False

        try:
            # Get all document IDs in the index
            doc_ids = self.redis_client.smembers(f"{self.index_key}:docs")

            if not doc_ids:
                return True

            # Convert to list of strings
            doc_ids = [doc_id.decode('utf-8') if isinstance(doc_id, bytes) else doc_id for doc_id in doc_ids]

            # Delete all documents
            for doc_id in doc_ids:
                self.redis_client.delete(doc_id)

            # Clear index
            self.redis_client.delete(f"{self.index_key}:docs")

            return True
        except Exception as e:
            print(f"Error clearing vector store: {e}")
            return False
