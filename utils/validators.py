"""
Validation utilities for the trading bot.

Provides input validation for configuration, orders, and API responses.
"""

from decimal import Decimal
from typing import Optional
from models.types import ProductSpec


def validate_portfolio_allocation(
    allocation: dict[str, float],
    tolerance: float = 0.01
) -> tuple[bool, list[str]]:
    """
    Validate portfolio allocation.

    Args:
        allocation: Dictionary of product_id -> percentage allocation
        tolerance: Tolerance for total allocation sum (default: 0.01 = 1%)

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []

    # Check if empty
    if not allocation:
        issues.append("Portfolio allocation is empty")
        return False, issues

    # Check for negative allocations
    for product_id, percentage in allocation.items():
        if percentage < 0:
            issues.append(f"{product_id} has negative allocation: {percentage}")
        if percentage == 0:
            issues.append(f"{product_id} has zero allocation")

    # Check total allocation
    total = sum(allocation.values())
    expected_total = 1.0
    if not (expected_total - tolerance <= total <= expected_total + tolerance):
        issues.append(
            f"Portfolio allocation sums to {total:.4f}, "
            f"expected {expected_total:.4f} ± {tolerance:.4f}"
        )

    # Check product ID format
    for product_id in allocation.keys():
        if '-' not in product_id or not product_id.endswith('-USD'):
            issues.append(f"Invalid product ID format: {product_id} (expected format: XXX-USD)")

    return len(issues) == 0, issues


def validate_investment_amount(
    total_investment: float,
    allocation: dict[str, float],
    min_per_asset: float = 1.0
) -> tuple[bool, list[str]]:
    """
    Validate total investment amount.

    Args:
        total_investment: Total USD to invest
        allocation: Portfolio allocation percentages
        min_per_asset: Minimum USD per asset (Coinbase requirement)

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []

    # Check total is positive
    if total_investment <= 0:
        issues.append(f"Total investment must be positive, got: ${total_investment}")

    # Check each asset meets minimum
    for product_id, percentage in allocation.items():
        amount = total_investment * percentage
        if amount < min_per_asset:
            issues.append(
                f"{product_id} allocation ${amount:.2f} is below "
                f"minimum ${min_per_asset:.2f}"
            )

    return len(issues) == 0, issues


def validate_order_size(
    product_id: str,
    quote_amount: float,
    base_size: Decimal,
    product_spec: ProductSpec
) -> tuple[bool, list[str]]:
    """
    Validate order meets Coinbase minimum requirements.

    Args:
        product_id: Trading pair identifier
        quote_amount: Order amount in USD
        base_size: Order size in base currency
        product_spec: Product specification from Coinbase

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []

    # Check base minimum size
    base_min = Decimal(product_spec['base_min_size'])
    if base_size < base_min:
        issues.append(
            f"{product_id}: Base size {base_size:.8f} is below minimum {base_min}"
        )

    # Check quote minimum size
    quote_min = Decimal(product_spec['quote_min_size'])
    if Decimal(str(quote_amount)) < quote_min:
        issues.append(
            f"{product_id}: Quote amount ${quote_amount:.2f} is below minimum ${quote_min}"
        )

    # Check base maximum size
    base_max = Decimal(product_spec['base_max_size'])
    if base_size > base_max:
        issues.append(
            f"{product_id}: Base size {base_size:.8f} exceeds maximum {base_max}"
        )

    # Check quote maximum size
    quote_max = Decimal(product_spec['quote_max_size'])
    if Decimal(str(quote_amount)) > quote_max:
        issues.append(
            f"{product_id}: Quote amount ${quote_amount:.2f} exceeds maximum ${quote_max}"
        )

    return len(issues) == 0, issues


def validate_api_credentials(api_key: Optional[str], api_secret: Optional[str]) -> tuple[bool, list[str]]:
    """
    Validate API credentials.

    Args:
        api_key: Coinbase API key
        api_secret: Coinbase API secret

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []

    if not api_key or not api_key.strip():
        issues.append("API key is missing or empty")

    if not api_secret or not api_secret.strip():
        issues.append("API secret is missing or empty")

    # Basic format validation (Coinbase API keys are typically alphanumeric)
    if api_key and len(api_key.strip()) < 10:
        issues.append("API key appears to be too short")

    if api_secret and len(api_secret.strip()) < 10:
        issues.append("API secret appears to be too short")

    return len(issues) == 0, issues


def validate_market_data(
    best_bid: Optional[Decimal],
    best_ask: Optional[Decimal]
) -> tuple[bool, list[str]]:
    """
    Validate market data is reasonable.

    Args:
        best_bid: Best bid price
        best_ask: Best ask price

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []

    if best_bid is None:
        issues.append("Best bid is None")
    elif best_bid <= 0:
        issues.append(f"Best bid is not positive: {best_bid}")

    if best_ask is None:
        issues.append("Best ask is None")
    elif best_ask <= 0:
        issues.append(f"Best ask is not positive: {best_ask}")

    # Check bid/ask relationship
    if best_bid is not None and best_ask is not None:
        if best_ask < best_bid:
            issues.append(f"Ask ${best_ask} is less than bid ${best_bid} (crossed market)")

    return len(issues) == 0, issues


def sanitize_error_message(error_message: str, max_length: int = 500) -> str:
    """
    Sanitize error message for safe logging.

    Removes potentially sensitive information and truncates long messages.

    Args:
        error_message: Raw error message
        max_length: Maximum length of sanitized message

    Returns:
        Sanitized error message
    """
    if not error_message:
        return "Unknown error"

    # Convert to string and truncate
    message = str(error_message)[:max_length]

    # Remove potential sensitive patterns (basic sanitization)
    # More thorough sanitization happens in the logging formatter
    sensitive_patterns = [
        ('api_key', '***'),
        ('api_secret', '***'),
        ('password', '***'),
        ('token', '***'),
    ]

    message_lower = message.lower()
    for pattern, replacement in sensitive_patterns:
        if pattern in message_lower:
            # Simple obfuscation - more sophisticated sanitization in logger
            message = message.replace(pattern, replacement)

    return message
