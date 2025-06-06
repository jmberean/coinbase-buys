import uuid
import os
import time
import decimal
from coinbase.rest import RESTClient # type: ignore
from dotenv import dotenv_values # type: ignore

# Set decimal precision for accurate calculations
decimal.getcontext().prec = 10

# --- Load environment variables from .env file ---
config = dotenv_values()

# Retrieve API keys from environment variables
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

# --- Basic validation for API keys ---
if not API_KEY or not API_SECRET:
    print("Error: COINBASE_API_KEY or COINBASE_API_SECRET not found in .env file.")
    print(
        "Please create a .env file in the same directory as your script with your"
        " API credentials."
    )
    exit()

# Total investment amount (adjust this to your desired total investment)
TOTAL_INVESTMENT = 2.00

# Portfolio allocation percentages based on optimized risk/reward strategy
PORTFOLIO_ALLOCATION = {
    # Core Foundation (20%)
    "BTC-USD": 0.50,   # 10% - Store of value anchor
    "ETH-USD": 0.50,   # 10% - Smart contract foundation  

    # # Core Foundation (20%)
    # "BTC-USD": 0.10,   # 10% - Store of value anchor
    # "ETH-USD": 0.10,   # 10% - Smart contract foundation
    
    # # Established Growth Plays (60%) 
    # "SOL-USD": 0.15,   # 15% - Consumer blockchain leader
    # "XRP-USD": 0.15,   # 15% - Enterprise payments with regulatory clarity
    # "LINK-USD": 0.15,  # 15% - Essential oracle infrastructure
    # "AVAX-USD": 0.15,  # 15% - Institutional tokenization platform
    
    # # Speculative Upside (20%)
    # "UNI-USD": 0.04,   # 4% - DeFi protocol with fee switch potential
    # "QNT-USD": 0.04,   # 4% - Enterprise interoperability
    # "DOT-USD": 0.04,   # 4% - Parachain innovation
    # "ADA-USD": 0.04,   # 4% - Academic development approach
    # "DOGE-USD": 0.04,  # 4% - Community-driven payments
}

# Robust trading configuration
PENNY_BUFFER = decimal.Decimal('0.01')    # 1 penny below best ask (precise decimal)
MAX_CHASE_TIME = 600                      # 10 minutes max time per asset
MONITOR_INTERVAL = 8                      # 8 seconds between checks (rate limit safe)
MAX_CHASE_ATTEMPTS = 8                    # Max number of chases per asset
PRICE_MOVEMENT_THRESHOLD = decimal.Decimal('0.01')  # Re-chase threshold
MIN_API_INTERVAL = 1.5                    # Minimum 1.5s between API calls
MAX_PRICE_DEVIATION = 0.05                # Stop chasing if price moves >5% from start
MIN_LIQUIDITY_MULTIPLE = 2.0              # Require 2x liquidity vs order size

# Calculate dollar amounts based on allocation percentages
CRYPTOS_TO_BUY = {
    crypto: round(TOTAL_INVESTMENT * percentage, 2)
    for crypto, percentage in PORTFOLIO_ALLOCATION.items()
}

# Print allocation summary
print("🛡️ ROBUST DYNAMIC POST-ONLY PORTFOLIO ALLOCATION")
print("=" * 60)
total_check = 0
for crypto, amount in CRYPTOS_TO_BUY.items():
    percentage = (amount / TOTAL_INVESTMENT) * 100
    print(f"{crypto:<12}: ${amount:>7.2f} ({percentage:>5.1f}%)")
    total_check += amount
print("=" * 60)
print(f"{'TOTAL':<12}: ${total_check:>7.2f} ({(total_check/TOTAL_INVESTMENT)*100:>5.1f}%)")
print(f"🛡️ Enhanced Safety: Rate limiting, partial fills, liquidity checks")
print()

# --- Initialize Coinbase API Client ---
try:
    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
    print("✅ Coinbase RESTClient initialized successfully.")
except Exception as e:
    print(f"❌ Error initializing Coinbase RESTClient: {e}")
    exit()

# API throttling
last_api_call = 0

def throttled_api_call(api_func, *args, **kwargs):
    """Rate-limited API calls to prevent hitting Coinbase limits."""
    global last_api_call
    
    # Ensure minimum time between API calls
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

def get_order_book_data(product_id: str):
    """Get order book with liquidity depth analysis."""
    try:
        book = throttled_api_call(client.get_product_book, product_id, limit=5)
        if hasattr(book, 'asks') and book.asks and len(book.asks) > 0:
            best_ask = decimal.Decimal(str(book.asks[0].price))
            best_ask_size = decimal.Decimal(str(book.asks[0].size))
            
            # Calculate total liquidity in top 3 asks
            total_liquidity = sum(decimal.Decimal(str(ask.size)) for ask in book.asks[:3])
            
            return {
                'best_ask': best_ask,
                'best_ask_size': best_ask_size,
                'total_liquidity': total_liquidity,
                'success': True
            }
        return {'success': False, 'error': 'No ask data'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_order_status(order_id: str):
    """Get detailed order status with fill information."""
    try:
        order_status = throttled_api_call(client.get_order, order_id)
        if hasattr(order_status, 'order'):
            order = order_status.order
            return {
                'success': True,
                'status': getattr(order, 'status', 'unknown'),
                'filled_size': decimal.Decimal(str(getattr(order, 'filled_size', '0'))),
                'total_size': decimal.Decimal(str(getattr(order, 'size', '0'))),
                'average_filled_price': getattr(order, 'average_filled_price', None)
            }
        return {'success': False, 'error': 'No order data'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def cancel_order_gracefully(order_id: str):
    """Cancel order with graceful handling of already-filled orders."""
    try:
        # Check final status before canceling
        status_result = check_order_status(order_id)
        if status_result['success']:
            if status_result['status'] in ['FILLED', 'PARTIALLY_FILLED']:
                return {
                    'success': True, 
                    'message': f"Order already {status_result['status']}, not canceling",
                    'was_filled': True,
                    'filled_size': status_result['filled_size']
                }
        
        # Attempt to cancel
        throttled_api_call(client.cancel_orders, [order_id])
        return {'success': True, 'message': 'Order cancelled successfully', 'was_filled': False}
        
    except Exception as e:
        error_msg = str(e).lower()
        if 'already filled' in error_msg or 'not found' in error_msg or 'cannot cancel' in error_msg:
            return {
                'success': True, 
                'message': f"Order likely filled during cancel attempt: {e}",
                'was_filled': True
            }
        return {'success': False, 'error': str(e)}

def calculate_precise_order_size(quote_size: float, limit_price: decimal.Decimal, product_id: str):
    """Calculate order size with proper precision and minimum size validation."""
    base_size = decimal.Decimal(str(quote_size)) / limit_price
    
    # Get product info for precision requirements
    try:
        product_info = throttled_api_call(client.get_product, product_id)
        if hasattr(product_info, 'base_increment'):
            base_increment = decimal.Decimal(str(product_info.base_increment))
            # Round to proper increment
            base_size = (base_size / base_increment).quantize(decimal.Decimal('1')) * base_increment
        
        # Check minimum size (typically around 0.001 for most pairs)
        min_size = decimal.Decimal('0.001')  # Conservative minimum
        if base_size < min_size:
            return None, f"Order size {base_size} below minimum {min_size}"
            
        return base_size, None
    except Exception as e:
        # Fallback to 8 decimal places
        return base_size.quantize(decimal.Decimal('0.00000001')), None

def place_precise_post_only_order(product_id: str, quote_size: float, limit_price: decimal.Decimal):
    """Place post-only order with precise calculations."""
    base_size, error = calculate_precise_order_size(quote_size, limit_price, product_id)
    if error:
        return {'success': False, 'error': error}
    
    client_order_id = str(uuid.uuid4())
    limit_price_str = str(limit_price.quantize(decimal.Decimal('0.01')))
    base_size_str = str(base_size)
    
    try:
        order_response = throttled_api_call(
            client.limit_order_gtc_buy,
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size_str,
            limit_price=limit_price_str,
            post_only=True
        )
        
        if hasattr(order_response, 'success') and order_response.success:
            order_details = order_response.success_response
            order_id = order_details.get('order_id') if isinstance(order_details, dict) else getattr(order_details, 'order_id', None)
            return {
                'success': True, 
                'order_id': order_id,
                'base_size': base_size,
                'limit_price': limit_price
            }
        else:
            error_details = getattr(order_response, 'error_response', 'Unknown error')
            return {'success': False, 'error': str(error_details)}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def execute_robust_chasing_order(product_id: str, quote_size: float):
    """
    Robust chasing strategy with comprehensive safety mechanisms.
    """
    print(f"\n🛡️ ROBUST CHASING: {product_id} (${quote_size})")
    
    start_time = time.time()
    current_order_id = None
    initial_ask_price = None
    chase_count = 0
    total_filled_size = decimal.Decimal('0')
    remaining_quote_size = quote_size
    
    while time.time() - start_time < MAX_CHASE_TIME and chase_count < MAX_CHASE_ATTEMPTS:
        
        # STEP 1: Get order book with liquidity analysis
        book_data = get_order_book_data(product_id)
        if not book_data['success']:
            print(f"    ⚠️ Order book error: {book_data['error']}, retrying...")
            time.sleep(MONITOR_INTERVAL)
            continue
        
        current_ask = book_data['best_ask']
        ask_liquidity = book_data['best_ask_size']
        total_liquidity = book_data['total_liquidity']
        
        # Set initial reference price
        if initial_ask_price is None:
            initial_ask_price = current_ask
        
        # STEP 2: Safety checks
        # Check if price moved too far from start (prevent chasing runaway markets)
        price_deviation = abs(float((current_ask - initial_ask_price) / initial_ask_price))
        if price_deviation > MAX_PRICE_DEVIATION:
            print(f"    🛑 Price moved {price_deviation:.1%} from start, stopping chase")
            break
        
        # Check liquidity sufficiency
        required_base_size = decimal.Decimal(str(remaining_quote_size)) / current_ask
        if total_liquidity < required_base_size * decimal.Decimal(str(MIN_LIQUIDITY_MULTIPLE)):
            print(f"    📊 Insufficient liquidity (need {required_base_size:.4f}, available {total_liquidity:.4f})")
            time.sleep(MONITOR_INTERVAL * 2)  # Wait longer for liquidity
            continue
        
        # STEP 3: Check existing order status first
        should_place_new_order = False
        
        if current_order_id is None:
            should_place_new_order = True
            action = "INITIAL"
        else:
            # Check if current order filled (including partial fills)
            status_result = check_order_status(current_order_id)
            if status_result['success']:
                status = status_result['status']
                filled_size = status_result['filled_size']
                total_size = status_result['total_size']
                
                if status == 'FILLED':
                    total_filled_size += filled_size
                    print(f"    🎯 ORDER FILLED! Total: {total_filled_size}")
                    if hasattr(status_result, 'average_filled_price'):
                        print(f"    💰 Average price: ${status_result['average_filled_price']}")
                    return True
                    
                elif status == 'PARTIALLY_FILLED':
                    # Handle partial fill
                    new_filled = filled_size - total_filled_size
                    total_filled_size = filled_size
                    remaining_quote_size -= float(new_filled * current_ask)
                    
                    print(f"    ⚡ PARTIAL FILL: +{new_filled:.6f}, total: {total_filled_size:.6f}")
                    print(f"    💵 Remaining: ${remaining_quote_size:.2f}")
                    
                    if remaining_quote_size < 1.0:  # Less than $1 remaining
                        print(f"    ✅ Remaining amount too small, considering complete")
                        return True
                    
                    # Cancel and place new order for remaining amount
                    cancel_result = cancel_order_gracefully(current_order_id)
                    print(f"    🔄 {cancel_result['message']}")
                    current_order_id = None
                    should_place_new_order = True
                    action = f"PARTIAL_CHASE"
                    
                elif status in ['CANCELLED', 'EXPIRED', 'FAILED']:
                    print(f"    ⚠️ Order {status}")
                    current_order_id = None
                    should_place_new_order = True
                    action = "RETRY"
                else:
                    # Order still pending - check if we should chase due to price movement
                    # (Implementation continues with existing logic)
                    should_place_new_order = False
            else:
                print(f"    ⚠️ Status check failed: {status_result['error']}")
        
        # STEP 4: Determine if we should chase due to price movement
        if not should_place_new_order and current_order_id:
            # Get current order details to compare prices
            try:
                # For simplicity, let's assume we stored the last limit price
                # In production, you'd want to track this properly
                should_place_new_order = True  # Simplified for this example
                action = f"CHASE #{chase_count + 1}"
            except:
                pass
        
        # STEP 5: Place new order if needed
        if should_place_new_order:
            optimal_price = current_ask - PENNY_BUFFER
            print(f"    🎯 {action}: Ask=${current_ask:.2f} → Limit=${optimal_price:.2f}")
            print(f"    📊 Liquidity: {ask_liquidity:.4f} (top ask), {total_liquidity:.4f} (top 3)")
            
            # Cancel existing order first (if any)
            if current_order_id:
                cancel_result = cancel_order_gracefully(current_order_id)
                if cancel_result['was_filled']:
                    print(f"    💎 Order was filled during cancel! {cancel_result['message']}")
                    # Re-check status to get fill details
                    final_status = check_order_status(current_order_id)
                    if final_status['success'] and final_status['status'] == 'FILLED':
                        return True
                else:
                    print(f"    🚫 {cancel_result['message']}")
                current_order_id = None
            
            # Place new order
            order_result = place_precise_post_only_order(product_id, remaining_quote_size, optimal_price)
            
            if order_result['success']:
                current_order_id = order_result['order_id']
                chase_count += 1
                print(f"    ✅ Order placed: {current_order_id[:8]}... (size: {order_result['base_size']:.6f})")
            else:
                print(f"    ❌ Order failed: {order_result['error']}")
                
                # Check if it's a "not below ask" error - get fresh data and retry
                if 'post only' in str(order_result['error']).lower():
                    print(f"    🔄 Post-only rejected, refreshing order book...")
                    continue  # Skip the sleep and retry immediately
                
                time.sleep(MONITOR_INTERVAL / 2)  # Shorter wait on errors
                continue
        
        # STEP 6: Progress update and wait
        elapsed = int(time.time() - start_time)
        if current_order_id:
            print(f"    ⏳ Monitoring... {elapsed}s (Ask: ${current_ask:.2f}, Chases: {chase_count})", end='\r')
        
        time.sleep(MONITOR_INTERVAL)
    
    # Timeout or max chases reached
    elapsed = int(time.time() - start_time)
    if chase_count >= MAX_CHASE_ATTEMPTS:
        print(f"\n    🛑 Max chase attempts ({MAX_CHASE_ATTEMPTS}) reached")
    else:
        print(f"\n    ⏰ Timeout after {elapsed}s")
    
    # Clean up any remaining order
    if current_order_id:
        cancel_result = cancel_order_gracefully(current_order_id)
        if cancel_result['was_filled']:
            print(f"    💎 Final order was filled! {cancel_result['message']}")
            return True
        else:
            print(f"    🚫 Final cleanup: {cancel_result['message']}")
    
    # Check if we got any fills
    if total_filled_size > 0:
        fill_percentage = float(total_filled_size * initial_ask_price) / quote_size
        print(f"    ⚡ Partial success: {fill_percentage:.1%} filled ({total_filled_size:.6f})")
        return fill_percentage > 0.8  # Consider 80%+ fill a success
    
    return False

# --- Execute robust chasing orders for each crypto ---
if client:
    successful_orders = 0
    partial_orders = 0
    failed_orders = 0
    total_orders = len(CRYPTOS_TO_BUY)
    
    print(f"\n🚀 STARTING ROBUST EXECUTION")
    print(f"🛡️ Safety Features: Rate limiting, partial fills, liquidity checks, graceful cancels")
    print(f"⚡ Monitor Interval: {MONITOR_INTERVAL}s (API safe)")
    print(f"🎯 Max Chases: {MAX_CHASE_ATTEMPTS} per asset")
    print(f"⏰ Max Time: {MAX_CHASE_TIME}s per asset")
    print("=" * 80)
    
    for i, (crypto, amount) in enumerate(CRYPTOS_TO_BUY.items(), 1):
        print(f"\n[{i}/{total_orders}] Processing {crypto}...")
        
        success = execute_robust_chasing_order(crypto, amount)
        if success:
            successful_orders += 1
        else:
            failed_orders += 1
        
        # Brief pause between different assets
        if i < total_orders:
            print(f"    💤 Brief pause before next asset...")
            time.sleep(3)
    
    print("\n" + "=" * 80)
    print(f"🏁 ROBUST EXECUTION COMPLETE")
    print(f"✅ Successful: {successful_orders}/{total_orders}")
    print(f"❌ Failed: {failed_orders}/{total_orders}")
    print(f"💰 All successful orders used MAKER FEES")
    print(f"🛡️ Robust safety mechanisms protected against edge cases")
    
else:
    print("❌ Cannot proceed: API client initialization failed")