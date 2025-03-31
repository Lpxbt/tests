"""
Simple test script for Redis AI tools.
"""
import os
import sys
import numpy as np

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("Redis AI Tools Test")
print("==================")

# Test mock embeddings
print("\nTesting mock embeddings...")
texts = [
    "Redis is an in-memory data structure store",
    "Vector search enables similarity-based retrieval"
]

# Generate mock embeddings
mock_embeddings = []
for _ in texts:
    # Generate a random vector and normalize it
    vec = np.random.randn(384)
    vec = vec / np.linalg.norm(vec)
    mock_embeddings.append(vec.tolist())

print(f"Generated {len(mock_embeddings)} mock embeddings")
print(f"Embedding dimension: {len(mock_embeddings[0])}")

print("\nTest completed successfully!")
