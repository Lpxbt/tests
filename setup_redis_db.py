"""
Script to set up Redis database structure for AvitoScraping integration.
"""
import os
import sys
import json
from typing import Dict, Any, List, Optional

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import Redis connection
import redis_connection
import vector_search.simple_vector_store

# Get Redis client and VectorStore class
get_redis_client = redis_connection.get_redis_client
VectorStore = vector_search.simple_vector_store.SimpleVectorStore

def setup_vehicle_index() -> Optional[VectorStore]:
    """
    Set up the Redis index for vehicle data.

    Returns:
        VectorStore instance if successful, None otherwise
    """
    print("Setting up vehicle index in Redis...")

    try:
        # Initialize vector store with specific schema for vehicles
        vehicle_store = VectorStore(
            index_name="avito_vehicles",
            vector_field_name="embedding",
            vector_dimensions=384,  # Dimensions for embedding model
            distance_metric="COSINE",
            prefix="vehicle:",
            metadata_fields=[
                "title",           # Vehicle title/name
                "price",           # Price in rubles
                "year",            # Manufacturing year
                "mileage",         # Mileage in km
                "engine_type",     # Engine type (diesel, gasoline, etc.)
                "engine_power",    # Engine power in HP
                "transmission",    # Transmission type
                "body_type",       # Body type (sedan, truck, etc.)
                "condition",       # Vehicle condition
                "location",        # Location (city)
                "seller_type",     # Private or dealer
                "url",             # Avito URL
                "image_url",       # Main image URL
                "date_posted",     # Date posted on Avito
                "category",        # Vehicle category
                "brand",           # Vehicle brand
                "model",           # Vehicle model
                "vin",             # VIN number if available
                "custom_field_1",  # Additional custom fields
                "custom_field_2",
                "custom_field_3"
            ],
            text_field="description"  # Full vehicle description
        )

        print(f"Successfully created vehicle index 'avito_vehicles'")
        return vehicle_store

    except Exception as e:
        print(f"Error setting up vehicle index: {e}")
        return None

def setup_knowledge_index() -> Optional[VectorStore]:
    """
    Set up the Redis index for vehicle knowledge.

    Returns:
        VectorStore instance if successful, None otherwise
    """
    print("Setting up knowledge index in Redis...")

    try:
        # Initialize vector store for vehicle knowledge
        knowledge_store = VectorStore(
            index_name="vehicle_knowledge",
            vector_field_name="embedding",
            vector_dimensions=384,  # Dimensions for embedding model
            distance_metric="COSINE",
            prefix="knowledge:",
            metadata_fields=[
                "topic",           # Knowledge topic
                "vehicle_type",    # Type of vehicle this knowledge applies to
                "brand",           # Brand this knowledge applies to
                "source",          # Source of information
                "last_updated",    # When this knowledge was last updated
                "confidence",      # Confidence score (1-10)
                "category"         # Knowledge category
            ],
            text_field="content"  # Knowledge content
        )

        print(f"Successfully created knowledge index 'vehicle_knowledge'")
        return knowledge_store

    except Exception as e:
        print(f"Error setting up knowledge index: {e}")
        return None

def setup_cache_index() -> Optional[VectorStore]:
    """
    Set up the Redis index for semantic cache.

    Returns:
        VectorStore instance if successful, None otherwise
    """
    print("Setting up semantic cache index in Redis...")

    try:
        # Initialize vector store for semantic cache
        cache_store = VectorStore(
            index_name="semantic_cache",
            vector_field_name="embedding",
            vector_dimensions=384,  # Dimensions for embedding model
            distance_metric="COSINE",
            prefix="cache:",
            metadata_fields=[
                "query",           # Original query
                "response",        # Cached response
                "timestamp",       # When this cache entry was created
                "hash",            # Hash of the query
                "ttl"              # Time-to-live in seconds
            ],
            text_field="query"  # Query text
        )

        print(f"Successfully created cache index 'semantic_cache'")
        return cache_store

    except Exception as e:
        print(f"Error setting up cache index: {e}")
        return None

def add_sample_vehicle_data(vehicle_store: VectorStore) -> bool:
    """
    Add sample vehicle data to test the index.

    Args:
        vehicle_store: VectorStore instance

    Returns:
        True if successful, False otherwise
    """
    print("Adding sample vehicle data...")

    # Sample vehicle data
    sample_vehicles = [
        {
            "title": "КАМАЗ 65115 Самосвал",
            "price": "3500000",
            "year": "2018",
            "mileage": "150000",
            "engine_type": "Дизель",
            "engine_power": "300",
            "transmission": "Механическая",
            "body_type": "Самосвал",
            "condition": "Хорошее",
            "location": "Москва",
            "seller_type": "Дилер",
            "url": "https://www.avito.ru/example/kamaz65115",
            "image_url": "https://example.com/image1.jpg",
            "date_posted": "2023-05-15",
            "category": "Грузовики",
            "brand": "КАМАЗ",
            "model": "65115",
            "description": "Самосвал КАМАЗ 65115 в хорошем состоянии. Грузоподъемность 15 тонн. Двигатель Cummins 300 л.с. Пробег 150000 км. Один владелец."
        },
        {
            "title": "ГАЗель NEXT Цельнометаллический фургон",
            "price": "1200000",
            "year": "2020",
            "mileage": "80000",
            "engine_type": "Дизель",
            "engine_power": "150",
            "transmission": "Механическая",
            "body_type": "Фургон",
            "condition": "Отличное",
            "location": "Санкт-Петербург",
            "seller_type": "Дилер",
            "url": "https://www.avito.ru/example/gazelnext",
            "image_url": "https://example.com/image2.jpg",
            "date_posted": "2023-06-20",
            "category": "Малый коммерческий транспорт",
            "brand": "ГАЗ",
            "model": "ГАЗель NEXT",
            "description": "ГАЗель NEXT цельнометаллический фургон. Идеально для малого бизнеса. Дизельный двигатель 150 л.с. Пробег 80000 км. Грузоподъемность 1.5 тонны."
        }
    ]

    try:
        # Generate mock embeddings (in a real scenario, these would be generated by an embedding model)
        import numpy as np
        mock_embeddings = []
        for _ in range(len(sample_vehicles)):
            vec = np.random.randn(384)
            vec = vec / np.linalg.norm(vec)
            mock_embeddings.append(vec.tolist())

        # Extract texts and metadata
        texts = [vehicle["description"] for vehicle in sample_vehicles]
        metadatas = []

        for vehicle in sample_vehicles:
            # Create a copy without the description field
            metadata = vehicle.copy()
            metadata.pop("description", None)
            metadatas.append(metadata)

        # Add to vector store
        ids = vehicle_store.add_texts(texts, mock_embeddings, metadatas)

        print(f"Added {len(ids)} sample vehicles to the index")
        return True

    except Exception as e:
        print(f"Error adding sample vehicle data: {e}")
        return False

def add_sample_knowledge_data(knowledge_store: VectorStore) -> bool:
    """
    Add sample knowledge data to test the index.

    Args:
        knowledge_store: VectorStore instance

    Returns:
        True if successful, False otherwise
    """
    print("Adding sample knowledge data...")

    # Sample knowledge data
    sample_knowledge = [
        {
            "topic": "КАМАЗ 65115",
            "vehicle_type": "Самосвал",
            "brand": "КАМАЗ",
            "source": "Официальный сайт КАМАЗ",
            "last_updated": "2023-01-15",
            "confidence": "9",
            "category": "Технические характеристики",
            "content": "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ. Оснащается дизельным двигателем мощностью от 240 до 300 л.с. Объем кузова составляет 10 кубических метров. Максимальная скорость - 90 км/ч."
        },
        {
            "topic": "ГАЗель NEXT",
            "vehicle_type": "Фургон",
            "brand": "ГАЗ",
            "source": "Официальный сайт ГАЗ",
            "last_updated": "2023-02-20",
            "confidence": "8",
            "category": "Общая информация",
            "content": "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях: фургон, бортовой, микроавтобус. Грузоподъемность до 2.5 тонн. Доступны версии с дизельным, бензиновым или газовым двигателем. Идеально подходит для малого и среднего бизнеса."
        }
    ]

    try:
        # Generate mock embeddings
        import numpy as np
        mock_embeddings = []
        for _ in range(len(sample_knowledge)):
            vec = np.random.randn(384)
            vec = vec / np.linalg.norm(vec)
            mock_embeddings.append(vec.tolist())

        # Extract texts and metadata
        texts = [item["content"] for item in sample_knowledge]
        metadatas = []

        for item in sample_knowledge:
            # Create a copy without the content field
            metadata = item.copy()
            metadata.pop("content", None)
            metadatas.append(metadata)

        # Add to vector store
        ids = knowledge_store.add_texts(texts, mock_embeddings, metadatas)

        print(f"Added {len(ids)} sample knowledge items to the index")
        return True

    except Exception as e:
        print(f"Error adding sample knowledge data: {e}")
        return False

def main():
    """Main function."""
    print("Setting up Redis database structure for AvitoScraping integration")
    print("===============================================================")

    # Check Redis connection
    redis_client = get_redis_client()
    if redis_client is None:
        print("Error: Redis connection failed. Cannot set up database structure.")
        return

    # Set up vehicle index
    vehicle_store = setup_vehicle_index()
    if vehicle_store is None:
        print("Error: Failed to set up vehicle index.")
        return

    # Set up knowledge index
    knowledge_store = setup_knowledge_index()
    if knowledge_store is None:
        print("Error: Failed to set up knowledge index.")
        return

    # Set up cache index
    cache_store = setup_cache_index()
    if cache_store is None:
        print("Error: Failed to set up cache index.")
        return

    # Add sample data
    add_sample_vehicle_data(vehicle_store)
    add_sample_knowledge_data(knowledge_store)

    print("\nRedis database structure set up successfully!")
    print("You can now import your AvitoScraping data into Redis.")

if __name__ == "__main__":
    main()
