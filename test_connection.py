"""
Test script for Redis connection and OpenRouter integration.
"""
import os
import sys
import time

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import tools
from redis_connection import get_redis_client
from utils import EmbeddingProvider, LLMProvider

def test_redis_connection():
    """Test Redis connection."""
    print("\n=== Testing Redis Connection ===")
    redis_client = get_redis_client()
    
    if redis_client is None:
        print("Redis connection failed.")
        return False
    
    # Test basic Redis operations
    try:
        # Set a test key
        test_key = "test:connection:" + str(int(time.time()))
        redis_client.set(test_key, "Connection successful!")
        
        # Get the test key
        value = redis_client.get(test_key)
        print(f"Retrieved value: {value.decode() if value else None}")
        
        # Delete the test key
        redis_client.delete(test_key)
        
        print("Redis connection and basic operations successful!")
        return True
    except Exception as e:
        print(f"Error testing Redis operations: {e}")
        return False

def test_openrouter():
    """Test OpenRouter integration."""
    print("\n=== Testing OpenRouter Integration ===")
    
    # Initialize LLM provider
    llm_provider = LLMProvider()
    
    # Check if using OpenRouter
    if llm_provider.use_openrouter:
        print(f"Using OpenRouter with model: {llm_provider.model_name}")
    else:
        print(f"Using OpenAI with model: {llm_provider.model_name}")
    
    # Test generation
    try:
        prompt = "Привет! Расскажи мне о грузовиках КАМАЗ в двух предложениях."
        print(f"Prompt: {prompt}")
        
        response = llm_provider.generate(prompt, max_tokens=100)
        print(f"Response: {response}")
        
        return True
    except Exception as e:
        print(f"Error testing LLM generation: {e}")
        return False

def main():
    """Main function."""
    print("Redis AI Tools Connection Test")
    print("=============================")
    
    # Test Redis connection
    redis_success = test_redis_connection()
    
    # Test OpenRouter integration
    openrouter_success = test_openrouter()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Redis Connection: {'SUCCESS' if redis_success else 'FAILED'}")
    print(f"OpenRouter Integration: {'SUCCESS' if openrouter_success else 'FAILED'}")
    
    if redis_success and openrouter_success:
        print("\nAll tests passed! The system is ready for integration.")
    else:
        print("\nSome tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
