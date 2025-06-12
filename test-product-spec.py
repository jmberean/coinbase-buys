#!/usr/bin/env python3
"""
Working Coinbase Product Info Extractor
Correctly extracts minimum order sizes and precision data
"""

import decimal
import json
from coinbase.rest import RESTClient
from dotenv import dotenv_values

# Your portfolio
PORTFOLIO_ALLOCATION = {
    "BTC-USD": 0.10,   # 10%
    "ETH-USD": 0.10,   # 10% 
    "SOL-USD": 0.15,   # 15%
    "XRP-USD": 0.15,   # 15%
    "LINK-USD": 0.15,  # 15%
    "AVAX-USD": 0.15,  # 15%
    "UNI-USD": 0.04,   # 4%
    "QNT-USD": 0.04,   # 4%
    "DOT-USD": 0.04,   # 4%
    "ADA-USD": 0.04,   # 4%
    "DOGE-USD": 0.04,  # 4%
}

def setup_client():
    """Initialize Coinbase client"""
    config = dotenv_values()
    api_key = config.get("COINBASE_API_KEY")
    api_secret = config.get("COINBASE_API_SECRET")
    
    if not api_key or not api_secret:
        print("❌ Error: API credentials not found")
        return None
    
    return RESTClient(api_key=api_key, api_secret=api_secret)

def extract_product_specs(product_response):
    """Extract specs from response object (which IS the product)"""
    # The response object itself contains all the product data!
    return {
        'product_id': getattr(product_response, 'product_id', None),
        'base_currency': getattr(product_response, 'base_currency_id', None),
        'quote_currency': getattr(product_response, 'quote_currency_id', None),
        'status': getattr(product_response, 'status', None),
        'base_min_size': getattr(product_response, 'base_min_size', None),
        'base_max_size': getattr(product_response, 'base_max_size', None),
        'quote_min_size': getattr(product_response, 'quote_min_size', None),
        'quote_max_size': getattr(product_response, 'quote_max_size', None),
        'base_increment': getattr(product_response, 'base_increment', None),
        'quote_increment': getattr(product_response, 'quote_increment', None),
        'price_increment': getattr(product_response, 'price_increment', None),
        'current_price': getattr(product_response, 'price', None),
    }

def analyze_precision(base_increment):
    """Calculate precision from increment"""
    if not base_increment:
        return None, None
    
    increment_str = str(base_increment)
    if '.' in increment_str:
        decimal_places = len(increment_str.split('.')[1])
        return decimal_places, decimal.Decimal(increment_str)
    else:
        return 0, decimal.Decimal(increment_str)

def test_allocation(specs, quote_amount):
    """Test if allocation will work"""
    if not specs.get('current_price') or not specs.get('base_increment'):
        return False, ["Missing price or increment data"]
    
    issues = []
    
    # Calculate order size
    price = decimal.Decimal(str(specs['current_price']))
    raw_size = decimal.Decimal(str(quote_amount)) / price
    
    # Round to increment
    base_increment = decimal.Decimal(str(specs['base_increment']))
    rounded_size = (raw_size / base_increment).quantize(decimal.Decimal('1')) * base_increment
    
    # Check minimums
    if specs.get('base_min_size'):
        base_min = decimal.Decimal(str(specs['base_min_size']))
        if rounded_size < base_min:
            issues.append(f"Base size {rounded_size:.8f} < min {base_min}")
    
    if specs.get('quote_min_size'):
        quote_min = float(specs['quote_min_size'])
        if quote_amount < quote_min:
            issues.append(f"Quote ${quote_amount:.2f} < min ${quote_min}")
    
    if rounded_size <= 0:
        issues.append("Rounds to zero")
    
    return len(issues) == 0, issues

def main():
    """Extract all product specifications"""
    print("🔍 COINBASE PRODUCT INFO EXTRACTOR")
    print("=" * 60)
    
    client = setup_client()
    if not client:
        return
    
    all_specs = {}
    size_precision_overrides = {}
    minimum_order_sizes = {}
    total_investment = 100.0
    
    for product_id in PORTFOLIO_ALLOCATION.keys():
        print(f"\n📊 {product_id}:")
        
        try:
            # Get product info (response IS the product!)
            response = client.get_product(product_id)
            specs = extract_product_specs(response)
            
            # Analyze precision
            size_precision, size_increment = analyze_precision(specs.get('base_increment'))
            
            print(f"  Base currency: {specs['base_currency']}")
            print(f"  Status: {specs['status']}")
            print(f"  Base min size: {specs['base_min_size']} {specs['base_currency']}")
            print(f"  Base increment: {specs['base_increment']} {specs['base_currency']}")
            print(f"  Quote min size: ${specs['quote_min_size']}")
            print(f"  Price increment: ${specs['price_increment']}")
            print(f"  Current price: ~${specs['current_price']}")
            
            if size_precision is not None:
                print(f"  → Size precision: {size_precision} decimal places")
                size_precision_overrides[product_id] = size_precision
            
            # Test your allocation
            quote_amount = total_investment * PORTFOLIO_ALLOCATION[product_id]
            success, issues = test_allocation(specs, quote_amount)
            
            status = "✅" if success else "❌"
            print(f"  → ${quote_amount:.2f} allocation: {status}")
            
            if issues:
                for issue in issues:
                    print(f"    ⚠️ {issue}")
            
            # Store data
            all_specs[product_id] = specs
            minimum_order_sizes[product_id] = {
                'base_min': specs.get('base_min_size'),
                'quote_min': specs.get('quote_min_size')
            }
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    # Generate code for your bot
    print(f"\n💻 CODE FOR YOUR TRADING BOT:")
    print("=" * 60)
    
    print("# Add this to your PrecisionDetector class:")
    print("self.size_precision_overrides = {")
    for product_id, precision in size_precision_overrides.items():
        base_curr = all_specs[product_id].get('base_currency', 'Unknown')
        increment = all_specs[product_id].get('base_increment', 'Unknown')
        print(f"    '{product_id}': {precision},  # {increment} {base_curr}")
    print("}")
    
    print(f"\n# Minimum order validation:")
    print("MINIMUM_ORDER_SIZES = {")
    for product_id, mins in minimum_order_sizes.items():
        print(f"    '{product_id}': {{'base_min': '{mins['base_min']}', 'quote_min': '{mins['quote_min']}'}},")
    print("}")
    
    # Summary
    failed_allocations = []
    for product_id in PORTFOLIO_ALLOCATION.keys():
        if product_id in all_specs:
            quote_amount = total_investment * PORTFOLIO_ALLOCATION[product_id]
            success, _ = test_allocation(all_specs[product_id], quote_amount)
            if not success:
                failed_allocations.append(product_id)
    
    print(f"\n📋 SUMMARY:")
    print(f"✅ Working allocations: {len(all_specs) - len(failed_allocations)}/{len(all_specs)}")
    if failed_allocations:
        print(f"❌ Problem allocations: {', '.join(failed_allocations)}")
        print(f"💡 Solution: Increase total investment to $200+ or adjust allocations")
    else:
        print(f"🎉 All allocations should work!")
    
    # Save complete data
    with open('coinbase_product_specs.json', 'w') as f:
        json.dump(all_specs, f, indent=2, default=str)
    print(f"\n💾 Complete specs saved to: coinbase_product_specs.json")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⏹️ Stopped by user")
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")