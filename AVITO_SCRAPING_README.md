# AvitoScraping Integration with Redis AI Tools

This guide explains how to set up and run the AvitoScraping integration with Redis AI tools.

## Overview

The integration consists of several components:

1. **Redis Database Setup**: Creates the necessary Redis indexes for storing vehicle data, knowledge, and cache.
2. **AvitoScraping Agent**: Intelligent scraper for Avito.ru commercial vehicles.
3. **Data Import Tool**: Imports scraped data into Redis vector store.
4. **Vector Search**: Enables semantic search for vehicles based on natural language queries.
5. **Pipeline Runner**: Orchestrates the entire process from scraping to search.

## Prerequisites

- Redis Cloud account (already configured)
- Python 3.7+ with virtual environment
- Required Python packages (listed in requirements.txt)

## Setup

1. Install the required dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. Set up the Redis database structure:
   ```bash
   python setup_redis_db.py
   ```
   This will create the necessary indexes in Redis and add sample data for testing.

## Running the Scraper

### Option 1: Run the Full Pipeline

To run the entire pipeline (scraping, importing, and testing):

```bash
python run_pipeline.py
```

This will:
1. Set up the Redis database structure
2. Scrape vehicles from Avito.ru
3. Import the scraped data to Redis
4. Test the vector search functionality

### Option 2: Run Components Individually

#### Scraping Only

To run just the scraping component:

```bash
python avito_scraping_agent.py
```

This will scrape a limited number of vehicles and save them to JSON and CSV files.

#### Import Only

To import data from a JSON file to Redis:

```bash
python import_avito_data.py path/to/vehicles.json
```

## Customizing the Scraper

The AvitoScraping agent can be customized in several ways:

### Categories

The agent is configured to scrape the following categories:
- trucks: Грузовики
- tractors: Тракторы
- buses: Автобусы
- vans: Легкие грузовики до 3.5 тонн
- construction: Строительная техника
- agricultural: Сельхозтехника
- trailers: Прицепы

You can modify the categories in `avito_scraping_agent.py`.

### Target Brands

The agent focuses on specific brands:
- Russian: КАМАЗ, ГАЗ, МАЗ, Урал, ЗИЛ
- European: MAN, Volvo, Scania, Mercedes-Benz, DAF, Iveco, Renault
- Asian: Hyundai, Isuzu

You can modify the target brands in `avito_scraping_agent.py`.

### LLM Enhancement

The agent uses an LLM to enhance the scraped data by:
- Extracting additional parameters from descriptions
- Normalizing data formats
- Categorizing vehicles

This feature can be disabled by setting `use_llm=False` when initializing the agent.

## Vector Search

Once data is imported into Redis, you can search for vehicles using natural language queries:

```python
from utils import EmbeddingProvider
from vector_search.vector_store import VectorStore

# Initialize embedding provider
embedding_provider = EmbeddingProvider()

# Initialize vector store
vehicle_store = VectorStore(index_name="avito_vehicles")

# Search for vehicles
query = "грузовик для перевозки строительных материалов"
query_embedding = embedding_provider.embed([query])[0]
results = vehicle_store.similarity_search(query_embedding, k=5)

# Display results
for result in results:
    print(f"{result.get('title')} - {result.get('price')}")
    print(f"Score: {result.get('score')}")
    print(f"URL: {result.get('url')}")
    print()
```

## Scheduled Scraping

To set up scheduled scraping, you can use the `schedule` library:

```python
import schedule
import time
import subprocess

def run_pipeline():
    subprocess.run(["python", "run_pipeline.py"])

# Schedule to run daily at 2 AM
schedule.every().day.at("02:00").do(run_pipeline)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Save this as `schedule_scraping.py` and run it in the background.

## Troubleshooting

### Rate Limiting

If you encounter rate limiting from Avito.ru, try:
- Reducing the scraping speed by increasing delays
- Using proxies (implement the `get_random_proxy` method)
- Reducing the number of pages scraped per category

### Redis Connection Issues

If you have issues connecting to Redis:
- Check that the Redis URL in `.env` is correct
- Ensure your IP is whitelisted in Redis Cloud
- Try connecting with the Redis CLI to verify access

### LLM Issues

If the LLM enhancement is not working:
- Check that the OpenRouter API key is correct
- Verify the model name is correct
- Try disabling LLM enhancement to see if basic scraping works

## Next Steps

1. **Improve Scraper Robustness**: Add more error handling and retry logic
2. **Add Proxy Support**: Implement rotation of proxies to avoid rate limiting
3. **Enhance Data Schema**: Add more fields and metadata for better search
4. **Implement Differential Updates**: Only scrape and update new or changed listings
5. **Add Monitoring**: Set up alerts for scraping failures or data issues
