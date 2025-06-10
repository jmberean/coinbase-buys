# Coinbase WebSocket Trading Bot

A sophisticated, real-time cryptocurrency trading bot for Coinbase Advanced that combines WebSocket market data with intelligent order placement strategies. Designed for precision, efficiency, and minimal fees through post-only limit orders.

## 🚀 Features

### Core Trading Features
- **Real-time WebSocket Data**: Live market data streaming for instant price updates
- **Post-Only Orders**: All orders use maker fees (lower costs) with intelligent limit pricing
- **Smart Price Chasing**: Automatically adjusts orders when market moves significantly
- **Portfolio Allocation**: Distribute investments across multiple cryptocurrencies with custom percentages
- **Intelligent Precision Detection**: Automatically learns market and order precision requirements

### Safety & Reliability
- **Rate Limiting**: Built-in API call throttling to respect Coinbase limits
- **Error Recovery**: Robust error handling with automatic retries and precision learning
- **Circuit Breakers**: Prevents infinite loops with configurable failure thresholds
- **Comprehensive Logging**: Detailed logs with timestamps for audit and debugging
- **Graceful Cleanup**: Automatically cancels unfilled orders on timeout or exit

## 📋 Prerequisites

- Python 3.7+
- Active Coinbase Advanced account with API access
- Sufficient USD balance for your intended trades

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
   - Create new API key with trading permissions
   - Copy the key and secret to your `.env` file

## ⚙️ Configuration

Edit the configuration section in `coinbase-buys.py`:

### Portfolio Settings
```python
# Total amount to invest (USD)
TOTAL_INVESTMENT = 2.00

# Portfolio allocation (must sum to 1.0)
PORTFOLIO_ALLOCATION = {
    "LINK-USD": 0.50,  # 50% allocation to Chainlink
    "AVAX-USD": 0.50,  # 50% allocation to Avalanche
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

## 🏃‍♂️ Usage

1. **Configure your portfolio** in the script
2. **Ensure sufficient USD balance** in your Coinbase account
3. **Run the bot**:
   ```bash
   python3 coinbase-buys.py
   ```

### Example Output
```
🚀 DYNAMIC PORTFOLIO TRADING BOT
==================================================
LINK-USD: $1.00 (50.0%)
AVAX-USD: $1.00 (50.0%)
==================================================
✅ REST client initialized
🔌 Connecting to WebSocket...
📡 Subscribing to ticker for ['LINK-USD', 'AVAX-USD']...
✅ WebSocket ready! Got data for: ['LINK-USD', 'AVAX-USD']

[1/2] Processing LINK-USD...
⚡ Trading LINK-USD ($1.00)
📏 LINK-USD: market=6dp, order=6dp (inc: 0.000001)
⚡ INITIAL: Bid=$11.234500 | Ask=$11.234600 | Limit=$11.234550 (mid-spread)
✅ Order placed successfully
✅ Order filled! Size: 0.088542

[2/2] Processing AVAX-USD...
⚡ Trading AVAX-USD ($1.00)
📏 AVAX-USD: market=4dp, order=4dp (inc: 0.0001)
⚡ INITIAL: Bid=$23.4500 | Ask=$23.4600 | Limit=$23.4550 (mid-spread)
✅ Order placed successfully
✅ Order filled! Size: 0.0426

🏁 Execution complete in 8.3s!
✅ Successful: 2/2
💰 All orders used post-only (maker fees)
```

## 🧠 How It Works

### 1. Market Data Collection
- Connects to Coinbase WebSocket for real-time ticker data
- Falls back to REST API if WebSocket data is stale
- Maintains fresh bid/ask prices for optimal order placement

### 2. Precision Detection
- Automatically analyzes market data to determine decimal precision
- Learns correct order precision through API error feedback
- Separates market precision (for analysis) from order precision (for placement)

### 3. Smart Order Placement
The bot calculates optimal limit prices based on current spread:
- **Zero spread**: Places below both bid/ask
- **Tight spread**: Small buffer below ask
- **Medium spread**: Between bid and ask
- **Wide spread**: Larger buffer below ask

### 4. Price Chasing
- Monitors market movement in real-time
- Cancels and replaces orders when price moves significantly
- Uses market precision to detect meaningful price changes
- Limits chasing attempts to prevent excessive trading

### 5. Order Management
- All orders are post-only (guaranteed maker fees)
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
- Market data updates
- Order placement and fills
- Error messages and recovery attempts
- Performance metrics

Log files are named with timestamps: `trading_bot_20241209_143022.log`

## ⚠️ Important Notes

### Risk Management
- **Start small**: Test with small amounts first
- **Monitor actively**: Watch the first few runs closely
- **Check balances**: Ensure sufficient USD before running
- **Understand fees**: Post-only orders get maker fees (typically lower)

### Market Conditions
- Works best in liquid markets with tight spreads
- May struggle in extremely volatile conditions
- Price chasing is limited to prevent excessive adjustments

### API Limits
- Respects Coinbase rate limits with built-in throttling
- Uses efficient WebSocket data to minimize API calls
- Automatically handles temporary API errors

## 🔧 Troubleshooting

### Common Issues

**WebSocket connection fails**
- Check internet connection
- Verify API credentials have proper permissions
- Bot will fall back to REST API automatically

**Orders keep getting rejected**
- Insufficient balance in USD wallet
- Check if trading is enabled for your account
- Verify API key has trading permissions

**Precision errors**
- Bot automatically learns correct precision
- If persistent, check Coinbase documentation for product specifications

**Post-only failures**
- Market is moving too fast for post-only orders
- Bot will retry with adjusted pricing
- Consider increasing MAX_POST_ONLY_FAILURES for volatile markets

### Debug Mode
Enable debug logging by changing the log level:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## 📈 Performance Tips

1. **Optimal Timing**: Run during high liquidity hours
2. **Portfolio Size**: Smaller allocations may face minimum size restrictions
3. **Network**: Stable, fast internet improves WebSocket performance
4. **Monitoring**: Watch first few runs to understand behavior

## 🔒 Security

- Never commit your `.env` file to version control
- Keep API keys secure and rotate them periodically
- Use API keys with minimal required permissions
- Consider IP whitelisting in Coinbase settings

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
- Test changes thoroughly
- Maintain the existing code style
- Add appropriate logging for new features
- Update documentation as needed

## 📜 License

This project is open source. Use at your own risk and responsibility.