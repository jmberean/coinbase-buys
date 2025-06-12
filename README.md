# Coinbase WebSocket Trading Bot

A sophisticated, real-time cryptocurrency trading bot for Coinbase Advanced that combines WebSocket market data with intelligent order placement strategies. Designed for precision, efficiency, and minimal fees through post-only limit orders.

## 🚀 Features

### Core Trading Features
- **Real-time WebSocket Data**: Live market data streaming for instant price updates
- **Post-Only Orders**: All orders use maker fees (lower costs) with intelligent limit pricing
- **Smart Price Chasing**: Automatically adjusts orders when market moves significantly
- **Portfolio Allocation**: Distribute investments across multiple cryptocurrencies with custom percentages
- **Asset-Specific Precision**: Uses correct decimal precision for each cryptocurrency (BTC: 8 decimals, LINK: 2 decimals, etc.)

### Safety & Reliability
- **Rate Limiting**: Built-in API call throttling to respect Coinbase limits
- **Error Recovery**: Robust error handling with automatic retries and precision learning
- **Circuit Breakers**: Prevents infinite loops with configurable failure thresholds
- **Minimum Order Validation**: Prevents orders that are too small for each asset
- **Comprehensive Logging**: Detailed logs with timestamps for audit and debugging
- **Graceful Cleanup**: Automatically cancels unfilled orders on timeout or exit

## 📋 Prerequisites

- Python 3.7+
- Active Coinbase Advanced account with API access
- Sufficient USD balance for your intended trades (minimum $1 per asset due to Coinbase requirements)

## 🛠️ Installation

1. **Clone or download the script**
   ```bash
   # Save the script as coinbase-buys.py
   ```

2. **Install required packages**
   ```bash
   pip install coinbase-advanced-py python-dotenv
   ```

3. **Set up API credentials**
   
   Create a `.env` file in the same directory:
   ```env
   COINBASE_API_KEY=your_api_key_here
   COINBASE_API_SECRET=your_api_secret_here
   ```

4. **Get Coinbase API credentials**
   - Log into [Coinbase Advanced](https://coinbase.com/advanced-trade)
   - Go to Settings → API
   - Create new API key with **trading permissions**
   - Copy the key and secret to your `.env` file

## ⚙️ Configuration

Edit the configuration section in `coinbase-buys.py`:

### Portfolio Settings
```python
# Total amount to invest (USD)
TOTAL_INVESTMENT = 100.00

# Portfolio allocation (must sum to 1.0)
PORTFOLIO_ALLOCATION = {
    # Core Foundation (20%)
    "BTC-USD": 0.10,   # 10% - Store of value anchor
    "ETH-USD": 0.10,   # 10% - Smart contract foundation
    
    # Established Growth Plays (60%) 
    "SOL-USD": 0.15,   # 15% - Consumer blockchain leader
    "XRP-USD": 0.15,   # 15% - Enterprise payments
    "LINK-USD": 0.15,  # 15% - Oracle infrastructure
    "AVAX-USD": 0.15,  # 15% - Institutional tokenization
    
    # Speculative Upside (20%)
    "UNI-USD": 0.04,   # 4% - DeFi protocol
    "QNT-USD": 0.04,   # 4% - Enterprise interoperability
    "DOT-USD": 0.04,   # 4% - Parachain innovation
    "ADA-USD": 0.04,   # 4% - Academic development
    "DOGE-USD": 0.04,  # 4% - Community-driven payments
}
```

### Trading Parameters
```python
MAX_CHASE_TIME = 300              # Max time to chase price (seconds)
MAX_CHASE_ATTEMPTS = 12           # Max number of order adjustments
MIN_API_INTERVAL = 0.5           # Rate limiting between API calls
MAX_POST_ONLY_FAILURES = 15      # Circuit breaker for post-only errors
MAX_PRECISION_FAILURES = 3       # Circuit breaker for precision errors
```

### Minimum Investment Requirements
Due to Coinbase's minimum order sizes, consider these guidelines:
- **Minimum per asset**: $1 (Coinbase requirement)
- **Recommended total**: $200+ for expensive assets like BTC/ETH
- **BTC/ETH**: Consider larger allocations due to high prices and 8-decimal precision

## 🏃‍♂️ Usage

1. **Configure your portfolio** in the script
2. **Ensure sufficient USD balance** in your Coinbase account
3. **Run the bot**:
   ```bash
   python coinbase-buys.py
   ```

### Example Output
```
🚀 DYNAMIC PORTFOLIO TRADING BOT
==================================================
BTC-USD: $10.00 (10.0%)
ETH-USD: $10.00 (10.0%)
SOL-USD: $15.00 (15.0%)
LINK-USD: $15.00 (15.0%)
==================================================
✅ REST client initialized
🔌 Connecting to WebSocket...
📡 Subscribing to ticker for ['BTC-USD', 'ETH-USD', 'SOL-USD', 'LINK-USD']...
✅ WebSocket ready! Got data for: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'LINK-USD']

[1/4] Processing BTC-USD...
⚡ Trading BTC-USD ($10.00)
📏 BTC-USD: price=2dp, size=8dp (inc: 0.00000001)
⚡ INITIAL: Bid=$108000.00 | Ask=$108000.01 | Limit=$108000.00 (tight-spread)
✅ Order placed successfully
✅ Order filled! Size: 0.00009259

[2/4] Processing ETH-USD...
⚡ Trading ETH-USD ($10.00)
📏 ETH-USD: price=2dp, size=8dp (inc: 0.00000001)
⚡ INITIAL: Bid=$2750.00 | Ask=$2750.01 | Limit=$2750.00 (tight-spread)
✅ Order placed successfully
✅ Order filled! Size: 0.00363636

🏁 Execution complete in 12.5s!
✅ Successful: 4/4
💰 All orders used post-only (maker fees)
```

## 🧠 How It Works

### 1. Market Data Collection
- Connects to Coinbase WebSocket for real-time ticker data
- Falls back to REST API if WebSocket data is stale
- Maintains fresh bid/ask prices for optimal order placement

### 2. Asset-Specific Precision Detection
The bot uses **hardcoded precision values** based on Coinbase's actual requirements:

```python
# Size precision for each cryptocurrency
'BTC-USD': 8,  # 0.00000001 BTC - High precision for expensive assets
'ETH-USD': 8,  # 0.00000001 ETH
'SOL-USD': 8,  # 0.00000001 SOL
'XRP-USD': 6,  # 0.000001 XRP
'LINK-USD': 2, # 0.01 LINK - Lower precision for mid-price assets
'AVAX-USD': 8, # 0.00000001 AVAX
'UNI-USD': 6,  # 0.000001 UNI
'QNT-USD': 3,  # 0.001 QNT
'DOT-USD': 8,  # 0.00000001 DOT
'ADA-USD': 8,  # 0.00000001 ADA
'DOGE-USD': 1, # 0.1 DOGE - Lowest precision for low-price assets
```

This prevents the common "Size too small" error that occurs when using incorrect decimal precision.

### 3. Smart Order Placement
The bot calculates optimal limit prices based on current spread:
- **Zero spread**: Places below both bid/ask
- **Tight spread**: Small buffer below ask
- **Medium spread**: Between bid and ask
- **Wide spread**: Larger buffer below ask

### 4. Price Chasing
- Monitors market movement in real-time
- Cancels and replaces orders when price moves significantly (2x market increment)
- Uses market precision to detect meaningful price changes
- Limits chasing attempts to prevent excessive trading

### 5. Order Management
- All orders are post-only (guaranteed maker fees)
- Automatic validation against minimum order sizes
- Automatic status checking and cleanup
- Graceful handling of partial fills and errors

## 📁 File Structure

```
├── coinbase-buys.py      # Main trading bot script
├── .env                  # API credentials (create this)
├── .env.example         # Example credentials file
└── logs/                # Auto-created log directory
    └── trading_bot_YYYYMMDD_HHMMSS.log
```

## 📊 Logging

The bot creates detailed logs in the `logs/` directory with:
- Timestamped trading actions
- Market data updates with precision info
- Order placement and fills
- Precision detection for each asset
- Error messages and recovery attempts
- Performance metrics

Log files are named with timestamps: `trading_bot_20241209_143022.log`

## ⚠️ Important Notes

### Risk Management
- **Start small**: Test with small amounts first ($20-50 total)
- **Monitor actively**: Watch the first few runs closely
- **Check balances**: Ensure sufficient USD before running
- **Understand fees**: Post-only orders get maker fees (typically 0.5% vs 0.6% taker)

### Minimum Order Requirements
Each cryptocurrency has different minimum order sizes:
- **Quote minimum**: $1 USD for all assets
- **Base minimums**: Vary by asset (e.g., 0.00000001 BTC, 0.01 LINK, 0.1 DOGE)
- **Precision requirements**: Critical for order success (BTC needs 8 decimals, LINK needs 2)

### Market Conditions
- Works best in liquid markets with tight spreads
- May struggle in extremely volatile conditions
- Price chasing is limited to prevent excessive adjustments
- WebSocket provides real-time data for optimal timing

### API Limits
- Respects Coinbase rate limits with built-in throttling (0.5s between calls)
- Uses efficient WebSocket data to minimize API calls
- Automatically handles temporary API errors

## 🔧 Troubleshooting

### Common Issues

**"Size too small" errors**
- ✅ **Fixed in latest version**: Bot now uses correct precision for each asset
- Ensure investment amounts meet minimum requirements ($1+ per asset)
- For expensive assets (BTC/ETH), consider higher total investment

**WebSocket connection fails**
- Check internet connection and firewall settings
- Verify API credentials have proper permissions
- Bot will fall back to REST API automatically

**Orders keep getting rejected**
- Insufficient balance in USD wallet
- Check if trading is enabled for your account
- Verify API key has trading permissions (not just view)

**Precision errors (legacy)**
- ✅ **Fixed**: Bot now uses hardcoded correct precision values
- No more learning required - precision is asset-specific

**Post-only failures**
- Market is moving too fast for post-only orders
- Bot will retry with adjusted pricing strategy
- Consider increasing MAX_POST_ONLY_FAILURES for volatile markets

### Debug Mode
Enable debug logging by changing the log level:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## 📈 Performance Tips

1. **Optimal Investment Size**: $100-500 total for good asset diversity
2. **Timing**: Run during high liquidity hours (US market hours)
3. **Portfolio Balance**: Avoid too many small allocations (under $5)
4. **Network**: Stable, fast internet improves WebSocket performance
5. **Monitoring**: Check logs for first few runs to understand behavior

## 🔒 Security

- Never commit your `.env` file to version control
- Keep API keys secure and rotate them periodically
- Use API keys with minimal required permissions (trading only)
- Consider IP whitelisting in Coinbase settings
- Store only necessary USD amounts in your trading account

## 📊 Supported Cryptocurrencies

The bot includes precision settings for these assets:
- **Bitcoin (BTC)** - 8 decimal precision
- **Ethereum (ETH)** - 8 decimal precision  
- **Solana (SOL)** - 8 decimal precision
- **Ripple (XRP)** - 6 decimal precision
- **Chainlink (LINK)** - 2 decimal precision
- **Avalanche (AVAX)** - 8 decimal precision
- **Uniswap (UNI)** - 6 decimal precision
- **Quant (QNT)** - 3 decimal precision
- **Polkadot (DOT)** - 8 decimal precision
- **Cardano (ADA)** - 8 decimal precision
- **Dogecoin (DOGE)** - 1 decimal precision

To add new cryptocurrencies, update the `size_precision_overrides` dictionary in the `PrecisionDetector` class.

## 📄 Disclaimer

This software is for educational and personal use only. Cryptocurrency trading involves substantial risk of loss. Always:
- Understand the risks before trading
- Never invest more than you can afford to lose
- Test thoroughly with small amounts
- Monitor your trades actively
- Comply with all applicable laws and regulations

The authors are not responsible for any financial losses incurred through the use of this software.

## 🤝 Contributing

Feel free to submit issues, feature requests, or improvements. When contributing:
- Test changes thoroughly with small amounts
- Maintain the existing code style
- Add appropriate logging for new features
- Update precision settings for new cryptocurrencies
- Update documentation as needed

## 📜 License

This project is open source. Use at your own risk and responsibility.

---

## 🔍 Recent Improvements

### v2.0 - Precision Fix Update
- ✅ **Fixed "Size too small" errors**: Asset-specific precision detection
- ✅ **Hardcoded precision values**: No more learning required
- ✅ **Minimum order validation**: Prevents failed orders
- ✅ **Better logging**: Shows price vs size precision separately
- ✅ **11 cryptocurrency support**: Tested and validated precision values

### Key Technical Changes
- `PrecisionDetector` now uses `size_precision_overrides` dictionary
- Separate handling of price precision (for display) vs size precision (for orders)
- Built-in minimum order size validation
- Enhanced error messages and debugging information