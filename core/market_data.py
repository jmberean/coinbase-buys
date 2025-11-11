"""
Market data providers for real-time and historical price information.

Handles WebSocket connections with automatic reconnection and REST API fallback.
"""

import json
import logging
import threading
import time
from decimal import Decimal
from typing import Optional, Tuple

from coinbase.rest import RESTClient
from coinbase.websocket import WSClient

from models.types import MarketData, WebSocketConfig
from utils.validators import validate_market_data

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """
    Provides real-time market data with WebSocket and REST fallback.

    Features:
    - WebSocket streaming for low-latency updates
    - Automatic reconnection with exponential backoff
    - REST API fallback for reliability
    - Thread-safe data access
    - Graceful shutdown
    """

    def __init__(
        self,
        rest_client: RESTClient,
        api_key: str,
        api_secret: str,
        products: list[str],
        config: WebSocketConfig
    ):
        """
        Initialize market data provider.

        Args:
            rest_client: Initialized REST client
            api_key: Coinbase API key
            api_secret: Coinbase API secret
            products: List of product IDs to subscribe to
            config: WebSocket configuration
        """
        self.rest_client = rest_client
        self.api_key = api_key
        self.api_secret = api_secret
        self.products = products
        self.config = config

        # Market data storage
        self.market_data: dict[str, MarketData] = {}
        self.market_data_lock = threading.Lock()

        # WebSocket state
        self.ws_client: Optional[WSClient] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()  # FIXED: Proper shutdown (BUG FIX #2)
        self.data_received = False

        # Reconnection state
        self.reconnection_attempts = 0
        self.last_connection_time = 0.0

    def start(self) -> None:
        """Start WebSocket connection in background thread."""
        self.stop_event.clear()
        self.ws_thread = threading.Thread(target=self._websocket_loop, daemon=True)
        self.ws_thread.start()
        logger.info("🔌 WebSocket thread started")

    def stop(self) -> None:
        """
        Stop WebSocket connection gracefully.

        FIXED: Proper cleanup (BUG FIX #2)
        """
        logger.info("⏹️ Stopping WebSocket connection...")
        self.stop_event.set()

        # Close WebSocket client
        if self.ws_client:
            try:
                self.ws_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebSocket: {e}")

        # Wait for thread to finish (with timeout)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)

        logger.info("✅ WebSocket stopped")

    def _websocket_loop(self) -> None:
        """
        Main WebSocket loop with reconnection logic.

        FIXED: Proper shutdown and reconnection (BUG FIX #2, #19)
        """
        while not self.stop_event.is_set():
            try:
                self._connect_websocket()
                self._subscribe_to_products()

                # Keep alive loop
                while not self.stop_event.is_set():
                    time.sleep(1)

                # Clean exit
                break

            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")

                if not self.config.enable_reconnection:
                    logger.error("🚫 Reconnection disabled, stopping WebSocket")
                    break

                # Check reconnection attempts
                self.reconnection_attempts += 1
                if self.reconnection_attempts > self.config.max_reconnection_attempts:
                    logger.error(
                        f"🚨 Max reconnection attempts ({self.config.max_reconnection_attempts}) "
                        "reached, stopping WebSocket"
                    )
                    break

                # Exponential backoff
                delay = (
                    self.config.reconnection_delay *
                    (self.config.reconnection_backoff_multiplier ** (self.reconnection_attempts - 1))
                )
                delay = min(delay, 60)  # Cap at 60 seconds

                logger.info(
                    f"🔄 Reconnecting in {delay}s "
                    f"(attempt {self.reconnection_attempts}/{self.config.max_reconnection_attempts})"
                )

                # Wait with ability to interrupt
                if self.stop_event.wait(timeout=delay):
                    break  # Stop event was set during wait

    def _connect_websocket(self) -> None:
        """Establish WebSocket connection."""
        logger.info("🔌 Connecting to WebSocket...")

        self.ws_client = WSClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            on_message=self._on_message
        )

        self.ws_client.open()
        self.last_connection_time = time.time()
        time.sleep(3)  # Allow connection to establish

        logger.info("✅ WebSocket connected")

    def _subscribe_to_products(self) -> None:
        """Subscribe to product ticker channels."""
        if not self.ws_client:
            return

        logger.info(f"📡 Subscribing to ticker for {len(self.products)} products...")
        self.ws_client.subscribe(product_ids=self.products, channels=["ticker"])
        time.sleep(3)  # Allow subscription to process

        # Reset reconnection counter on successful subscription
        self.reconnection_attempts = 0

    def _on_message(self, msg: str | dict) -> None:
        """
        Process WebSocket messages.

        Args:
            msg: WebSocket message (string or dict)
        """
        try:
            # Parse message if string
            if isinstance(msg, str):
                msg = json.loads(msg)

            # Handle ticker updates
            if msg.get('channel') == 'ticker':
                self._process_ticker_update(msg)

            # Handle subscription confirmations
            elif msg.get('channel') == 'subscriptions':
                logger.info("✅ Subscription confirmed")

        except Exception as e:
            logger.debug(f"⚠️ WebSocket message error: {e}")

    def _process_ticker_update(self, msg: dict) -> None:
        """
        Process ticker update message.

        Args:
            msg: Ticker message from WebSocket
        """
        for event in msg.get('events', []):
            if event.get('type') not in ['snapshot', 'update']:
                continue

            for ticker in event.get('tickers', []):
                if ticker.get('type') != 'ticker':
                    continue

                product_id = ticker.get('product_id')
                if product_id not in self.products:
                    continue

                best_bid = ticker.get('best_bid')
                best_ask = ticker.get('best_ask')

                if not best_bid or not best_ask:
                    continue

                # Convert to Decimal
                bid_decimal = Decimal(str(best_bid))
                ask_decimal = Decimal(str(best_ask))

                # Validate market data
                valid, _ = validate_market_data(bid_decimal, ask_decimal)
                if not valid:
                    continue

                # Store market data
                with self.market_data_lock:
                    self.market_data[product_id] = {
                        'best_bid': bid_decimal,
                        'best_ask': ask_decimal,
                        'timestamp': time.time()
                    }

                self.data_received = True
                logger.debug(f"📊 WS {product_id}: ${bid_decimal:.6f}|${ask_decimal:.6f}")

    def get_market_data(self, product_id: str) -> Tuple[Optional[Decimal], Optional[Decimal], bool]:
        """
        Get current market data for a product.

        Tries WebSocket data first, falls back to REST API if stale or unavailable.

        Args:
            product_id: Trading pair identifier

        Returns:
            Tuple of (best_bid, best_ask, success)
        """
        # Try WebSocket data first
        with self.market_data_lock:
            if product_id in self.market_data:
                data = self.market_data[product_id]
                age = time.time() - data['timestamp']

                # Use if fresh
                if age < self.config.data_freshness_timeout:
                    return data['best_bid'], data['best_ask'], True

                logger.debug(f"⚠️ WebSocket data stale for {product_id} ({age:.1f}s old)")

        # Fallback to REST API
        return self._get_rest_market_data(product_id)

    def _get_rest_market_data(self, product_id: str) -> Tuple[Optional[Decimal], Optional[Decimal], bool]:
        """
        Get market data from REST API.

        Args:
            product_id: Trading pair identifier

        Returns:
            Tuple of (best_bid, best_ask, success)
        """
        try:
            response = self.rest_client.get_product_book(product_id, limit=1)

            if not hasattr(response, 'pricebook') or not response.pricebook:
                return None, None, False

            pricebook = response.pricebook

            if not pricebook.asks or not pricebook.bids:
                return None, None, False

            best_ask = Decimal(pricebook.asks[0]['price'])
            best_bid = Decimal(pricebook.bids[0]['price'])

            # Validate
            valid, _ = validate_market_data(best_bid, best_ask)
            if not valid:
                return None, None, False

            logger.debug(f"📊 REST {product_id}: ${best_bid:.6f}|${best_ask:.6f}")
            return best_bid, best_ask, True

        except Exception as e:
            logger.warning(f"⚠️ REST market data failed for {product_id}: {e}")
            return None, None, False

    def wait_for_data(self, timeout: int = 15) -> bool:
        """
        Wait for WebSocket to receive initial data.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if data received, False if timeout
        """
        logger.info("⏳ Waiting for WebSocket market data...")

        for i in range(timeout):
            if self.stop_event.is_set():
                return False

            time.sleep(1)

            with self.market_data_lock:
                available_products = list(self.market_data.keys())

            if len(available_products) == len(self.products):
                logger.info(f"✅ WebSocket ready! Got data for: {available_products}")
                return True
            elif available_products:
                logger.debug(f"    📊 Got {len(available_products)}/{len(self.products)} products...")

        logger.warning("⚠️ WebSocket timeout, using REST-only mode")
        return False
