"""
Vector Search implementation using RedisVL.
"""
import os
import uuid
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np

# Add the parent directory to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Redis connection
from redis_connection import get_redis_client

# Try to import RedisVL
try:
    import redisvl
    from redisvl.index import SearchIndex
    from redisvl.schema import IndexSchema
    from redisvl.query import VectorQuery
    from redisvl.client import Redis
    REDISVL_AVAILABLE = True
    print("Successfully imported RedisVL version:", redisvl.__version__)
except ImportError as e:
    REDISVL_AVAILABLE = False
    print(f"Error importing RedisVL: {e}")



class VectorStore:
    """
    Vector store implementation using RedisVL.
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

        # Check if RedisVL is available
        if not REDISVL_AVAILABLE:
            print("Warning: RedisVL is not installed. Vector search functionality will be limited.")
            self.redis_client = get_redis_client()
            self.index = None
            return

        # Get Redis client
        redis_client = get_redis_client()
        if redis_client is None:
            print("Warning: Redis connection failed. Vector search functionality will be limited.")
            self.redis_client = None
            self.index = None
            return

        self.redis_client = Redis(client=redis_client)

        # Create schema and index
        self._create_index()

    def _create_index(self) -> None:
        """Create the vector search index if it doesn't exist."""
        if not REDISVL_AVAILABLE or self.redis_client is None:
            return

        try:
            # Define schema
            schema_fields = {
                self.vector_field_name: {
                    "type": "VECTOR",
                    "dims": self.vector_dimensions,
                    "distance_metric": self.distance_metric,
                    "algorithm": "HNSW",
                    "attributes": {
                        "TYPE": "FLOAT32",
                        "M": 16,
                        "EF_CONSTRUCTION": 200,
                        "EF_RUNTIME": 10
                    }
                },
                self.text_field: {
                    "type": "TEXT"
                }
            }

            # Add metadata fields
            for field in self.metadata_fields:
                schema_fields[field] = {"type": "TEXT"}

            # Create schema
            schema = IndexSchema(
                index_name=self.index_name,
                prefix=[self.prefix],
                schema=schema_fields
            )

            # Create index
            self.index = SearchIndex(self.redis_client, schema)

            # Check if index exists, create if not
            if not self.index.exists():
                self.index.create()
                print(f"Created vector index '{self.index_name}'")
            else:
                print(f"Using existing vector index '{self.index_name}'")

        except Exception as e:
            print(f"Error creating vector index: {e}")
            self.index = None

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
        if not REDISVL_AVAILABLE or self.redis_client is None or self.index is None:
            print("Warning: RedisVL or Redis connection not available. Cannot add texts.")
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

        # Prepare documents
        documents = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc = {
                self.text_field: text,
                self.vector_field_name: embedding
            }

            # Add metadata if available
            if metadatas is not None:
                for key, value in metadatas[i].items():
                    if key in self.metadata_fields:
                        doc[key] = value

            documents.append((ids[i], doc))

        # Add documents to index
        try:
            for doc_id, doc in documents:
                self.redis_client.hset(doc_id, mapping=doc)
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
            filter_str: Optional filter string

        Returns:
            List of documents with their scores and metadata
        """
        if not REDISVL_AVAILABLE or self.redis_client is None or self.index is None:
            print("Warning: RedisVL or Redis connection not available. Cannot perform search.")
            return []

        try:
            # Create vector query
            query = VectorQuery(
                vector=query_embedding,
                vector_field_name=self.vector_field_name,
                return_fields=[self.text_field] + self.metadata_fields,
                num_results=k
            )

            # Add filter if provided
            if filter_str:
                query.filter_expression = filter_str

            # Execute search
            results = self.index.query(query)

            # Format results
            documents = []
            for result in results.docs:
                doc = {
                    "id": result.id,
                    "text": result.get(self.text_field, ""),
                    "score": result.score,
                }

                # Add metadata
                for field in self.metadata_fields:
                    if field in result:
                        doc[field] = result[field]

                documents.append(doc)

            return documents

        except Exception as e:
            print(f"Error performing similarity search: {e}")
            return []

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
            # Get all keys with prefix
            keys = self.redis_client.keys(f"{self.prefix}*")

            # Delete all keys
            if keys:
                self.redis_client.delete(*keys)

            return True
        except Exception as e:
            print(f"Error clearing vector store: {e}")
            return False
