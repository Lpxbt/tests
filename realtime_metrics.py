"""
Real-time metrics for the dashboard.
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading

from redis_connection import get_redis_client
from redis_pubsub import get_redis_pubsub

# Channels
VEHICLE_UPDATES_CHANNEL = "vehicle_updates"
SCRAPER_UPDATES_CHANNEL = "scraper_updates"
SEARCH_UPDATES_CHANNEL = "search_updates"
AGENT_UPDATES_CHANNEL = "agent_updates"

class RealtimeMetrics:
    """
    Real-time metrics for the dashboard.
    """

    def __init__(self):
        """Initialize the real-time metrics."""
        self.redis_client = get_redis_client()
        self.redis_pubsub = get_redis_pubsub()

        # Metrics
        self.vehicle_count = 0
        self.vehicle_count_by_category = {}
        self.vehicle_count_by_brand = {}
        self.scraper_status = "idle"
        self.scraper_progress = 0
        self.scraper_last_update = None
        self.search_count = 0
        self.popular_searches = []
        self.agent_chat_count = 0

        # Last update time
        self.last_update = datetime.now()

        # Initialize metrics
        self._initialize_metrics()

        # Start background update thread
        self.update_thread = threading.Thread(target=self._background_update)
        self.update_thread.daemon = True
        self.update_thread.start()

    def _initialize_metrics(self) -> None:
        """Initialize metrics from Redis."""
        if not self.redis_client:
            print("Warning: Redis client is not available. Using default metrics.")
            # Initialize with default values
            self.vehicle_count = 0
            self.vehicle_count_by_category = {
                "trucks": 0, "tractors": 0, "buses": 0, "vans": 0,
                "construction": 0, "agricultural": 0, "trailers": 0
            }
            self.vehicle_count_by_brand = {}
            self.scraper_status = "idle"
            self.scraper_progress = 0
            self.scraper_last_update = None
            self.search_count = 0
            self.popular_searches = []
            self.agent_chat_count = 0
            return

        try:
            # Get vehicle count
            vehicle_keys = self.redis_client.keys("vehicle:*")
            self.vehicle_count = len(vehicle_keys)

            # Get vehicle count by category
            self.vehicle_count_by_category = {}
            categories = ["trucks", "tractors", "buses", "vans", "construction", "agricultural", "trailers"]
            for category in categories:
                count = self.redis_client.scard(f"category:{category}")
                self.vehicle_count_by_category[category] = count

            # Get vehicle count by brand
            self.vehicle_count_by_brand = {}
            brand_keys = self.redis_client.keys("brand:*")
            for brand_key in brand_keys:
                brand = brand_key.decode("utf-8").split(":")[1]
                count = self.redis_client.scard(brand_key)
                self.vehicle_count_by_brand[brand] = count

            # Get scraper status
            scraper_status = self.redis_client.get("scraper:status")
            if scraper_status:
                self.scraper_status = scraper_status.decode("utf-8")

            # Get scraper progress
            scraper_progress = self.redis_client.get("scraper:progress")
            if scraper_progress:
                self.scraper_progress = float(scraper_progress.decode("utf-8"))

            # Get scraper last update
            scraper_last_update = self.redis_client.get("scraper:last_update")
            if scraper_last_update:
                self.scraper_last_update = datetime.fromisoformat(scraper_last_update.decode("utf-8"))

            # Get search count
            search_count = self.redis_client.get("search:count")
            if search_count:
                self.search_count = int(search_count.decode("utf-8"))

            # Get popular searches
            popular_searches = self.redis_client.zrevrange("search:popular", 0, 9, withscores=True)
            self.popular_searches = [(search.decode("utf-8"), int(count)) for search, count in popular_searches]

            # Get agent chat count
            agent_chat_count = self.redis_client.get("agent:chat_count")
            if agent_chat_count:
                self.agent_chat_count = int(agent_chat_count.decode("utf-8"))

            # Subscribe to updates
            self.redis_pubsub.subscribe(VEHICLE_UPDATES_CHANNEL, self._handle_vehicle_update)
            self.redis_pubsub.subscribe(SCRAPER_UPDATES_CHANNEL, self._handle_scraper_update)
            self.redis_pubsub.subscribe(SEARCH_UPDATES_CHANNEL, self._handle_search_update)
            self.redis_pubsub.subscribe(AGENT_UPDATES_CHANNEL, self._handle_agent_update)

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error initializing metrics: {e}")

    def _background_update(self) -> None:
        """Background update thread."""
        while True:
            try:
                # Check if Redis client is available
                if self.redis_client:
                    # Try to ping Redis to check connection
                    try:
                        self.redis_client.ping()
                        # Update metrics from Redis every 5 seconds
                        self._update_metrics_from_redis()
                    except Exception as e:
                        print(f"Error connecting to Redis: {e}")
                        # Try to reconnect to Redis
                        self.redis_client = get_redis_client()
                        # Update last update time even if Redis is not available
                        self.last_update = datetime.now()
                else:
                    # Try to reconnect to Redis
                    self.redis_client = get_redis_client()
                    # Update last update time even if Redis is not available
                    self.last_update = datetime.now()

                # Sleep for 5 seconds
                time.sleep(5)
            except Exception as e:
                print(f"Error in background update: {e}")
                # Update last update time even if there's an error
                self.last_update = datetime.now()
                time.sleep(5)

    def _update_metrics_from_redis(self) -> None:
        """Update metrics from Redis."""
        if not self.redis_client:
            return

        try:
            # Get vehicle count
            vehicle_keys = self.redis_client.keys("vehicle:*")
            self.vehicle_count = len(vehicle_keys)

            # Get vehicle count by category
            categories = ["trucks", "tractors", "buses", "vans", "construction", "agricultural", "trailers"]
            for category in categories:
                count = self.redis_client.scard(f"category:{category}")
                self.vehicle_count_by_category[category] = count

            # Get vehicle count by brand
            brand_keys = self.redis_client.keys("brand:*")
            for brand_key in brand_keys:
                brand = brand_key.decode("utf-8").split(":")[1]
                count = self.redis_client.scard(brand_key)
                self.vehicle_count_by_brand[brand] = count

            # Get popular searches
            popular_searches = self.redis_client.zrevrange("search:popular", 0, 9, withscores=True)
            self.popular_searches = [(search.decode("utf-8"), int(count)) for search, count in popular_searches]

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error updating metrics from Redis: {e}")

    def _handle_vehicle_update(self, data: Dict[str, Any]) -> None:
        """
        Handle vehicle update.

        Args:
            data: Update data
        """
        try:
            # Update vehicle count
            if "count" in data:
                self.vehicle_count = data["count"]

            # Update vehicle count by category
            if "categories" in data:
                for category, count in data["categories"].items():
                    self.vehicle_count_by_category[category] = count

            # Update vehicle count by brand
            if "brands" in data:
                for brand, count in data["brands"].items():
                    self.vehicle_count_by_brand[brand] = count

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error handling vehicle update: {e}")

    def _handle_scraper_update(self, data: Dict[str, Any]) -> None:
        """
        Handle scraper update.

        Args:
            data: Update data
        """
        try:
            # Update scraper status
            if "status" in data:
                self.scraper_status = data["status"]

            # Update scraper progress
            if "progress" in data:
                self.scraper_progress = data["progress"]

            # Update scraper last update
            if "last_update" in data:
                self.scraper_last_update = datetime.fromisoformat(data["last_update"])

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error handling scraper update: {e}")

    def _handle_search_update(self, data: Dict[str, Any]) -> None:
        """
        Handle search update.

        Args:
            data: Update data
        """
        try:
            # Update search count
            if "count" in data:
                self.search_count = data["count"]

            # Update popular searches
            if "popular" in data:
                self.popular_searches = data["popular"]

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error handling search update: {e}")

    def _handle_agent_update(self, data: Dict[str, Any]) -> None:
        """
        Handle agent update.

        Args:
            data: Update data
        """
        try:
            # Update agent chat count
            if "chat_count" in data:
                self.agent_chat_count = data["chat_count"]

            # Update last update time
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error handling agent update: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.

        Returns:
            Dictionary with all metrics
        """
        return {
            "vehicle_count": self.vehicle_count,
            "vehicle_count_by_category": self.vehicle_count_by_category,
            "vehicle_count_by_brand": self.vehicle_count_by_brand,
            "scraper_status": self.scraper_status,
            "scraper_progress": self.scraper_progress,
            "scraper_last_update": self.scraper_last_update,
            "search_count": self.search_count,
            "popular_searches": self.popular_searches,
            "agent_chat_count": self.agent_chat_count,
            "last_update": self.last_update
        }

    def publish_vehicle_update(self, data: Dict[str, Any]) -> bool:
        """
        Publish vehicle update.

        Args:
            data: Update data

        Returns:
            True if successful, False otherwise
        """
        return self.redis_pubsub.publish(VEHICLE_UPDATES_CHANNEL, data)

    def publish_scraper_update(self, data: Dict[str, Any]) -> bool:
        """
        Publish scraper update.

        Args:
            data: Update data

        Returns:
            True if successful, False otherwise
        """
        return self.redis_pubsub.publish(SCRAPER_UPDATES_CHANNEL, data)

    def publish_search_update(self, data: Dict[str, Any]) -> bool:
        """
        Publish search update.

        Args:
            data: Update data

        Returns:
            True if successful, False otherwise
        """
        return self.redis_pubsub.publish(SEARCH_UPDATES_CHANNEL, data)

    def publish_agent_update(self, data: Dict[str, Any]) -> bool:
        """
        Publish agent update.

        Args:
            data: Update data

        Returns:
            True if successful, False otherwise
        """
        return self.redis_pubsub.publish(AGENT_UPDATES_CHANNEL, data)

    def update_search_stats(self, query: str) -> None:
        """
        Update search statistics.

        Args:
            query: Search query
        """
        if not self.redis_client:
            return

        try:
            # Increment search count
            self.redis_client.incr("search:count")
            self.search_count += 1

            # Add to popular searches
            self.redis_client.zincrby("search:popular", 1, query)

            # Publish update
            self.publish_search_update({
                "count": self.search_count,
                "query": query
            })
        except Exception as e:
            print(f"Error updating search stats: {e}")

    def update_agent_stats(self) -> None:
        """Update agent statistics."""
        if not self.redis_client:
            return

        try:
            # Increment agent chat count
            self.redis_client.incr("agent:chat_count")
            self.agent_chat_count += 1

            # Publish update
            self.publish_agent_update({
                "chat_count": self.agent_chat_count
            })
        except Exception as e:
            print(f"Error updating agent stats: {e}")

    def update_scraper_status(self, status: str, progress: float = 0.0) -> None:
        """
        Update scraper status.

        Args:
            status: Scraper status
            progress: Scraper progress (0.0 to 1.0)
        """
        if not self.redis_client:
            return

        try:
            # Update scraper status
            self.redis_client.set("scraper:status", status)
            self.scraper_status = status

            # Update scraper progress
            self.redis_client.set("scraper:progress", str(progress))
            self.scraper_progress = progress

            # Update scraper last update
            now = datetime.now()
            self.redis_client.set("scraper:last_update", now.isoformat())
            self.scraper_last_update = now

            # Publish update
            self.publish_scraper_update({
                "status": status,
                "progress": progress,
                "last_update": now.isoformat()
            })
        except Exception as e:
            print(f"Error updating scraper status: {e}")

# Create a global instance
realtime_metrics = RealtimeMetrics()

def get_realtime_metrics() -> RealtimeMetrics:
    """
    Get the real-time metrics instance.

    Returns:
        Real-time metrics instance
    """
    return realtime_metrics
