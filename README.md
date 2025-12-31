# 🚀 Crypto Trading Analysis System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-purple.svg)

**Automated cryptocurrency trading analysis system with AI-powered trading plan generation.**
Real-time data from Binance & Bybit + DeepSeek AI analysis = Professional trading plans.

## ✨ Features

### 📊 **Data Collection**

- ✅ Real-time OHLCV data from **Binance & Bybit**
- ✅ Historical data collection with smart caching
- ✅ Multi-timeframe support (1m to 1W)
- ✅ Automatic rate limiting and error handling

### 🧠 **AI Analysis**

- ✅ **DeepSeek AI** integration for market analysis
- ✅ Complete **trading plan generation** with:
  - 🎯 **Multiple Entry Points** (Entry 1, 2, 3 with weights)
  - ✅ **Take Profit Targets** (TP1, TP2, TP3 with R/R ratios)
  - 🛑 **Stop Loss** with clear reasoning
  - 📊 **Risk Management** (position sizing, risk per trade)
  - 📈 **Support & Resistance** levels
- ✅ Portfolio analysis and risk assessment

### ⏰ **Automation**

- ✅ **Scheduler** for automatic plan generation
- ✅ Daily, intraday, and weekly analysis
- ✅ Auto-save to JSON & CSV formats
- ✅ Alert system (Slack/Telegram ready)

### 🤖 **Telegram Bot Integration**

- ✅ **Multi-user support** dengan SQLite database
- ✅ **15+ commands** lengkap untuk trading
- ✅ **Real-time price updates** via WebSocket
- ✅ **Price alerts** - notifications saat price reach target
- ✅ **Coin subscriptions** - monitor favorit coins
- ✅ **AI trading plans** langsung dari Telegram
- ✅ **Quick analysis** dengan technical indicators
- ✅ **Trending coins** - top movers 24h

### 📁 **Organization**

- ✅ **Auto-generated folder structure**
- ✅ Smart caching system
- ✅ Comprehensive logging
- ✅ Configurable via JSON and .env files

## 🚀 Quick Start

### **1. Prerequisites**

```bash
# Python 3.8 or higher
python --version

# Git
git --version
```


### **2. Clone & Setup**

```
# Clone repository
git clone <your-repository-url>
cd crypto_trading_system

# Run automatic setup
python init_system.py
```

### **3. Configure API Keys**

**bash**

```
# Copy environment template
cp .env.template .env

# Edit .env with your API keys
# Use your favorite text editor:
nano .env
# or
vim .env
# or open in VS Code:
code .env
```

#### **Required API Keys:**

**env**

```
# Get from: https://www.binance.com/en/my/settings/api-management
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_here

# Get from: https://www.bybit.com/app/user/api-management
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_SECRET_KEY=your_bybit_secret_here

# Get from: https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### **4. Install Dependencies**

**bash**

```
# Install all requirements
pip install -r requirements.txt

# Or if you prefer pipenv:
pipenv install
```

### **5. Test the System**

**bash**

```
# Test 1: Data Collection
python collector.py

# Test 2: Generate Trading Plan for BTC
python run_trading_plans.py --symbol BTCUSDT

# Test 3: Start Automatic Scheduler
python run_trading_plans.py --schedule

# Test 4: Start Telegram Bot
python run_telegram_bot.py

# Test 5: Start All Services (Recommended)
./run_all.sh
```

## 📂 Project Structure

**text**

```
crypto_trading_system/
│
├── 📄 README.md                    # This file
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.template               # Environment variables template
├── 📄 .gitignore                  # Git ignore file
│
├── 🐍 CORE MODULES
│   ├── 📄 collector.py            # Data collection (Binance & Bybit)
│   ├── 📄 deepseek_integration.py # AI trading plan generation
│   ├── 📄 streaming.py            # Real-time WebSocket data
│   ├── 📄 config.py               # System configuration
│   ├── 📄 run_trading_plans.py    # Trading plan generator
│   ├── 📄 run_integrated_system.py # Integrated streaming + scheduler
│   ├── 📄 run_telegram_bot.py     # Telegram bot runner
│   ├── 📄 run_all.sh              # Start all services
│   └── 📄 stop_all.sh             # Stop all services
│
├── 🤖 TELEGRAM BOT
│   └── 📁 tg_bot/                 # Telegram bot module
│       ├── 📄 bot.py              # Main bot class
│       ├── 📄 database.py         # SQLite database operations
│       ├── 📄 formatter.py        # Message formatting
│       └── 📁 handlers/           # Command handlers
│           ├── 📄 basic.py        # Basic commands
│           └── 📄 trading.py      # Trading commands
│
├── 📁 data/                       # AUTO-GENERATED Data storage
│   ├── 📁 binance/                # Binance data cache
│   ├── 📁 bybit/                  # Bybit data cache
│   ├── 📁 analysis/               # Analysis results
│   ├── 📁 reports/                # Generated reports
│   └── 📁 trading_plans/          # Complete trading plans
│
├── 📁 logs/                       # AUTO-GENERATED Log files
│   ├── 📁 trading_plans/          # Trading plan generation logs
│   ├── 📁 data_collection/        # Data collection logs
│   └── 📁 errors/                 # Error logs
│
├── 📁 configs/                    # AUTO-GENERATED Config files
│   └── trading_config.json        # Trading parameters
│
├── 📁 scripts/                    # Utility scripts
├── 📁 tests/                      # Test files
└── 📁 docs/                       # Documentation
```


## Usage Examples

### **1. Manual Trading Plan Generation**

**bash**

```
# Generate plan for Bitcoin
python run_trading_plans.py --symbol BTCUSDT --timeframe 4h

# Generate plan for Ethereum
python run_trading_plans.py --symbol ETHUSDT --timeframe 1h

# Generate for all major pairs
python run_trading_plans.py --all

# Generate with aggressive risk profile
python run_trading_plans.py --symbol SOLUSDT --timeframe 1h
```

### **2. Automatic Scheduler**

**bash**

```
# Start automatic scheduler
python run_trading_plans.py --schedule

# Or use the dedicated runner
python scheduler.py
```

### **3. Real-time Data Streaming**

**bash**

```
# Start WebSocket streaming (separate terminal)
python streaming.py
```

### **4. Telegram Bot**

**bash**

```
# Start Telegram Bot
python run_telegram_bot.py

# Or start all services including bot
./run_all.sh
```

#### **Telegram Bot Commands:**

**Basic Commands:**
- `/start` - Initialize bot dan register user
- `/help` - Tampilkan semua available commands
- `/status` - Cek system status

**Trading Commands:**
- `/price [symbol]` - Get current price (e.g., `/price BTCUSDT`)
- `/plan [symbol] [timeframe]` - Generate AI trading plan (e.g., `/plan BTCUSDT 4h`)
- `/analyze [symbol]` - Quick technical analysis (e.g., `/analyze ETHUSDT`)
- `/signals` - Get trading signals untuk subscriptions
- `/trending` - Show trending coins (24h)

**Subscription Commands:**
- `/subscribe [symbol]` - Subscribe ke coin (e.g., `/subscribe SOLUSDT`)
- `/unsubscribe [symbol]` - Unsubscribe dari coin
- `/mysubscriptions` - List semua subscriptions
- `/subscribeall` - Subscribe ke semua major pairs (BTC, ETH, BNB, SOL, XRP)

**Alert Commands:**
- `/setalert [symbol] [above/below] [price]` - Set price alert
  - Example: `/setalert BTCUSDT above 100000`
- `/myalerts` - List semua active alerts
- `/delalert [alert_id]` - Delete specific alert
- `/clearalerts` - Clear semua alerts

### **5. Start All Services (Recommended)**

**bash**

```
# Start all services (Integrated System + Scheduler + Telegram Bot)
./run_all.sh

# Stop all services
./stop_all.sh

# Monitor logs
tail -f logs/*.log
```

### **6. Custom Analysis**

**python**

```
# In your own Python script
from deepseek_integration import TradingPlanGenerator, AnalysisRequest

generator = TradingPlanGenerator()

request = AnalysisRequest(
    symbol="BTCUSDT",
    timeframe="4h",
    risk_profile="moderate"
)

plan = generator.generate_trading_plan(request)
generator.print_trading_plan(plan)
```


## Sample Trading Plan Output

**plaintext**

```
======================================================================
🎯 TRADING PLAN - BTCUSDT (4h)
======================================================================

📊 GENERATED: 2024-12-30 14:30:15
📈 TREND: BULLISH
🚦 SIGNAL: BUY (Confidence: 78.5%)

🎯 ENTRY POINTS:
📍 ENTRY 1: $42,150.00 (50% weight) - Retest breakout
📍 ENTRY 2: $41,800.00 (30% weight) - Support minor
📍 ENTRY 3: $41,200.00 (20% weight) - Deep retracement

🎯 TAKE PROFIT TARGETS:
✅ TP1: $43,500.00 (1:1.5 R/R) - Resistance minor
✅ TP2: $44,800.00 (1:2.5 R/R) - Fibonacci extension
✅ TP3: $46,000.00 (1:3.8 R/R) - Psychological level

🛑 STOP LOSS: $40,500.00 (Below key support)

📊 RISK MANAGEMENT:
   Position Size: 5.0%
   Risk per Trade: 2.0%
   Risk/Reward Ratio: 1:2.5
   Probability of Success: 65.0%
```

## ⏰ Automatic Schedule

The scheduler automatically runs:

| Task                      | Schedule      | Description                   |
| ------------------------- | ------------- | ----------------------------- |
| **Daily Plans**     | 00:00 UTC     | 4h timeframe for major pairs  |
| **Intraday Plans**  | Every 4 hours | 1h timeframe for BTC & ETH    |
| **Weekly Analysis** | Monday 00:00  | 1d timeframe for top 10 coins |
| **Market Open**     | 00:00 UTC     | Multi-timeframe analysis      |
| **Data Cleanup**    | 23:00 UTC     | Remove old cache files        |

## 🔧 Configuration

### **1. Environment Variables (`.env`)**

**env**

```
# API Keys (REQUIRED)
BINANCE_API_KEY=your_key_here
BYBIT_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here

# Trading Parameters
RISK_PER_TRADE=0.02
DEFAULT_TIMEFRAME=4h

# Alerts (OPTIONAL)
ENABLE_SLACK=false
ENABLE_TELEGRAM=false
SLACK_WEBHOOK_URL=your_webhook
TELEGRAM_BOT_TOKEN=your_token
```

### **2. Trading Configuration (`configs/trading_config.json`)**

**json**

```
{
  "trading": {
    "default_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    "risk_per_trade": 0.02,
    "timeframes": ["1h", "4h", "1d"]
  }
}
```

## 📈 Output Files

### **Generated Files Structure:**

**text**

```
data/trading_plans/
├── trading_plan_BTCUSDT_20241230_000000.json
├── trading_plan_BTCUSDT_20241230_000000.csv
├── trading_plan_ETHUSDT_20241230_000000.json
└── intraday_BTCUSDT_1h_20241230_120000.json

data/reports/
├── weekly_20241230.json
├── generation_20241230.json
└── performance_20241230.json
```

### **JSON Output Example:**

**json**

```
{
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "entries": [
    {"level": 42150.00, "weight": 0.5, "description": "Entry 1"},
    {"level": 41800.00, "weight": 0.3, "description": "Entry 2"}
  ],
  "take_profits": [
    {"level": 43500.00, "reward_ratio": 1.5},
    {"level": 44800.00, "reward_ratio": 2.5}
  ],
  "stop_loss": 40500.00
}
```

## 🚨 Alerts & Notifications

### **Configure Alerts:**

1. **Slack** : Set `ENABLE_SLACK=true` and add webhook URL
2. **Telegram** : Set `ENABLE_TELEGRAM=true` and add bot token
3. **Email** : Configure SMTP settings in config

### **Alert Triggers:**

* ✅ High confidence signals (>70%)
* ⚠️ Significant price movements (>5%)
* ❌ System errors or failures
* 📊 Daily summary reports

## 🐛 Troubleshooting

### **Common Issues:**

| Issue                          | Solution                                   |
| ------------------------------ | ------------------------------------------ |
| **API Key Errors**       | Verify keys in `.env`, check permissions |
| **No Data Returned**     | Check internet, exchange API status        |
| **DeepSeek API Errors**  | Verify API key, check quota                |
| **Memory Issues**        | Reduce cache size in config                |
| **Schedule Not Running** | Check system timezone (should be UTC)      |

### **Debug Mode:**

**bash**

```
# Enable debug logging
export LOG_LEVEL=DEBUG
python collector.py

# Or in Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Testing

**bash**

```
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_collector.py

# Run with coverage
python -m pytest --cov=collector tests/
```

## 📚 API Reference

### **Main Classes:**

**python**

```
# Data Collection
from collector import CryptoDataCollector
collector = CryptoDataCollector()
data = collector.get_binance_klines("BTCUSDT", "1h", 100)

# Trading Plan Generation
from deepseek_integration import TradingPlanGenerator
generator = TradingPlanGenerator()
plan = generator.generate_trading_plan(request)

# Scheduler
from scheduler import TradingScheduler
scheduler = TradingScheduler()
scheduler.setup_trading_plan_tasks()
scheduler.start()
```

### **Analysis Request:**

**python**

```
from deepseek_integration import AnalysisRequest

request = AnalysisRequest(
    symbol="BTCUSDT",
    timeframe="4h",
    data_points=200,
    risk_profile="moderate",  # conservative/moderate/aggressive
    include_multi_timeframe=True
)
```

## 🔄 Updating

**bash**

```
# Update dependencies
pip install --upgrade -r requirements.txt

# Update trading config
# Edit configs/trading_config.json

# Clear cache if needed
rm -rf data/cache/*
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** Pull Request

### **Development Setup:**

**bash**

```
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black *.py

# Linting
flake8 *.py
```

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](https://license/) file for details.

## 🙏 Acknowledgments

* **Binance** & **Bybit** for their excellent APIs
* **DeepSeek AI** for powerful language models
* All contributors and testers

## 📞 Support

### **Need Help?**

1. Check the [Issues](https://github.com/yourusername/crypto-trading-system/issues) page
2. Create a new issue with detailed description
3. Join our [Discord/Telegram] community

### **Found a Bug?**

Please report with:

* Error message
* Steps to reproduce
* Your configuration
* Log files from `logs/` directory

---

## 🎯 Quick Command Cheat Sheet

**bash**

```
# SETUP
python init_system.py                    # Initial setup
cp .env.template .env                    # Create env file
pip install -r requirements.txt          # Install dependencies

# DATA COLLECTION
python collector.py                      # Test data collection
python streaming.py                      # Real-time data

# TRADING PLANS
python run_trading_plans.py --symbol BTCUSDT    # Single plan
python run_trading_plans.py --all               # All majors
python run_trading_plans.py --schedule          # Auto scheduler

# MAINTENANCE
python init_system.py --skip-verify      # Recreate folders
rm -rf data/cache/*                      # Clear cache
```

---

**⭐ Star this repo if you find it useful!**

**Happy Trading! 🚀📈**

**text**

```
## 🎯 **INSTALLATION CHECKLIST**

```markdown
## ✅ Installation Checklist

### Phase 1: Prerequisites
- [ ] Python 3.8+ installed
- [ ] Git installed
- [ ] Terminal/Command Prompt ready

### Phase 2: Project Setup
- [ ] Clone repository
- [ ] Run `python init_system.py`
- [ ] Verify folder structure created

### Phase 3: API Configuration
- [ ] Get Binance API keys
- [ ] Get Bybit API keys  
- [ ] Get DeepSeek API key
- [ ] Create `.env` file from template
- [ ] Add all API keys to `.env`

### Phase 4: Dependencies
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify no installation errors

### Phase 5: Testing
- [ ] Test data collection: `python collector.py`
- [ ] Test trading plan: `python run_trading_plans.py --symbol BTCUSDT`
- [ ] Check logs folder for output

### Phase 6: Automation (Optional)
- [ ] Start scheduler: `python scheduler.py`
- [ ] Configure alerts if needed
- [ ] Set up automatic backups
```

## 📱 **QUICK START FOR DIFFERENT USERS**

### **For Beginners:**

**bash**

```
# Just these 5 commands:
git clone <repo-url>
cd crypto_trading_system
python init_system.py
# Edit .env with your API keys
python run_trading_plans.py --symbol BTCUSDT
```

### **For Traders:**

**bash**

```
# Focus on trading plans
python run_trading_plans.py --all           # All pairs
python scheduler.py                         # Auto schedule
# Check data/trading_plans/ for results
```

### **For Developers:**

**bash**

```
# Full setup with development
git clone <repo-url>
python init_system.py
pip install -r requirements-dev.txt
pytest tests/                              # Run tests
python -m black *.py                       # Format code
```


## 🆘 **TROUBLESHOOTING QUICK GUIDE**

| Symptom                 | Quick Fix                               |
| ----------------------- | --------------------------------------- |
| "API key invalid"       | Check `.env` file, regenerate keys    |
| "No module named..."    | Run `pip install -r requirements.txt` |
| "No data returned"      | Check internet, API status pages        |
| "Scheduler not running" | Check system time (should be UTC)       |
| "Out of memory"         | Reduce cache size in config             |
