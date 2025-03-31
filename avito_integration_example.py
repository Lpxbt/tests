"""
Example integration of Redis AI tools with the AvitoScraping project.
"""
import os
import sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Import tools
from utils import EmbeddingProvider, LLMProvider
from vector_search.vector_store import VectorStore
from rag.rag_system import RAGSystem
from semantic_cache.semantic_cache import SemanticCache
from session_manager.session_manager import SessionManager, Session

class AvitoVehicleSearch:
    """
    Example class for integrating Redis AI tools with AvitoScraping project.
    """

    def __init__(self):
        """Initialize the AvitoVehicleSearch."""
        # Initialize providers
        self.embedding_provider = EmbeddingProvider()
        self.llm_provider = LLMProvider()

        # Initialize vector store for vehicle search
        self.vehicle_vector_store = VectorStore(
            index_name="avito_vehicles",
            vector_dimensions=384,  # Dimensions for all-MiniLM-L6-v2
            metadata_fields=["model", "price", "year", "mileage", "engine", "transmission", "url"]
        )

        # Initialize RAG system for vehicle knowledge
        self.vehicle_rag = RAGSystem(
            vector_store=VectorStore(index_name="vehicle_knowledge"),
            embedding_function=self.embedding_provider.embed,
            llm_function=self.llm_provider.generate
        )

        # Initialize semantic cache
        self.cache = SemanticCache(
            embedding_function=self.embedding_provider.embed,
            similarity_threshold=0.85
        )

        # Initialize session manager
        self.session_manager = SessionManager(ttl=86400)  # Sessions expire after 24 hours

    def index_vehicles(self, vehicles: List[Dict[str, Any]]) -> None:
        """
        Index vehicles in the vector store.

        Args:
            vehicles: List of vehicle dictionaries
        """
        # Extract text descriptions and metadata
        texts = []
        metadatas = []

        for vehicle in vehicles:
            # Create text description
            description = f"{vehicle['model']} {vehicle['year']} - {vehicle['engine']} - {vehicle['transmission']} - {vehicle.get('description', '')}"
            texts.append(description)

            # Create metadata
            metadata = {
                "model": vehicle["model"],
                "price": str(vehicle["price"]),
                "year": str(vehicle["year"]),
                "mileage": str(vehicle.get("mileage", "")),
                "engine": vehicle.get("engine", ""),
                "transmission": vehicle.get("transmission", ""),
                "url": vehicle.get("url", "")
            }
            metadatas.append(metadata)

        # Generate embeddings
        embeddings = self.embedding_provider.embed(texts)

        # Add to vector store
        self.vehicle_vector_store.add_texts(texts, embeddings, metadatas)
        print(f"Indexed {len(texts)} vehicles in vector store.")

    def add_vehicle_knowledge(self, knowledge_texts: List[str]) -> None:
        """
        Add vehicle knowledge to the RAG system.

        Args:
            knowledge_texts: List of knowledge text strings
        """
        # Add to RAG system
        self.vehicle_rag.add_texts(knowledge_texts)
        print(f"Added {len(knowledge_texts)} knowledge texts to RAG system.")

    def search_vehicles(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for vehicles based on a query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of vehicle dictionaries
        """
        # Generate query embedding
        query_embedding = self.embedding_provider.embed([query])[0]

        # Search vector store
        results = self.vehicle_vector_store.similarity_search(query_embedding, k=top_k)

        # Format results
        vehicles = []
        for result in results:
            vehicle = {
                "model": result.get("model", ""),
                "price": result.get("price", ""),
                "year": result.get("year", ""),
                "mileage": result.get("mileage", ""),
                "engine": result.get("engine", ""),
                "transmission": result.get("transmission", ""),
                "url": result.get("url", ""),
                "description": result.get("text", ""),
                "score": result.get("score", 0)
            }
            vehicles.append(vehicle)

        return vehicles

    def get_vehicle_info(self, query: str) -> str:
        """
        Get information about vehicles based on a query.

        Args:
            query: Query about vehicles

        Returns:
            Information about vehicles
        """
        # Use semantic cache to avoid redundant LLM calls
        def generate_info(q):
            # Use RAG to generate response
            result = self.vehicle_rag.query(q)
            return result["response"]

        # Get from cache or generate
        response, cache_hit = self.cache.get_or_set(query, generate_info)
        status = "Cache hit" if cache_hit else "Cache miss"
        print(f"Status: {status}")

        return response

    def create_customer_session(self, customer_id: str) -> Session:
        """
        Create a new customer session.

        Args:
            customer_id: Customer ID

        Returns:
            New session
        """
        # Create session with customer metadata
        session = self.session_manager.create_session(metadata={"customer_id": customer_id})

        # Add system message
        self.session_manager.add_system_message(
            session.session_id,
            "Вы Анна, AI-ассистент по продажам компании Business Trucks. "
            "Вы помогаете клиентам найти подходящие коммерческие транспортные средства. "
            "Всегда отвечайте на русском языке."
        )

        return session

    def process_customer_message(self, session_id: str, message: str) -> str:
        """
        Process a customer message and generate a response.

        Args:
            session_id: Session ID
            message: Customer message

        Returns:
            Assistant response
        """
        # Add user message to session
        self.session_manager.add_user_message(session_id, message)

        # Get message history
        history = self.session_manager.get_message_history(session_id)

        # Generate response using LLM
        prompt = self._create_prompt(history)
        response = self.llm_provider.generate(prompt)

        # Add assistant response to session
        self.session_manager.add_assistant_message(session_id, response)

        return response

    def _create_prompt(self, history: List[Dict[str, str]]) -> str:
        """
        Create a prompt from message history.

        Args:
            history: Message history

        Returns:
            Prompt string
        """
        prompt = "Вы Анна, AI-ассистент по продажам компании Business Trucks. Отвечайте на русском языке.\n\n"

        for msg in history:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt += f"Инструкция: {content}\n\n"
            elif role == "user":
                prompt += f"Клиент: {content}\n\n"
            elif role == "assistant":
                prompt += f"Анна: {content}\n\n"

        prompt += "Анна: "

        return prompt


# Example usage
def main():
    """Main function."""
    print("AvitoScraping Integration Example")
    print("================================")

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("OpenAI API key not set. Exiting.")
        return

    # Initialize AvitoVehicleSearch
    avito_search = AvitoVehicleSearch()

    # Example vehicles (in a real scenario, these would come from the AvitoScraping project)
    vehicles = [
        {
            "model": "КАМАЗ 65115",
            "price": 3500000,
            "year": 2018,
            "mileage": 150000,
            "engine": "Дизель, 300 л.с.",
            "transmission": "Механическая",
            "description": "Самосвал КАМАЗ 65115 в хорошем состоянии. Грузоподъемность 15 тонн.",
            "url": "https://www.avito.ru/example/kamaz65115"
        },
        {
            "model": "ГАЗель NEXT",
            "price": 1200000,
            "year": 2020,
            "mileage": 80000,
            "engine": "Дизель, 150 л.с.",
            "transmission": "Механическая",
            "description": "ГАЗель NEXT цельнометаллический фургон. Идеально для малого бизнеса.",
            "url": "https://www.avito.ru/example/gazelnext"
        },
        {
            "model": "MAN TGX",
            "price": 5800000,
            "year": 2019,
            "mileage": 200000,
            "engine": "Дизель, 480 л.с.",
            "transmission": "Автоматическая",
            "description": "Седельный тягач MAN TGX в отличном состоянии. Евро 6.",
            "url": "https://www.avito.ru/example/mantgx"
        },
        {
            "model": "Mercedes-Benz Sprinter",
            "price": 2500000,
            "year": 2021,
            "mileage": 50000,
            "engine": "Дизель, 190 л.с.",
            "transmission": "Автоматическая",
            "description": "Mercedes-Benz Sprinter микроавтобус на 19 мест. Идеально для пассажирских перевозок.",
            "url": "https://www.avito.ru/example/sprinter"
        },
        {
            "model": "Volvo FH",
            "price": 6200000,
            "year": 2020,
            "mileage": 180000,
            "engine": "Дизель, 540 л.с.",
            "transmission": "Автоматическая",
            "description": "Седельный тягач Volvo FH с рефрижератором. Подходит для международных перевозок.",
            "url": "https://www.avito.ru/example/volvofh"
        }
    ]

    # Example vehicle knowledge
    knowledge_texts = [
        "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
        "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях: фургон, бортовой, микроавтобус.",
        "MAN TGX - это седельный тягач премиум-класса, отличается высокой надежностью и экономичностью.",
        "Mercedes-Benz Sprinter - это универсальный микроавтобус, который может использоваться как для пассажирских перевозок, так и в качестве фургона.",
        "Volvo FH - это флагманский седельный тягач Volvo, предназначенный для дальних перевозок.",
        "Дизельные двигатели более экономичны для коммерческого транспорта по сравнению с бензиновыми.",
        "Автоматическая трансмиссия в грузовиках снижает утомляемость водителя при длительных поездках.",
        "Для перевозки строительных материалов лучше всего подходят самосвалы или бортовые грузовики.",
        "Для международных перевозок важно, чтобы грузовик соответствовал экологическому стандарту Евро 6.",
        "Лизинг коммерческого транспорта позволяет снизить первоначальные затраты на приобретение."
    ]

    # Index vehicles
    print("\nIndexing vehicles...")
    avito_search.index_vehicles(vehicles)

    # Add vehicle knowledge
    print("\nAdding vehicle knowledge...")
    avito_search.add_vehicle_knowledge(knowledge_texts)

    # Search for vehicles
    print("\nSearching for vehicles...")
    search_queries = [
        "самосвал для строительства",
        "автомобиль для малого бизнеса",
        "тягач для международных перевозок"
    ]

    for query in search_queries:
        print(f"\nQuery: {query}")
        results = avito_search.search_vehicles(query, top_k=2)

        for i, vehicle in enumerate(results):
            print(f"Result {i+1}:")
            print(f"  Model: {vehicle['model']}")
            print(f"  Price: {vehicle['price']} руб.")
            print(f"  Year: {vehicle['year']}")
            print(f"  Description: {vehicle['description']}")
            print(f"  Score: {vehicle['score']:.4f}")

    # Get vehicle information
    print("\nGetting vehicle information...")
    info_queries = [
        "Какой грузовик лучше для строительных работ?",
        "Что лучше для малого бизнеса - ГАЗель или Sprinter?"
    ]

    for query in info_queries:
        print(f"\nQuery: {query}")
        info = avito_search.get_vehicle_info(query)
        print(f"Response: {info}")

    # Create customer session
    print("\nCreating customer session...")
    session = avito_search.create_customer_session("customer123")
    print(f"Created session: {session.session_id}")

    # Process customer messages
    print("\nProcessing customer messages...")
    messages = [
        "Здравствуйте, я ищу грузовик для перевозки строительных материалов.",
        "Мне нужна грузоподъемность около 15 тонн.",
        "Какие есть варианты с автоматической коробкой передач?"
    ]

    for message in messages:
        print(f"\nCustomer: {message}")
        response = avito_search.process_customer_message(session.session_id, message)
        print(f"Anna: {response}")

    print("\nExample completed.")

if __name__ == "__main__":
    main()
