# Enhanced Redis AI Tools with LangChain and LangGraph

This is an enhanced version of the Redis AI tools that integrates LangChain, LangGraph, and a Streamlit dashboard.

## Overview

This implementation includes:

1. **Redis AI Tools**: Vector search, RAG, semantic cache, and session management
2. **LangChain Integration**: Enhanced RAG system and agent capabilities
3. **LangGraph Workflow**: Orchestrated workflows for scraping, searching, and agent interaction
4. **Streamlit Dashboard**: Visual interface for interacting with the system
5. **AvitoScraping Agent**: Intelligent scraper for Avito.ru commercial vehicles

## Installation

1. Run the installation script:
   ```bash
   ./install_dependencies.sh
   ```

2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Set up the Redis database structure:
   ```bash
   python setup_redis_db.py
   ```

## Components

### 1. Redis AI Tools

The core Redis AI tools have been enhanced with:

- **SimpleVectorStore**: A custom implementation that works with standard Redis
- **LangChain Integration**: Integration with LangChain for enhanced RAG capabilities
- **LangGraph Workflow**: Orchestrated workflows for complex operations

### 2. LangChain Integration

The LangChain integration provides:

- **CustomEmbeddings**: A LangChain-compatible embeddings class that uses our EmbeddingProvider
- **CustomLLM**: A LangChain-compatible LLM class that uses our LLMProvider
- **LangChainRAG**: A RAG system implementation using LangChain
- **LangChainAgent**: An agent implementation using LangChain

### 3. LangGraph Workflow

The LangGraph workflow provides:

- **ScraperWorkflow**: A workflow for scraping vehicles from Avito
- **SearchWorkflow**: A workflow for searching vehicles
- **AgentWorkflow**: A workflow for the agent

### 4. Streamlit Dashboard

The Streamlit dashboard provides:

- **Dashboard**: Overview of the system
- **Vehicle Search**: Search for vehicles using natural language
- **Data Overview**: View and filter vehicle data
- **Scraper Control**: Control the scraper
- **Agent Chat**: Chat with the AI agent

### 5. AvitoScraping Agent

The AvitoScraping agent has been enhanced with:

- **LLM Integration**: Uses LLM for data enhancement
- **Proxy Support**: Optional MCP proxy server support
- **Workflow Integration**: Integration with LangGraph workflow

## Usage

### Running the Dashboard

```bash
streamlit run dashboard.py
```

### Using the LangChain RAG System

```python
from langchain_integration import LangChainRAG

# Initialize RAG system
rag = LangChainRAG()

# Add texts
texts = [
    "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
    "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях."
]
rag.add_texts(texts)

# Query the RAG system
response = rag.query("Какой грузовик лучше для строительных работ?")
print(response)
```

### Using the LangGraph Workflow

```python
from langgraph_workflow import SearchWorkflow, ScraperWorkflow, AgentWorkflow

# Search for vehicles
search_workflow = SearchWorkflow()
result = search_workflow.run("грузовик для перевозки строительных материалов")
print(result)

# Scrape vehicles
scraper_workflow = ScraperWorkflow()
result = scraper_workflow.run("грузовик для перевозки мебели")
print(result)

# Chat with the agent
agent_workflow = AgentWorkflow()
response = agent_workflow.run("Я ищу грузовик для перевозки мебели. Что вы можете предложить?")
print(response)
```

## MCP Proxy Server Integration

The AvitoScraping agent can use the MCP proxy server to avoid rate limiting by Avito. To enable this:

1. Make sure the MCP proxy server is running
2. Set `use_proxy=True` when initializing the AvitoScrapingAgent
3. Implement the `get_random_proxy` method in the AvitoScrapingAgent class

## Troubleshooting

### Redis Connection Issues

If you have issues connecting to Redis:
- Check that the Redis URL in `.env` is correct
- Ensure your IP is whitelisted in Redis Cloud
- Try connecting with the Redis CLI to verify access

### LangChain/LangGraph Issues

If you have issues with LangChain or LangGraph:
- Make sure you have installed the correct versions
- Check that the OpenRouter API key is correct
- Try running the basic Redis AI tools without LangChain/LangGraph

### Streamlit Dashboard Issues

If you have issues with the Streamlit dashboard:
- Make sure Streamlit is installed
- Check that Redis is connected
- Try running a simple Streamlit app to verify installation

## Next Steps

1. **Enhance Proxy Support**: Implement rotation of proxies to avoid rate limiting
2. **Improve Data Schema**: Add more fields and metadata for better search
3. **Implement Differential Updates**: Only scrape and update new or changed listings
4. **Add Monitoring**: Set up alerts for scraping failures or data issues
5. **Enhance Dashboard**: Add more visualizations and controls
