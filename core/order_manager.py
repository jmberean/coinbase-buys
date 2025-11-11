"""
Order management and execution for cryptocurrency trading.

Handles order placement, tracking, and fill detection with retry logic.
"""

import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, Tuple

from coinbase.rest import RESTClient

from core.market_data import MarketDataProvider
from core.precision import PrecisionDetector
from models.types import (
    CircuitBreakerConfig,
    OrderResult,
    OrderStatus,
    PrecisionData,
    ProductSpec,
    TradeResult,
    TradingConfig,
)
from strategies.limit_price import PricingStrategy, DEFAULT_STRATEGY
from utils.validators import validate_order_size, sanitize_error_message

logger = logging.getLogger(__name__)


class OrderPlacer:
    """Handles order placement with precision formatting."""

    def __init__(self, rest_client: RESTClient, min_api_interval: float):
        """
        Initialize order placer.

        Args:
            rest_client: Coinbase REST client
            min_api_interval: Minimum time between API calls
        """
        self.rest_client = rest_client
        self.min_api_interval = min_api_interval
        self.last_api_call = 0.0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        time_since_last = time.time() - self.last_api_call
        if time_since_last < self.min_api_interval:
            time.sleep(self.min_api_interval - time_since_last)

    def place_limit_order(
        self,
        product_id: str,
        quote_amount: float,
        limit_price: Decimal,
        precision_data: PrecisionData,
        dry_run: bool = False
    ) -> OrderResult:
        """
        Place a post-only limit buy order.

        Args:
            product_id: Trading pair identifier
            quote_amount: Amount in USD to spend
            limit_price: Limit price for the order
            precision_data: Precision information for the product
            dry_run: If True, simulate order without placing

        Returns:
            OrderResult with success status and order ID or error
        """
        try:
            # Calculate base size
            base_size = Decimal(str(quote_amount)) / limit_price
            base_size = (
                base_size / precision_data['size_increment']
            ).quantize(Decimal('1')) * precision_data['size_increment']

            if base_size <= 0:
                return {
                    'success': False,
                    'order_id': None,
                    'error_message': 'Calculated size is zero or negative'
                }

            # Format limit price with correct precision
            formatted_limit_price = limit_price.quantize(precision_data['price_increment'])

            # Dry run mode
            if dry_run:
                logger.info(
                    f"    🧪 DRY RUN: Would place order - "
                    f"size: {base_size}, price: ${formatted_limit_price}"
                )
                return {
                    'success': True,
                    'order_id': f"dry-run-{uuid.uuid4()}",
                    'error_message': None
                }

            # Rate limiting
            self._rate_limit()

            # Place actual order
            response = self.rest_client.limit_order_gtc_buy(
                client_order_id=str(uuid.uuid4()),
                product_id=product_id,
                base_size=str(base_size),
                limit_price=str(formatted_limit_price),
                post_only=True
            )

            self.last_api_call = time.time()

            # Check response
            if hasattr(response, 'success') and response.success:
                order_id = response.success_response.get('order_id')
                return {
                    'success': True,
                    'order_id': order_id,
                    'error_message': None
                }
            else:
                error_msg = str(getattr(response, 'error_response', 'Unknown error'))
                return {
                    'success': False,
                    'order_id': None,
                    'error_message': error_msg
                }

        except Exception as e:
            error_msg = sanitize_error_message(str(e))
            return {
                'success': False,
                'order_id': None,
                'error_message': error_msg
            }

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successful, False otherwise
        """
        try:
            self._rate_limit()
            self.rest_client.cancel_orders([order_id])
            self.last_api_call = time.time()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Cancel failed: {sanitize_error_message(str(e))}")
            return False


class OrderTracker:
    """Tracks order status and fill detection."""

    def __init__(self, rest_client: RESTClient, min_api_interval: float):
        """
        Initialize order tracker.

        Args:
            rest_client: Coinbase REST client
            min_api_interval: Minimum time between API calls
        """
        self.rest_client = rest_client
        self.min_api_interval = min_api_interval
        self.last_api_call = 0.0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        time_since_last = time.time() - self.last_api_call
        if time_since_last < self.min_api_interval:
            time.sleep(self.min_api_interval - time_since_last)

    def check_order_status(
        self,
        order_id: str,
        dry_run: bool = False
    ) -> Tuple[OrderStatus, Optional[Decimal], Optional[Decimal], bool]:
        """
        Check order status with retry logic.

        FIXED: Added retry logic for better reliability (BUG FIX #4)
        UPDATED: Now returns filled_value for partial fill tracking

        Args:
            order_id: Order ID to check
            dry_run: If True, simulate status check

        Returns:
            Tuple of (status, filled_size, filled_value, success)
        """
        if dry_run:
            # Simulate filled order in dry run
            return 'FILLED', Decimal('0.1'), Decimal('10.0'), True

        # Try twice for better reliability
        for attempt in range(2):
            try:
                self._rate_limit()
                response = self.rest_client.get_order(order_id)
                self.last_api_call = time.time()

                if hasattr(response, 'order') and response.order:
                    status = response.order.status
                    filled_size = Decimal(str(response.order.filled_size or '0'))
                    filled_value = Decimal(str(response.order.filled_value or '0'))
                    return status, filled_size, filled_value, True

            except Exception as e:
                logger.warning(
                    f"⚠️ Order check attempt {attempt + 1} failed: "
                    f"{sanitize_error_message(str(e))}"
                )
                if attempt == 0:
                    time.sleep(0.5)  # Brief pause before retry

        return 'UNKNOWN', None, None, False


class TradingEngine:
    """
    Core trading engine with improved order management.

    Handles trade execution with:
    - Intelligent price chasing
    - Circuit breakers
    - Fill detection
    - Error recovery
    """

    def __init__(
        self,
        rest_client: RESTClient,
        market_data: MarketDataProvider,
        precision_detector: PrecisionDetector,
        config: TradingConfig,
        circuit_breaker_config: CircuitBreakerConfig,
        pricing_strategy: PricingStrategy = DEFAULT_STRATEGY,
        dry_run: bool = False
    ):
        """
        Initialize trading engine.

        Args:
            rest_client: Coinbase REST client
            market_data: Market data provider
            precision_detector: Precision detector
            config: Trading configuration
            circuit_breaker_config: Circuit breaker configuration
            pricing_strategy: Pricing strategy to use
            dry_run: If True, simulate trades without placing real orders
        """
        self.rest_client = rest_client
        self.market_data = market_data
        self.precision_detector = precision_detector
        self.config = config
        self.circuit_breaker_config = circuit_breaker_config
        self.pricing_strategy = pricing_strategy
        self.dry_run = dry_run

        # Create order placer and tracker
        self.order_placer = OrderPlacer(rest_client, config.min_api_interval)
        self.order_tracker = OrderTracker(rest_client, config.min_api_interval)

        # Track pending orders for cleanup
        self.pending_orders: list[str] = []

    def execute_trade(
        self,
        product_id: str,
        quote_amount: float,
        product_spec: ProductSpec
    ) -> TradeResult:
        """
        Execute a single trade with partial fill tracking and cumulative fills.

        FIXED: Multiple bug fixes applied (BUG FIX #3, #4, #7, #8)
        UPDATED: Now handles partial fills with cumulative tracking

        Args:
            product_id: Trading pair identifier
            quote_amount: Amount in USD to spend
            product_spec: Product specification

        Returns:
            TradeResult with execution details
        """
        logger.info(f"\n⚡ Trading {product_id} (${quote_amount})")

        start_time = time.time()
        attempts = 0

        # Cumulative fill tracking
        target_usd = Decimal(str(quote_amount))
        total_filled_size = Decimal('0')
        total_filled_value = Decimal('0')

        # Current order state
        current_order_id: Optional[str] = None
        last_limit_price: Optional[Decimal] = None
        precision_failures = 0
        post_only_failures = 0
        precision_data: Optional[PrecisionData] = None
        order_place_time: Optional[float] = None

        while (time.time() - start_time) < self.config.max_chase_time:

            # FIXED: Check attempt limit properly (BUG FIX #3)
            if attempts >= self.config.max_chase_attempts:
                logger.warning(f"    ⏰ Max attempts ({attempts}) reached")
                break

            # Circuit breakers
            if precision_failures >= self.circuit_breaker_config.max_precision_failures:
                logger.error(f"    🚨 Too many precision failures ({precision_failures})")
                break

            if post_only_failures >= self.circuit_breaker_config.max_post_only_failures:
                logger.error(f"    🚨 Too many post-only failures ({post_only_failures})")
                break

            # Get market data
            best_bid, best_ask, success = self.market_data.get_market_data(product_id)
            if not success or not best_bid or not best_ask:
                logger.warning(f"    ⚠️ Invalid market data, retrying...")
                time.sleep(1)
                continue

            # Detect precision once
            if precision_data is None:
                precision_data = self.precision_detector.detect(product_id, best_bid, best_ask)

            # Calculate limit price
            limit_price, strategy = self.pricing_strategy.calculate(
                best_bid, best_ask, precision_data['price_increment']
            )

            # Determine if we should place an order
            should_place_order = False
            action = "UNKNOWN"

            if current_order_id is None:
                # No existing order - place initial order
                should_place_order = True
                action = "INITIAL"

            else:
                # FIXED: Check order status after minimum wait time (BUG FIX #4)
                if order_place_time and (time.time() - order_place_time) >= self.config.min_order_wait_time:
                    status, filled_size, filled_value, status_ok = self.order_tracker.check_order_status(
                        current_order_id, self.dry_run
                    )

                    # Handle any fills (partial or full)
                    if status_ok and filled_size and filled_size > 0:
                        # Accumulate this fill
                        total_filled_size += filled_size
                        total_filled_value += filled_value

                        completion = (total_filled_value / target_usd) * 100

                        logger.info(
                            f"    ✅ Filled {filled_size} for ${filled_value:.2f} "
                            f"(Progress: ${total_filled_value:.2f}/${target_usd:.2f} = {completion:.1f}%)"
                        )

                        # Check if we've reached target
                        if completion >= self.config.completion_threshold_percentage:
                            execution_time = time.time() - start_time
                            logger.info(f"    🎯 Target reached ({completion:.1f}%)!")
                            return TradeResult(
                                product_id=product_id,
                                success=True,
                                quote_amount=quote_amount,
                                filled_size=total_filled_size,
                                filled_value=total_filled_value,
                                execution_time=execution_time,
                                attempts=attempts,
                                completion_percentage=float(completion)
                            )

                        # Partial fill - cancel remaining and place new order for remainder
                        if status == 'OPEN':
                            logger.info(f"    📊 Partial fill, continuing for remaining ${target_usd - total_filled_value:.2f}")
                            self.order_placer.cancel_order(current_order_id)
                            current_order_id = None
                            should_place_order = True
                            action = "PARTIAL"
                            order_place_time = None

                    elif status_ok and status in ['CANCELLED', 'EXPIRED', 'FAILED']:
                        logger.warning(f"    ⚠️ Order {status}, retrying...")
                        current_order_id = None
                        should_place_order = True
                        action = "RETRY"
                        order_place_time = None

                # Consider price chasing
                if (
                    current_order_id is not None
                    and order_place_time
                    and (time.time() - order_place_time) >= self.config.min_chase_wait_time
                ):
                    # Calculate significant movement threshold
                    threshold = (
                        precision_data['market_increment'] *
                        self.config.chase_threshold_multiplier
                    )

                    if last_limit_price and abs(limit_price - last_limit_price) >= threshold:
                        move_amount = limit_price - last_limit_price
                        logger.info(
                            f"    🏃 Market move detected! "
                            f"${last_limit_price:.{precision_data['price_precision']}f} → "
                            f"${limit_price:.{precision_data['price_precision']}f} "
                            f"({move_amount:+.{precision_data['market_precision']}f})"
                        )

                        # FIXED: Double-check order not filled before canceling (BUG FIX #4)
                        status, filled_size, filled_value, status_ok = self.order_tracker.check_order_status(
                            current_order_id, self.dry_run
                        )

                        # Check for any fills before chasing
                        if status_ok and filled_size and filled_size > 0:
                            # Accumulate fills
                            total_filled_size += filled_size
                            total_filled_value += filled_value
                            completion = (total_filled_value / target_usd) * 100

                            logger.info(f"    ✅ Filled {filled_size} for ${filled_value:.2f} during chase check!")
                            logger.info(f"    📊 Progress: {completion:.1f}%")

                            # Check if target reached
                            if completion >= self.config.completion_threshold_percentage:
                                execution_time = time.time() - start_time
                                return TradeResult(
                                    product_id=product_id,
                                    success=True,
                                    quote_amount=quote_amount,
                                    filled_size=total_filled_size,
                                    filled_value=total_filled_value,
                                    execution_time=execution_time,
                                    attempts=attempts,
                                    completion_percentage=float(completion)
                                )

                        # Cancel and chase
                        self.order_placer.cancel_order(current_order_id)
                        logger.debug(f"    ✅ Cancelled order for price chasing")
                        time.sleep(1)

                        current_order_id = None
                        should_place_order = True
                        action = f"CHASE"
                        order_place_time = None

            # Place order if needed
            if should_place_order:
                attempts += 1  # FIXED: Increment after deciding to place (BUG FIX #3)

                # Calculate remaining budget to spend
                remaining_usd = float(target_usd - total_filled_value)

                logger.info(
                    f"    ⚡ {action} #{attempts}: "
                    f"Remaining=${remaining_usd:.2f} | "
                    f"Bid=${best_bid:.{precision_data['market_precision']}f} | "
                    f"Ask=${best_ask:.{precision_data['market_precision']}f} | "
                    f"Limit=${limit_price:.{precision_data['price_precision']}f} ({strategy})"
                )

                # FIXED: Validate order size before placing (BUG FIX #7)
                # Use remaining budget, not original quote_amount
                base_size = Decimal(str(remaining_usd)) / limit_price
                base_size = (
                    base_size / precision_data['size_increment']
                ).quantize(Decimal('1')) * precision_data['size_increment']

                valid, issues = validate_order_size(product_id, remaining_usd, base_size, product_spec)
                if not valid:
                    logger.error(f"    ❌ Order validation failed: {', '.join(issues)}")
                    break

                # Place order for remaining amount
                result = self.order_placer.place_limit_order(
                    product_id, remaining_usd, limit_price, precision_data, self.dry_run
                )

                if result['success']:
                    current_order_id = result['order_id']
                    last_limit_price = limit_price
                    order_place_time = time.time()
                    precision_failures = 0
                    post_only_failures = 0

                    # Track for cleanup
                    if current_order_id and not self.dry_run:
                        self.pending_orders.append(current_order_id)

                    logger.info(f"    ✅ Order placed successfully")

                else:
                    error_msg = result['error_message'] or 'Unknown error'
                    logger.warning(f"    ❌ Order failed: {error_msg}")

                    # Handle specific errors
                    if 'INVALID_LIMIT_PRICE_POST_ONLY' in error_msg:
                        post_only_failures += 1
                        continue

                    elif 'INVALID_PRICE_PRECISION' in error_msg:
                        adjusted = self.precision_detector.adjust_price_precision(product_id, error_msg)
                        if adjusted:
                            precision_data = adjusted
                            logger.info(f"    🔄 Retrying with adjusted price precision")
                            continue
                        else:
                            precision_failures += 1
                            continue

                    elif 'INVALID_SIZE_PRECISION' in error_msg:
                        adjusted = self.precision_detector.adjust_size_precision(product_id, error_msg)
                        if adjusted:
                            precision_data = adjusted
                            logger.info(f"    🔄 Retrying with adjusted size precision")
                            continue
                        else:
                            precision_failures += 1
                            continue

                    elif 'INSUFFICIENT_FUND' in error_msg:
                        logger.error(f"    💰 Insufficient funds - stopping trade")
                        break

                    else:
                        time.sleep(1)
                        continue

            time.sleep(1)

        # FIXED: Multiple final checks for fills (BUG FIX #8)
        if current_order_id:
            logger.info(f"    🔍 Final fill checks...")
            for i in range(3):
                status, filled_size, filled_value, status_ok = self.order_tracker.check_order_status(
                    current_order_id, self.dry_run
                )

                # Check for any fills (partial or full)
                if status_ok and filled_size and filled_size > 0:
                    # Accumulate final fills
                    total_filled_size += filled_size
                    total_filled_value += filled_value
                    completion = (total_filled_value / target_usd) * 100

                    logger.info(f"    ✅ Final fill detected! {filled_size} for ${filled_value:.2f}")
                    logger.info(f"    📊 Total filled: {completion:.1f}%")

                    # Check if we reached target
                    if completion >= self.config.completion_threshold_percentage:
                        execution_time = time.time() - start_time
                        return TradeResult(
                            product_id=product_id,
                            success=True,
                            quote_amount=quote_amount,
                            filled_size=total_filled_size,
                            filled_value=total_filled_value,
                            execution_time=execution_time,
                            attempts=attempts,
                            completion_percentage=float(completion)
                        )
                time.sleep(1)

            # Cancel unfilled/partial order
            if not self.dry_run:
                self.order_placer.cancel_order(current_order_id)
                logger.debug(f"    🧹 Cancelled remaining order")

        # Trade completed or failed
        execution_time = time.time() - start_time
        completion = (total_filled_value / target_usd) * 100 if total_filled_value > 0 else 0

        if completion > 0:
            logger.warning(
                f"    ⏰ Timeout after {attempts} attempts - "
                f"Partially filled: {completion:.1f}%"
            )
        else:
            logger.warning(f"    ⏰ Timeout after {attempts} attempts - No fills")

        # Determine success based on completion percentage
        success = completion >= self.config.completion_threshold_percentage

        return TradeResult(
            product_id=product_id,
            success=success,
            quote_amount=quote_amount,
            filled_size=total_filled_size if total_filled_size > 0 else None,
            filled_value=total_filled_value if total_filled_value > 0 else None,
            execution_time=execution_time,
            attempts=attempts,
            completion_percentage=float(completion),
            error_message=None if success else f"Only {completion:.1f}% filled (target: {self.config.completion_threshold_percentage}%)"
        )

    def cleanup_pending_orders(self) -> None:
        """
        Cancel all pending orders.

        FIXED: Proper cleanup on shutdown (BUG FIX #24)
        """
        if not self.pending_orders:
            return

        logger.info(f"🧹 Cleaning up {len(self.pending_orders)} pending orders...")

        for order_id in self.pending_orders:
            try:
                self.order_placer.cancel_order(order_id)
            except Exception as e:
                logger.debug(f"Failed to cancel {order_id}: {e}")

        self.pending_orders.clear()
        logger.info("✅ Cleanup complete")
