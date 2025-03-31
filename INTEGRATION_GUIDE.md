# Integration Guide: Redis AI Tools with AvitoScraping and Anna AI

This guide provides step-by-step instructions for integrating the Redis AI tools with your AvitoScraping project and Anna AI sales agent.

## Prerequisites

✅ Redis Cloud connection is configured and working
✅ OpenRouter API integration is configured and working
✅ Python environment with required dependencies is set up

## Step 1: Connect AvitoScraping Data to Vector Store

### 1.1 Import Vehicle Data

```python
from redis_ai_tools.vector_search.vector_store import VectorStore
from redis_ai_tools.utils import EmbeddingProvider

# Initialize embedding provider
embedding_provider = EmbeddingProvider()

# Initialize vector store for vehicles
vehicle_store = VectorStore(
    index_name="avito_vehicles",
    vector_dimensions=384,  # Dimensions for embedding model
    metadata_fields=["model", "price", "year", "mileage", "engine", "transmission", "url"]
)

# Function to import vehicle data from your database
def import_vehicles_to_vector_store():
    # Replace this with your actual data retrieval code
    # This could be from Prisma, a CSV file, or any other source
    vehicles = get_vehicles_from_database()

    texts = []
    metadatas = []

    for vehicle in vehicles:
        # Create text description in Russian
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
    embeddings = embedding_provider.embed(texts)

    # Add to vector store
    ids = vehicle_store.add_texts(texts, embeddings, metadatas)
    print(f"Indexed {len(ids)} vehicles in vector store")

    return ids
```

### 1.2 Create Search Function

```python
def search_vehicles(query, top_k=5):
    # Generate query embedding
    query_embedding = embedding_provider.embed([query])[0]

    # Search vector store
    results = vehicle_store.similarity_search(query_embedding, k=top_k)

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
```

## Step 2: Build RAG System for Vehicle Knowledge

### 2.1 Create Knowledge Base

```python
from redis_ai_tools.rag.rag_system import RAGSystem

# Initialize RAG system
vehicle_rag = RAGSystem(
    embedding_function=embedding_provider.embed,
    llm_function=None  # We'll set this later
)

# Add vehicle knowledge
def add_vehicle_knowledge():
    # Replace with your actual vehicle knowledge
    knowledge_texts = [
        "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
        "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях: фургон, бортовой, микроавтобус.",
        "MAN TGX - это седельный тягач премиум-класса, отличается высокой надежностью и экономичностью.",
        "Mercedes-Benz Sprinter - это универсальный микроавтобус, который может использоваться как для пассажирских перевозок, так и в качестве фургона.",
        "Volvo FH - это флагманский седельный тягач Volvo, предназначенный для дальних перевозок.",
        # Add more knowledge texts as needed
    ]

    # Add to RAG system
    ids = vehicle_rag.add_texts(knowledge_texts)
    print(f"Added {len(ids)} knowledge texts to RAG system")

    return ids
```

### 2.2 Set Up LLM Function

```python
from redis_ai_tools.utils import LLMProvider

# Initialize LLM provider with the correct model
llm_provider = LLMProvider(model_name="google/gemini-2.5-pro-exp-03-25:free")

# Set LLM function for RAG system
vehicle_rag.llm_function = llm_provider.generate

# Function to get vehicle information
def get_vehicle_info(query):
    # Use RAG to generate response
    result = vehicle_rag.query(query)
    return result["response"]
```

## Step 3: Implement Semantic Cache

```python
from redis_ai_tools.semantic_cache.semantic_cache import SemanticCache

# Initialize semantic cache
semantic_cache = SemanticCache(
    embedding_function=embedding_provider.embed,
    similarity_threshold=0.85
)

# Function to get cached or new response
def get_cached_response(query, generate_func):
    response, cache_hit = semantic_cache.get_or_set(query, generate_func)
    status = "Cache hit" if cache_hit else "Cache miss"
    print(f"Cache status: {status}")
    return response
```

## Step 4: Set Up Session Manager for Anna AI

```python
from redis_ai_tools.session_manager.session_manager import SessionManager

# Initialize session manager
session_manager = SessionManager(ttl=86400)  # Sessions expire after 24 hours

# Create a new customer session
def create_customer_session(customer_id):
    # Create session with customer metadata
    session = session_manager.create_session(metadata={"customer_id": customer_id})

    # Add system message
    session_manager.add_system_message(
        session.session_id,
        "Вы Анна, AI-ассистент по продажам компании Business Trucks. "
        "Вы помогаете клиентам найти подходящие коммерческие транспортные средства. "
        "Всегда отвечайте на русском языке."
    )

    return session

# Process customer message
def process_customer_message(session_id, message):
    # Add user message to session
    session_manager.add_user_message(session_id, message)

    # Get message history
    history = session_manager.get_message_history(session_id)

    # Generate response using cached LLM
    def generate_response(prompt):
        # Create a prompt from message history
        full_prompt = create_prompt_from_history(history)

        # Use RAG to enhance response with vehicle knowledge if needed
        if is_vehicle_question(prompt):
            vehicle_info = get_vehicle_info(prompt)
            full_prompt += f"\n\nИнформация о транспортных средствах:\n{vehicle_info}"

        # Generate response
        return llm_provider.generate(full_prompt)

    # Get cached or new response
    response = get_cached_response(message, generate_response)

    # Add assistant response to session
    session_manager.add_assistant_message(session_id, response)

    return response

# Helper function to create prompt from history
def create_prompt_from_history(history):
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

# Helper function to detect vehicle questions
def is_vehicle_question(query):
    vehicle_keywords = ["грузовик", "автомобиль", "транспорт", "камаз", "газель", "ман", "мерседес", "вольво"]
    return any(keyword in query.lower() for keyword in vehicle_keywords)
```

## Step 5: Integration with AvitoScraping

### 5.1 Scheduled Data Import

Set up a scheduled task to import new vehicle data from AvitoScraping to the vector store:

```python
import schedule
import time

def scheduled_import():
    print("Running scheduled import of vehicle data...")
    import_vehicles_to_vector_store()

# Schedule the import to run daily at 2 AM
schedule.every().day.at("02:00").do(scheduled_import)

# Run the scheduler in a separate thread
import threading
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()
```

### 5.2 API Endpoints for Anna AI

Create API endpoints for Anna AI to use the Redis AI tools:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CustomerMessage(BaseModel):
    customer_id: str
    message: str
    session_id: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

@app.post("/api/chat")
async def chat(request: CustomerMessage):
    try:
        # Get or create session
        if request.session_id:
            # Check if session exists
            session = session_manager.get_session(request.session_id)
            if not session:
                # Create new session if not found
                session = create_customer_session(request.customer_id)
                session_id = session.session_id
            else:
                session_id = request.session_id
        else:
            # Create new session
            session = create_customer_session(request.customer_id)
            session_id = session.session_id

        # Process message
        response = process_customer_message(session_id, request.message)

        return {
            "session_id": session_id,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search(request: SearchQuery):
    try:
        # Search for vehicles
        vehicles = search_vehicles(request.query, request.top_k)

        return {
            "query": request.query,
            "results": vehicles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Step 6: Monitoring and Maintenance

### 6.1 Cache Management

```python
# Function to clear the semantic cache
def clear_cache():
    semantic_cache.clear()
    print("Semantic cache cleared")

# Function to invalidate specific entries
def invalidate_cache_entry(query):
    success = semantic_cache.invalidate(query)
    if success:
        print(f"Cache entry for '{query}' invalidated")
    else:
        print(f"No matching cache entry found for '{query}'")
```

### 6.2 Session Cleanup

```python
# Function to list all active sessions
def list_active_sessions():
    session_ids = session_manager.list_sessions()
    print(f"Found {len(session_ids)} active sessions")
    return session_ids

# Function to delete old sessions
def cleanup_old_sessions(days=30):
    session_ids = session_manager.list_sessions()
    current_time = time.time()
    deleted_count = 0

    for session_id in session_ids:
        session = session_manager.get_session(session_id)
        if session and (current_time - session.updated_at > days * 86400):
            session_manager.delete_session(session_id)
            deleted_count += 1

    print(f"Deleted {deleted_count} sessions older than {days} days")
```

## Step 7: Testing and Deployment

### 7.1 Testing

Before deploying to production, test the integration thoroughly:

1. Test Redis connection and basic operations
2. Test vector search with sample queries
3. Test RAG system with vehicle knowledge
4. Test semantic cache with repeated queries
5. Test session management with simulated conversations
6. Test the full integration with sample customer interactions

### 7.2 Deployment

Deploy the integration to your production environment:

1. Set up the required environment variables
2. Install the dependencies
3. Run the initial data import
4. Start the API server
5. Configure monitoring and logging
6. Set up scheduled tasks for data import and maintenance

## Conclusion

By following this guide, you've integrated the Redis AI tools with your AvitoScraping project and Anna AI sales agent. This integration provides:

1. Fast semantic search for vehicles
2. Enhanced responses with domain-specific knowledge
3. Reduced API costs through semantic caching
4. Persistent conversation context for better customer interactions

For any issues or questions, refer to the documentation in the `README.md` file or contact the development team.
