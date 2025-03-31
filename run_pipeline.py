"""
Script to run the entire AvitoScraping and Redis AI pipeline.
"""
import os
import sys
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import components
from setup_redis_db import main as setup_db
from avito_scraping_agent import AvitoScrapingAgent
from import_avito_data import AvitoDataImporter
from utils import EmbeddingProvider
from vector_search.simple_vector_store import SimpleVectorStore

async def run_scraping(categories: List[str] = None, max_vehicles: int = 50) -> str:
    """
    Run the AvitoScraping agent.

    Args:
        categories: List of categories to scrape (None for all)
        max_vehicles: Maximum number of vehicles to scrape per category

    Returns:
        Path to the saved JSON file
    """
    print("\n=== Running AvitoScraping Agent ===")

    # Initialize agent
    agent = AvitoScrapingAgent(use_llm=True)

    # Determine categories to scrape
    if categories is None:
        categories = list(agent.categories.keys())
    else:
        # Filter out invalid categories
        categories = [c for c in categories if c in agent.categories]

    if not categories:
        print("Error: No valid categories to scrape.")
        return None

    # Scrape each category
    all_vehicles = []

    for category in categories:
        print(f"Scraping category: {category}")
        vehicles = await agent.scrape_category(category, max_pages=2, max_vehicles=max_vehicles)
        all_vehicles.extend(vehicles)

        # Random delay between categories
        await asyncio.sleep(5)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scraped_vehicles_{timestamp}.json"

    if all_vehicles:
        agent.save_to_json(all_vehicles, output_file)
        print(f"Saved {len(all_vehicles)} vehicles to {output_file}")
        return output_file
    else:
        print("No vehicles scraped.")
        return None

def import_to_redis(json_file: str) -> bool:
    """
    Import scraped data to Redis.

    Args:
        json_file: Path to the JSON file with scraped data

    Returns:
        True if successful, False otherwise
    """
    print("\n=== Importing Data to Redis ===")

    # Initialize importer
    importer = AvitoDataImporter()

    # Import from JSON file
    if os.path.exists(json_file):
        ids = importer.import_from_json_file(json_file)
        return len(ids) > 0
    else:
        print(f"Error: File not found: {json_file}")
        return False

def test_vector_search() -> bool:
    """
    Test vector search functionality.

    Returns:
        True if successful, False otherwise
    """
    print("\n=== Testing Vector Search ===")

    try:
        # Initialize embedding provider
        embedding_provider = EmbeddingProvider()

        # Initialize vector store
        vehicle_store = SimpleVectorStore(
            index_name="avito_vehicles",
            vector_dimensions=384  # Dimensions for embedding model
        )

        # Test queries
        test_queries = [
            "грузовик для перевозки строительных материалов",
            "седельный тягач для дальних перевозок",
            "малый коммерческий транспорт для доставки"
        ]

        for query in test_queries:
            print(f"\nQuery: {query}")

            # Generate query embedding
            query_embedding = embedding_provider.embed([query])[0]

            # Search vector store
            results = vehicle_store.similarity_search(query_embedding, k=3)

            if results:
                print(f"Found {len(results)} matching vehicles:")
                for i, result in enumerate(results):
                    print(f"  {i+1}. {result.get('title', '')} - Score: {result.get('score', 0):.4f}")
                    print(f"     Price: {result.get('price', '')}")
                    print(f"     URL: {result.get('url', '')}")
            else:
                print("No matching vehicles found.")

        return True
    except Exception as e:
        print(f"Error testing vector search: {e}")
        return False

async def main_async():
    """Async main function."""
    print("AvitoScraping and Redis AI Pipeline")
    print("==================================")

    # Step 1: Set up Redis database structure
    setup_db()

    # Step 2: Run scraping
    json_file = await run_scraping(categories=["trucks", "vans"], max_vehicles=20)

    if not json_file:
        print("Error: Scraping failed. Exiting pipeline.")
        return

    # Step 3: Import data to Redis
    import_success = import_to_redis(json_file)

    if not import_success:
        print("Error: Import to Redis failed.")

    # Step 4: Test vector search
    search_success = test_vector_search()

    if not search_success:
        print("Error: Vector search test failed.")

    print("\nPipeline completed!")

def main():
    """Main function."""
    # Run async main
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
