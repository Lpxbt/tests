"""
Script to import data from AvitoScraping to Redis.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import tools
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore
from utils import EmbeddingProvider

# Import Prisma client (optional)
try:
    from prisma import Prisma
    PRISMA_AVAILABLE = True
except (ImportError, RuntimeError):
    PRISMA_AVAILABLE = False
    print("Warning: Prisma client not available or not generated. Skipping database integration.")

class AvitoDataImporter:
    """
    Class to import data from AvitoScraping to Redis.
    """

    def __init__(self):
        """Initialize the AvitoDataImporter."""
        # Initialize Redis vector store
        self.vehicle_store = SimpleVectorStore(
            index_name="avito_vehicles",
            vector_dimensions=384,  # Dimensions for embedding model
            metadata_fields=[
                "title", "price", "year", "mileage", "engine_type", "engine_power",
                "transmission", "body_type", "condition", "location", "seller_type",
                "url", "image_url", "date_posted", "category", "brand", "model", "vin",
                "custom_field_1", "custom_field_2", "custom_field_3"
            ],
            text_field="description"
        )

        # Initialize embedding provider
        self.embedding_provider = EmbeddingProvider()

        # Initialize Prisma client if available
        self.prisma_client = None
        if PRISMA_AVAILABLE:
            self.prisma_client = Prisma()

    async def connect_to_database(self):
        """Connect to the Prisma database."""
        if not PRISMA_AVAILABLE:
            print("Error: Prisma client not available.")
            return False

        try:
            await self.prisma_client.connect()
            print("Connected to Prisma database")
            return True
        except Exception as e:
            print(f"Error connecting to Prisma database: {e}")
            return False

    async def disconnect_from_database(self):
        """Disconnect from the Prisma database."""
        if self.prisma_client:
            await self.prisma_client.disconnect()
            print("Disconnected from Prisma database")

    async def get_vehicles_from_database(self, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get vehicles from the Prisma database.

        Args:
            limit: Maximum number of vehicles to retrieve
            offset: Offset for pagination

        Returns:
            List of vehicle dictionaries
        """
        if not self.prisma_client:
            print("Error: Prisma client not connected.")
            return []

        try:
            # Replace 'Vehicle' with your actual model name
            # Adjust the query based on your actual schema
            vehicles = await self.prisma_client.vehicle.find_many(
                take=limit,
                skip=offset,
                include={
                    # Include related data if needed
                    # 'images': True,
                    # 'specifications': True,
                }
            )

            print(f"Retrieved {len(vehicles)} vehicles from database")
            return vehicles
        except Exception as e:
            print(f"Error retrieving vehicles from database: {e}")
            return []

    def transform_vehicle_data(self, vehicles: List[Dict[str, Any]]) -> tuple:
        """
        Transform vehicle data from Prisma format to Redis format.

        Args:
            vehicles: List of vehicle dictionaries from Prisma

        Returns:
            Tuple of (texts, metadatas) for Redis
        """
        texts = []
        metadatas = []

        for vehicle in vehicles:
            # Create description text
            # Adjust based on your actual schema
            description = f"{vehicle.get('brand', '')} {vehicle.get('model', '')} {vehicle.get('year', '')} - "
            description += f"{vehicle.get('engineType', '')} {vehicle.get('enginePower', '')} л.с. - "
            description += f"{vehicle.get('transmission', '')} - {vehicle.get('bodyType', '')} - "
            description += f"{vehicle.get('description', '')}"

            # Use the description from the vehicle if available
            if 'description' in vehicle and vehicle['description']:
                description = vehicle['description']

            texts.append(description)

            # Create metadata
            metadata = {
                "title": f"{vehicle.get('brand', '')} {vehicle.get('model', '')}",
                "price": str(vehicle.get('price', '')),
                "year": str(vehicle.get('year', '')),
                "mileage": str(vehicle.get('mileage', '')),
                "engine_type": vehicle.get('engineType', ''),
                "engine_power": str(vehicle.get('enginePower', '')),
                "transmission": vehicle.get('transmission', ''),
                "body_type": vehicle.get('bodyType', ''),
                "condition": vehicle.get('condition', ''),
                "location": vehicle.get('location', ''),
                "seller_type": vehicle.get('sellerType', ''),
                "url": vehicle.get('url', ''),
                "image_url": vehicle.get('imageUrl', ''),
                "date_posted": vehicle.get('datePosted', ''),
                "category": vehicle.get('category', ''),
                "brand": vehicle.get('brand', ''),
                "model": vehicle.get('model', ''),
                "vin": vehicle.get('vin', '')
            }

            # Add any custom fields if needed
            if 'customField1' in vehicle:
                metadata['custom_field_1'] = vehicle['customField1']
            if 'customField2' in vehicle:
                metadata['custom_field_2'] = vehicle['customField2']
            if 'customField3' in vehicle:
                metadata['custom_field_3'] = vehicle['customField3']

            metadatas.append(metadata)

        return texts, metadatas

    def import_vehicles_to_redis(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> List[str]:
        """
        Import vehicles to Redis.

        Args:
            texts: List of vehicle description texts
            metadatas: List of vehicle metadata dictionaries

        Returns:
            List of document IDs
        """
        if not texts or not metadatas:
            print("Error: No data to import.")
            return []

        try:
            # Generate embeddings
            print(f"Generating embeddings for {len(texts)} vehicles...")
            embeddings = self.embedding_provider.embed(texts)

            # Add to vector store
            print(f"Adding {len(texts)} vehicles to Redis...")
            ids = self.vehicle_store.add_texts(texts, embeddings, metadatas)

            print(f"Successfully imported {len(ids)} vehicles to Redis")
            return ids
        except Exception as e:
            print(f"Error importing vehicles to Redis: {e}")
            return []

    def import_from_json_file(self, file_path: str) -> List[str]:
        """
        Import vehicles from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            List of document IDs
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return []

        try:
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                vehicles = json.load(f)

            print(f"Loaded {len(vehicles)} vehicles from {file_path}")

            # Transform data
            texts, metadatas = self.transform_vehicle_data(vehicles)

            # Import to Redis
            return self.import_vehicles_to_redis(texts, metadatas)
        except Exception as e:
            print(f"Error importing from JSON file: {e}")
            return []

    def clear_vehicle_index(self) -> bool:
        """
        Clear the vehicle index in Redis.

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.vehicle_store.clear()
            if result:
                print("Vehicle index cleared successfully")
            else:
                print("Failed to clear vehicle index")
            return result
        except Exception as e:
            print(f"Error clearing vehicle index: {e}")
            return False

async def main_async():
    """Async main function for Prisma integration."""
    print("Importing data from AvitoScraping to Redis")
    print("=========================================")

    # Initialize importer
    importer = AvitoDataImporter()

    # Connect to database
    connected = await importer.connect_to_database()
    if not connected:
        print("Error: Failed to connect to database. Exiting.")
        return

    try:
        # Get vehicles from database
        vehicles = await importer.get_vehicles_from_database(limit=100)

        if not vehicles:
            print("No vehicles found in database. Exiting.")
            return

        # Transform data
        texts, metadatas = importer.transform_vehicle_data(vehicles)

        # Import to Redis
        importer.import_vehicles_to_redis(texts, metadatas)

    finally:
        # Disconnect from database
        await importer.disconnect_from_database()

    print("\nImport completed successfully!")

def main():
    """Main function."""
    print("Importing data from AvitoScraping to Redis")
    print("=========================================")

    # Initialize importer
    importer = AvitoDataImporter()

    # Check if JSON file path is provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Importing from JSON file: {file_path}")
        importer.import_from_json_file(file_path)
    else:
        print("No JSON file path provided.")
        print("To import from a JSON file, run:")
        print(f"python {sys.argv[0]} path/to/vehicles.json")

        if PRISMA_AVAILABLE:
            print("\nAlternatively, you can import directly from the database:")
            print(f"python -c 'import asyncio; from {os.path.basename(__file__)[:-3]} import main_async; asyncio.run(main_async())'")
        else:
            print("\nTo import from the database, install Prisma client:")
            print("pip install prisma")

    print("\nImport completed!")

if __name__ == "__main__":
    main()
