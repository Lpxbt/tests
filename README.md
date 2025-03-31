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

4. Set up Redis credentials:

   **Option 1: Using .env file (for local development)**
   Create a `.env` file with your Redis and OpenRouter credentials:
   ```
   REDIS_URL=redis://username:password@host:port
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

   **Option 2: Using Streamlit secrets (for Streamlit Cloud deployment)**
   Create a `.streamlit/secrets.toml` file with your Redis and OpenRouter credentials:
   ```toml
   [redis]
   url = "redis://username:password@host:port"

   [openrouter]
   api_key = "your-openrouter-api-key"
   ```

5. Set up Redis Cloud (recommended):
   - Sign up for a free Redis Cloud account at https://redis.com/try-free/
   - Create a new database
   - Get the connection details (host, port, username, password)
   - Update your credentials in the `.env` or `.streamlit/secrets.toml` file

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
4. Set up your secrets in the Streamlit Cloud dashboard:
   - Go to your app settings
   - Click on "Secrets"
   - Add your Redis and OpenRouter credentials in TOML format:
     ```toml
     [redis]
     url = "redis://username:password@host:port"

     [openrouter]
     api_key = "your-openrouter-api-key"
     ```
5. Deploy the app

You can see a live example at: https://scotty.streamlit.app/

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
