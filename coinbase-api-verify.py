#!/usr/bin/env python3
"""
Coinbase Advanced Trade API Method Verification Script
Run this to verify all API methods used in your trading bot exist and work correctly.
"""

from coinbase.rest import RESTClient
from dotenv import dotenv_values
import json

# Load API credentials
config = dotenv_values()
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

def test_api_methods():
    """Test all API methods used in your trading script"""
    
    if not API_KEY or not API_SECRET:
        print("❌ API credentials not found in .env file")
        return False
    
    try:
        # Initialize client with rate limit headers
        client = RESTClient(api_key=API_KEY, api_secret=API_SECRET, rate_limit_headers=True)
        print("✅ RESTClient initialized successfully")
        
        # Test 1: Get product info
        print("\n1. Testing get_product()...")
        try:
            product = client.get_product("BTC-USD")
            print(f"   ✅ Method exists. Current BTC price: ${product.price}")
            print(f"   📊 Response type: {type(product)}")
            
            # Check for base_increment (used in your size calculation)
            if hasattr(product, 'base_increment'):
                print(f"   ✅ base_increment available: {product.base_increment}")
            else:
                print("   ⚠️ base_increment not found - check your precision logic")
                
        except AttributeError as e:
            print(f"   ❌ get_product method issue: {e}")
        except Exception as e:
            print(f"   ❌ get_product failed: {e}")
        
        # Test 2: Get order book
        print("\n2. Testing get_product_book()...")
        try:
            book = client.get_product_book("BTC-USD", limit=5)
            print(f"   ✅ Method exists. Response type: {type(book)}")
            
            # Check structure matches your expectations
            if hasattr(book, 'asks') and book.asks:
                best_ask = book.asks[0]
                print(f"   ✅ Best ask: ${best_ask.price} (size: {best_ask.size})")
                print(f"   ✅ Ask structure matches your code")
            else:
                print("   ⚠️ Order book structure different than expected")
                print(f"   📋 Available attributes: {dir(book)}")
                
        except AttributeError as e:
            print(f"   ❌ get_product_book method not found: {e}")
            print("   💡 Consider using WebSocket for order book data")
        except Exception as e:
            print(f"   ❌ get_product_book failed: {e}")
        
        # Test 3: Order placement (dry run)
        print("\n3. Testing limit_order_gtc_buy() structure...")
        try:
            # Don't actually place order, just check method signature
            method = getattr(client, 'limit_order_gtc_buy')
            print("   ✅ limit_order_gtc_buy method exists")
            print(f"   📋 Method signature: {method.__doc__[:100]}..." if method.__doc__ else "No docs")
            
        except AttributeError:
            print("   ❌ limit_order_gtc_buy method not found")
        
        # Test 4: Order status checking
        print("\n4. Testing get_order()...")
        try:
            method = getattr(client, 'get_order')
            print("   ✅ get_order method exists")
            
        except AttributeError:
            print("   ❌ get_order method not found")
        
        # Test 5: Order cancellation
        print("\n5. Testing cancel_orders()...")
        try:
            method = getattr(client, 'cancel_orders')
            print("   ✅ cancel_orders method exists")
            print("   📋 Expected parameter: list of order IDs")
            
        except AttributeError:
            print("   ❌ cancel_orders method not found")
        
        # Test 6: Rate limit headers
        print("\n6. Testing rate limit headers...")
        try:
            # Make a simple request to check rate limit headers
            accounts = client.get_accounts()
            print("   ✅ Request successful")
            
            # Check if response has rate limit info
            if hasattr(accounts, '__dict__'):
                attrs = [attr for attr in dir(accounts) if 'rate' in attr.lower() or 'limit' in attr.lower()]
                if attrs:
                    print(f"   ✅ Rate limit attributes found: {attrs}")
                else:
                    print("   ⚠️ No rate limit headers in response object")
            
        except Exception as e:
            print(f"   ❌ Rate limit test failed: {e}")
        
        print("\n" + "="*60)
        print("🎯 RECOMMENDATIONS:")
        print("1. Verify any failed methods above")
        print("2. Test with small orders ($1-2) before running full script")
        print("3. Monitor rate limit headers during execution")
        print("4. Consider WebSocket for real-time order book data")
        
        return True
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

def test_simple_order_response():
    """Test the actual response structure of an order"""
    print("\n" + "="*60)
    print("🧪 RESPONSE STRUCTURE TEST")
    print("This shows you the actual response structure for orders")
    
    try:
        client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
        
        # Get current BTC price
        product = client.get_product("BTC-USD")
        current_price = float(product.price)
        
        # Set a very low limit price so order won't fill
        low_price = str(current_price * 0.5)  # 50% below current price
        
        print(f"Current BTC price: ${current_price}")
        print(f"Test order limit price: ${low_price}")
        print("Placing test order (won't fill due to low price)...")
        
        # Place a very small test order
        response = client.limit_order_gtc_buy(
            client_order_id="test_verification_order",
            product_id="BTC-USD",
            base_size="0.0001",  # Very small size
            limit_price=low_price,
            post_only=True
        )
        
        print(f"\n📋 Response type: {type(response)}")
        print(f"📋 Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        
        # Try to access order_id directly
        if hasattr(response, 'order_id'):
            print(f"✅ Direct access: response.order_id = {response.order_id}")
            
            # Now test order status
            order_status = client.get_order(response.order_id)
            print(f"📋 Order status type: {type(order_status)}")
            print(f"📋 Order status attributes: {[attr for attr in dir(order_status) if not attr.startswith('_')]}")
            
            # Cancel the test order
            cancel_result = client.cancel_orders([response.order_id])
            print(f"✅ Order cancelled: {type(cancel_result)}")
            
        else:
            print("⚠️ No direct order_id attribute - check response structure")
            print(f"Raw response: {response}")
        
    except Exception as e:
        print(f"❌ Order test failed: {e}")
        print("This is expected if you have insufficient funds or API issues")

if __name__ == "__main__":
    print("🔍 COINBASE ADVANCED TRADE API VERIFICATION")
    print("="*60)
    
    success = test_api_methods()
    
    if success:
        print("\n🤔 Want to test actual order response structure?")
        print("This will place and immediately cancel a small test order.")
        
        user_input = input("Run order response test? (y/N): ").lower()
        if user_input == 'y':
            test_simple_order_response()
    
    print("\n✅ Verification complete!")