"""
Configuration loader for the trading bot.

Loads settings from YAML files and environment variables.
"""

import logging
from pathlib import Path
from typing import Tuple

import yaml
from dotenv import dotenv_values

from models.types import (
    APIConfig,
    CircuitBreakerConfig,
    LoggingConfig,
    PortfolioConfig,
    SafetyConfig,
    TradingConfig,
    WebSocketConfig,
)
from utils.validators import (
    validate_api_credentials,
    validate_investment_amount,
    validate_portfolio_allocation,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


def load_portfolio_config(portfolio_path: Path = Path("config/portfolio.yaml")) -> PortfolioConfig:
    """
    Load portfolio configuration from YAML file.

    Args:
        portfolio_path: Path to portfolio.yaml

    Returns:
        PortfolioConfig instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not portfolio_path.exists():
        raise ConfigurationError(f"Portfolio config not found: {portfolio_path}")

    with open(portfolio_path, 'r') as f:
        data = yaml.safe_load(f)

    if not data or 'portfolio' not in data:
        raise ConfigurationError("Portfolio config missing 'portfolio' section")

    allocation = data['portfolio']
    total_investment = data.get('total_investment', 100.0)

    # Validate allocation
    valid, issues = validate_portfolio_allocation(allocation)
    if not valid:
        error_msg = "Portfolio allocation validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
        raise ConfigurationError(error_msg)

    # Validate investment amounts
    valid, issues = validate_investment_amount(total_investment, allocation)
    if not valid:
        error_msg = "Investment amount validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
        raise ConfigurationError(error_msg)

    logger.info(f"✅ Loaded portfolio: {len(allocation)} products, ${total_investment:.2f} total")

    return PortfolioConfig(
        allocation=allocation,
        total_investment=total_investment
    )


def load_trading_config(config_path: Path = Path("config/config.yaml")) -> Tuple[
    TradingConfig,
    CircuitBreakerConfig,
    WebSocketConfig,
    LoggingConfig,
    SafetyConfig
]:
    """
    Load trading configuration from YAML file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Tuple of configuration objects

    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not config_path.exists():
        raise ConfigurationError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        raise ConfigurationError("Config file is empty")

    # Trading config
    trading_data = data.get('trading', {})
    trading_config = TradingConfig(
        max_chase_time=trading_data.get('max_chase_time', 300),
        max_chase_attempts=trading_data.get('max_chase_attempts', 8),
        min_api_interval=trading_data.get('min_api_interval', 0.5),
        min_order_wait_time=trading_data.get('min_order_wait_time', 2.0),
        min_chase_wait_time=trading_data.get('min_chase_wait_time', 5.0),
        chase_threshold_multiplier=trading_data.get('chase_threshold_multiplier', 10),
        completion_threshold_percentage=trading_data.get('completion_threshold_percentage', 95.0),
    )

    # Circuit breaker config
    breaker_data = data.get('circuit_breakers', {})
    circuit_breaker_config = CircuitBreakerConfig(
        max_post_only_failures=breaker_data.get('max_post_only_failures', 10),
        max_precision_failures=breaker_data.get('max_precision_failures', 3),
    )

    # WebSocket config
    ws_data = data.get('websocket', {})
    websocket_config = WebSocketConfig(
        connection_timeout=ws_data.get('connection_timeout', 15),
        data_freshness_timeout=ws_data.get('data_freshness_timeout', 5),
        enable_reconnection=ws_data.get('enable_reconnection', True),
        max_reconnection_attempts=ws_data.get('max_reconnection_attempts', 5),
        reconnection_delay=ws_data.get('reconnection_delay', 3),
        reconnection_backoff_multiplier=ws_data.get('reconnection_backoff_multiplier', 2),
    )

    # Logging config
    log_data = data.get('logging', {})
    logging_config = LoggingConfig(
        level=log_data.get('level', 'INFO'),
        log_directory=log_data.get('log_directory', 'logs'),
        console_output=log_data.get('console_output', True),
        max_log_files=log_data.get('max_log_files', 30),
    )

    # Safety config
    safety_data = data.get('safety', {})
    safety_config = SafetyConfig(
        dry_run=safety_data.get('dry_run', False),
        validate_allocation=safety_data.get('validate_allocation', True),
        allocation_tolerance=safety_data.get('allocation_tolerance', 0.01),
        enable_health_checks=safety_data.get('enable_health_checks', True),
    )

    logger.info("✅ Loaded trading configuration")

    return (
        trading_config,
        circuit_breaker_config,
        websocket_config,
        logging_config,
        safety_config
    )


def load_api_config(env_path: Path = Path(".env")) -> APIConfig:
    """
    Load API credentials from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        APIConfig instance

    Raises:
        ConfigurationError: If credentials are invalid
    """
    if not env_path.exists():
        raise ConfigurationError(
            f".env file not found at {env_path}\n"
            "Please create a .env file with your Coinbase API credentials.\n"
            "See .env.example for template."
        )

    config = dotenv_values(str(env_path))

    api_key = config.get("COINBASE_API_KEY")
    api_secret = config.get("COINBASE_API_SECRET")

    # Validate credentials
    valid, issues = validate_api_credentials(api_key, api_secret)
    if not valid:
        error_msg = "API credentials validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
        raise ConfigurationError(error_msg)

    logger.info("✅ Loaded API credentials")

    return APIConfig(
        api_key=api_key or "",  # Should never be empty due to validation
        api_secret=api_secret or ""
    )


def load_all_config() -> dict:
    """
    Load all configuration.

    Returns:
        Dictionary containing all configuration objects

    Raises:
        ConfigurationError: If any configuration is invalid
    """
    try:
        # Load API config
        api_config = load_api_config()

        # Load portfolio config
        portfolio_config = load_portfolio_config()

        # Load trading config
        (
            trading_config,
            circuit_breaker_config,
            websocket_config,
            logging_config,
            safety_config
        ) = load_trading_config()

        return {
            'api': api_config,
            'portfolio': portfolio_config,
            'trading': trading_config,
            'circuit_breaker': circuit_breaker_config,
            'websocket': websocket_config,
            'logging': logging_config,
            'safety': safety_config,
        }

    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")
