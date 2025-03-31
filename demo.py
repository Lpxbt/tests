"""
Demo script for Redis AI tools.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Import tools
from redis_connection import get_redis_client
from utils import EmbeddingProvider, LLMProvider
from vector_search.vector_store import VectorStore
from rag.rag_system import RAGSystem
from semantic_cache.semantic_cache import SemanticCache
from session_manager.session_manager import SessionManager

def check_redis_connection():
    """Check if Redis is connected."""
    redis_client = get_redis_client()
    if redis_client is None:
        print("Redis connection failed. Some functionality may be limited.")
        return False
    else:
        print("Redis connection successful.")
        return True

def demo_vector_search():
    """Demo vector search functionality."""
    print("\n=== Vector Search Demo ===")

    # Initialize embedding provider
    embedding_provider = EmbeddingProvider()

    # Initialize vector store
    vector_store = VectorStore(
        index_name="demo_vectors",
        vector_dimensions=384  # Dimensions for all-MiniLM-L6-v2
    )

    # Add texts to vector store
    texts = [
        "Redis is an in-memory data structure store",
        "Vector search enables similarity-based retrieval",
        "AI applications benefit from fast vector operations",
        "Commercial trucks are used for transporting goods",
        "Business Trucks offers a wide range of commercial vehicles"
    ]

    print(f"Adding {len(texts)} texts to vector store...")
    embeddings = embedding_provider.embed(texts)
    ids = vector_store.add_texts(texts, embeddings)

    if ids:
        print(f"Added {len(ids)} texts to vector store.")
    else:
        print("Failed to add texts to vector store.")
        return

    # Search for similar texts
    queries = [
        "How does Redis help with AI?",
        "Tell me about commercial vehicles"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        query_embedding = embedding_provider.embed([query])[0]
        results = vector_store.similarity_search(query_embedding, k=2)

        for i, result in enumerate(results):
            print(f"Result {i+1}: Score: {result['score']:.4f}, Text: {result['text']}")

    # Clean up
    print("\nCleaning up vector store...")
    vector_store.clear()

def demo_rag():
    """Demo RAG functionality."""
    print("\n=== RAG Demo ===")

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("OpenAI API key not set. Skipping RAG demo.")
        return

    # Initialize providers
    embedding_provider = EmbeddingProvider()
    llm_provider = LLMProvider()

    # Initialize RAG system
    rag = RAGSystem(
        embedding_function=embedding_provider.embed,
        llm_function=llm_provider.generate
    )

    # Add texts to the system
    texts = [
        "Business Trucks (BtTrucks) is a Russian company specializing in commercial vehicles.",
        "BtTrucks offers a wide range of trucks, vans, and specialized vehicles for businesses.",
        "The company has a website at btrucks.ru where customers can browse available vehicles.",
        "BtTrucks provides financing options for purchasing commercial vehicles.",
        "The company also offers maintenance and repair services for commercial trucks."
    ]

    print(f"Adding {len(texts)} texts to RAG system...")
    rag.add_texts(texts)

    # Query the RAG system
    query = "What services does Business Trucks offer?"
    print(f"\nQuery: {query}")

    result = rag.query(query)
    print(f"\nResponse: {result['response']}")

    print("\nSource Documents:")
    for doc in result['source_documents']:
        print(f"- {doc.text}")

def demo_semantic_cache():
    """Demo semantic cache functionality."""
    print("\n=== Semantic Cache Demo ===")

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("OpenAI API key not set. Skipping semantic cache demo.")
        return

    # Initialize providers
    embedding_provider = EmbeddingProvider()
    llm_provider = LLMProvider()

    # Initialize semantic cache
    cache = SemanticCache(
        embedding_function=embedding_provider.embed,
        similarity_threshold=0.85
    )

    # Function to generate response (expensive operation)
    def generate_response(query):
        print("Cache miss! Generating new response...")
        return llm_provider.generate(query)

    # Use the cache
    queries = [
        "What is Business Trucks?",
        "Tell me about BtTrucks company",  # Semantically similar to the first query
        "What types of vehicles does Business Trucks sell?"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        response, cache_hit = cache.get_or_set(query, generate_response)
        status = "Cache hit" if cache_hit else "Cache miss"
        print(f"Status: {status}")
        print(f"Response: {response[:100]}...")

    # Clean up
    print("\nCleaning up cache...")
    cache.clear()

def demo_session_manager():
    """Demo session manager functionality."""
    print("\n=== Session Manager Demo ===")

    # Initialize session manager
    session_manager = SessionManager(ttl=3600)  # Sessions expire after 1 hour

    # Create a new session
    session = session_manager.create_session(metadata={"user_id": "customer123"})
    print(f"Created session: {session.session_id}")

    # Add messages to the session
    print("\nAdding messages to session...")
    session_manager.add_system_message(session.session_id, "You are Anna, an AI sales assistant for Business Trucks.")
    session_manager.add_user_message(session.session_id, "Здравствуйте, я ищу грузовик для моего бизнеса.")
    session_manager.add_assistant_message(session.session_id, "Здравствуйте! Я Анна, виртуальный ассистент компании Business Trucks. Какой тип грузовика вас интересует?")

    # Get message history
    history = session_manager.get_message_history(session.session_id)
    print("\nMessage History:")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")

    # Add more messages
    print("\nAdding more messages...")
    session_manager.add_user_message(session.session_id, "Мне нужен грузовик для перевозки строительных материалов.")
    session_manager.add_assistant_message(session.session_id, "Для перевозки строительных материалов у нас есть несколько отличных вариантов. Какая грузоподъемность вам требуется?")

    # Retrieve the session
    retrieved_session = session_manager.get_session(session.session_id)
    print(f"\nRetrieved session: {retrieved_session.session_id}")
    print(f"Number of messages: {len(retrieved_session.messages)}")

    # Get updated message history
    history = session_manager.get_message_history(session.session_id)
    print("\nUpdated Message History:")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")

    # Clean up
    print("\nCleaning up session...")
    session_manager.delete_session(session.session_id)

def main():
    """Main function."""
    print("Redis AI Tools Demo")
    print("==================")

    # Check Redis connection
    redis_connected = check_redis_connection()

    # Run demos that don't require Redis
    print("\nRunning demo in standalone mode (without Redis)")
    print("The tools are designed to work with Redis, but can also function in a limited capacity without it.")
    print("To use the full functionality, please start a Redis server.")

    # Initialize embedding provider
    embedding_provider = EmbeddingProvider()
    print(f"\nInitialized embedding provider with model: {embedding_provider.model_name}")

    # Test embedding generation
    test_texts = [
        "Redis is an in-memory data structure store",
        "Vector search enables similarity-based retrieval"
    ]
    print(f"\nGenerating embeddings for {len(test_texts)} texts...")
    try:
        embeddings = embedding_provider.embed(test_texts)
        print(f"Successfully generated embeddings of dimension {len(embeddings[0])}")
    except Exception as e:
        print(f"Error generating embeddings: {e}")

    print("\nDemo completed.")

if __name__ == "__main__":
    main()
