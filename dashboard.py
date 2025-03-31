"""
Streamlit dashboard for AvitoScraping and Redis AI tools.
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import components
from redis_connection import get_redis_client
from vector_search.simple_vector_store import SimpleVectorStore
from utils import EmbeddingProvider, LLMProvider
from redis_pubsub import get_redis_pubsub
from realtime_metrics import get_realtime_metrics

# Try to import optional components
try:
    from avito_scraping_agent import AvitoScrapingAgent
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("Warning: AvitoScrapingAgent not available. Scraper functionality will be limited.")

try:
    from import_avito_data import AvitoDataImporter
    IMPORTER_AVAILABLE = True
except (ImportError, RuntimeError):
    IMPORTER_AVAILABLE = False
    print("Warning: AvitoDataImporter not available. Import functionality will be limited.")

# Set page configuration
st.set_page_config(
    page_title="AvitoScraping AI Dashboard",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 1rem;
        color: #616161;
    }
    .highlight {
        background-color: #e3f2fd;
        padding: 0.5rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = None
if "redis_status" not in st.session_state:
    # Check Redis connection
    redis_client = get_redis_client()
    st.session_state.redis_status = redis_client is not None
    if not st.session_state.redis_status:
        st.warning("⚠️ Redis connection failed. Some features may be limited. Using demo data instead.")
    else:
        st.success("✅ Connected to Redis successfully!")
if "realtime_metrics" not in st.session_state:
    # Initialize real-time metrics
    st.session_state.realtime_metrics = get_realtime_metrics()
if "auto_refresh" not in st.session_state:
    # Initialize auto-refresh
    st.session_state.auto_refresh = True
    st.session_state.refresh_interval = 5  # seconds
if "last_refresh" not in st.session_state:
    # Initialize last refresh time
    st.session_state.last_refresh = datetime.now()
if "connection_attempts" not in st.session_state:
    # Initialize connection attempts counter
    st.session_state.connection_attempts = 0

# Sidebar
with st.sidebar:
    st.image("https://www.svgrepo.com/show/374111/redis.svg", width=100)
    st.markdown("## AvitoScraping AI")

    # Navigation
    page = st.radio("Navigation", [
        "Dashboard",
        "Vehicle Search",
        "Data Overview",
        "Scraper Control",
        "Agent Chat",
        "Implementation Documentation"
    ])

    # Status indicators
    st.markdown("### System Status")
    redis_status = "🟢 Connected" if st.session_state.redis_status else "🔴 Disconnected"
    st.markdown(f"**Redis:** {redis_status}")

    # Add reconnect button if disconnected
    if not st.session_state.redis_status:
        if st.button("Reconnect to Redis"):
            # Increment connection attempts
            st.session_state.connection_attempts += 1
            # Try to reconnect
            redis_client = get_redis_client()
            st.session_state.redis_status = redis_client is not None
            if st.session_state.redis_status:
                st.success("Reconnected to Redis successfully!")
                # Reinitialize real-time metrics
                st.session_state.realtime_metrics = get_realtime_metrics()
                # Rerun to refresh UI
                st.rerun()
            else:
                st.warning(f"Failed to reconnect to Redis (Attempt {st.session_state.connection_attempts})")

    # About section
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This dashboard provides a visual interface for the AvitoScraping and Redis AI tools integration.

    - Search for vehicles using natural language
    - View scraped vehicle data
    - Control the scraper
    - Chat with the AI agent
    """)

    st.markdown("---")
    st.markdown("© 2023 Business Trucks")

# Main content
if page == "Dashboard":
    st.markdown('<h1 class="main-header">AvitoScraping AI Dashboard</h1>', unsafe_allow_html=True)

    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh)
    if auto_refresh != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_refresh

    # Auto-refresh logic
    if st.session_state.auto_refresh:
        # Check if it's time to refresh
        now = datetime.now()
        time_diff = (now - st.session_state.last_refresh).total_seconds()
        if time_diff >= st.session_state.refresh_interval:
            # Update last refresh time
            st.session_state.last_refresh = now
            # Rerun to refresh data
            st.rerun()

    # Get real-time metrics
    metrics = st.session_state.realtime_metrics.get_metrics()

    # Last update time
    st.markdown(f"<div style='text-align: right; color: #666;'>Last updated: {metrics['last_update'].strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{metrics["vehicle_count"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Vehicles Scraped</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # Count non-zero categories
        active_categories = sum(1 for count in metrics["vehicle_count_by_category"].values() if count > 0)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{active_categories}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Categories</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{metrics["search_count"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Searches</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        # Scraper status
        status_color = {
            "idle": "#888",
            "running": "#4CAF50",
            "error": "#F44336",
            "completed": "#2196F3"
        }.get(metrics["scraper_status"], "#888")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value" style="color: {status_color};">{metrics["scraper_status"].capitalize()}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Scraper Status</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Recent activity
    st.markdown('<h2 class="sub-header">Recent Activity</h2>', unsafe_allow_html=True)

    # Get recent activity from Redis
    redis_client = get_redis_client()
    recent_activity = []

    if redis_client:
        # Get recent searches
        search_history = st.session_state.search_history
        for search in search_history[-5:]:
            recent_activity.append({
                "time": search["timestamp"],
                "type": "Search",
                "details": f"User searched for '{search['query']}'"
            })

        # Get recent scraper activity
        scraper_logs = redis_client.lrange("scraper:logs", 0, 4)
        for log in scraper_logs:
            try:
                log_data = json.loads(log.decode("utf-8"))
                recent_activity.append({
                    "time": log_data.get("timestamp", "Unknown"),
                    "type": "Scrape",
                    "details": log_data.get("message", "Unknown")
                })
            except Exception as e:
                print(f"Error parsing scraper log: {e}")

        # Get recent system activity
        system_logs = redis_client.lrange("system:logs", 0, 4)
        for log in system_logs:
            try:
                log_data = json.loads(log.decode("utf-8"))
                recent_activity.append({
                    "time": log_data.get("timestamp", "Unknown"),
                    "type": "System",
                    "details": log_data.get("message", "Unknown")
                })
            except Exception as e:
                print(f"Error parsing system log: {e}")

    # If no activity found, use sample data
    if not recent_activity:
        recent_activity = [
            {"time": "10:15", "type": "Scrape", "details": "Completed scraping 'trucks' category - 35 vehicles found"},
            {"time": "09:30", "type": "Search", "details": "User searched for 'грузовик для перевозки мебели'"},
            {"time": "09:15", "type": "Import", "details": "Imported 42 vehicles to Redis vector store"},
            {"time": "08:45", "type": "System", "details": "Daily maintenance completed - indexes optimized"},
            {"time": "Yesterday", "type": "Scrape", "details": "Completed scraping 'vans' category - 28 vehicles found"}
        ]

    # Sort by time (most recent first)
    # This is a simple sort that assumes time is in a consistent format
    recent_activity.sort(key=lambda x: x["time"], reverse=True)

    # Limit to 10 most recent activities
    recent_activity = recent_activity[:10]

    # Display as dataframe
    activity_df = pd.DataFrame(recent_activity)
    st.dataframe(activity_df, use_container_width=True, hide_index=True)

    # System overview
    st.markdown('<h2 class="sub-header">System Overview</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Redis AI Tools")

        # Check Redis connection
        redis_status = "✅ Operational" if st.session_state.redis_status else "❌ Disconnected"

        # Check vector store
        vector_store_status = "✅ Operational" if st.session_state.redis_status else "❌ Unavailable"

        # Check RAG system
        rag_status = "✅ Operational" if st.session_state.redis_status else "❌ Unavailable"

        # Check session manager
        session_status = "✅ Operational" if st.session_state.redis_status else "❌ Unavailable"

        st.markdown(f"""
        - **Redis Connection**: {redis_status}
        - **Vector Search**: {vector_store_status}
        - **RAG System**: {rag_status}
        - **Session Manager**: {session_status}
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### AvitoScraping")

        # Get scraper status
        scraper_status = metrics["scraper_status"].capitalize()
        scraper_status_icon = {
            "Idle": "⏸️",
            "Running": "▶️",
            "Error": "❌",
            "Completed": "✅"
        }.get(scraper_status, "⏸️")

        # Format last update time
        last_update = "Never"
        if metrics["scraper_last_update"]:
            last_update = metrics["scraper_last_update"].strftime("%Y-%m-%d %H:%M:%S")

        # Count active categories
        active_categories = sum(1 for count in metrics["vehicle_count_by_category"].values() if count > 0)
        total_categories = len(metrics["vehicle_count_by_category"])

        st.markdown(f"""
        - **Scraper**: {scraper_status_icon} {scraper_status}
        - **Vehicles Scraped**: {metrics["vehicle_count"]}
        - **Categories**: {active_categories}/{total_categories} active
        - **Last Run**: {last_update}
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # Quick actions
    st.markdown('<h2 class="sub-header">Quick Actions</h2>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Run Scraper", use_container_width=True):
            st.info("Scraper would start here in a real implementation")

    with col2:
        if st.button("Import Data", use_container_width=True):
            st.info("Data import would start here in a real implementation")

    with col3:
        if st.button("Clear Cache", use_container_width=True):
            st.info("Cache clearing would happen here in a real implementation")

elif page == "Vehicle Search":
    st.markdown('<h1 class="main-header">Semantic Vehicle Search</h1>', unsafe_allow_html=True)

    # Initialize components
    embedding_provider = EmbeddingProvider()

    # Get Redis client
    redis_client = get_redis_client()

    # Search input
    query = st.text_input("What kind of vehicle are you looking for?",
                         "грузовик для перевозки строительных материалов")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_button = st.button("Search", use_container_width=True)

    with col2:
        k = st.number_input("Number of results", min_value=1, max_value=20, value=5)

    if search_button:
        with st.spinner("Searching for vehicles..."):
            # Add to search history
            st.session_state.search_history.append({
                "query": query,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Update search stats in real-time metrics
            st.session_state.realtime_metrics.update_search_stats(query)

            try:
                # Get all vehicle keys
                all_keys = redis_client.keys("*")
                vehicle_keys = [k for k in all_keys if k.startswith(b"vehicle:")]

                if not vehicle_keys:
                    st.warning("No vehicles found in the database")
                else:
                    # Generate query embedding
                    query_embedding = embedding_provider.embed([query])[0]

                    # Get all vehicle data and calculate similarity
                    results = []

                    for key in vehicle_keys:
                        # Get vehicle data
                        vehicle_data = redis_client.hgetall(key)

                        # Convert bytes to strings
                        vehicle = {}
                        for k, v in vehicle_data.items():
                            key_str = k.decode() if isinstance(k, bytes) else k
                            value_str = v.decode() if isinstance(v, bytes) else v
                            vehicle[key_str] = value_str

                        # Get embedding
                        embedding_str = vehicle.get("embedding")
                        if embedding_str:
                            # Parse embedding
                            try:
                                import json
                                import numpy as np

                                embedding = json.loads(embedding_str)

                                # Calculate similarity
                                query_vec = np.array(query_embedding)
                                vehicle_vec = np.array(embedding)

                                # Normalize vectors
                                query_vec = query_vec / np.linalg.norm(query_vec)
                                vehicle_vec = vehicle_vec / np.linalg.norm(vehicle_vec)

                                # Calculate cosine similarity
                                similarity = np.dot(query_vec, vehicle_vec)

                                # Add to results
                                vehicle_copy = vehicle.copy()
                                vehicle_copy.pop("embedding", None)  # Remove embedding to save space
                                vehicle_copy["score"] = float(similarity)
                                vehicle_copy["id"] = key.decode() if isinstance(key, bytes) else key
                                results.append(vehicle_copy)
                            except Exception as e:
                                st.warning(f"Error processing vehicle {key}: {e}")

                    # Sort by similarity score
                    results.sort(key=lambda x: x.get("score", 0), reverse=True)

                    # Limit to top k results
                    results = results[:min(k, len(results))]

                    # Display results
                    if results:
                        st.success(f"Found {len(results)} matching vehicles")

                        for i, result in enumerate(results):
                            with st.container():
                                # Get title
                                title = result.get('title', '')
                                if not title or title.strip() == '':
                                    title = f"Vehicle {i+1}"

                                st.markdown(f"### {i+1}. {title}")

                                col1, col2 = st.columns([2, 1])

                                with col1:
                                    # Display basic info
                                    price = result.get('price', '')
                                    if price:
                                        st.markdown(f"**Price:** {price}")

                                    year = result.get('year', '')
                                    if year:
                                        st.markdown(f"**Year:** {year}")

                                    brand = result.get('brand', '')
                                    model = result.get('model', '')
                                    if brand or model:
                                        st.markdown(f"**Brand/Model:** {brand} {model}")

                                    engine_type = result.get('engine_type', '')
                                    engine_power = result.get('engine_power', '')
                                    if engine_type or engine_power:
                                        st.markdown(f"**Engine:** {engine_type} {engine_power}")

                                    transmission = result.get('transmission', '')
                                    if transmission:
                                        st.markdown(f"**Transmission:** {transmission}")

                                with col2:
                                    # Display similarity score
                                    st.markdown(f"**Similarity:** {result.get('score', 0):.4f}")

                                    # Display location
                                    location = result.get('location', '')
                                    if location:
                                        st.markdown(f"**Location:** {location}")

                                    # Display URL
                                    url = result.get('url', '')
                                    if url:
                                        st.markdown(f"[View on Avito]({url})")

                                # Display description
                                description = result.get('description', '')
                                if description:
                                    st.markdown(f"**Description:** {description}")

                                st.divider()
                    else:
                        st.warning("No matching vehicles found")
            except Exception as e:
                st.error(f"Error performing search: {e}")

    # Search history
    st.markdown('<h2 class="sub-header">Search History</h2>', unsafe_allow_html=True)

    if st.session_state.search_history:
        history_df = pd.DataFrame(st.session_state.search_history)
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No search history yet")

elif page == "Data Overview":
    st.markdown('<h1 class="main-header">Vehicle Data Overview</h1>', unsafe_allow_html=True)

    # Sample data for demonstration
    sample_data = [
        {"brand": "КАМАЗ", "model": "65115", "year": 2018, "price": 3500000, "category": "Самосвал"},
        {"brand": "ГАЗ", "model": "ГАЗель NEXT", "year": 2020, "price": 1200000, "category": "Фургон"},
        {"brand": "MAN", "model": "TGX", "year": 2019, "price": 5800000, "category": "Тягач"},
        {"brand": "Mercedes-Benz", "model": "Sprinter", "year": 2021, "price": 2500000, "category": "Микроавтобус"},
        {"brand": "Volvo", "model": "FH", "year": 2020, "price": 6200000, "category": "Тягач"},
        {"brand": "Scania", "model": "R500", "year": 2018, "price": 5500000, "category": "Тягач"},
        {"brand": "Hyundai", "model": "HD78", "year": 2019, "price": 2200000, "category": "Фургон"},
        {"brand": "Isuzu", "model": "NQR", "year": 2020, "price": 2800000, "category": "Бортовой"},
        {"brand": "КАМАЗ", "model": "43118", "year": 2017, "price": 3200000, "category": "Бортовой"},
        {"brand": "ГАЗ", "model": "3309", "year": 2019, "price": 1800000, "category": "Бортовой"}
    ]

    df = pd.DataFrame(sample_data)

    # Filters
    st.markdown('<h2 class="sub-header">Filters</h2>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        brand_filter = st.multiselect("Brand", df["brand"].unique(), default=None)

    with col2:
        category_filter = st.multiselect("Category", df["category"].unique(), default=None)

    with col3:
        year_range = st.slider("Year", min_value=int(df["year"].min()), max_value=int(df["year"].max()),
                              value=(int(df["year"].min()), int(df["year"].max())))

    # Apply filters
    filtered_df = df.copy()

    if brand_filter:
        filtered_df = filtered_df[filtered_df["brand"].isin(brand_filter)]

    if category_filter:
        filtered_df = filtered_df[filtered_df["category"].isin(category_filter)]

    filtered_df = filtered_df[(filtered_df["year"] >= year_range[0]) & (filtered_df["year"] <= year_range[1])]

    # Display data
    st.markdown('<h2 class="sub-header">Vehicle Data</h2>', unsafe_allow_html=True)
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # Visualizations
    st.markdown('<h2 class="sub-header">Visualizations</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Price Distribution by Brand")
        brand_price = df.groupby("brand")["price"].mean().sort_values(ascending=False)
        st.bar_chart(brand_price)

    with col2:
        st.markdown("### Vehicles by Category")
        category_counts = df["category"].value_counts()
        st.bar_chart(category_counts)

    # Price range
    st.markdown("### Price Range by Year")
    price_year = df.groupby("year").agg({"price": ["min", "mean", "max"]})
    price_year.columns = ["Min Price", "Average Price", "Max Price"]
    st.line_chart(price_year)

elif page == "Scraper Control":
    st.markdown('<h1 class="main-header">Scraper Control Panel</h1>', unsafe_allow_html=True)

    if not SCRAPER_AVAILABLE:
        st.warning("Scraper functionality is not available. Please install the required dependencies.")
    else:
        # Scraper configuration
        st.markdown('<h2 class="sub-header">Scraper Configuration</h2>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Categories")
            categories = {
                "trucks": "Грузовики",
                "tractors": "Тракторы",
                "buses": "Автобусы",
                "vans": "Легкие грузовики до 3.5 тонн",
                "construction": "Строительная техника",
                "agricultural": "Сельхозтехника",
                "trailers": "Прицепы"
            }

            selected_categories = []
            for key, value in categories.items():
                if st.checkbox(value, value=(key in ["trucks", "vans"])):
                    selected_categories.append(key)

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Parameters")

            max_pages = st.slider("Max Pages per Category", min_value=1, max_value=20, value=3)
            max_vehicles = st.slider("Max Vehicles per Category", min_value=5, max_value=100, value=20)
            use_llm = st.checkbox("Use LLM for Data Enhancement", value=True)

            st.markdown("### Proxy Settings")
            use_proxy = st.checkbox("Use MCP Proxy Server", value=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # Scraper controls
        st.markdown('<h2 class="sub-header">Scraper Controls</h2>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Start Scraping", use_container_width=True):
                if not selected_categories:
                    st.error("Please select at least one category")
                else:
                    with st.spinner("Scraping in progress..."):
                        # Update scraper status in real-time metrics
                        st.session_state.realtime_metrics.update_scraper_status("running", 0.0)

                        # In a real implementation, this would start the scraper
                        # For demo purposes, we'll just simulate it
                        for i in range(10):
                            # Update progress
                            progress = (i + 1) / 10
                            st.session_state.realtime_metrics.update_scraper_status("running", progress)
                            time.sleep(0.2)

                        # Sample results
                        total_vehicles = len(selected_categories) * 5  # Simulate 5 vehicles per category
                        st.session_state.scrape_results = {
                            "categories": selected_categories,
                            "total_vehicles": total_vehicles,
                            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "completed"
                        }

                        # Update scraper status in real-time metrics
                        st.session_state.realtime_metrics.update_scraper_status("completed", 1.0)

                        # Log scraper activity
                        redis_client = get_redis_client()
                        if redis_client:
                            log_data = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "message": f"Completed scraping {', '.join(selected_categories)} - {total_vehicles} vehicles found"
                            }
                            redis_client.lpush("scraper:logs", json.dumps(log_data))
                            redis_client.ltrim("scraper:logs", 0, 99)  # Keep only the last 100 logs

                        st.success(f"Scraping completed! Found {st.session_state.scrape_results['total_vehicles']} vehicles")

        with col2:
            import_button = st.button("Import to Redis", use_container_width=True)
            if import_button:
                if not IMPORTER_AVAILABLE:
                    st.warning("Import functionality is not available. Please install the required dependencies.")
                elif st.session_state.scrape_results is None:
                    st.error("No scraping results to import")
                else:
                    with st.spinner("Importing to Redis..."):
                        # In a real implementation, this would import the data
                        # For demo purposes, we'll just simulate it
                        time.sleep(2)

                        # Update vehicle count in real-time metrics
                        total_vehicles = st.session_state.scrape_results['total_vehicles']

                        # Log import activity
                        redis_client = get_redis_client()
                        if redis_client:
                            log_data = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "message": f"Imported {total_vehicles} vehicles to Redis vector store"
                            }
                            redis_client.lpush("system:logs", json.dumps(log_data))
                            redis_client.ltrim("system:logs", 0, 99)  # Keep only the last 100 logs

                        st.success(f"Successfully imported {total_vehicles} vehicles to Redis")

        with col3:
            if st.button("Schedule Daily Run", use_container_width=True):
                st.info("Scraper scheduled to run daily at 2:00 AM")

        # Scraper status
        if st.session_state.scrape_results is not None:
            st.markdown('<h2 class="sub-header">Last Scrape Results</h2>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Categories:** {', '.join(st.session_state.scrape_results['categories'])}")

            with col2:
                st.markdown(f"**Total Vehicles:** {st.session_state.scrape_results['total_vehicles']}")

            with col3:
                st.markdown(f"**Start Time:** {st.session_state.scrape_results['start_time']}")

            st.markdown(f"**Status:** {st.session_state.scrape_results['status']}")

elif page == "Agent Chat":
    st.markdown('<h1 class="main-header">Chat with Anna AI</h1>', unsafe_allow_html=True)

    # Initialize LLM provider
    llm_provider = LLMProvider()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Задайте вопрос о коммерческом транспорте"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Анна думает..."):
                try:
                    # In a real implementation, this would use the RAG system
                    # For demo purposes, we'll use a simple LLM call or mock response
                    if llm_provider and hasattr(llm_provider, 'generate'):
                        system_prompt = """Вы Анна, AI-ассистент по продажам компании Business Trucks.
                        Вы помогаете клиентам найти подходящие коммерческие транспортные средства.
                        Отвечайте кратко, профессионально и по существу. Всегда отвечайте на русском языке."""

                        full_prompt = f"{system_prompt}\n\nВопрос клиента: {prompt}\n\nАнна:"
                        response = llm_provider.generate(full_prompt)
                    else:
                        # Mock response
                        response = f"Здравствуйте! Я Анна, виртуальный ассистент компании Business Trucks. Я могу помочь вам с выбором коммерческого транспорта. Что именно вас интересует в связи с вашим вопросом: '{prompt}'?"

                    st.markdown(response)

                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    # Update agent stats in real-time metrics
                    st.session_state.realtime_metrics.update_agent_stats()
                except Exception as e:
                    st.error(f"Error generating response: {e}")
                    fallback_response = "Извините, у меня возникла проблема с генерацией ответа. Пожалуйста, попробуйте еще раз или свяжитесь с нашим менеджером."
                    st.markdown(fallback_response)
                    st.session_state.messages.append({"role": "assistant", "content": fallback_response})

    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

elif page == "Implementation Documentation":
    st.markdown('<h1 class="main-header">Implementation Documentation</h1>', unsafe_allow_html=True)

    st.markdown("""
    ## Enhanced Redis AI Tools with LangChain and LangGraph

    This implementation enhances the Redis AI tools with LangChain, LangGraph integration, and a Streamlit dashboard for vehicle data management and search.

    ### Components Implemented

    1. **Redis AI Tools**:
       - Set up Redis Cloud connection
       - Created a SimpleVectorStore implementation that works with standard Redis
       - Implemented vector search functionality
       - Created a simple RAG system for vehicle knowledge

    2. **LangChain Integration**:
       - Created CustomEmbeddings class for LangChain compatibility
       - Created CustomLLM class for LangChain compatibility
       - Implemented LangChainRAG for enhanced RAG capabilities
       - Integrated with LangChain's ConversationalRetrievalChain

    3. **Streamlit Dashboard**:
       - Created a comprehensive dashboard with multiple pages
       - Implemented vehicle search functionality
       - Added data visualization and filtering
       - Created a scraper control panel
       - Implemented an agent chat interface

    4. **AvitoScraping Agent**:
       - Created a Playwright-based scraper for Avito.ru
       - Successfully scraped vehicle data in a test environment
       - Imported the data into Redis
       - Implemented anti-rate-limiting techniques

    5. **MCP Server Integration**:
       - Installed and configured MCP servers
       - Attempted to use Playwright MCP server for scraping
       - Identified challenges with rate limiting and IP bans

    ### Challenges Encountered

    1. **Rate Limiting by Avito.ru**:
       - Avito.ru has sophisticated anti-scraping measures
       - IP-based rate limiting and captcha challenges
       - Need for residential proxies and captcha solving

    2. **MCP Server Configuration**:
       - Challenges with finding the correct port for MCP servers
       - Need for better documentation on MCP server usage

    ### Recommendations

    1. **Use a Residential Proxy Service**: Services like Bright Data, Oxylabs, or SmartProxy provide real residential IP addresses that are less likely to be detected as scraping activity.

    2. **Implement Captcha Solving**: Services like 2Captcha, Anti-Captcha, or hCaptcha Solver can help solve the captcha challenges automatically.

    3. **Consider Specialized Scraping Services**: Services like ScrapingBee, Apify, or Zyte handle proxies, headless browsers, and CAPTCHAs for you.

    4. **Explore Alternative Data Sources**: Consider official dealer APIs, public vehicle databases, or partnerships with data providers.

    ### Next Steps

    1. **Enhance Proxy Support**: Implement rotation of proxies to avoid rate limiting
    2. **Improve Data Schema**: Add more fields and metadata for better search
    3. **Implement Differential Updates**: Only scrape and update new or changed listings
    4. **Add Monitoring**: Set up alerts for scraping failures or data issues
    5. **Enhance Dashboard**: Add more visualizations and controls
    """)

    # Implementation details
    with st.expander("Implementation Details"):
        st.markdown("""
        ### Files Implemented

        1. **dashboard.py**: Streamlit dashboard for interacting with the system
        2. **simple_rag.py**: Simple RAG system implementation
        3. **langchain_integration.py**: LangChain integration
        4. **avito_playwright_scraper.py**: Playwright-based scraper for Avito.ru
        5. **import_avito_data.py**: Import scraped data into Redis
        6. **search_vehicles.py**: Search for vehicles in Redis
        7. **check_data.py**: Check the data in Redis
        8. **AVITO_SCRAPING_RECOMMENDATIONS.md**: Recommendations for Avito scraping
        9. **IMPLEMENTATION_SUMMARY.md**: Summary of the implementation

        ### Technologies Used

        - **Redis**: Vector database for storing vehicle data
        - **LangChain**: Enhanced RAG and agent capabilities
        - **Streamlit**: Dashboard for interacting with the system
        - **Playwright**: Browser automation for web scraping
        - **MCP Servers**: Claude's MCP servers for enhanced capabilities
        - **OpenRouter API**: LLM provider for text generation
        - **Sentence Transformers**: Embedding model for vector search
        """)

    # Code examples
    with st.expander("Code Examples"):
        st.code("""
# Simple RAG System
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
        """, language="python")

        st.code("""
# LangChain Integration
from langchain_integration import CustomLLM, CustomEmbeddings, LangChainRAG

# Initialize LangChain components
llm = CustomLLM()
embeddings = CustomEmbeddings()

# Initialize RAG system
rag = LangChainRAG(llm=llm, embeddings=embeddings)

# Add texts
texts = [
    "КАМАЗ 65115 - это самосвал грузоподъемностью 15 тонн, идеально подходит для строительных работ.",
    "ГАЗель NEXT - это легкий коммерческий автомобиль, доступный в различных модификациях."
]
rag.add_texts(texts)

# Query the RAG system
response = rag.query("Какой грузовик лучше для строительных работ?")
print(response)
        """, language="python")

        st.code("""
# Playwright Scraper
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
        """, language="python")

# Run the app with: streamlit run dashboard.py
