#!/usr/bin/env python3
"""
Coinbase WebSocket Trading Bot - Refactored Version

A sophisticated cryptocurrency trading bot for Coinbase Advanced that combines
WebSocket market data with intelligent order placement strategies.

Features:
- Real-time WebSocket data with automatic reconnection
- Post-only orders for maker fees
- Intelligent price chasing
- Comprehensive error handling and recovery
- Graceful shutdown with order cleanup
"""

import logging
import signal
import sys
import time
from pathlib import Path

from coinbase.rest import RESTClient

from config.settings import ConfigurationError, load_all_config
from core.market_data import MarketDataProvider
from core.order_manager import TradingEngine
from core.precision import PrecisionDetector
from models.types import TradingSummary, TradeResult
from utils.logging import setup_logger

# Global references for signal handling
market_data_provider = None
trading_engine = None
logger = None


def signal_handler(signum, frame):
    """
    Handle shutdown signals gracefully.

    FIXED: Proper cleanup on Ctrl+C (BUG FIX #24)
    """
    global market_data_provider, trading_engine, logger

    if logger:
        logger.info("\n⏹️ Shutdown signal received, cleaning up...")

    # Cancel pending orders
    if trading_engine:
        trading_engine.cleanup_pending_orders()

    # Stop WebSocket
    if market_data_provider:
        market_data_provider.stop()

    if logger:
        logger.info("✅ Cleanup complete")
        logger.info("=" * 60)
        logger.info("TRADING BOT SESSION ENDED")
        logger.info("=" * 60)

    sys.exit(0)


def perform_health_checks(
    rest_client: RESTClient,
    portfolio_config,
    product_specs_path: Path
) -> bool:
    """
    Perform pre-flight health checks.

    FIXED: Added health checks (IMPROVEMENT #29)

    Args:
        rest_client: Coinbase REST client
        portfolio_config: Portfolio configuration
        product_specs_path: Path to product specs file

    Returns:
        True if all checks pass, False otherwise
    """
    logger.info("🏥 Performing health checks...")

    # Check product specs file exists
    if not product_specs_path.exists():
        logger.error(f"❌ Product specs file not found: {product_specs_path}")
        return False

    # Check API connectivity
    try:
        accounts = rest_client.get_accounts()
        logger.info("✅ API connectivity check passed")
    except Exception as e:
        logger.error(f"❌ API connectivity check failed: {e}")
        return False

    # Check USD balance
    try:
        usd_balance = None
        if hasattr(accounts, 'accounts'):
            for account in accounts.accounts:
                if account.currency == 'USD':
                    usd_balance = float(account.available_balance.value)
                    break

        if usd_balance is None:
            logger.warning("⚠️ Could not verify USD balance")
        elif usd_balance < portfolio_config.total_investment:
            logger.error(
                f"❌ Insufficient USD balance: "
                f"${usd_balance:.2f} available, ${portfolio_config.total_investment:.2f} needed"
            )
            return False
        else:
            logger.info(f"✅ USD balance check passed (${usd_balance:.2f} available)")

    except Exception as e:
        logger.warning(f"⚠️ Balance check failed: {e}")

    # Check all products are tradeable
    try:
        for product_id in portfolio_config.allocation.keys():
            product = rest_client.get_product(product_id)
            if hasattr(product, 'status') and product.status != 'online':
                logger.error(f"❌ Product {product_id} is not online (status: {product.status})")
                return False

        logger.info(f"✅ All {len(portfolio_config.allocation)} products are online")

    except Exception as e:
        logger.warning(f"⚠️ Product status check failed: {e}")

    logger.info("✅ All health checks passed")
    return True


def print_portfolio_summary(portfolio_config) -> None:
    """
    Print portfolio allocation summary.

    Args:
        portfolio_config: Portfolio configuration
    """
    logger.info("=" * 60)
    logger.info("PORTFOLIO ALLOCATION")
    logger.info("=" * 60)

    for product_id, percentage in portfolio_config.allocation.items():
        amount = portfolio_config.total_investment * percentage
        logger.info(f"{product_id}: ${amount:.2f} ({percentage * 100:.1f}%)")

    logger.info("=" * 60)
    logger.info(f"TOTAL INVESTMENT: ${portfolio_config.total_investment:.2f}")
    logger.info("=" * 60)


def print_execution_summary(summary: TradingSummary) -> None:
    """
    Print execution summary.

    FIXED: Added execution summary (IMPROVEMENT #27)

    Args:
        summary: Trading summary
    """
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 60)

    logger.info(f"Total trades: {summary.total_trades}")
    logger.info(f"✅ Successful: {summary.successful_trades}")
    logger.info(f"❌ Failed: {summary.failed_trades}")
    logger.info(f"⏱️ Total time: {summary.total_execution_time:.1f}s")

    if summary.successful_trades > 0:
        avg_time = summary.total_execution_time / summary.successful_trades
        logger.info(f"📊 Average time per successful trade: {avg_time:.1f}s")

    logger.info("\nDetailed results:")
    for result in summary.results:
        status = "✅" if result.success else "❌"
        logger.info(
            f"  {status} {result.product_id}: "
            f"${result.quote_amount:.2f} in {result.execution_time:.1f}s "
            f"({result.attempts} attempts)"
        )

        if result.filled_size and result.filled_value:
            logger.info(
                f"     Filled: {result.filled_size} units for ${result.filled_value:.2f} "
                f"({result.completion_percentage:.1f}%)"
            )
        elif result.filled_size:
            logger.info(f"     Filled: {result.filled_size} units")

        if result.error_message:
            logger.info(f"     Error: {result.error_message}")

    logger.info("=" * 60)


def main() -> int:
    """
    Main entry point for the trading bot.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    global market_data_provider, trading_engine, logger

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Load configuration (can't use logger yet - not initialized)
        print("📋 Loading configuration...")
        config = load_all_config()

    except ConfigurationError as e:
        print(f"❌ Configuration error:\n{e}")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error loading configuration: {e}")
        return 1

    try:
        # Setup logging
        logger = setup_logger(
            name=__name__,
            log_dir=Path(config['logging'].log_directory),
            level=config['logging'].level,
            console_output=config['logging'].console_output,
            max_log_files=config['logging'].max_log_files
        )

        logger.info("🚀 COINBASE TRADING BOT - REFACTORED VERSION")

        # Show dry-run warning
        if config['safety'].dry_run:
            logger.info("🧪 DRY RUN MODE - No real orders will be placed")

        # Print portfolio summary
        print_portfolio_summary(config['portfolio'])

        # Initialize REST client
        logger.info("🔧 Initializing REST client...")
        rest_client = RESTClient(
            api_key=config['api'].api_key,
            api_secret=config['api'].api_secret,
            rate_limit_headers=True
        )
        logger.info("✅ REST client initialized")

        # Product specs path
        product_specs_path = Path("data/coinbase_product_specs.json")

        # Health checks
        if config['safety'].enable_health_checks:
            if not perform_health_checks(rest_client, config['portfolio'], product_specs_path):
                logger.error("❌ Health checks failed, aborting")
                return 1

        # Initialize precision detector
        logger.info("📏 Loading product specifications...")
        precision_detector = PrecisionDetector(product_specs_path)

        # Calculate trade amounts
        products = list(config['portfolio'].allocation.keys())
        trade_amounts = {
            product_id: config['portfolio'].total_investment * percentage
            for product_id, percentage in config['portfolio'].allocation.items()
        }

        # Initialize market data provider
        logger.info("📡 Initializing market data provider...")
        market_data_provider = MarketDataProvider(
            rest_client=rest_client,
            api_key=config['api'].api_key,
            api_secret=config['api'].api_secret,
            products=products,
            config=config['websocket']
        )

        # Start WebSocket
        market_data_provider.start()
        market_data_provider.wait_for_data(timeout=config['websocket'].connection_timeout)

        # Initialize trading engine
        logger.info("⚙️ Initializing trading engine...")
        trading_engine = TradingEngine(
            rest_client=rest_client,
            market_data=market_data_provider,
            precision_detector=precision_detector,
            config=config['trading'],
            circuit_breaker_config=config['circuit_breaker'],
            dry_run=config['safety'].dry_run
        )

        # Execute trades
        logger.info(f"\n🏁 Starting trade execution: {len(products)} products")
        logger.info("=" * 60)

        results: list[TradeResult] = []
        start_total = time.time()

        for i, (product_id, amount) in enumerate(trade_amounts.items(), 1):
            logger.info(f"\n[{i}/{len(products)}] Processing {product_id}...")

            # Get product spec
            product_spec = precision_detector.get_product_spec(product_id)
            if not product_spec:
                logger.error(f"❌ No product spec for {product_id}, skipping")
                continue

            # Execute trade
            result = trading_engine.execute_trade(product_id, amount, product_spec)
            results.append(result)

            if result.success:
                logger.info(f"    ⚡ {product_id} completed in {result.execution_time:.1f}s!")
            else:
                logger.error(f"    ❌ {product_id} failed after {result.execution_time:.1f}s")

            # Brief pause between trades
            if i < len(products):
                time.sleep(1)

        total_time = time.time() - start_total

        # Create summary
        summary = TradingSummary(
            total_trades=len(results),
            successful_trades=sum(1 for r in results if r.success),
            failed_trades=sum(1 for r in results if not r.success),
            total_execution_time=total_time,
            results=results
        )

        # Print summary
        print_execution_summary(summary)

        if config['safety'].dry_run:
            logger.info("🧪 DRY RUN COMPLETE - No real orders were placed")

        logger.info("💰 All orders used post-only (maker fees)")

        # Cleanup
        logger.info("\n🧹 Cleaning up...")
        trading_engine.cleanup_pending_orders()
        market_data_provider.stop()

        logger.info("=" * 60)
        logger.info("TRADING BOT SESSION ENDED SUCCESSFULLY")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("\n⏹️ Trading bot stopped by user")
        return 0

    except Exception as e:
        if logger:
            logger.error(f"💥 Unexpected error: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
        else:
            print(f"💥 Unexpected error: {e}")
            import traceback
            traceback.print_exc()

        return 1

    finally:
        # Ensure cleanup happens
        if trading_engine:
            try:
                trading_engine.cleanup_pending_orders()
            except:
                pass

        if market_data_provider:
            try:
                market_data_provider.stop()
            except:
                pass


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
