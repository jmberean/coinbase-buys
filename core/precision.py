"""
Precision detection and management for cryptocurrency orders.

Handles size and price precision requirements for each trading pair,
loading specifications from product specs file.
"""

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional

from models.types import PrecisionData, ProductSpec

logger = logging.getLogger(__name__)


class PrecisionDetector:
    """
    Manages precision requirements for cryptocurrency trading pairs.

    Loads product specifications from JSON file and provides precision
    information for order placement.
    """

    def __init__(self, product_specs_path: Path):
        """
        Initialize precision detector.

        Args:
            product_specs_path: Path to coinbase_product_specs.json
        """
        self.cache: dict[str, PrecisionData] = {}
        self.product_specs: dict[str, ProductSpec] = {}
        self._load_product_specs(product_specs_path)

    def _load_product_specs(self, path: Path) -> None:
        """
        Load product specifications from JSON file.

        Args:
            path: Path to product specs JSON file

        Raises:
            FileNotFoundError: If specs file doesn't exist
            json.JSONDecodeError: If specs file is invalid JSON
        """
        if not path.exists():
            raise FileNotFoundError(f"Product specs file not found: {path}")

        with open(path, 'r') as f:
            self.product_specs = json.load(f)

        logger.info(f"✅ Loaded specs for {len(self.product_specs)} products")

    def get_product_spec(self, product_id: str) -> Optional[ProductSpec]:
        """
        Get product specification for a trading pair.

        Args:
            product_id: Trading pair identifier (e.g., 'BTC-USD')

        Returns:
            Product specification or None if not found
        """
        return self.product_specs.get(product_id)

    def detect(
        self,
        product_id: str,
        best_bid: Decimal,
        best_ask: Decimal
    ) -> PrecisionData:
        """
        Detect precision requirements for a trading pair.

        Args:
            product_id: Trading pair identifier
            best_bid: Current best bid price
            best_ask: Current best ask price

        Returns:
            Precision data for order placement

        Raises:
            ValueError: If product specs not found for product_id
        """
        # Return cached precision if available
        if product_id in self.cache:
            return self.cache[product_id]

        # Get product specs
        spec = self.get_product_spec(product_id)
        if not spec:
            raise ValueError(f"No product specification found for {product_id}")

        # Calculate price precision from market data
        bid_str = str(best_bid)
        ask_str = str(best_ask)

        bid_decimals = len(bid_str.split('.')[1]) if '.' in bid_str else 0
        ask_decimals = len(ask_str.split('.')[1]) if '.' in ask_str else 0

        market_precision = max(bid_decimals, ask_decimals)

        # FIXED: Handle zero precision case (BUG FIX #1)
        if market_precision == 0:
            market_increment = Decimal('1')
        else:
            market_increment = Decimal('0.' + '0' * (market_precision - 1) + '1')

        # Get price precision from product spec
        price_increment_str = spec.get('price_increment', '0.01')
        price_increment = Decimal(price_increment_str)

        # Calculate price precision (number of decimal places)
        price_precision = len(price_increment_str.split('.')[1]) if '.' in price_increment_str else 0

        # Get size precision from product spec (base_increment)
        size_increment_str = spec.get('base_increment', '0.00000001')
        size_increment = Decimal(size_increment_str)

        # Calculate size precision (number of decimal places)
        # FIXED: Handle zero precision case (BUG FIX #1)
        if '.' in size_increment_str:
            size_precision = len(size_increment_str.split('.')[1])
        else:
            size_precision = 0

        result: PrecisionData = {
            'market_increment': market_increment,
            'market_precision': market_precision,
            'price_increment': price_increment,
            'price_precision': price_precision,
            'size_increment': size_increment,
            'size_precision': size_precision
        }

        # Cache the result
        self.cache[product_id] = result

        logger.info(
            f"📏 {product_id}: "
            f"price={price_precision}dp (inc: {price_increment}), "
            f"size={size_precision}dp (inc: {size_increment})"
        )

        return result

    def adjust_price_precision(
        self,
        product_id: str,
        error_message: str
    ) -> Optional[PrecisionData]:
        """
        Adjust price precision based on error feedback.

        Args:
            product_id: Trading pair identifier
            error_message: Error message from order placement

        Returns:
            Updated precision data or None if no adjustment made
        """
        if 'INVALID_PRICE_PRECISION' not in str(error_message):
            return None

        if product_id not in self.cache:
            return None

        current = self.cache[product_id]
        current_precision = current['price_precision']
        new_precision = max(0, current_precision - 1)

        # FIXED: Handle zero precision case (BUG FIX #1)
        if new_precision == 0:
            new_increment = Decimal('1')
        else:
            new_increment = Decimal('0.' + '0' * (new_precision - 1) + '1')

        # Update cache
        self.cache[product_id]['price_precision'] = new_precision
        self.cache[product_id]['price_increment'] = new_increment

        logger.info(
            f"🔧 {product_id}: Adjusted price precision: "
            f"{current_precision} → {new_precision} decimals"
        )

        return self.cache[product_id]

    def adjust_size_precision(
        self,
        product_id: str,
        error_message: str
    ) -> Optional[PrecisionData]:
        """
        Adjust size precision based on error feedback.

        Args:
            product_id: Trading pair identifier
            error_message: Error message from order placement

        Returns:
            Updated precision data or None if no adjustment made
        """
        if 'INVALID_SIZE_PRECISION' not in str(error_message):
            return None

        if product_id not in self.cache:
            return None

        current = self.cache[product_id]
        current_precision = current['size_precision']
        new_precision = max(0, current_precision - 1)

        # FIXED: Handle zero precision case (BUG FIX #1)
        if new_precision == 0:
            new_increment = Decimal('1')
        else:
            new_increment = Decimal('0.' + '0' * (new_precision - 1) + '1')

        # Update cache
        self.cache[product_id]['size_precision'] = new_precision
        self.cache[product_id]['size_increment'] = new_increment

        logger.info(
            f"🔧 {product_id}: Adjusted size precision: "
            f"{current_precision} → {new_precision} decimals"
        )

        return self.cache[product_id]

    def clear_cache(self, product_id: Optional[str] = None) -> None:
        """
        Clear precision cache.

        Args:
            product_id: Specific product to clear, or None to clear all
        """
        if product_id:
            self.cache.pop(product_id, None)
            logger.debug(f"Cleared precision cache for {product_id}")
        else:
            self.cache.clear()
            logger.debug("Cleared all precision cache")
