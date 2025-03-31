"""
LangGraph workflow for orchestrating AvitoScraping and Redis AI tools.
"""
import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional, Union, TypedDict, Annotated, Literal
from enum import Enum

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import MessageGraph
    from langgraph.prebuilt import ToolNode
    import operator
    
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("Warning: LangGraph is not installed. Install with 'pip install langgraph'")

# Try to import LangChain
try:
    from langchain.schema import HumanMessage, AIMessage, SystemMessage
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.tools import BaseTool, StructuredTool, tool
    
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain is not installed. Install with 'pip install langchain'")

# Import our components
from utils import LLMProvider
from avito_scraping_agent import AvitoScrapingAgent
from import_avito_data import AvitoDataImporter
from vector_search.simple_vector_store import SimpleVectorStore

# Define state types
class ScraperState(TypedDict):
    """State for the scraper workflow."""
    query: str
    categories: List[str]
    max_pages: int
    max_vehicles: int
    use_proxy: bool
    use_llm: bool
    vehicles: List[Dict[str, Any]]
    status: str
    error: Optional[str]

class SearchState(TypedDict):
    """State for the search workflow."""
    query: str
    results: List[Dict[str, Any]]
    status: str
    error: Optional[str]

class AgentState(TypedDict):
    """State for the agent workflow."""
    messages: List[Dict[str, Any]]
    current_message: str
    context: List[Dict[str, Any]]
    status: str
    error: Optional[str]

# Define workflow nodes
class ScraperWorkflow:
    """
    Workflow for scraping vehicles from Avito.
    """
    
    def __init__(self):
        """Initialize the scraper workflow."""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not installed. Install with 'pip install langgraph'")
            
        # Initialize components
        self.llm_provider = LLMProvider()
        
        # Create state graph
        self.graph = self._create_graph()
        
    def _create_graph(self) -> StateGraph:
        """
        Create the state graph for the scraper workflow.
        
        Returns:
            StateGraph instance
        """
        # Create graph
        graph = StateGraph(ScraperState)
        
        # Add nodes
        graph.add_node("parse_request", self._parse_request)
        graph.add_node("scrape_vehicles", self._scrape_vehicles)
        graph.add_node("process_vehicles", self._process_vehicles)
        graph.add_node("import_to_redis", self._import_to_redis)
        
        # Add edges
        graph.add_edge("parse_request", "scrape_vehicles")
        graph.add_edge("scrape_vehicles", "process_vehicles")
        graph.add_edge("process_vehicles", "import_to_redis")
        graph.add_edge("import_to_redis", END)
        
        # Add conditional edges
        graph.add_conditional_edges(
            "parse_request",
            self._check_parse_result,
            {
                "success": "scrape_vehicles",
                "error": END
            }
        )
        
        graph.add_conditional_edges(
            "scrape_vehicles",
            self._check_scrape_result,
            {
                "success": "process_vehicles",
                "error": END
            }
        )
        
        graph.add_conditional_edges(
            "process_vehicles",
            self._check_process_result,
            {
                "success": "import_to_redis",
                "error": END
            }
        )
        
        # Compile graph
        return graph.compile()
        
    def _parse_request(self, state: ScraperState) -> ScraperState:
        """
        Parse the scraper request.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Extract categories from query using LLM
            if self.llm_provider:
                prompt = f"""
                Определите категории транспортных средств для поиска на основе запроса пользователя.
                Доступные категории:
                - trucks: Грузовики
                - tractors: Тракторы
                - buses: Автобусы
                - vans: Легкие грузовики до 3.5 тонн
                - construction: Строительная техника
                - agricultural: Сельхозтехника
                - trailers: Прицепы
                
                Запрос пользователя: {state['query']}
                
                Верните только список категорий в формате JSON, например:
                ["trucks", "vans"]
                """
                
                response = self.llm_provider.generate(prompt)
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\[.*\]', response)
                if json_match:
                    categories = json.loads(json_match.group(0))
                else:
                    categories = ["trucks"]  # Default to trucks if parsing fails
            else:
                # Default categories if LLM is not available
                categories = ["trucks"]
                
            # Update state
            return {
                **state,
                "categories": categories,
                "status": "parsed",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error parsing request: {str(e)}"
            }
            
    def _check_parse_result(self, state: ScraperState) -> str:
        """
        Check the result of parsing the request.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute
        """
        if state["status"] == "error":
            return "error"
        return "success"
        
    async def _scrape_vehicles(self, state: ScraperState) -> ScraperState:
        """
        Scrape vehicles from Avito.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Initialize scraper
            scraper = AvitoScrapingAgent(use_llm=state["use_llm"])
            
            # Scrape vehicles
            all_vehicles = []
            
            for category in state["categories"]:
                # Check if category is valid
                if category not in scraper.categories:
                    continue
                    
                # Scrape category
                vehicles = await scraper.scrape_category(
                    category,
                    max_pages=state["max_pages"],
                    max_vehicles=state["max_vehicles"]
                )
                
                all_vehicles.extend(vehicles)
                
            # Update state
            return {
                **state,
                "vehicles": all_vehicles,
                "status": "scraped",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error scraping vehicles: {str(e)}"
            }
            
    def _check_scrape_result(self, state: ScraperState) -> str:
        """
        Check the result of scraping vehicles.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute
        """
        if state["status"] == "error":
            return "error"
        return "success"
        
    def _process_vehicles(self, state: ScraperState) -> ScraperState:
        """
        Process scraped vehicles.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Process vehicles
            # In a real implementation, this would do more processing
            # For now, we'll just count the vehicles
            
            # Update state
            return {
                **state,
                "status": "processed",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error processing vehicles: {str(e)}"
            }
            
    def _check_process_result(self, state: ScraperState) -> str:
        """
        Check the result of processing vehicles.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute
        """
        if state["status"] == "error":
            return "error"
        return "success"
        
    def _import_to_redis(self, state: ScraperState) -> ScraperState:
        """
        Import vehicles to Redis.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Initialize importer
            importer = AvitoDataImporter()
            
            # Transform vehicles
            texts = []
            metadatas = []
            
            for vehicle in state["vehicles"]:
                # Create description
                description = f"{vehicle.get('title', '')} - {vehicle.get('description', '')}"
                texts.append(description)
                
                # Create metadata
                metadata = {
                    "title": vehicle.get("title", ""),
                    "price": vehicle.get("price", ""),
                    "url": vehicle.get("url", ""),
                    # Add more fields as needed
                }
                
                metadatas.append(metadata)
                
            # Import to Redis
            if texts and metadatas:
                importer.import_vehicles_to_redis(texts, metadatas)
                
            # Update state
            return {
                **state,
                "status": "imported",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error importing to Redis: {str(e)}"
            }
            
    def run(self, query: str, max_pages: int = 3, max_vehicles: int = 20, use_proxy: bool = True, use_llm: bool = True) -> Dict[str, Any]:
        """
        Run the scraper workflow.
        
        Args:
            query: Query string
            max_pages: Maximum number of pages to scrape per category
            max_vehicles: Maximum number of vehicles to scrape per category
            use_proxy: Whether to use a proxy server
            use_llm: Whether to use LLM for data enhancement
            
        Returns:
            Workflow result
        """
        # Create initial state
        initial_state = {
            "query": query,
            "categories": [],
            "max_pages": max_pages,
            "max_vehicles": max_vehicles,
            "use_proxy": use_proxy,
            "use_llm": use_llm,
            "vehicles": [],
            "status": "initialized",
            "error": None
        }
        
        # Run workflow
        try:
            # For async nodes, we need to run the workflow in an event loop
            import asyncio
            
            # Get event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Run workflow
            result = loop.run_until_complete(self.graph.ainvoke(initial_state))
            
            return result
        except Exception as e:
            return {
                **initial_state,
                "status": "error",
                "error": f"Error running workflow: {str(e)}"
            }

class SearchWorkflow:
    """
    Workflow for searching vehicles.
    """
    
    def __init__(self):
        """Initialize the search workflow."""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not installed. Install with 'pip install langgraph'")
            
        # Initialize components
        self.embedding_provider = None  # Will be initialized on demand
        
        # Create state graph
        self.graph = self._create_graph()
        
    def _create_graph(self) -> StateGraph:
        """
        Create the state graph for the search workflow.
        
        Returns:
            StateGraph instance
        """
        # Create graph
        graph = StateGraph(SearchState)
        
        # Add nodes
        graph.add_node("parse_query", self._parse_query)
        graph.add_node("search_vehicles", self._search_vehicles)
        graph.add_node("rank_results", self._rank_results)
        
        # Add edges
        graph.add_edge("parse_query", "search_vehicles")
        graph.add_edge("search_vehicles", "rank_results")
        graph.add_edge("rank_results", END)
        
        # Compile graph
        return graph.compile()
        
    def _parse_query(self, state: SearchState) -> SearchState:
        """
        Parse the search query.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # In a real implementation, this would do more parsing
        # For now, we'll just pass the query through
        return {
            **state,
            "status": "parsed",
            "error": None
        }
        
    def _search_vehicles(self, state: SearchState) -> SearchState:
        """
        Search for vehicles.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Initialize components
            from utils import EmbeddingProvider
            self.embedding_provider = EmbeddingProvider()
            
            # Initialize vector store
            vector_store = SimpleVectorStore(index_name="avito_vehicles")
            
            # Generate query embedding
            query_embedding = self.embedding_provider.embed([state["query"]])[0]
            
            # Search vector store
            results = vector_store.similarity_search(query_embedding, k=10)
            
            # Update state
            return {
                **state,
                "results": results,
                "status": "searched",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error searching vehicles: {str(e)}"
            }
            
    def _rank_results(self, state: SearchState) -> SearchState:
        """
        Rank search results.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # In a real implementation, this would do more ranking
            # For now, we'll just sort by score
            results = sorted(state["results"], key=lambda x: x.get("score", 0), reverse=True)
            
            # Update state
            return {
                **state,
                "results": results,
                "status": "ranked",
                "error": None
            }
        except Exception as e:
            return {
                **state,
                "status": "error",
                "error": f"Error ranking results: {str(e)}"
            }
            
    def run(self, query: str) -> Dict[str, Any]:
        """
        Run the search workflow.
        
        Args:
            query: Query string
            
        Returns:
            Workflow result
        """
        # Create initial state
        initial_state = {
            "query": query,
            "results": [],
            "status": "initialized",
            "error": None
        }
        
        # Run workflow
        try:
            result = self.graph.invoke(initial_state)
            return result
        except Exception as e:
            return {
                **initial_state,
                "status": "error",
                "error": f"Error running workflow: {str(e)}"
            }

class AgentWorkflow:
    """
    Workflow for the agent.
    """
    
    def __init__(self):
        """Initialize the agent workflow."""
        if not LANGGRAPH_AVAILABLE or not LANGCHAIN_AVAILABLE:
            raise ImportError("LangGraph and LangChain are required. Install with 'pip install langgraph langchain'")
            
        # Initialize components
        self.llm_provider = LLMProvider()
        
        # Create message graph
        self.graph = self._create_graph()
        
    def _create_graph(self) -> MessageGraph:
        """
        Create the message graph for the agent workflow.
        
        Returns:
            MessageGraph instance
        """
        # Create tools
        tools = [
            self._create_search_tool(),
            self._create_scrape_tool()
        ]
        
        # Create system prompt
        system_prompt = """
        Вы Анна, AI-ассистент по продажам компании Business Trucks.
        Вы помогаете клиентам найти подходящие коммерческие транспортные средства.
        
        Вы можете использовать следующие инструменты:
        - search_vehicles: Поиск транспортных средств по запросу
        - scrape_vehicles: Сбор информации о транспортных средствах с Avito
        
        Всегда отвечайте на русском языке.
        """
        
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Create graph
        graph = MessageGraph()
        
        # Add nodes
        graph.add_node("agent", self._create_agent_node(prompt))
        graph.add_node("tools", tool_node)
        
        # Add edges
        graph.add_edge("agent", "tools")
        graph.add_edge("tools", "agent")
        
        # Set entry point
        graph.set_entry_point("agent")
        
        # Compile graph
        return graph.compile()
        
    def _create_agent_node(self, prompt: ChatPromptTemplate):
        """
        Create the agent node.
        
        Args:
            prompt: Chat prompt template
            
        Returns:
            Agent node function
        """
        def agent_node(state):
            # Get messages
            messages = state["messages"]
            
            # Format prompt
            formatted_prompt = prompt.format(
                messages=messages,
                agent_scratchpad=state.get("agent_scratchpad", [])
            )
            
            # Generate response
            response = self.llm_provider.generate(formatted_prompt)
            
            # Parse response
            # In a real implementation, this would parse tool calls
            # For now, we'll just return the response
            return {"messages": messages + [AIMessage(content=response)]}
            
        return agent_node
        
    def _create_search_tool(self) -> BaseTool:
        """
        Create a tool for searching vehicles.
        
        Returns:
            Search tool
        """
        @tool
        def search_vehicles(query: str) -> str:
            """
            Search for vehicles based on a query.
            
            Args:
                query: Search query
                
            Returns:
                Search results
            """
            # Create search workflow
            search_workflow = SearchWorkflow()
            
            # Run workflow
            result = search_workflow.run(query)
            
            # Format results
            if result["status"] == "error":
                return f"Error searching vehicles: {result['error']}"
                
            if not result["results"]:
                return "No matching vehicles found."
                
            # Format results
            formatted_results = []
            
            for i, vehicle in enumerate(result["results"][:5]):  # Limit to top 5
                formatted_results.append(f"{i+1}. {vehicle.get('title', '')}")
                formatted_results.append(f"   Цена: {vehicle.get('price', '')}")
                formatted_results.append(f"   URL: {vehicle.get('url', '')}")
                formatted_results.append("")
                
            return "\n".join(formatted_results)
            
        return search_vehicles
        
    def _create_scrape_tool(self) -> BaseTool:
        """
        Create a tool for scraping vehicles.
        
        Returns:
            Scrape tool
        """
        @tool
        def scrape_vehicles(query: str) -> str:
            """
            Scrape vehicles from Avito based on a query.
            
            Args:
                query: Search query
                
            Returns:
                Scraping results
            """
            # Create scraper workflow
            scraper_workflow = ScraperWorkflow()
            
            # Run workflow
            result = scraper_workflow.run(query, max_pages=1, max_vehicles=5)
            
            # Format results
            if result["status"] == "error":
                return f"Error scraping vehicles: {result['error']}"
                
            if not result["vehicles"]:
                return "No vehicles found."
                
            # Format results
            return f"Scraped {len(result['vehicles'])} vehicles from categories: {', '.join(result['categories'])}"
            
        return scrape_vehicles
        
    def run(self, message: str) -> str:
        """
        Run the agent workflow.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=message)]
        }
        
        # Run workflow
        try:
            result = self.graph.invoke(initial_state)
            
            # Extract response
            response = result["messages"][-1].content
            
            return response
        except Exception as e:
            return f"Error running agent: {str(e)}"

def main():
    """Main function."""
    if not LANGGRAPH_AVAILABLE:
        print("LangGraph is not installed. Install with 'pip install langgraph'")
        return
        
    # Test search workflow
    print("Testing search workflow...")
    search_workflow = SearchWorkflow()
    search_result = search_workflow.run("грузовик для перевозки строительных материалов")
    print(f"Search result status: {search_result['status']}")
    print(f"Found {len(search_result['results'])} vehicles")
    
    # Test agent workflow
    print("\nTesting agent workflow...")
    agent_workflow = AgentWorkflow()
    agent_response = agent_workflow.run("Я ищу грузовик для перевозки мебели. Что вы можете предложить?")
    print(f"Agent response: {agent_response}")

if __name__ == "__main__":
    main()
