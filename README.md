# Coinbase WebSocket Trading Bot (Refactored)

A sophisticated, real-time cryptocurrency trading bot for Coinbase Advanced that combines WebSocket market data with intelligent order placement strategies. **Fully refactored** with modular architecture, comprehensive bug fixes, and enhanced safety features.

## 🎯 Version 2.0 - Refactored Release

This is a completely refactored version with:
- ✅ **33 bugs fixed** from comprehensive code review
- ✅ **Modular architecture** - 13 files instead of 1 monolithic file
- ✅ **External configuration** - No code changes needed for portfolio adjustments
- ✅ **Enhanced safety** - Dry-run mode, health checks, graceful shutdown
- ✅ **Better testing** - Type hints, validation, structured logging
- ✅ **Improved maintainability** - Each file has single responsibility

See [MIGRATION.md](MIGRATION.md) for migration guide from v1.0.

---

## 🚀 Features

### Core Trading Features
- **Real-time WebSocket Data**: Live market data streaming with automatic reconnection
- **Post-Only Orders**: All orders use maker fees (lower costs) with intelligent limit pricing
- **Smart Price Chasing**: Automatically adjusts orders when market moves significantly
- **Portfolio Allocation**: Distribute investments across cryptocurrencies via YAML config
- **Asset-Specific Precision**: Loads precision from product specs (no more hardcoded values!)

### Safety & Reliability
- **🆕 Dry-Run Mode**: Test without placing real orders
- **🆕 Health Checks**: Pre-flight validation (API connectivity, balances, product status)
- **🆕 Graceful Shutdown**: Ctrl+C cancels pending orders and closes connections properly
- **Rate Limiting**: Built-in API call throttling
- **Error Recovery**: Robust error handling with automatic retries
- **Circuit Breakers**: Prevents infinite loops with configurable thresholds
- **Order Validation**: Validates minimums before placing orders
- **Comprehensive Logging**: Sanitized logs with auto-rotation

### New in v2.0
- **External Configuration**: Portfolio and settings in YAML files
- **Type Hints**: Full type coverage for better IDE support
- **WebSocket Reconnection**: Automatic reconnection with exponential backoff
- **Execution Summary**: Detailed trading summary after completion
- **Log Rotation**: Automatic cleanup (keeps last 30 logs by default)
- **Sensitive Data Sanitization**: API keys redacted from logs

---

## 📋 Prerequisites

- Python 3.7+ (3.10+ recommended for best type hint support)
- Active Coinbase Advanced account with API access
- Sufficient USD balance (minimum $1 per asset)

---

## 🛠️ Installation

### 1. Clone or Download

```bash
git clone <your-repo-url>
cd coinbase-buys
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies:
- `coinbase-advanced-py` - Official Coinbase SDK
- `python-dotenv` - Environment variable management
- `PyYAML` - Configuration file parsing

### 3. Set Up API Credentials

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your Coinbase API credentials:

```env
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here
```

**Get API credentials:**
1. Log into [Coinbase Advanced](https://coinbase.com/advanced-trade)
2. Go to Settings → API
3. Create new API key with **View** and **Trade** permissions
4. Copy key and secret to `.env` file

⚠️ **Important**: Never commit your `.env` file! It's already in `.gitignore`.

---

## ⚙️ Configuration

### Portfolio Configuration

Edit `config/portfolio.yaml`:

```yaml
portfolio:
  # Adjust allocations to your preference (must sum to 1.0)
  SOL-USD: 1.00     # 100% in Solana (example)

  # Or diversify:
  # BTC-USD: 0.30    # 30% Bitcoin
  # ETH-USD: 0.30    # 30% Ethereum
  # SOL-USD: 0.20    # 20% Solana
  # XRP-USD: 0.20    # 20% Ripple

total_investment: 333.00
```

**Benefits of YAML configuration:**
- ✅ No code changes needed
- ✅ Easy to maintain multiple portfolios
- ✅ Automatic validation on load
- ✅ Comments preserved

### Trading Settings

Edit `config/config.yaml`:

```yaml
trading:
  max_chase_time: 300           # Max seconds to chase price
  max_chase_attempts: 8         # Max order adjustment attempts
  min_api_interval: 0.5         # Rate limiting (seconds)
  min_order_wait_time: 2.0      # Wait before checking order status
  min_chase_wait_time: 5.0      # Wait before price chasing
  chase_threshold_multiplier: 10 # Price movement to trigger chase

circuit_breakers:
  max_post_only_failures: 10    # Stop after N post-only failures
  max_precision_failures: 3     # Stop after N precision errors

websocket:
  connection_timeout: 15        # WebSocket connection timeout
  data_freshness_timeout: 5     # Max age of WebSocket data (seconds)
  enable_reconnection: true     # Auto-reconnect on disconnect
  max_reconnection_attempts: 5  # Max reconnection tries
  reconnection_delay: 3         # Initial reconnection delay
  reconnection_backoff_multiplier: 2  # Exponential backoff

logging:
  level: INFO                   # DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_directory: logs           # Log file location
  console_output: true          # Print to console
  max_log_files: 30            # Keep last N log files (0 = unlimited)

safety:
  dry_run: false               # 🧪 Set true to test without real orders!
  validate_allocation: true     # Validate portfolio sums to 1.0
  allocation_tolerance: 0.01    # Tolerance for allocation (1%)
  enable_health_checks: true    # Run pre-flight checks
```

---

## 🏃 Usage

### Basic Usage

```bash
python main.py
```

That's it! The bot will:
1. Load configuration from YAML files
2. Validate API credentials and portfolio
3. Run health checks (optional)
4. Start WebSocket connection
5. Execute trades according to portfolio
6. Print execution summary

### Dry-Run Mode (Recommended First)

Test without placing real orders:

1. Edit `config/config.yaml`:
   ```yaml
   safety:
     dry_run: true  # ← Enable this
   ```

2. Run:
   ```bash
   python main.py
   ```

3. Review logs to see what would happen
4. Disable `dry_run` when ready

### Example Output

```
🚀 COINBASE TRADING BOT - REFACTORED VERSION
============================================================
PORTFOLIO ALLOCATION
============================================================
SOL-USD: $333.00 (100.0%)
============================================================
TOTAL INVESTMENT: $333.00
============================================================

✅ REST client initialized
🏥 Performing health checks...
✅ API connectivity check passed
✅ USD balance check passed ($500.00 available)
✅ All 1 products are online
✅ All health checks passed

📏 Loading product specifications...
✅ Loaded specs for 11 products

📡 Initializing market data provider...
🔌 WebSocket thread started
⏳ Waiting for WebSocket market data...
✅ WebSocket ready! Got data for: ['SOL-USD']

🏁 Starting trade execution: 1 products
============================================================

[1/1] Processing SOL-USD...

⚡ Trading SOL-USD ($333.00)
📏 SOL-USD: price=2dp (inc: 0.01), size=8dp (inc: 0.00000001)
    ⚡ INITIAL #1: Bid=$175.65 | Ask=$175.66 | Limit=$175.65 (tight-spread)
    ✅ Order placed successfully
    ✅ Order filled! Size: 1.89531139
    ⚡ SOL-USD completed in 3.2s!

============================================================
EXECUTION SUMMARY
============================================================
Total trades: 1
✅ Successful: 1
❌ Failed: 0
⏱️ Total time: 5.8s
📊 Average time per successful trade: 5.8s

Detailed results:
  ✅ SOL-USD: $333.00 in 5.8s (1 attempts)
     Filled: 1.89531139 units
============================================================
💰 All orders used post-only (maker fees)
```

---

## 📁 Project Structure

```
coinbase-buys/
├── main.py                      # Entry point - run this!
│
├── config/                      # Configuration files
│   ├── portfolio.yaml          # Portfolio allocation (EDIT THIS)
│   └── config.yaml             # Trading settings (EDIT THIS)
│
├── core/                        # Core trading logic
│   ├── precision.py            # Precision detection & management
│   ├── market_data.py          # WebSocket & REST market data
│   └── order_manager.py        # Order placement & tracking
│
├── strategies/                  # Pricing strategies
│   └── limit_price.py          # Limit price calculation
│
├── utils/                       # Utility modules
│   ├── logging.py              # Logging setup & sanitization
│   └── validators.py           # Input validation functions
│
├── models/                      # Type definitions
│   └── types.py                # TypedDicts and dataclasses
│
├── coinbase_product_specs.json # Product specifications
├── .env                        # API credentials (CREATE THIS)
├── .env.example               # API credentials template
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── MIGRATION.md              # Migration guide from v1.0
└── logs/                     # Log files (auto-created)
```

### What to Edit

**Frequently:**
- `config/portfolio.yaml` - Your investment allocation
- `config/config.yaml` - Trading behavior

**Rarely:**
- `.env` - Only when rotating API keys
- `coinbase_product_specs.json` - Only if Coinbase changes specs

**Never:**
- Files in `core/`, `utils/`, `models/`, `strategies/` - Core logic

---

## 🧪 Testing

### 1. Dry-Run Mode

Test without real orders:

```yaml
# config/config.yaml
safety:
  dry_run: true
```

```bash
python main.py
```

### 2. Small Amounts

Test with real orders using small amounts:

```yaml
# config/portfolio.yaml
total_investment: 10.00  # Just $10
```

### 3. Review Logs

```bash
# Watch live logs
tail -f logs/trading_bot_*.log

# Or view latest log
ls -t logs/ | head -1 | xargs -I {} cat logs/{}
```

---

## 🐛 Bug Fixes in v2.0

All bugs from comprehensive code review fixed:

### Critical Bugs Fixed
1. ✅ Precision calculation crash on zero decimals
2. ✅ WebSocket thread never terminates properly
3. ✅ Chase count logic error (counted initial order)
4. ✅ Race condition in order fill detection
5. ✅ Empty .env causes immediate crash

### Logic Errors Fixed
6. ✅ Post-only price adjustment insufficient
7. ✅ Order size validation never called
8. ✅ Final fill checks too quick
9. ✅ Insufficient funds not tracked
10. ✅ Portfolio allocation not validated

### Security Issues Fixed
11. ✅ API errors leak sensitive data
12. ✅ No input validation for configuration
13. ✅ Environment variables not validated

### Code Quality Improvements
14. ✅ Duplicate data (product specs)
15. ✅ Magic numbers replaced with config
16. ✅ Inconsistent error handling standardized
17. ✅ Type hints added throughout
18. ✅ Broad exception handling narrowed
19. ✅ WebSocket reconnection logic added
20. ✅ Logger configuration fixed
21. ✅ Decimal context configured
22. ✅ Log directory rotation added
23. ✅ Dry-run mode added
24. ✅ Graceful shutdown implemented

Plus 9 major improvements! See code review in original issue for details.

---

## 🔒 Security

### Best Practices
- ✅ Never commit `.env` file (already in `.gitignore`)
- ✅ API keys sanitized from logs automatically
- ✅ Use API keys with minimal permissions (View + Trade only)
- ✅ Rotate API keys periodically
- ✅ Keep only necessary USD in trading account
- ✅ Enable IP whitelisting on Coinbase if possible

### Sensitive Data Handling
The bot automatically sanitizes logs:
- API keys → `***REDACTED***`
- API secrets → `***REDACTED***`
- Error messages checked for sensitive patterns

---

## 📊 Supported Cryptocurrencies

The bot includes precision settings for:

| Crypto | Pair | Size Precision | Price Precision |
|--------|------|----------------|-----------------|
| Bitcoin | BTC-USD | 8 decimals | 2 decimals |
| Ethereum | ETH-USD | 8 decimals | 2 decimals |
| Solana | SOL-USD | 8 decimals | 2 decimals |
| Ripple | XRP-USD | 6 decimals | 4 decimals |
| Chainlink | LINK-USD | 2 decimals | 3 decimals |
| Avalanche | AVAX-USD | 8 decimals | 2 decimals |
| Uniswap | UNI-USD | 6 decimals | 3 decimals |
| Quant | QNT-USD | 3 decimals | 2 decimals |
| Polkadot | DOT-USD | 8 decimals | 3 decimals |
| Cardano | ADA-USD | 8 decimals | 4 decimals |
| Dogecoin | DOGE-USD | 1 decimal | 5 decimals |

**Add new cryptocurrencies:**
1. Add entry to `coinbase_product_specs.json`
2. Add to portfolio in `config/portfolio.yaml`
3. Run - precision auto-detected!

---

## ⚠️ Important Notes

### Risk Management
- Start with **dry-run mode** (`dry_run: true`)
- Test with **small amounts** ($10-20) first
- Monitor the first few runs closely
- Understand that crypto trading involves risk
- Only invest what you can afford to lose

### Minimum Requirements
- **Per asset**: $1 USD minimum (Coinbase requirement)
- **Total recommended**: $50+ for meaningful diversification
- **BTC/ETH**: Consider larger allocations due to high prices

### Market Conditions
- Works best in **liquid markets** with tight spreads
- May struggle in **extremely volatile** conditions
- Price chasing is **limited** to prevent over-trading
- WebSocket provides **real-time** data for optimal timing

### API Limits
- Built-in rate limiting (0.5s between calls)
- Efficient WebSocket usage minimizes API calls
- Handles temporary API errors gracefully

---

## 🔧 Troubleshooting

### Configuration Errors

**"Portfolio config not found"**
```bash
# Make sure config files exist
ls config/
# Should show: portfolio.yaml config.yaml
```

**"API credentials validation failed"**
```bash
# Check .env file
cat .env
# Should have both: COINBASE_API_KEY and COINBASE_API_SECRET
```

**"Portfolio allocation sums to X, expected 1.0"**
```yaml
# In portfolio.yaml, ensure allocations sum to 1.0:
portfolio:
  BTC-USD: 0.50  # 50%
  ETH-USD: 0.50  # 50%
  # Total: 1.00 ✅
```

### Runtime Errors

**"Insufficient USD balance"**
- Check your Coinbase account has enough USD
- Reduce `total_investment` in `portfolio.yaml`

**"WebSocket timeout"**
- Check internet connection
- Bot will fall back to REST API automatically

**"Order validation failed"**
- Amount too small for asset (increase `total_investment`)
- Check logs for specific validation errors

### Getting Help

1. Enable debug logging:
   ```yaml
   # config/config.yaml
   logging:
     level: DEBUG
   ```

2. Check latest log:
   ```bash
   ls -t logs/ | head -1
   ```

3. Review the detailed logs for error messages

---

## 📈 Performance Tips

1. **Optimal Investment**: $100-500 total for good diversification
2. **Timing**: Run during high liquidity hours (US market hours)
3. **Portfolio**: Avoid too many small allocations (under $5 each)
4. **Network**: Stable, fast internet improves WebSocket performance
5. **Monitoring**: Check logs for first few runs

---

## 🤝 Contributing

Contributions welcome! When contributing:
- Maintain existing code style
- Add type hints to new code
- Update configuration schema if needed
- Test with dry-run mode first
- Update documentation

---

## 📄 License

This project is for educational and personal use. Use at your own risk.

---

## 📝 Changelog

### v2.0.0 (Current) - Refactored Release
- Complete refactor into modular architecture
- 33 bugs fixed from code review
- External YAML configuration
- Dry-run mode
- Health checks
- Graceful shutdown
- WebSocket reconnection
- Type hints throughout
- Log rotation
- Sensitive data sanitization
- Execution summary

### v1.0.0 - Original Release
- Single-file monolithic design
- Hardcoded configuration
- Basic trading functionality
- WebSocket market data
- Post-only orders

---

## 📚 Additional Documentation

- [MIGRATION.md](MIGRATION.md) - Migration guide from v1.0
- [Code Review Report](CODE_REVIEW.md) - Full bug analysis (if available)

---

## 💡 Quick Start Checklist

- [ ] Install Python 3.7+
- [ ] Run `pip install -r requirements.txt`
- [ ] Create `.env` with API credentials
- [ ] Edit `config/portfolio.yaml` with your allocation
- [ ] Review `config/config.yaml` settings
- [ ] Set `dry_run: true` in `config/config.yaml`
- [ ] Run `python main.py` (dry-run test)
- [ ] Review logs in `logs/` directory
- [ ] Set `dry_run: false` when ready
- [ ] Run `python main.py` (real trading)

---

**Ready to trade? Start with dry-run mode and small amounts!**

```bash
python main.py
```
