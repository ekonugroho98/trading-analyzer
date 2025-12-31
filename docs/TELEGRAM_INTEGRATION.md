# Telegram Trading Bot Integration

## Overview
Multi-user Telegram bot untuk crypto trading analyzer dengan real-time notifications, trading plan generation, dan personalized alerts.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Bot API                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Telegram Bot Core                          │
│  - python-telegram-bot / aiogram                             │
│  - Multi-user management                                     │
│  - Command handlers                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────────┐
│  UserManager  │ │Handlers  │ │ Notifications  │
│ - Subscribe   │ │Commands  │ │ - Alerts       │
│ - Alerts      │ │Plans     │ │ - Trading Plans│
│ - Profile     │ │Price     │ │ - Reports      │
└───────┬──────┘ └────┬─────┘ └─────┬──────────┘
        │            │            │
        └────────────┼────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│              Trading System Backend                         │
│  - TradingScheduler (scheduled tasks)                      │
│  - DeepSeekIntegration (AI analysis)                       │
│  - StreamingIntegration (real-time data)                   │
│  - DataCollector (market data)                             │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. User Commands

#### Basic Commands (All Users)
| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot & welcome message | `/start` |
| `/help` | Show all available commands | `/help` |
| `/status` | Check system status | `/status` |
| `/price [symbol]` | Get current price & basic info | `/price BTCUSDT` |
| `/plan [symbol]` | Generate AI trading plan | `/plan BTCUSDT` |
| `/plan [symbol] [timeframe]` | Generate plan with timeframe | `/plan ETHUSDT 1h` |

#### Subscription Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/subscribe [symbol]` | Subscribe to symbol updates | `/subscribe SOLUSDT` |
| `/unsubscribe [symbol]` | Unsubscribe from symbol | `/unsubscribe SOLUSDT` |
| `/mysubscriptions` | List personal subscriptions | `/mysubscriptions` |
| `/subscribeall` | Subscribe to all major pairs | `/subscribeall` |

#### Alert Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/setalert [symbol] [above/below] [price]` | Set price alert | `/setalert BTCUSDT above 90000` |
| `/myalerts` | List personal alerts | `/myalerts` |
| `/delalert [alert_id]` | Delete alert | `/delalert 123` |
| `/clearalerts` | Clear all alerts | `/clearalerts` |

#### Portfolio Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/myportfolio` | Show portfolio summary | `/myportfolio` |
| `/addposition [symbol] [type] [price] [qty]` | Add position | `/addposition BTCUSDT buy 85000 0.1` |
| `/closeposition [symbol]` | Close position | `/closeposition BTCUSDT` |

#### Analysis Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/analyze [symbol]` | Quick technical analysis | `/analyze BTCUSDT` |
| `/signals` | Get current signals for subscriptions | `/signals` |
| `/trending` | Show trending coins | `/trending` |

#### Admin Commands (Admin Only)
| Command | Description | Example |
|---------|-------------|---------|
| `/users` | List all users | `/users` |
| `/broadcast [message]` | Broadcast to all users | `/broadcast Market alert!` |
| `/system` | System health & stats | `/system` |
| `/addadmin [chat_id]` | Add new admin | `/addadmin 123456` |

### 2. Automated Notifications

#### Real-time Alerts
- Price break alerts (support/resistance)
- Volume spike alerts
- Volatility alerts
- Signal change alerts (BUY → SELL)

#### Scheduled Notifications
- Daily trading plans (9 AM UTC)
- Market open/close notifications
- Weekly summary reports (Sunday 10 PM UTC)
- Monthly performance reports

#### Personalized Notifications
- Custom price alerts per user
- Symbol-specific updates
- Portfolio notifications

### 3. Database Schema

#### Users Table (SQLite)
```sql
CREATE TABLE users (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    role TEXT DEFAULT 'user',  -- 'user' or 'admin'
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    symbol TEXT,
    timeframe TEXT DEFAULT '4h',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES users(chat_id),
    UNIQUE(chat_id, symbol)
);
```

#### Alerts Table
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    symbol TEXT,
    alert_type TEXT,  -- 'above', 'below', 'change_percent'
    target_price REAL,
    triggered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES users(chat_id)
);
```

#### Portfolio Table (Future)
```sql
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    symbol TEXT,
    position_type TEXT,  -- 'long' or 'short'
    entry_price REAL,
    quantity REAL,
    status TEXT DEFAULT 'open',  -- 'open' or 'closed'
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES users(chat_id)
);
```

### 4. File Structure

```
crypto_trading_analyzer/
├── telegram/
│   ├── __init__.py
│   ├── bot.py                    # Main bot class
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── basic.py              # /start, /help, /status
│   │   ├── trading.py            # /plan, /price, /analyze
│   │   ├── subscription.py       # /subscribe, /unsubscribe
│   │   ├── alerts.py             # /setalert, /myalerts
│   │   ├── portfolio.py          # /myportfolio (future)
│   │   └── admin.py              # Admin commands
│   ├── user_manager.py           # User management
│   ├── notifications.py          # Notification templates
│   ├── database.py               # Database operations
│   └── formatter.py              # Message formatting
├── config.py                      # + Telegram config
├── data/
│   └── telegram_users.db         # SQLite database
└── docs/
    └── TELEGRAM_INTEGRATION.md   # This file
```

### 5. Configuration

#### Environment Variables (.env)
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_CHAT_IDS=123456789,987654321

# Rate Limiting
TELEGRAM_MAX_REQUESTS_PER_MINUTE=20
TELEGRAM_BAN_THRESHOLD=100

# Notification Settings
TELEGRAM_ENABLE_NOTIFICATIONS=true
TELEGRAM_DAILY_PLAN_TIME=09:00
TELEGRAM_WEEKLY_REPORT_DAY=sunday
```

#### Config Class (config.py)
```python
# Telegram Configuration
self.TELEGRAM = type('TelegramNamespace', (), {
    'bot_token': os.getenv("TELEGRAM_BOT_TOKEN", ""),
    'admin_chat_ids': [
        int(cid) for cid in os.getenv("TELEGRAM_ADMIN_CHAT_IDS", "").split(",")
        if cid.strip()
    ],
    'max_requests_per_minute': int(os.getenv("TELEGRAM_MAX_REQUESTS_PER_MINUTE", 20)),
    'enable_notifications': os.getenv("TELEGRAM_ENABLE_NOTIFICATIONS", "true").lower() == "true",
    'daily_plan_time': os.getenv("TELEGRAM_DAILY_PLAN_TIME", "09:00"),
    'weekly_report_day': os.getenv("TELEGRAM_WEEKLY_REPORT_DAY", "sunday"),
})()
```

### 6. Notification Templates

#### Trading Plan Notification
```markdown
🤖 *AI Trading Plan*
📊 *BTCUSDT* - 4h

*Signal*: BUY 🟢
*Confidence*: 75%
*Trend*: BULLISH

*Entry Levels*:
💰 $87,500 (50%)
💰 $86,800 (30%)
💰 $86,200 (20%)

*Take Profits*:
🎯 $88,900 (1.8x)
🎯 $91,200 (3.2x)
🎯 $94,000 (5.0x)

*Stop Loss*: $85,100
*Risk/Reward*: 2.5

_Reason: Strong bullish momentum with RSI rebound from support zone._
```

#### Price Alert Notification
```markdown
🚨 *Price Alert Triggered*
📊 *BTCUSDT*

💥 Price broke above $90,000!

*Current Price*: $90,234
*Change*: +3.2% in 15min

Consider taking profits or tightening stops! 🎯
```

#### Signal Change Notification
```markdown
⚠️ *Signal Change Alert*
📊 *ETHUSDT* - 1h

*Previous*: HOLD 🟡
*Current*: BUY 🟢

*Entry*: $3,450
*Target*: $3,600 (+4.3%)
*Stop*: $3,380 (-2.0%)

Reason: MACD crossover + volume confirmation
```

### 7. Rate Limiting & Security

#### Rate Limiting
- Max 20 requests/minute per user
- Ban after 100 violations in 1 hour
- Queue for heavy operations (plan generation)

#### Security
- Admin verification via chat_id whitelist
- Input validation for all commands
- SQL injection prevention (parameterized queries)
- XSS prevention in messages

### 8. Implementation Phases

#### Phase 1: Basic Bot (MVP)
- [x] Design architecture
- [ ] Set up bot infrastructure
- [ ] Basic commands (/start, /help, /status)
- [ ] User registration & database
- [ ] Single trading plan generation

#### Phase 2: Core Features
- [ ] Subscription system
- [ ] Alert system
- [ ] Real-time notifications
- [ ] Multiple timeframe support

#### Phase 3: Advanced Features
- [ ] Portfolio tracking
- [ ] Performance reports
- [ ] Backtesting integration
- [ ] Admin panel

#### Phase 4: Premium Features (Future, Winrate > 70%)
- [ ] Web dashboard
- [ ] User tiers (Free/Premium)
- [ ] Advanced analytics
- [ ] API access
- [ ] Mobile app

### 9. Dependencies

```bash
# Add to requirements.txt
python-telegram-bot==20.7  # or aiogram==3.4
aiohttp==3.9.1
SQLAlchemy==2.0.25  # optional for ORM
```

### 10. Testing Plan

#### Unit Tests
- User management functions
- Database operations
- Notification formatting
- Command handlers

#### Integration Tests
- Bot API integration
- Trading system integration
- Alert triggering
- Multi-user scenarios

#### Load Tests
- 100+ concurrent users
- 1000+ messages/minute
- Database performance

---

## Next Steps

1. **Set up Telegram Bot**: Create bot via @BotFather
2. **Implement Phase 1**: Basic bot with user management
3. **Test**: Single user testing
4. **Deploy**: Run bot alongside trading system
5. **Iterate**: Add features based on feedback

---

**Status**: 📝 Planning Phase
**Target**: Multi-user MVP in 2 weeks
**Winrate Goal**: > 70% before premium features
