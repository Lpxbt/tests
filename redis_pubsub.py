"""
Redis Pub/Sub module for real-time updates.
"""
import os
import json
import threading
import time
from typing import Dict, Any, Callable, List, Optional
from redis.client import Redis, PubSub

from redis_connection import get_redis_client

class RedisPubSub:
    """
    Redis Pub/Sub for real-time updates.
    """

    def __init__(self):
        """Initialize the Redis Pub/Sub."""
        self.redis_client = get_redis_client()
        self.pubsub: Optional[PubSub] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.thread = None
        self.running = False

        # Initialize if Redis is available
        if self.redis_client:
            self.pubsub = self.redis_client.pubsub()

    def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a channel.

        Args:
            channel: Channel name
            message: Message to publish

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            # Convert message to JSON
            message_json = json.dumps(message)

            # Publish message
            self.redis_client.publish(channel, message_json)
            return True
        except Exception as e:
            print(f"Error publishing message: {e}")
            return False

    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a channel.

        Args:
            channel: Channel name
            callback: Callback function to call when a message is received

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client or not self.pubsub:
            return False

        try:
            # Subscribe to channel
            self.pubsub.subscribe(channel)

            # Add callback to subscribers
            if channel not in self.subscribers:
                self.subscribers[channel] = []
            self.subscribers[channel].append(callback)

            # Start listener thread if not already running
            if not self.running:
                self.start_listener()

            return True
        except Exception as e:
            print(f"Error subscribing to channel: {e}")
            return False

    def unsubscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Unsubscribe from a channel.

        Args:
            channel: Channel name
            callback: Callback function to remove

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client or not self.pubsub:
            return False

        try:
            # Remove callback from subscribers
            if channel in self.subscribers:
                if callback in self.subscribers[channel]:
                    self.subscribers[channel].remove(callback)

                # Unsubscribe if no more callbacks
                if not self.subscribers[channel]:
                    self.pubsub.unsubscribe(channel)
                    del self.subscribers[channel]

            # Stop listener thread if no more subscribers
            if not self.subscribers and self.running:
                self.stop_listener()

            return True
        except Exception as e:
            print(f"Error unsubscribing from channel: {e}")
            return False

    def start_listener(self) -> None:
        """Start the listener thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._listener_thread)
        self.thread.daemon = True
        self.thread.start()

    def stop_listener(self) -> None:
        """Stop the listener thread."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _listener_thread(self) -> None:
        """Listener thread function."""
        if not self.pubsub:
            return

        while self.running:
            try:
                # Check if Redis client is still connected
                if not self.redis_client:
                    # Try to reconnect
                    self.redis_client = get_redis_client()
                    if self.redis_client:
                        # Reinitialize pubsub
                        self.pubsub = self.redis_client.pubsub()
                        # Resubscribe to all channels
                        for channel, callbacks in self.subscribers.items():
                            self.pubsub.subscribe(channel)
                    else:
                        # Sleep and try again later
                        time.sleep(5.0)
                        continue

                # Try to ping Redis to check connection
                try:
                    self.redis_client.ping()
                except Exception:
                    # Connection lost, set client to None and try again later
                    self.redis_client = None
                    self.pubsub = None
                    time.sleep(5.0)
                    continue

                # Get message
                message = self.pubsub.get_message(timeout=0.1)

                if message and message['type'] == 'message':
                    # Parse message
                    channel = message['channel'].decode('utf-8')
                    data = json.loads(message['data'].decode('utf-8'))

                    # Call callbacks
                    if channel in self.subscribers:
                        for callback in self.subscribers[channel]:
                            try:
                                callback(data)
                            except Exception as e:
                                print(f"Error in callback: {e}")

                # Sleep to avoid high CPU usage
                time.sleep(0.01)
            except Exception as e:
                print(f"Error in listener thread: {e}")
                time.sleep(5.0)  # Sleep longer on error

# Create a global instance
redis_pubsub = RedisPubSub()

def get_redis_pubsub() -> RedisPubSub:
    """
    Get the Redis Pub/Sub instance.

    Returns:
        Redis Pub/Sub instance
    """
    return redis_pubsub
