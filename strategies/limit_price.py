"""
Limit price calculation strategies for post-only orders.

Provides different strategies for calculating optimal limit prices
based on market spread conditions.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple

from models.types import PricingStrategy as PricingStrategyType


class PricingStrategy(ABC):
    """Abstract base class for pricing strategies."""

    @abstractmethod
    def calculate(
        self,
        best_bid: Decimal,
        best_ask: Decimal,
        price_increment: Decimal
    ) -> Tuple[Decimal, PricingStrategyType]:
        """
        Calculate optimal limit price for post-only order.

        Args:
            best_bid: Current best bid price
            best_ask: Current best ask price
            price_increment: Minimum price increment for the product

        Returns:
            Tuple of (limit_price, strategy_name)
        """
        pass


class AdaptiveSpreadStrategy(PricingStrategy):
    """
    Adaptive pricing strategy that adjusts based on spread width.

    Selects different pricing approaches depending on the size of the
    bid-ask spread to optimize fill probability while maintaining
    post-only status.
    """

    def calculate(
        self,
        best_bid: Decimal,
        best_ask: Decimal,
        price_increment: Decimal
    ) -> Tuple[Decimal, PricingStrategyType]:
        """
        Calculate limit price based on spread conditions.

        Strategy selection:
        - Zero spread: Place below both bid and ask
        - Tight spread (≤2 increments): Small buffer below ask
        - Medium spread (≤10 increments): Between bid and ask
        - Wide spread (>10 increments): Larger buffer below ask

        Args:
            best_bid: Current best bid price
            best_ask: Current best ask price
            price_increment: Minimum price increment

        Returns:
            Tuple of (limit_price, strategy_name)
        """
        spread = best_ask - best_bid

        if spread == 0:
            # Zero spread - go below both to ensure post-only
            limit_price = best_bid - price_increment
            strategy: PricingStrategyType = "zero-spread"

        elif spread <= price_increment * 2:
            # Tight spread - small buffer below ask
            limit_price = best_ask - price_increment
            strategy = "tight-spread"

        elif spread <= price_increment * 10:
            # Medium spread - between bid and ask
            limit_price = best_bid + (spread / 2)
            strategy = "mid-spread"

        else:
            # Wide spread - larger buffer below ask
            limit_price = best_ask - (price_increment * 2)
            strategy = "below-ask"

        # FIXED: Ensure limit price is always below ask for post-only (BUG FIX #6)
        if limit_price >= best_ask:
            limit_price = best_ask - price_increment

        # Additional safety: ensure limit price is not negative or zero
        if limit_price <= 0:
            limit_price = price_increment

        return limit_price, strategy


class ConservativeStrategy(PricingStrategy):
    """
    Conservative pricing strategy that always places well below ask.

    Prioritizes post-only guarantee over fill speed.
    """

    def calculate(
        self,
        best_bid: Decimal,
        best_ask: Decimal,
        price_increment: Decimal
    ) -> Tuple[Decimal, PricingStrategyType]:
        """
        Calculate conservative limit price.

        Always places order at least 2 increments below ask.

        Args:
            best_bid: Current best bid price
            best_ask: Current best ask price
            price_increment: Minimum price increment

        Returns:
            Tuple of (limit_price, strategy_name)
        """
        limit_price = best_ask - (price_increment * 2)

        # Ensure we don't go below zero
        if limit_price <= 0:
            limit_price = price_increment

        strategy: PricingStrategyType = "below-ask"
        return limit_price, strategy


class AggressiveStrategy(PricingStrategy):
    """
    Aggressive pricing strategy that places close to ask.

    Prioritizes fill speed over post-only guarantee (may fail more often).
    """

    def calculate(
        self,
        best_bid: Decimal,
        best_ask: Decimal,
        price_increment: Decimal
    ) -> Tuple[Decimal, PricingStrategyType]:
        """
        Calculate aggressive limit price.

        Places order just below ask for faster fills.

        Args:
            best_bid: Current best bid price
            best_ask: Current best ask price
            price_increment: Minimum price increment

        Returns:
            Tuple of (limit_price, strategy_name)
        """
        limit_price = best_ask - price_increment

        # Ensure we don't go below zero
        if limit_price <= 0:
            limit_price = price_increment

        strategy: PricingStrategyType = "tight-spread"
        return limit_price, strategy


# Default strategy for the trading bot
DEFAULT_STRATEGY = AdaptiveSpreadStrategy()
