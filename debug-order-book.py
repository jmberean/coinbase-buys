#!/usr/bin/env python3
"""
Debug version to find exactly where the string/int comparison error occurs
"""

import uuid
import os
import time
import decimal
from coinbase.rest import RESTClient
from dotenv import dotenv_values
import traceback

# Set decimal precision for accurate calculations
decimal.getcontext().prec = 10

# Load environment variables
config = dotenv_values()
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

if not API_KEY or not API_SECRET:
    print("Error: API credentials not found")
    exit()

# Configuration
PENNY_BUFFER = decimal.Decimal('0.01')
MIN_API_INTERVAL = 1.5
MAX_PRICE_DEVIATION = 0.05
MIN_LIQUIDITY_MULTIPLE = 2.0

# Initialize client
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET, rate_limit_headers=True)

last_api_call = 0

def throttled_api_call(api_func, *args, **kwargs):
    """Rate-limited API calls with detailed debugging."""
    global last_api_call
    
    time_since_last = time.time() - last_api_call
    if time_since_last < MIN_API_INTERVAL:
        time.sleep(MIN_API_INTERVAL - time_since_last)
    
    try:
        print(f"    📡 API Call: {api_func.__name__} with args: {args}")
        result = api_func(*args, **kwargs)
        last_api_call = time.time()
        print(f"    ✅ API Call successful")
        return result
    except Exception as e:
        last_api_call = time.time()
        print(f"    ❌ API Call failed: {e}")
        raise e

def debug_get_order_book_data(product_id: str):
    """Debug version of order book function."""
    try:
        print(f"    🔍 Getting order book for {product_id}")
        book_response = throttled_api_call(client.get_product_book, product_id, limit=5)
        
        print(f"    📋 Book response type: {type(book_response)}")
        
        if hasattr(book_response, 'pricebook') and book_response.pricebook:
            pricebook = book_response.pricebook
            print(f"    📋 Pricebook type: {type(pricebook)}")
            
            if hasattr(pricebook, 'asks') and pricebook.asks:
                asks = pricebook.asks
                print(f"    📋 Asks type: {type(asks)}, length: {len(asks)}")
                
                if len(asks) > 0:
                    first_ask = asks[0]
                    print(f"    📋 First ask: {first_ask} (type: {type(first_ask)})")
                    
                    # Carefully extract price and size
                    price_str = first_ask['price']
                    size_str = first_ask['size']
                    print(f"    📋 Price string: '{price_str}' (type: {type(price_str)})")
                    print(f"    📋 Size string: '{size_str}' (type: {type(size_str)})")
                    
                    # Convert to Decimal
                    best_ask = decimal.Decimal(str(price_str))
                    best_ask_size = decimal.Decimal(str(size_str))
                    print(f"    📋 Best ask Decimal: {best_ask} (type: {type(best_ask)})")
                    print(f"    📋 Best ask size Decimal: {best_ask_size} (type: {type(best_ask_size)})")
                    
                    # Calculate total liquidity
                    total_liquidity = decimal.Decimal('0')
                    for i, ask in enumerate(asks[:3]):
                        ask_size = decimal.Decimal(str(ask['size']))
                        total_liquidity += ask_size
                        print(f"    📋 Ask {i} size: {ask_size}, running total: {total_liquidity}")
                    
                    print(f"    ✅ Order book data processed successfully")
                    return {
                        'best_ask': best_ask,
                        'best_ask_size': best_ask_size,
                        'total_liquidity': total_liquidity,
                        'success': True
                    }
        
        return {'success': False, 'error': 'No ask data available'}
        
    except Exception as e:
        print(f"    ❌ Order book error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def debug_execute_order(product_id: str, quote_size: float):
    """Debug version of order execution."""
    print(f"\n🔍 DEBUG EXECUTION: {product_id} (${quote_size})")
    
    try:
        # Step 1: Get order book
        print(f"\n📊 STEP 1: Getting order book data...")
        book_data = debug_get_order_book_data(product_id)
        
        if not book_data['success']:
            print(f"❌ Order book failed: {book_data['error']}")
            return False
        
        current_ask = book_data['best_ask']
        ask_liquidity = book_data['best_ask_size']
        total_liquidity = book_data['total_liquidity']
        
        print(f"✅ Order book data:")
        print(f"    Current ask: {current_ask} (type: {type(current_ask)})")
        print(f"    Ask liquidity: {ask_liquidity} (type: {type(ask_liquidity)})")
        print(f"    Total liquidity: {total_liquidity} (type: {type(total_liquidity)})")
        
        # Step 2: Safety checks
        print(f"\n🛡️ STEP 2: Safety checks...")
        
        # Price deviation check (this might be where the error occurs)
        initial_ask_price = current_ask  # Set initial price
        print(f"    Initial ask price: {initial_ask_price} (type: {type(initial_ask_price)})")
        
        try:
            price_deviation = abs(float((current_ask - initial_ask_price) / initial_ask_price))
            print(f"    Price deviation: {price_deviation} (type: {type(price_deviation)})")
            print(f"    Max deviation: {MAX_PRICE_DEVIATION} (type: {type(MAX_PRICE_DEVIATION)})")
            
            if price_deviation > MAX_PRICE_DEVIATION:
                print(f"    🛑 Price moved {price_deviation:.1%} from start")
                return False
            else:
                print(f"    ✅ Price deviation OK: {price_deviation:.1%}")
        except Exception as e:
            print(f"    ❌ Price deviation check failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
        
        # Liquidity check (this might also cause the error)
        print(f"\n💧 Liquidity check...")
        remaining_quote_size = quote_size
        print(f"    Remaining quote size: {remaining_quote_size} (type: {type(remaining_quote_size)})")
        print(f"    Current ask: {current_ask} (type: {type(current_ask)})")
        
        try:
            required_base_size = decimal.Decimal(str(remaining_quote_size)) / current_ask
            print(f"    Required base size: {required_base_size} (type: {type(required_base_size)})")
            
            min_liquidity_multiple = decimal.Decimal(str(MIN_LIQUIDITY_MULTIPLE))
            print(f"    Min liquidity multiple: {min_liquidity_multiple} (type: {type(min_liquidity_multiple)})")
            
            required_liquidity = required_base_size * min_liquidity_multiple
            print(f"    Required liquidity: {required_liquidity} (type: {type(required_liquidity)})")
            print(f"    Available liquidity: {total_liquidity} (type: {type(total_liquidity)})")
            
            if total_liquidity < required_liquidity:
                print(f"    📊 Insufficient liquidity")
                return False
            else:
                print(f"    ✅ Liquidity OK")
        except Exception as e:
            print(f"    ❌ Liquidity check failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
        
        # Step 3: Order placement calculation
        print(f"\n📝 STEP 3: Order calculation...")
        try:
            optimal_price = current_ask - PENNY_BUFFER
            print(f"    Optimal price: {optimal_price} (type: {type(optimal_price)})")
            print(f"    ✅ All calculations successful!")
            return True
            
        except Exception as e:
            print(f"    ❌ Order calculation failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Execution failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 DEBUGGING STRING/INT COMPARISON ERROR")
    print("="*60)
    
    # Test with BTC-USD
    result = debug_execute_order("BTC-USD", 1.0)
    
    if result:
        print("✅ Debug execution completed successfully!")
    else:
        print("❌ Debug execution failed - check output above for details")