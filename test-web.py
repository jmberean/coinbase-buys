#!/usr/bin/env python3
"""
Simple Product Data Streamer
Real-time streaming of Coinbase product ticker data
"""

import json
import time
import logging
from datetime import datetime
from coinbase.websocket import WSClient
from dotenv import dotenv_values

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load API credentials
config = dotenv_values()
API_KEY = config.get("COINBASE_API_KEY")
API_SECRET = config.get("COINBASE_API_SECRET")

if not API_KEY or not API_SECRET:
    logger.error("❌ API credentials not found in .env file")
    exit()

# Products to stream
# PRODUCTS = ["BTC-USD", "ETH-USD", "LINK-USD", "AVAX-USD"]
PRODUCTS = ["BTC-USD"]

def on_message(msg):
    """Handle incoming WebSocket messages"""
    try:
        if isinstance(msg, str):
            data = json.loads(msg)
        else:
            return
        
        # Process ticker data
        if data.get('channel') == 'ticker':
            for event in data.get('events', []):
                if event.get('type') in ['snapshot', 'update']:
                    for ticker in event.get('tickers', []):
                        if ticker.get('type') == 'ticker':
                            product_id = ticker.get('product_id')
                            best_bid = ticker.get('best_bid')
                            best_ask = ticker.get('best_ask')
                            price = ticker.get('price')
                            
                            if product_id and best_bid and best_ask:
                                spread = float(best_ask) - float(best_bid)
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                
                                print(f"{timestamp} | {product_id:8} | "
                                      f"Bid: ${float(best_bid):>8.2f} | "
                                      f"Ask: ${float(best_ask):>8.2f} | "
                                      f"Spread: ${spread:>6.4f}")
                                      
        elif data.get('channel') == 'subscriptions':
            logger.info("✅ Subscription confirmed")
            
    except Exception as e:
        logger.warning(f"⚠️ Message error: {e}")

def main():
    """Main streaming function"""
    logger.info("🚀 Starting product data stream...")
    logger.info(f"📊 Streaming: {', '.join(PRODUCTS)}")
    logger.info("="*70)
    
    # Initialize WebSocket client
    ws_client = WSClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        on_message=on_message
    )
    
    try:
        # Connect and subscribe
        logger.info("🔌 Connecting to WebSocket...")
        ws_client.open()
        time.sleep(2)
        
        logger.info("📡 Subscribing to ticker data...")
        ws_client.subscribe(product_ids=PRODUCTS, channels=["ticker"])
        time.sleep(2)
        
        logger.info("📈 Live data stream (Ctrl+C to stop):")
        print("-" * 70)
        
        # Keep streaming
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Stream stopped by user")
    except Exception as e:
        logger.error(f"💥 Error: {e}")
    finally:
        try:
            ws_client.close()
            logger.info("🔌 WebSocket connection closed")
        except:
            pass

if __name__ == "__main__":
    main()