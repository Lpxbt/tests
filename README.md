# Redis AI Tools with Real-Time Dashboard

A comprehensive suite of AI tools powered by Redis for enhancing AI applications with vector search, RAG, semantic caching, and session management. Features a real-time Streamlit dashboard for monitoring and control.

## Features

- **Real-Time Dashboard**: Monitor and control your AI system with a Streamlit dashboard
- **Vector Search**: Fast similarity search using Redis as a vector database
- **RAG System**: Enhance LLM responses with relevant context
- **Semantic Cache**: Cache LLM responses based on semantic similarity
- **Session Manager**: Maintain conversation context for LLM applications
- **AvitoScraping Integration**: Scrape and analyze vehicle data from Avito.ru
- **LangChain Integration**: Enhanced RAG capabilities with LangChain
- **Redis Pub/Sub**: Real-time updates and notifications

## Dashboard

The Streamlit dashboard provides:

- **Dashboard Overview**: Real-time metrics and system status
- **Vehicle Search**: Search for vehicles using natural language
- **Data Overview**: View and filter vehicle data
- **Scraper Control**: Control the AvitoScraping agent
- **Agent Chat**: Chat with the AI agent
- **Implementation Documentation**: Documentation of the implementation

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/redis-ai-tools.git
   cd redis-ai-tools
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Redis and OpenRouter credentials:
   ```
   REDIS_URL=redis://username:password@host:port
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

## Usage

### Running the Dashboard

```bash
streamlit run dashboard.py
```

### Using the RAG System

```python
from simple_rag import SimpleRAG

# Initialize RAG system
rag = SimpleRAG()

# Add texts
texts = [
    "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
    "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях."
]
rag.add_texts(texts)

# Query the RAG system
result = rag.query("Какой грузовик лучше для строительных работ?")
print(result["response"])
```

### Using the Playwright Scraper

```python
from avito_playwright_scraper import AvitoPlaywrightScraper
import asyncio

async def main():
    # Initialize scraper
    scraper = AvitoPlaywrightScraper(use_llm=True)
    
    # Scrape a category
    vehicles = await scraper.scrape_category("trucks", max_pages=1, max_vehicles=3)
    
    # Save results
    scraper.save_to_json(vehicles, "scraped_vehicles.json")
    scraper.save_to_csv(vehicles, "scraped_vehicles.csv")

# Run the scraper
asyncio.run(main())
```

## Deployment

### Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Deploy the app

### Docker

```bash
docker build -t redis-ai-dashboard .
docker run -p 8501:8501 redis-ai-dashboard
```

### VPS with PM2

```bash
# Install PM2
npm install pm2 -g

# Start the app with PM2
pm2 start --name redis-dashboard -- streamlit run dashboard.py --server.port=80 --server.address=0.0.0.0
pm2 save
pm2 startup
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
