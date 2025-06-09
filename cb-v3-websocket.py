import uuid
import time
import decimal
import json
import threading
from coinbase.rest import RESTClient
from coinbase.websocket import WSClient
from dotenv import dotenv_values

# Set decimal precision
decimal.getcontext().prec = 10

# Load environment variables
config = dotenv_values()
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

if not API_KEY or not API_SECRET:
    print("❌ Error: API credentials not found in .env file")
    exit()

# Configuration
TOTAL_INVESTMENT = 2.00
PORTFOLIO_ALLOCATION = {
    # "BTC-USD": 0.50,  # 50%
    # "ETH-USD": 0.50,  # 50%
    
    # Core Foundation (20%)
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

# Fast trading settings
PENNY_BUFFER = decimal.Decimal('0.01')
MAX_CHASE_TIME = 300  # 5 minutes
MAX_CHASE_ATTEMPTS = 12
MIN_API_INTERVAL = 0.5
SIGNIFICANT_PRICE_MOVE = decimal.Decimal('0.05')

# Calculate amounts
CRYPTOS_TO_BUY = {
    crypto: round(TOTAL_INVESTMENT * percentage, 2)
    for crypto, percentage in PORTFOLIO_ALLOCATION.items()
}

print("🚀 DYNAMIC PORTFOLIO TRADING BOT")
print("=" * 50)
for crypto, amount in CRYPTOS_TO_BUY.items():
    percentage = (amount / TOTAL_INVESTMENT) * 100
    print(f"{crypto}: ${amount:.2f} ({percentage:.1f}%)")
print("=" * 50)

# Initialize REST client
try:
    rest_client = RESTClient(api_key=API_KEY, api_secret=API_SECRET, rate_limit_headers=True)
    print("✅ REST client initialized")
except Exception as e:
    print(f"❌ REST client failed: {e}")
    exit()

# Global market data storage
market_data = {}
market_data_lock = threading.Lock()
ws_connected = False
ws_data_received = False

class DynamicTrader:
    def __init__(self):
        self.last_api_call = 0
        # Dynamic product list from portfolio allocation
        self.trading_products = list(CRYPTOS_TO_BUY.keys())
        
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

    def get_live_market_data(self, product_id):
        """Get market data from WebSocket or fallback to REST"""
        global ws_data_received
        
        # Try WebSocket data first
        if ws_data_received:
            with market_data_lock:
                if product_id in market_data:
                    data = market_data[product_id]
                    # Check if data is fresh (less than 5 seconds old)
                    if time.time() - data.get('timestamp', 0) < 5:
                        return data.get('best_bid'), data.get('best_ask'), True
        
        # Fallback to REST API
        try:
            book_response = self.safe_api_call(rest_client.get_product_book, product_id, limit=1)
            if hasattr(book_response, 'pricebook') and book_response.pricebook:
                pricebook = book_response.pricebook
                if pricebook.asks and pricebook.bids:
                    best_ask = decimal.Decimal(pricebook.asks[0]['price'])
                    best_bid = decimal.Decimal(pricebook.bids[0]['price'])
                    return best_bid, best_ask, True
            return None, None, False
        except:
            return None, None, False

    def place_fast_order(self, product_id, quote_amount, limit_price):
        """Optimized order placement"""
        try:
            base_size = decimal.Decimal(str(quote_amount)) / limit_price
            base_size = base_size.quantize(decimal.Decimal('0.00000001'))
            
            response = self.safe_api_call(
                rest_client.limit_order_gtc_buy,
                client_order_id=str(uuid.uuid4()),
                product_id=product_id,
                base_size=str(base_size),
                limit_price=str(limit_price.quantize(decimal.Decimal('0.01'))),
                post_only=True
            )
            
            if hasattr(response, 'success') and response.success:
                order_id = response.success_response.get('order_id')
                return order_id, True
            else:
                error = getattr(response, 'error_response', 'Unknown error')
                return str(error), False
                
        except Exception as e:
            return str(e), False

    def check_order_fast(self, order_id):
        """Quick order status check"""
        try:
            response = self.safe_api_call(rest_client.get_order, order_id)
            if hasattr(response, 'order') and response.order:
                status = response.order.status
                filled_size = decimal.Decimal(str(response.order.filled_size or '0'))
                return status, filled_size, True
            return None, None, False
        except Exception as e:
            return None, None, False

    def execute_fast_trade(self, product_id, quote_amount):
        """Ultra-fast trading execution with fixed tight spread handling"""
        print(f"\n⚡ Fast Trading {product_id} (${quote_amount})")
        
        start_time = time.time()
        chase_count = 0
        current_order_id = None
        last_limit_price = None
        
        while (time.time() - start_time) < MAX_CHASE_TIME and chase_count < MAX_CHASE_ATTEMPTS:
            
            # Get market data
            best_bid, best_ask, success = self.get_live_market_data(product_id)
            if not success:
                print(f"    ⚠️ No market data for {product_id}, waiting...")
                time.sleep(1)
                continue
            
            # Calculate limit price with improved tight spread handling
            spread = best_ask - best_bid
            
            if spread <= decimal.Decimal('0.02'):  # Very tight spread (≤2¢)
                # Use mid-spread pricing for tight markets
                limit_price = best_bid + (spread / 2)
                pricing_strategy = "mid-spread"
            else:
                # Normal spread - use ask-based pricing
                limit_price = best_ask - PENNY_BUFFER
                pricing_strategy = "below-ask"
            
            # FIXED: Changed <= to < to fix the equality bug
            if limit_price >= best_ask:
                limit_price = best_ask - decimal.Decimal('0.005')  # Half penny below
            if limit_price < best_bid:  # FIXED: was <= best_bid
                limit_price = best_bid + decimal.Decimal('0.005')  # Half penny above
            
            # Smart order management
            should_place_order = False
            
            if current_order_id is None:
                should_place_order = True
                action = "INITIAL"
            elif last_limit_price is None or abs(limit_price - last_limit_price) >= SIGNIFICANT_PRICE_MOVE:
                # Cancel and replace for better price
                try:
                    self.safe_api_call(rest_client.cancel_orders, [current_order_id])
                except:
                    pass
                current_order_id = None
                should_place_order = True
                action = f"CHASE #{chase_count + 1}"
            else:
                # Check if existing order filled
                status, filled_size, status_success = self.check_order_fast(current_order_id)
                if status_success and status == 'FILLED':
                    print(f"    ✅ Order filled! Size: {filled_size}")
                    return True
                elif status_success and status in ['CANCELLED', 'EXPIRED', 'FAILED']:
                    current_order_id = None
                    should_place_order = True
                    action = "RETRY"
            
            if should_place_order:
                if pricing_strategy == "mid-spread":
                    print(f"    ⚡ {action}: Bid=${best_bid:.2f} | Ask=${best_ask:.2f} | Limit=${limit_price:.3f} (mid-spread)")
                else:
                    print(f"    ⚡ {action}: Bid=${best_bid:.2f} | Ask=${best_ask:.2f} | Limit=${limit_price:.2f} (below-ask)")
                
                order_result, order_success = self.place_fast_order(product_id, quote_amount, limit_price)
                
                if order_success:
                    current_order_id = order_result
                    last_limit_price = limit_price
                    chase_count += 1
                    print(f"    ✅ Fast order placed (attempt {chase_count})")
                else:
                    print(f"    ❌ Order failed: {order_result}")
                    if 'INVALID_LIMIT_PRICE_POST_ONLY' in str(order_result):
                        continue  # Immediate retry with fresh data
                    time.sleep(0.5)
                    continue
            
            # Short wait
            time.sleep(0.5)
        
        # Final cleanup
        if current_order_id:
            status, filled_size, status_success = self.check_order_fast(current_order_id)
            if status_success and status == 'FILLED':
                print(f"    ✅ Order filled at timeout! Size: {filled_size}")
                return True
            
            try:
                self.safe_api_call(rest_client.cancel_orders, [current_order_id])
            except:
                pass
            
            print(f"    ⏰ Fast timeout after {chase_count} attempts")
        
        return False

# FIXED WebSocket message handler - NOW DYNAMIC!
def dynamic_on_message(msg):
    """Dynamic message handler that works with any portfolio"""
    global ws_data_received
    
    try:
        # Parse message
        if isinstance(msg, str):
            msg = json.loads(msg)
        
        # Handle ticker channel
        if isinstance(msg, dict) and msg.get('channel') == 'ticker':
            events = msg.get('events', [])
            
            for event in events:
                # Check for ticker type (most important)
                if event.get('type') == 'ticker':
                    product_id = event.get('product_id')
                    
                    # DYNAMIC: Check if product is in our trading portfolio
                    if product_id in CRYPTOS_TO_BUY:
                        best_bid = event.get('best_bid')
                        best_ask = event.get('best_ask')
                        
                        if best_bid and best_ask:
                            try:
                                bid_decimal = decimal.Decimal(str(best_bid))
                                ask_decimal = decimal.Decimal(str(best_ask))
                                
                                if bid_decimal > 0 and ask_decimal > 0:
                                    with market_data_lock:
                                        market_data[product_id] = {
                                            'best_bid': bid_decimal,
                                            'best_ask': ask_decimal,
                                            'timestamp': time.time()
                                        }
                                    
                                    # CRITICAL: Set the flag!
                                    ws_data_received = True
                                    # print(f"📊 WS {product_id}: ${bid_decimal:.2f}|${ask_decimal:.2f}")
                                    
                            except (ValueError, decimal.InvalidOperation):
                                continue
                
                # Also handle tickers array (alternative structure)
                tickers = event.get('tickers', [])
                for ticker in tickers:
                    if ticker.get('type') == 'ticker':
                        product_id = ticker.get('product_id')
                        
                        # DYNAMIC: Check if product is in our trading portfolio
                        if product_id in CRYPTOS_TO_BUY:
                            best_bid = ticker.get('best_bid')
                            best_ask = ticker.get('best_ask')
                            
                            if best_bid and best_ask:
                                try:
                                    bid_decimal = decimal.Decimal(str(best_bid))
                                    ask_decimal = decimal.Decimal(str(best_ask))
                                    
                                    if bid_decimal > 0 and ask_decimal > 0:
                                        with market_data_lock:
                                            market_data[product_id] = {
                                                'best_bid': bid_decimal,
                                                'best_ask': ask_decimal,
                                                'timestamp': time.time()
                                            }
                                        
                                        # CRITICAL: Set the flag!
                                        ws_data_received = True
                                        # print(f"📊 WS {product_id}: ${bid_decimal:.2f}|${ask_decimal:.2f}")
                                        
                                except (ValueError, decimal.InvalidOperation):
                                    continue
        
        # Handle subscriptions confirmation
        elif isinstance(msg, dict) and msg.get('channel') == 'subscriptions':
            print(f"✅ Subscription confirmed: {msg}")
            
    except Exception as e:
        print(f"⚠️ Message handler error: {e}")  # Don't fail silently

# Start WebSocket with dynamic subscriptions
def start_dynamic_websocket():
    """Start WebSocket with dynamic product subscriptions"""
    global ws_connected, ws_data_received
    
    try:
        ws_client = WSClient(api_key=API_KEY, api_secret=API_SECRET, on_message=dynamic_on_message)
        
        # DYNAMIC: Get products from portfolio allocation
        products = list(CRYPTOS_TO_BUY.keys())
        
        print("🔌 Connecting to WebSocket...")
        ws_client.open()
        time.sleep(3)
        ws_connected = True
        
        # Subscribe to ticker channel for all portfolio products
        print(f"📡 Subscribing to ticker for {products}...")
        ws_client.subscribe(product_ids=products, channels=["ticker"])
        print(f"✅ Subscribed to ticker for {products}")
        
        # Give it time to receive initial snapshots
        time.sleep(3)
        
        # Keep WebSocket alive
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        ws_connected = False

def main():
    """Main execution with dynamic portfolio handling"""
    trader = DynamicTrader()
    
    # Start WebSocket in background
    ws_thread = threading.Thread(target=start_dynamic_websocket, daemon=True)
    ws_thread.start()
    
    # Wait for WebSocket data with clear progress
    print("⏳ Waiting for WebSocket market data...")
    wait_start = time.time()
    timeout = 15  # Shorter timeout since we know it works
    
    while (time.time() - wait_start) < timeout:
        time.sleep(1)
        elapsed = int(time.time() - wait_start)
        
        # Check if we have data for all products
        with market_data_lock:
            products_with_data = list(market_data.keys())
            missing_products = [p for p in CRYPTOS_TO_BUY.keys() if p not in products_with_data]
        
        if len(products_with_data) == len(CRYPTOS_TO_BUY):
            print(f"\n✅ WebSocket ready! Got data for: {products_with_data}")
            data_source = "WebSocket + REST fallback"
            break
        elif len(products_with_data) > 0:
            print(f"    📊 Got: {products_with_data} | Missing: {missing_products} | {elapsed}s", end='\r')
        else:
            print(f"    ⏳ Waiting for data... {elapsed}s", end='\r')
    else:
        print(f"\n⚠️ WebSocket timeout, using REST-only mode")
        data_source = "REST API only"
    
    # Execute trades
    successful_trades = 0
    total_trades = len(CRYPTOS_TO_BUY)
    start_total = time.time()
    
    for i, (crypto, amount) in enumerate(CRYPTOS_TO_BUY.items(), 1):
        print(f"\n[{i}/{total_trades}] Processing {crypto}...")
        
        trade_start = time.time()
        success = trader.execute_fast_trade(crypto, amount)
        trade_time = time.time() - trade_start
        
        if success:
            successful_trades += 1
            print(f"    ⚡ {crypto} completed in {trade_time:.1f}s!")
        else:
            print(f"    ❌ {crypto} failed after {trade_time:.1f}s")
        
        if i < total_trades:
            time.sleep(0.5)
    
    total_time = time.time() - start_total
    
    print(f"\n🏁 Dynamic portfolio execution complete in {total_time:.1f}s!")
    print(f"✅ Successful: {successful_trades}/{total_trades}")
    print(f"💰 All orders used post-only (maker fees)")
    print(f"📡 Data source: {data_source}")
    if ws_data_received:
        print(f"🚀 WebSocket provided real-time market data!")

if __name__ == "__main__":
    main()