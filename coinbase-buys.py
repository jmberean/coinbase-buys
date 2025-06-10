#!/usr/bin/env python3
"""
Coinbase WebSocket Trading Bot - Clean & Focused Version
Intelligent precision detection, real-time WebSocket data, post-only orders
"""

import uuid
import time
import decimal
import json
import threading
import logging
import os
from datetime import datetime
from coinbase.rest import RESTClient
from coinbase.websocket import WSClient
from dotenv import dotenv_values
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Portfolio allocation
TOTAL_INVESTMENT = 100.00
PORTFOLIO_ALLOCATION = {
    # Core Foundation (20%)Add commentMore actions
    "BTC-USD": 0.10,   # 10% - Store of value anchor
    "ETH-USD": 0.10,   # 10% - Smart contract foundation
    
    # Established Growth Plays (60%) 
    "SOL-USD": 0.15,   # 15% - Consumer blockchain leader
    "XRP-USD": 0.15,   # 15% - Enterprise payments with regulatory clarity
    "LINK-USD": 0.15,  # 15% - Essential oracle infrastructure
    "AVAX-USD": 0.15,  # 15% - Institutional tokenization platform
    
    # Speculative Upside (20%)
    "UNI-USD": 0.04,   # 4% - DeFi protocol with fee switch potential
    "QNT-USD": 0.04,   # 4% - Enterprise interoperability
    "DOT-USD": 0.04,   # 4% - Parachain innovation
    "ADA-USD": 0.04,   # 4% - Academic development approach
    "DOGE-USD": 0.04,  # 4% - Community-driven payments
}

# Trading settings
MAX_CHASE_TIME = 300
MAX_CHASE_ATTEMPTS = 12
MIN_API_INTERVAL = 0.5
MAX_POST_ONLY_FAILURES = 15
MAX_PRECISION_FAILURES = 3

# Calculate amounts
CRYPTOS_TO_BUY = {
    crypto: round(TOTAL_INVESTMENT * percentage, 2)
    for crypto, percentage in PORTFOLIO_ALLOCATION.items()
}

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/trading_bot_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"=== TRADING BOT SESSION STARTED ===")
    logger.info(f"Log file: {log_filename}")
    return logger

logger = setup_logging()

# ============================================================================
# API SETUP
# ============================================================================

config = dotenv_values()
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

if not API_KEY or not API_SECRET:
    logger.error("❌ Error: API credentials not found in .env file")
    exit()

try:
    rest_client = RESTClient(api_key=API_KEY, api_secret=API_SECRET, rate_limit_headers=True)
    logger.info("✅ REST client initialized")
except Exception as e:
    logger.error(f"❌ REST client failed: {e}")
    exit()

# ============================================================================
# PRECISION DETECTOR
# ============================================================================

class PrecisionDetector:
    """Simple precision detection with separate market vs order precision"""
    
    def __init__(self):
        self.cache = {}
    
    def detect(self, product_id, best_bid, best_ask):
        """Detect precision from bid/ask data - learn order precision dynamically"""
        if product_id in self.cache:
            return self.cache[product_id]
        
        # Analyze decimal places in bid/ask for market precision
        bid_decimals = len(str(best_bid).split('.')[1]) if '.' in str(best_bid) else 0
        ask_decimals = len(str(best_ask).split('.')[1]) if '.' in str(best_ask) else 0
        
        # Market precision (for analyzing movements)
        market_precision = max(bid_decimals, ask_decimals)
        market_increment = decimal.Decimal('0.' + '0' * (market_precision - 1) + '1') if market_precision > 0 else decimal.Decimal('1')
        
        # Start by assuming order precision = market precision (learn if wrong)
        order_precision = market_precision
        order_increment = market_increment
        
        # Use same precision for size initially
        result = {
            'market_increment': market_increment,
            'market_precision': market_precision,
            'price_increment': order_increment,    # For order placement
            'price_precision': order_precision,    # For order placement
            'size_increment': order_increment,     # Same as price initially
            'size_precision': order_precision      # Same as price initially
        }
        
        self.cache[product_id] = result
        logger.info(f"📏 {product_id}: market={market_precision}dp, order={order_precision}dp (inc: {order_increment})")
        return result
    
    def adjust_price_precision(self, product_id, error_message):
        """Adjust order price precision based on error feedback"""
        if 'INVALID_PRICE_PRECISION' in str(error_message) and product_id in self.cache:
            current_precision = self.cache[product_id]['price_precision']
            new_precision = max(0, current_precision - 1)
            new_increment = decimal.Decimal('0.' + '0' * (new_precision - 1) + '1') if new_precision > 0 else decimal.Decimal('1')
            
            self.cache[product_id]['price_precision'] = new_precision
            self.cache[product_id]['price_increment'] = new_increment
            
            logger.info(f"🔧 {product_id}: Learned order price precision: {current_precision} → {new_precision} decimals")
            return self.cache[product_id]
        return None
    
    def adjust_size_precision(self, product_id, error_message):
        """Adjust size precision based on error feedback"""
        if 'INVALID_SIZE_PRECISION' in str(error_message) and product_id in self.cache:
            current_precision = self.cache[product_id]['size_precision']
            new_precision = max(0, current_precision - 1)
            new_increment = decimal.Decimal('0.' + '0' * (new_precision - 1) + '1') if new_precision > 0 else decimal.Decimal('1')
            
            self.cache[product_id]['size_precision'] = new_precision
            self.cache[product_id]['size_increment'] = new_increment
            
            logger.info(f"🔧 {product_id}: Learned order size precision: {current_precision} → {new_precision} decimals")
            return self.cache[product_id]
        return None

# ============================================================================
# WEBSOCKET HANDLER  
# ============================================================================

class WebSocketHandler:
    """Handles WebSocket connection and market data"""
    
    def __init__(self, products):
        self.products = products
        self.market_data = {}
        self.market_data_lock = threading.Lock()
        self.data_received = False
        
    def on_message(self, msg):
        """Process WebSocket messages"""
        try:
            if isinstance(msg, str):
                msg = json.loads(msg)
            
            if msg.get('channel') == 'ticker':
                for event in msg.get('events', []):
                    if event.get('type') in ['snapshot', 'update']:
                        for ticker in event.get('tickers', []):
                            if ticker.get('type') == 'ticker':
                                product_id = ticker.get('product_id')
                                if product_id in self.products:
                                    best_bid = ticker.get('best_bid')
                                    best_ask = ticker.get('best_ask')
                                    
                                    if best_bid and best_ask:
                                        bid_decimal = decimal.Decimal(str(best_bid))
                                        ask_decimal = decimal.Decimal(str(best_ask))
                                        
                                        if bid_decimal > 0 and ask_decimal > 0 and ask_decimal >= bid_decimal:
                                            with self.market_data_lock:
                                                self.market_data[product_id] = {
                                                    'best_bid': bid_decimal,
                                                    'best_ask': ask_decimal,
                                                    'timestamp': time.time()
                                                }
                                            self.data_received = True
                                            logger.debug(f"📊 WS {product_id}: ${bid_decimal:.6f}|${ask_decimal:.6f}")
            
            elif msg.get('channel') == 'subscriptions':
                logger.info(f"✅ Subscription confirmed")
                
        except Exception as e:
            logger.warning(f"⚠️ WebSocket error: {e}")
    
    def get_market_data(self, product_id):
        """Get fresh market data for product"""
        # Try WebSocket data first
        with self.market_data_lock:
            if product_id in self.market_data:
                data = self.market_data[product_id]
                if time.time() - data['timestamp'] < 5:  # Fresh data
                    return data['best_bid'], data['best_ask'], True
        
        # Fallback to REST API
        try:
            response = rest_client.get_product_book(product_id, limit=1)
            if hasattr(response, 'pricebook') and response.pricebook:
                pricebook = response.pricebook
                if pricebook.asks and pricebook.bids:
                    best_ask = decimal.Decimal(pricebook.asks[0]['price'])
                    best_bid = decimal.Decimal(pricebook.bids[0]['price'])
                    return best_bid, best_ask, True
        except Exception as e:
            logger.warning(f"⚠️ REST data failed for {product_id}: {e}")
        
        return None, None, False
    
    def start(self):
        """Start WebSocket connection"""
        try:
            ws_client = WSClient(api_key=API_KEY, api_secret=API_SECRET, on_message=self.on_message)
            logger.info("🔌 Connecting to WebSocket...")
            ws_client.open()
            time.sleep(3)
            
            logger.info(f"📡 Subscribing to ticker for {self.products}...")
            ws_client.subscribe(product_ids=self.products, channels=["ticker"])
            time.sleep(3)
            
            # Keep alive
            while True:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")

# ============================================================================
# TRADING ENGINE
# ============================================================================

class TradingEngine:
    """Core trading logic with smart pricing"""
    
    def __init__(self, ws_handler, precision_detector):
        self.ws_handler = ws_handler
        self.precision_detector = precision_detector
        self.last_api_call = 0
        
    def safe_api_call(self, api_func, *args, **kwargs):
        """Rate-limited API calls"""
        time_since_last = time.time() - self.last_api_call
        if time_since_last < MIN_API_INTERVAL:
            time.sleep(MIN_API_INTERVAL - time_since_last)
        
        try:
            result = api_func(*args, **kwargs)
            self.last_api_call = time.time()
            return result
        except Exception as e:
            self.last_api_call = time.time()
            raise e
    
    def calculate_limit_price(self, best_bid, best_ask, price_increment):
        """Calculate optimal limit price for post-only orders"""
        spread = best_ask - best_bid
        
        if spread == 0:
            # Zero spread - go below both
            return best_bid - price_increment, "zero-spread"
        elif spread <= price_increment * 2:
            # Tight spread - small buffer below ask
            return best_ask - price_increment, "tight-spread"
        elif spread <= price_increment * 10:
            # Mid spread - between bid/ask
            return best_bid + (spread / 2), "mid-spread"
        else:
            # Wide spread - larger buffer below ask
            return best_ask - (price_increment * 2), "below-ask"
    
    def place_order(self, product_id, quote_amount, limit_price, size_increment, price_increment):
        """Place post-only order with correct precision for both size and price"""
        try:
            base_size = decimal.Decimal(str(quote_amount)) / limit_price
            base_size = (base_size / size_increment).quantize(decimal.Decimal('1')) * size_increment
            
            if base_size <= 0:
                return "Size too small", False
            
            # Format limit price with correct order precision
            formatted_limit_price = limit_price.quantize(price_increment)
            
            response = self.safe_api_call(
                rest_client.limit_order_gtc_buy,
                client_order_id=str(uuid.uuid4()),
                product_id=product_id,
                base_size=str(base_size),
                limit_price=str(formatted_limit_price),  # Use properly formatted price
                post_only=True
            )
            
            if hasattr(response, 'success') and response.success:
                return response.success_response.get('order_id'), True
            else:
                return getattr(response, 'error_response', 'Unknown error'), False
                
        except Exception as e:
            return str(e), False
    
    def check_order_status(self, order_id):
        """Check if order is filled"""
        try:
            response = self.safe_api_call(rest_client.get_order, order_id)
            if hasattr(response, 'order') and response.order:
                status = response.order.status
                filled_size = decimal.Decimal(str(response.order.filled_size or '0'))
                return status, filled_size, True
            return None, None, False
        except Exception as e:
            logger.warning(f"⚠️ Order check failed: {e}")
            return None, None, False
    
    def execute_trade(self, product_id, quote_amount):
        """Execute single trade with smart retry logic and price chasing"""
        logger.info(f"\n⚡ Trading {product_id} (${quote_amount})")
        
        start_time = time.time()
        chase_count = 0
        current_order_id = None
        last_limit_price = None  # Track last order price for chasing
        precision_failures = 0
        post_only_failures = 0
        precision_data = None
        
        while (time.time() - start_time) < MAX_CHASE_TIME and chase_count < MAX_CHASE_ATTEMPTS:
            
            # Circuit breakers
            if precision_failures >= MAX_PRECISION_FAILURES:
                logger.error(f"    🚨 Too many precision failures ({precision_failures})")
                break
            if post_only_failures >= MAX_POST_ONLY_FAILURES:
                logger.error(f"    🚨 Too many post-only failures ({post_only_failures})")
                break
            
            # Get market data
            best_bid, best_ask, success = self.ws_handler.get_market_data(product_id)
            if not success or not best_bid or not best_ask or best_ask < best_bid:
                logger.warning(f"    ⚠️ Invalid market data, retrying...")
                time.sleep(1)
                continue
            
            # Detect precision once
            if precision_data is None:
                precision_data = self.precision_detector.detect(product_id, best_bid, best_ask)
            
            # Calculate limit price using order precision
            limit_price, strategy = self.calculate_limit_price(
                best_bid, best_ask, precision_data['price_increment']
            )
            
            # Ensure valid post-only price (< ask)
            if limit_price >= best_ask:
                limit_price = best_ask - precision_data['price_increment']
            
            # CHASING LOGIC: Pure price-movement based (no time component)
            should_place_order = False
            action = "UNKNOWN"
            
            if current_order_id is None:
                # No existing order - place initial order
                should_place_order = True
                action = "INITIAL"
                
            else:
                # We have an existing order - check if market moved significantly
                # Use market_increment (not order increment) for movement detection
                significant_price_move = precision_data['market_increment'] * 2  # Lowered from 10x to 3x
                
                if last_limit_price is not None and abs(limit_price - last_limit_price) >= significant_price_move:
                    # Market moved significantly - cancel and chase with better price
                    move_amount = limit_price - last_limit_price
                    logger.info(f"    🏃 Market moved! ${last_limit_price:.{precision_data['price_precision']}f} → ${limit_price:.{precision_data['price_precision']}f} ({move_amount:+.{precision_data['market_precision']}f})")
                    try:
                        self.safe_api_call(rest_client.cancel_orders, [current_order_id])
                        logger.debug(f"    ✅ Cancelled order for price chasing")
                    except Exception as e:
                        logger.warning(f"    ⚠️ Cancel failed: {e}")
                    
                    current_order_id = None
                    should_place_order = True
                    action = f"CHASE #{chase_count + 1}"
                    
                else:
                    # Price hasn't moved significantly - check existing order status
                    status, filled_size, status_ok = self.check_order_status(current_order_id)
                    if status_ok and status == 'FILLED':
                        logger.info(f"    ✅ Order filled! Size: {filled_size}")
                        return True
                    elif status_ok and status in ['CANCELLED', 'EXPIRED', 'FAILED']:
                        logger.warning(f"    ⚠️ Order {status}, retrying...")
                        current_order_id = None
                        should_place_order = True
                        action = "RETRY"
                    # If status is 'OPEN' or check failed, continue monitoring (no action needed)
            
            if should_place_order:
                chase_count += 1
                logger.info(f"    ⚡ {action}: Bid=${best_bid:.{precision_data['market_precision']}f} | Ask=${best_ask:.{precision_data['market_precision']}f} | Limit=${limit_price:.{precision_data['price_precision']}f} ({strategy})")
                
                order_result, order_success = self.place_order(
                    product_id, quote_amount, limit_price, precision_data['size_increment'], precision_data['price_increment']
                )
                
                if order_success:
                    current_order_id = order_result
                    last_limit_price = limit_price  # Remember this price for chasing
                    precision_failures = 0
                    post_only_failures = 0
                    logger.info(f"    ✅ Order placed successfully")
                else:
                    logger.warning(f"    ❌ Order failed: {order_result}")
                    
                    if 'INVALID_LIMIT_PRICE_POST_ONLY' in str(order_result):
                        post_only_failures += 1
                        continue
                    elif 'INVALID_PRICE_PRECISION' in str(order_result):
                        # Learn the correct order price precision
                        precision_data = self.precision_detector.adjust_price_precision(product_id, order_result)
                        if precision_data:
                            logger.info(f"    🔄 Retrying with learned price precision")
                            continue
                        else:
                            precision_failures += 1
                            continue
                    elif 'INVALID_SIZE_PRECISION' in str(order_result):
                        # Learn the correct size precision
                        precision_data = self.precision_detector.adjust_size_precision(product_id, order_result)
                        if precision_data:
                            logger.info(f"    🔄 Retrying with learned size precision")
                            continue
                        else:
                            precision_failures += 1
                            continue
                    else:
                        time.sleep(0.5)
                        continue
            
            time.sleep(0.5)
        
        # Cleanup
        if current_order_id:
            # Final check if order filled during timeout
            status, filled_size, status_ok = self.check_order_status(current_order_id)
            if status_ok and status == 'FILLED':
                logger.info(f"    ✅ Order filled at timeout! Size: {filled_size}")
                return True
            
            # Cancel unfilled order
            try:
                self.safe_api_call(rest_client.cancel_orders, [current_order_id])
                logger.debug(f"    🧹 Cancelled unfilled order")
            except:
                pass
        
        logger.warning(f"    ⏰ Trade timeout after {chase_count} attempts")
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main trading execution"""
    logger.info("🚀 DYNAMIC PORTFOLIO TRADING BOT")
    logger.info("=" * 50)
    for crypto, amount in CRYPTOS_TO_BUY.items():
        percentage = (amount / TOTAL_INVESTMENT) * 100
        logger.info(f"{crypto}: ${amount:.2f} ({percentage:.1f}%)")
    logger.info("=" * 50)
    
    # Initialize components
    products = list(CRYPTOS_TO_BUY.keys())
    ws_handler = WebSocketHandler(products)
    precision_detector = PrecisionDetector()
    trading_engine = TradingEngine(ws_handler, precision_detector)
    
    # Start WebSocket in background
    ws_thread = threading.Thread(target=ws_handler.start, daemon=True)
    ws_thread.start()
    
    # Wait for WebSocket data
    logger.info("⏳ Waiting for WebSocket market data...")
    timeout = 15
    for i in range(timeout):
        time.sleep(1)
        with ws_handler.market_data_lock:
            available_products = list(ws_handler.market_data.keys())
        
        if len(available_products) == len(products):
            logger.info(f"✅ WebSocket ready! Got data for: {available_products}")
            break
        elif available_products:
            logger.debug(f"    📊 Got {len(available_products)}/{len(products)} products...")
    else:
        logger.warning("⚠️ WebSocket timeout, using REST-only mode")
    
    # Execute trades
    successful_trades = 0
    total_trades = len(CRYPTOS_TO_BUY)
    start_total = time.time()
    
    logger.info(f"🏁 Starting trade execution: {total_trades} products")
    
    for i, (crypto, amount) in enumerate(CRYPTOS_TO_BUY.items(), 1):
        logger.info(f"\n[{i}/{total_trades}] Processing {crypto}...")
        
        trade_start = time.time()
        success = trading_engine.execute_trade(crypto, amount)
        trade_time = time.time() - trade_start
        
        if success:
            successful_trades += 1
            logger.info(f"    ⚡ {crypto} completed in {trade_time:.1f}s!")
        else:
            logger.error(f"    ❌ {crypto} failed after {trade_time:.1f}s")
        
        if i < total_trades:
            time.sleep(0.5)
    
    total_time = time.time() - start_total
    logger.info(f"\n🏁 Execution complete in {total_time:.1f}s!")
    logger.info(f"✅ Successful: {successful_trades}/{total_trades}")
    logger.info(f"💰 All orders used post-only (maker fees)")
    logger.info("=== TRADING BOT SESSION ENDED ===")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Trading bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")