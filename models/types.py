"""
Type definitions for the trading bot.

Provides type hints and data structures for better code clarity and IDE support.
"""

from typing import TypedDict, Literal, Optional
from decimal import Decimal
from dataclasses import dataclass


# Type aliases for better readability
OrderStatus = Literal['FILLED', 'OPEN', 'CANCELLED', 'EXPIRED', 'FAILED', 'UNKNOWN']
PricingStrategy = Literal['zero-spread', 'tight-spread', 'mid-spread', 'below-ask']


class PrecisionData(TypedDict):
    """Precision information for a trading pair."""
    market_increment: Decimal
    market_precision: int
    price_increment: Decimal
    price_precision: int
    size_increment: Decimal
    size_precision: int


class MarketData(TypedDict):
    """Real-time market data for a trading pair."""
    best_bid: Decimal
    best_ask: Decimal
    timestamp: float


class ProductSpec(TypedDict):
    """Product specification from Coinbase."""
    product_id: str
    base_currency: str
    quote_currency: str
    status: str
    base_min_size: str
    base_max_size: str
    quote_min_size: str
    quote_max_size: str
    base_increment: str
    quote_increment: str
    price_increment: str
    current_price: Optional[str]


class OrderResult(TypedDict):
    """Result of an order placement attempt."""
    success: bool
    order_id: Optional[str]
    error_message: Optional[str]


@dataclass
class TradingConfig:
    """Trading configuration parameters."""
    max_chase_time: int
    max_chase_attempts: int
    min_api_interval: float
    min_order_wait_time: float
    min_chase_wait_time: float
    chase_threshold_multiplier: int
    completion_threshold_percentage: float  # Minimum % filled to consider success (e.g., 95.0)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    max_post_only_failures: int
    max_precision_failures: int


@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    connection_timeout: int
    data_freshness_timeout: int
    enable_reconnection: bool
    max_reconnection_attempts: int
    reconnection_delay: int
    reconnection_backoff_multiplier: int


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    log_directory: str
    console_output: bool
    max_log_files: int


@dataclass
class SafetyConfig:
    """Safety and validation configuration."""
    dry_run: bool
    validate_allocation: bool
    allocation_tolerance: float
    enable_health_checks: bool


@dataclass
class PortfolioConfig:
    """Portfolio configuration."""
    allocation: dict[str, float]
    total_investment: float


@dataclass
class APIConfig:
    """API credentials configuration."""
    api_key: str
    api_secret: str


@dataclass
class TradeResult:
    """Result of a single trade execution."""
    product_id: str
    success: bool
    quote_amount: float
    filled_size: Optional[Decimal]
    filled_value: Optional[Decimal]  # USD value of filled amount
    execution_time: float
    attempts: int
    completion_percentage: float = 0.0  # Percentage of target filled
    error_message: Optional[str] = None


@dataclass
class TradingSummary:
    """Summary of all trading activity."""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_execution_time: float
    results: list[TradeResult]
