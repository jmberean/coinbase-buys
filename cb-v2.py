import uuid
import time
import decimal
from coinbase.rest import RESTClient
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
    "BTC-USD": 0.50,  # 50%
    "ETH-USD": 0.50,  # 50%
}

# Trading settings
PENNY_BUFFER = decimal.Decimal('0.01')
MAX_CHASE_TIME = 600  # 10 minutes
MONITOR_INTERVAL = 8  # 8 seconds
MAX_CHASE_ATTEMPTS = 8
MIN_API_INTERVAL = 1.5

# Calculate amounts
CRYPTOS_TO_BUY = {
    crypto: round(TOTAL_INVESTMENT * percentage, 2)
    for crypto, percentage in PORTFOLIO_ALLOCATION.items()
}

# Print summary
print("🛡️ COINBASE POST-ONLY TRADING BOT")
print("=" * 50)
for crypto, amount in CRYPTOS_TO_BUY.items():
    percentage = (amount / TOTAL_INVESTMENT) * 100
    print(f"{crypto}: ${amount:.2f} ({percentage:.1f}%)")
print("=" * 50)

# Initialize client
try:
    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET, rate_limit_headers=True)
    print("✅ Coinbase client initialized")
except Exception as e:
    print(f"❌ Client initialization failed: {e}")
    exit()

# Rate limiting
last_api_call = 0

def safe_api_call(api_func, *args, **kwargs):
    """Rate-limited API calls"""
    global last_api_call
    
    time_since_last = time.time() - last_api_call
    if time_since_last < MIN_API_INTERVAL:
        time.sleep(MIN_API_INTERVAL - time_since_last)
    
    try:
        result = api_func(*args, **kwargs)
        last_api_call = time.time()
        return result
    except Exception as e:
        last_api_call = time.time()
        raise e

def get_market_data(product_id):
    """Get best bid and ask prices"""
    try:
        book_response = safe_api_call(client.get_product_book, product_id, limit=3)
        
        if hasattr(book_response, 'pricebook') and book_response.pricebook:
            pricebook = book_response.pricebook
            
            asks = pricebook.asks
            bids = pricebook.bids
            
            if asks and bids and len(asks) > 0 and len(bids) > 0:
                best_ask = decimal.Decimal(asks[0]['price'])
                best_bid = decimal.Decimal(bids[0]['price'])
                return best_bid, best_ask, True
        
        return None, None, False
    except Exception as e:
        print(f"    ❌ Order book error: {e}")
        return None, None, False

def place_order(product_id, quote_amount, limit_price):
    """Place a post-only limit order"""
    try:
        # Calculate base size
        base_size = decimal.Decimal(str(quote_amount)) / limit_price
        base_size = base_size.quantize(decimal.Decimal('0.00000001'))
        
        client_order_id = str(uuid.uuid4())
        
        response = safe_api_call(
            client.limit_order_gtc_buy,
            client_order_id=client_order_id,
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

def check_order(order_id):
    """Check order status"""
    try:
        response = safe_api_call(client.get_order, order_id)
        if hasattr(response, 'order') and response.order:
            status = response.order.status
            filled_size = decimal.Decimal(str(response.order.filled_size or '0'))
            return status, filled_size, True
        return None, None, False
    except Exception as e:
        print(f"    ❌ Order status error: {e}")
        return None, None, False

def cancel_order(order_id):
    """Cancel an order"""
    try:
        safe_api_call(client.cancel_orders, [order_id])
        return True
    except Exception as e:
        print(f"    ❌ Cancel error: {e}")
        return False

def execute_trade(product_id, quote_amount):
    """Execute a single trade with chasing logic"""
    print(f"\n🎯 Trading {product_id} (${quote_amount})")
    
    start_time = time.time()
    chase_count = 0
    current_order_id = None
    
    while (time.time() - start_time) < MAX_CHASE_TIME and chase_count < MAX_CHASE_ATTEMPTS:
        
        # Get fresh market data
        best_bid, best_ask, success = get_market_data(product_id)
        if not success:
            print("    ⚠️ Failed to get market data, retrying...")
            time.sleep(MONITOR_INTERVAL)
            continue
        
        # Start with penny below ask (your original approach)
        spread = best_ask - best_bid
        limit_price = best_ask - PENNY_BUFFER
        
        # Safety check: ensure limit is below ask but above bid
        if limit_price >= best_ask:
            limit_price = best_ask - (PENNY_BUFFER * 2)
        if limit_price <= best_bid:
            limit_price = best_bid + PENNY_BUFFER
        
        # Check existing order
        if current_order_id:
            status, filled_size, status_success = check_order(current_order_id)
            
            if status_success:
                if status == 'FILLED':
                    print(f"    ✅ Order filled! Size: {filled_size}")
                    return True
                elif status in ['CANCELLED', 'EXPIRED', 'FAILED']:
                    print(f"    ⚠️ Order {status}, retrying...")
                    current_order_id = None
                # If PENDING, we'll cancel and replace with better price
            
            # Cancel existing order to place new one
            if current_order_id:
                cancel_order(current_order_id)
                current_order_id = None
        
        # Show market context
        print(f"    📊 Bid: ${best_bid:.2f} | Ask: ${best_ask:.2f} | Spread: ${spread:.2f}")
        print(f"    🎯 Limit: ${limit_price:.2f} (${best_ask - limit_price:.2f} below ask)")
        
        # Place order with retry logic for stale data
        order_result, order_success = place_order(product_id, quote_amount, limit_price)
        
        if order_success:
            current_order_id = order_result
            chase_count += 1
            print(f"    ✅ Order placed (attempt {chase_count})")
        else:
            print(f"    ❌ Order failed: {order_result}")
            
            # Handle post-only rejections due to stale market data
            if 'INVALID_LIMIT_PRICE_POST_ONLY' in str(order_result) or 'post only' in str(order_result).lower():
                print(f"    🔄 Market moved! Getting fresh data...")
                # Don't sleep - immediately retry with fresh market data
                continue
            
            # Other errors - wait a bit
            time.sleep(MONITOR_INTERVAL / 2)
            continue
        
        # Wait before next check
        elapsed = int(time.time() - start_time)
        print(f"    ⏳ Monitoring... {elapsed}s", end='\r')
        time.sleep(MONITOR_INTERVAL)
    
    # Cleanup
    if current_order_id:
        # Final check if order filled during timeout
        status, filled_size, status_success = check_order(current_order_id)
        if status_success and status == 'FILLED':
            print(f"\n    ✅ Order filled at timeout! Size: {filled_size}")
            return True
        
        # Cancel remaining order
        cancel_order(current_order_id)
        print(f"\n    ⏰ Timeout after {chase_count} attempts")
    
    return False

# Main execution
if __name__ == "__main__":
    print(f"\n🚀 Starting execution...")
    
    successful_trades = 0
    total_trades = len(CRYPTOS_TO_BUY)
    
    for i, (crypto, amount) in enumerate(CRYPTOS_TO_BUY.items(), 1):
        print(f"\n[{i}/{total_trades}] Processing {crypto}...")
        
        success = execute_trade(crypto, amount)
        if success:
            successful_trades += 1
            print(f"    ✅ {crypto} trade successful!")
        else:
            print(f"    ❌ {crypto} trade failed")
        
        # Brief pause between trades
        if i < total_trades:
            time.sleep(3)
    
    print(f"\n🏁 Execution complete!")
    print(f"✅ Successful: {successful_trades}/{total_trades}")
    print(f"💰 All orders used post-only (maker fees)")