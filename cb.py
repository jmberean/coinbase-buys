import uuid
import os
import time
from coinbase.rest import RESTClient # type: ignore
from dotenv import dotenv_values # type: ignore

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

AMOUNT_TO_BUY = 88.8  # Default amount to buy in USD if not specified
# Cryptocurrencies you want to buy and the USD amount for each
CRYPTOS_TO_BUY = {
    "BTC-USD": AMOUNT_TO_BUY,  # Buy $10 worth of Bitcoin
    "ETH-USD": AMOUNT_TO_BUY,  # Buy $10 worth of Ethereum
    "SOL-USD": AMOUNT_TO_BUY,   # Buy $5 worth of Solana
    "XRP-USD": AMOUNT_TO_BUY,   # Buy $7.5 worth of Cardano
    "UNI-USD": AMOUNT_TO_BUY, # Buy $10 worth of Dogecoin
    "AVAX-USD": AMOUNT_TO_BUY,
    "ADA-USD": AMOUNT_TO_BUY,
    "DOT-USD": AMOUNT_TO_BUY,
    "LINK-USD": AMOUNT_TO_BUY,
    "DOGE-USD": AMOUNT_TO_BUY,
}

# --- Initialize Coinbase API Client ---
try:
    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
    print("Coinbase RESTClient initialized successfully using .env credentials.")
except Exception as e:
    print(f"Error initializing Coinbase RESTClient: {e}")
    exit()

def execute_market_buy_order(product_id: str, quote_size: float):
    """
    Executes a market buy order for a given cryptocurrency.

    Args:
        product_id (str): The trading pair (e.g., 'BTC-USD').
        quote_size (float): The amount of quote currency (e.g., USD) to spend.
    """
    client_order_id = str(uuid.uuid4())

    print(f"\nAttempting to place market buy order for {quote_size} USD of {product_id}...")
    try:
        order_response = client.market_order_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            quote_size=str(quote_size)
        )

        # Access attributes of the response object
        if hasattr(order_response, 'success') and order_response.success:
            order_details = order_response.success_response
            # Print only essential success message
            if isinstance(order_details, dict):
                print(f"SUCCESS: Order placed for {product_id}. Order ID: {order_details.get('order_id', 'N/A')}")
            else:
                print(f"SUCCESS: Order placed for {product_id}. Order ID: {order_details.order_id if hasattr(order_details, 'order_id') else 'N/A'}")
        elif hasattr(order_response, 'error_response'):
            error_details = order_response.error_response
            # Print only essential error message
            if isinstance(error_details, dict):
                print(f"FAILED: Order for {product_id}. Error: {error_details.get('error_message', 'Unknown error')}")
            else:
                print(f"FAILED: Order for {product_id}. Error: {error_details.error_message if hasattr(error_details, 'error_message') else 'Unknown error'}")
        else:
            print(f"Unexpected response structure for {product_id}. Response: {order_response}")

    except Exception as e:
        print(f"An unexpected error occurred while placing order for {product_id}: {e}")


# --- Execute orders for each crypto ---
if client:
    for crypto, amount in CRYPTOS_TO_BUY.items():
        execute_market_buy_order(crypto, amount)
        time.sleep(5)  # Add a 5-second delay between buys
else:
    print("Cannot proceed with orders due to API client initialization failure.")