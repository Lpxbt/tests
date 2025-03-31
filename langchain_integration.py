"""
LangChain integration for Redis AI tools.
"""
import os
import sys
import json
from typing import List, Dict, Any, Optional, Union

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis tools
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore
from utils import EmbeddingProvider, LLMProvider

# Try to import LangChain
try:
    # Import from langchain core
    from langchain_core.embeddings import Embeddings
    from langchain_core.documents import Document
    from langchain_core.prompts import PromptTemplate
    from langchain_core.language_models import BaseLLM
    from langchain_core.callbacks import CallbackManagerForLLMRun

    # Import from langchain community
    from langchain_community.vectorstores import Redis
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.llms import OpenAI

    # Import from langchain
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain is not installed. Install with 'pip install langchain'")

class CustomEmbeddings(Embeddings):
    """
    Custom embeddings class for LangChain that uses our EmbeddingProvider.
    """

    def __init__(self):
        """Initialize the custom embeddings."""
        self.embedding_provider = EmbeddingProvider()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed documents using our EmbeddingProvider.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return self.embedding_provider.embed(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a query using our EmbeddingProvider.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        return self.embedding_provider.embed([text])[0]

class CustomLLM(BaseLLM):
    """
    Custom LLM class for LangChain that uses our LLMProvider.
    """

    def __init__(self):
        """Initialize the custom LLM."""
        super().__init__()
        self.llm_provider = LLMProvider()

    @property
    def _llm_type(self) -> str:
        """Return the LLM type."""
        return "custom_llm"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """
        Call the LLM with the given prompt.

        Args:
            prompt: Prompt to send to the LLM
            stop: Optional list of stop sequences
            run_manager: Optional callback manager

        Returns:
            Generated text
        """
        return self.llm_provider.generate(prompt)

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> List[str]:
        """
        Generate text for multiple prompts.

        Args:
            prompts: List of prompts to send to the LLM
            stop: Optional list of stop sequences
            run_manager: Optional callback manager

        Returns:
            List of generated texts
        """
        return [self._call(prompt, stop, run_manager, **kwargs) for prompt in prompts]

class LangChainRAG:
    """
    RAG system implementation using LangChain.
    """

    def __init__(
        self,
        index_name: str = "vehicle_knowledge",
        redis_url: Optional[str] = None
    ):
        """
        Initialize the LangChain RAG system.

        Args:
            index_name: Name of the Redis index
            redis_url: Redis URL (if None, uses the default from environment)
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed. Install with 'pip install langchain'")

        # Initialize embeddings
        self.embeddings = CustomEmbeddings()

        # Initialize LLM
        self.llm = CustomLLM()

        # Get Redis URL
        if redis_url is None:
            redis_client = get_redis_client()
            if redis_client is None:
                raise ValueError("Redis connection failed")
            redis_url = os.getenv("REDIS_URL")

        # Initialize Redis vector store
        self.redis_url = redis_url
        self.index_name = index_name

        # Create Redis vector store
        self.vector_store = Redis.from_existing_index(
            embedding=self.embeddings,
            redis_url=self.redis_url,
            index_name=self.index_name,
            schema="redis_schema"  # This is a placeholder, adjust as needed
        )

        # Create QA chain
        self.qa_chain = self._create_qa_chain()

        # Create conversational chain
        self.conversational_chain = self._create_conversational_chain()

    def _create_qa_chain(self) -> RetrievalQA:
        """
        Create a QA chain.

        Returns:
            RetrievalQA chain
        """
        # Create prompt template
        template = """Используйте следующую информацию для ответа на вопрос пользователя.
        Если вы не знаете ответа, просто скажите, что не знаете, не пытайтесь придумать ответ.

        Контекст:
        {context}

        Вопрос: {question}

        Ответ:"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Create QA chain
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(),
            chain_type_kwargs={"prompt": prompt}
        )

    def _create_conversational_chain(self) -> ConversationalRetrievalChain:
        """
        Create a conversational chain.

        Returns:
            ConversationalRetrievalChain
        """
        # Create memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Create conversational chain
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(),
            memory=memory
        )

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of LangChain Document objects
        """
        self.vector_store.add_documents(documents)

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Add texts to the vector store.

        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dictionaries
        """
        documents = []

        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            documents.append(Document(page_content=text, metadata=metadata))

        self.add_documents(documents)

    def process_file(self, file_path: str) -> None:
        """
        Process a file and add it to the vector store.

        Args:
            file_path: Path to the file
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        # Split text
        chunks = text_splitter.split_text(text)

        # Create metadata
        metadatas = [{"source": file_path} for _ in chunks]

        # Add to vector store
        self.add_texts(chunks, metadatas)

    def query(self, query: str) -> str:
        """
        Query the RAG system.

        Args:
            query: Query string

        Returns:
            Generated response
        """
        return self.qa_chain.run(query)

    def chat(self, query: str) -> str:
        """
        Chat with the RAG system.

        Args:
            query: Query string

        Returns:
            Generated response
        """
        return self.conversational_chain({"question": query})["answer"]

class LangChainAgent:
    """
    Agent implementation using LangChain.
    """

    def __init__(self):
        """Initialize the LangChain agent."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed. Install with 'pip install langchain'")

        # Initialize components
        self.embeddings = CustomEmbeddings()
        self.llm = CustomLLM()

        # Initialize tools
        self.tools = []

        # TODO: Implement agent tools

    def add_tool(self, tool: Any) -> None:
        """
        Add a tool to the agent.

        Args:
            tool: LangChain tool
        """
        self.tools.append(tool)

    def run(self, query: str) -> str:
        """
        Run the agent.

        Args:
            query: Query string

        Returns:
            Generated response
        """
        # TODO: Implement agent execution
        return "Agent execution not implemented yet"

def main():
    """Main function."""
    if not LANGCHAIN_AVAILABLE:
        print("LangChain is not installed. Install with 'pip install langchain'")
        return

    # Initialize RAG system
    rag = LangChainRAG()

    # Add sample texts
    texts = [
        "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
        "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях: фургон, бортовой, микроавтобус.",
        "MAN TGX - это седельный тягач премиум-класса, отличается высокой надежностью и экономичностью.",
        "Mercedes-Benz Sprinter - это универсальный микроавтобус, который может использоваться как для пассажирских перевозок, так и в качестве фургона.",
        "Volvo FH - это флагманский седельный тягач Volvo, предназначенный для дальних перевозок."
    ]

    rag.add_texts(texts)

    # Query the RAG system
    query = "Какой грузовик лучше для строительных работ?"
    response = rag.query(query)

    print(f"Query: {query}")
    print(f"Response: {response}")

if __name__ == "__main__":
    main()
