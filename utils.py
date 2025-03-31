"""
Utility functions for Redis AI tools.
"""
import os
from typing import List, Dict, Any, Optional, Union
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class EmbeddingProvider:
    """
    Embedding provider for generating text embeddings.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding provider.

        Args:
            model_name: Name of the embedding model
        """
        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL
        self.model = None

        # Initialize model
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("Warning: sentence-transformers is not installed. Embedding functionality will be limited.")
            return

        try:
            # For demo purposes, we'll use a mock embedding function if the model can't be loaded
            try:
                self.model = SentenceTransformer(self.model_name)
                print(f"Initialized embedding model: {self.model_name}")
            except Exception as e:
                print(f"Error initializing embedding model: {e}")
                print("Using mock embedding function for demonstration purposes.")
                self.model = None
        except Exception as e:
            print(f"Error in _initialize_model: {e}")
            self.model = None

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self.model is None:
            print("Warning: Using mock embeddings for demonstration purposes.")
            # Generate mock embeddings of dimension 384 (same as all-MiniLM-L6-v2)
            import numpy as np
            mock_embeddings = []
            for _ in texts:
                # Generate a random vector and normalize it
                vec = np.random.randn(384)
                vec = vec / np.linalg.norm(vec)
                mock_embeddings.append(vec.tolist())
            return mock_embeddings

        # Generate embeddings
        embeddings = self.model.encode(texts)

        # Convert to list of lists
        return embeddings.tolist()


class LLMProvider:
    """
    LLM provider for generating text using OpenAI or OpenRouter.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the LLM provider.

        Args:
            model_name: Name of the LLM model
        """
        self.use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() == "true"

        # Set default model based on provider
        if self.use_openrouter:
            # Use the correct Gemini model from OpenRouter
            self.model_name = model_name or "google/gemini-2.5-pro-exp-03-25:free"
            self.api_base = "https://openrouter.ai/api/v1"
        else:
            self.model_name = model_name or "gpt-3.5-turbo"
            self.api_base = None

        # Initialize OpenAI
        if OPENAI_AVAILABLE:
            if self.use_openrouter:
                openai.api_key = os.getenv("OPENROUTER_API_KEY")
                openai.api_base = self.api_base
            else:
                openai.api_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Prompt string
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation

        Returns:
            Generated text
        """
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI is not installed")

        # Check for appropriate API key
        if self.use_openrouter and not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError("OpenRouter API key not set")
        elif not self.use_openrouter and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key not set")

        try:
            # Set up headers for OpenRouter if needed
            headers = None
            if self.use_openrouter:
                headers = {
                    "HTTP-Referer": "https://btrucks.ru",  # Optional, for including your app on openrouter.ai rankings
                    "X-Title": "Anna AI Sales Agent"  # Optional, for including your app on openrouter.ai rankings
                }

            # Generate text using the new OpenAI client API (v1.0+)
            client = openai.OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY") if self.use_openrouter else os.getenv("OPENAI_API_KEY"),
                base_url=self.api_base if self.use_openrouter else openai.api_base,
                default_headers=headers if self.use_openrouter else None
            )

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract generated text from the new API response format
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating text: {e}")
            # For demo purposes, return a mock response if generation fails
            return f"[Mock response for: {prompt[:50]}...]"
