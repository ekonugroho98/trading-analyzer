# 🚧 TODO Features List

File ini berisi 7 fitur prioritas yang belum diimplementasikan dan ingin ditambahkan ke Crypto Trading Analyzer.

---

## 📋 Priority Features

### 1. 📊 **Trading Signals Database** ⭐ HIGH PRIORITY

**Description**: Save semua historical signals yang di-generate oleh AI untuk analysis dan tracking.

**Current Status**: Signals hanya di-generate dan dikirim ke Telegram, tidak disimpan untuk analysis.

**Features to Implement**:

#### a) **Signal History Storage**
- Save semua AI signals ke database:
  - Symbol, timeframe, signal type (BUY/SELL/HOLD)
  - Confidence score
  - Entry levels, take profits, stop loss
  - Generated timestamp
  - Plan ID/Reference

#### b) **Signal Tracking**
- Track outcome dari setiap signal:
  - Did entry tercapai? (YA/TIDAK)
  - Did take profit tercapai? (TP1/TP2/TP3)
  - Did stop loss ter-trigger?
  - Actual profit/loss (jika posisi ditutup)
  - Time to outcome (berapa lama signal aktif)

#### c) **Signal Analytics**
- Signal accuracy rate
- Best performing timeframes
- Best performing symbols
- Average confidence vs actual outcome
- Signal expiration rate (signals yang tidak hit target)

#### d) **Telegram Commands**
- `/signal_history [symbol]` - Lihat signal history untuk suatu coin
- `/signal_stats` - Statistik signal performance
- `/best_signals` - Top 10 most accurate signals
- `/worst_signals - Bottom 10 least accurate signals
- `/signal_accuracy [timeframe]` - Accuracy rate per timeframe

**Implementation Plan**:
1. Create database table `signal_history`:
   ```sql
   CREATE TABLE signal_history (
       id INTEGER PRIMARY KEY,
       user_id INTEGER,
       symbol TEXT,
       timeframe TEXT,
       signal_type TEXT,  -- BUY/SELL/HOLD
       confidence REAL,
       entries JSON,  -- Entry levels
       take_profits JSON,  -- TP levels
       stop_loss REAL,
       generated_at TIMESTAMP,
       outcome TEXT,  -- 'pending', 'won', 'lost', 'breakeven'
       actual_outcome REAL,  -- Actual P&L
       outcome_at TIMESTAMP
   );
   ```
2. Create `analytics/signal_tracker.py` - Track signal outcomes
3. Create `tg_bot/handlers/signals.py` - Signal history commands
4. Add outcome checking ke scheduler

---

### 2. 💬 **Sentiment Analysis** ⭐ HIGH PRIORITY

**Description**: Integrasi dengan social media sentiment analysis (Twitter, Reddit, dll).

**Current Status**: Belum ada sentiment analysis sama sekali.

**Features to Implement**:

#### a) **Twitter Sentiment**
- Real-time sentiment dari tweets tentang crypto
- Track mentions untuk specific coins
- Sentiment score: Bullish/Bearish/Neutral
- Volume of mentions

#### b) **Reddit Sentiment**
- Sentiment dari r/cryptocurrency, r/bitcoin, r/ethereum
- Upvote/downvote ratio analysis
- Hot posts discussion

#### c) **Sentiment Scoring**
- Combined sentiment score dari multiple sources
- Weighted average (Twitter 40%, Reddit 40%, News 20%)
- Historical sentiment trends

#### d) **Telegram Commands**
- `/sentiment [symbol]` - Cek sentiment suatu coin
- `/sentiment_trending` - Coins dengan highest positive sentiment
- `/sentiment_heatmap` - Visual sentiment comparison

**Implementation Plan**:
1. Integrasi APIs:
   - Twitter API v2 (Academic Research access)
   - Reddit API (PRAW)
   - Alternative: CryptoCompare Sentiment API
2. Create `integrations/sentiment.py` - Sentiment analyzer
3. Add sentiment calculation ke trading plan generation
4. Create handlers untuk sentiment commands

**Data Sources**:
- Twitter API: https://developer.twitter.com/en/docs/twitter-api
- Reddit API: https://praw.readthedocs.io/
- LunarCrush (Crypto social analytics): https://lunarcrush.com/
- CryptoCompare: https://min-api.cryptocompare.com/

---

### 3. 🔗 **Correlation Matrix** ⭐ MEDIUM PRIORITY

**Description**: Analisa korelasi antar cryptocurrencies untuk diversification.

**Current Status**: Belum ada korelasi analysis.

**Features to Implement**:

#### a) **Correlation Calculation**
- Calculate Pearson correlation coefficient antar coins
- Multiple timeframe correlation (1h, 4h, 1d, 1w)
- Rolling correlation (dynamic updates)

#### b) **Correlation Heatmap**
- Visual matrix dengan colors:
  - Red: High positive correlation (>0.7)
  - Green: Low/negative correlation (<0.3)
- Group by sectors (DeFi, Layer 1, Exchange tokens, dll)

#### c) **Diversification Suggestions**
- Suggest uncorrelated pairs untuk portfolio
- Risk reduction strategies
- Sector allocation recommendations

#### d) **Telegram Commands**
- `/correlation [symbol]` - Korelasi suatu coin vs top coins
- `/correlation_matrix` - Full correlation heatmap
- `/uncorrelated` - List uncorrelated pairs
- `/sector_correlation` - Correlation by sector

**Implementation Plan**:
1. Create `analytics/correlation.py` - Correlation calculator
2. Use pandas.DataFrame.corr() untuk correlation matrix
3. Generate heatmap images (matplotlib/seaborn)
4. Add correlation data ke market screening

**Example Output**:
```
BTC/ETH: 0.85 (High correlation)
BTC/SOL: 0.62 (Medium correlation)
BTC/DOGE: 0.35 (Low correlation)
```

---

### 4. 📏 **Auto-Scaling Position Sizing** ⭐ MEDIUM PRIORITY

**Description**: Automatic position sizing berdasarkan volatility dan risk parameters.

**Current Status**: Position sizing manual (user harus tentukan quantity sendiri).

**Features to Implement**:

#### a) **Volatility-Based Sizing**
- Calculate ATR (Average True Range) untuk volatility
- Higher volatility = smaller position size
- Lower volatility = larger position size
- Fixed risk per trade (e.g., 2% of portfolio)

#### b) **Kelly Criterion**
- Position sizing berdasarkan Kelly Criterion
- Based on historical win rate and avg win/loss
- Optimal growth rate calculation

#### c) **Risk-Adjusted Sizing**
- Scale in based on confidence score
- High confidence (>70%) = full position
- Medium confidence (50-70%) = 50-70% position
- Low confidence (<50%) = skip trade

#### d) **Telegram Commands**
- `/position_size [symbol] [entry] [sl]` - Calculate optimal size
- `/sizing_method` - Set sizing method (fixed, volatility, kelly)
- `/risk_params` - Set risk per trade percentage

**Implementation Plan**:
1. Create `analytics/position_sizing.py` - Position sizing calculator
2. Integrate ke paper trading dan trading plans
3. Add ATR calculation ke collector
4. Update portfolio handlers untuk auto-sizing

**Formulas**:
```
# Volatility-based
position_size = (portfolio_value * risk_per_trade) / (entry_price - stop_loss)

# Kelly Criterion
kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
position_size = portfolio_value * kelly
```

---

### 5. 📰 **News Integration** ⭐ MEDIUM PRIORITY

**Description**: Crypto news feeds untuk fundamental analysis dan market context.

**Current Status**: Belum ada news integration.

**Features to Implement**:

#### a) **News Feeds**
- Real-time crypto news dari multiple sources:
  - CoinDesk
  - CryptoSlate
  - CoinTelegraph
  - Bloomberg Crypto
  - Decrypt

#### b) **News Categorization**
- Categorize news by impact:
  - High impact (regulation, exchange hacks, dll)
  - Medium impact (partnerships, listings)
  - Low impact (opinions, rumors)

#### c) **News Sentiment**
- AI-powered sentiment analysis untuk news
- Positive/Negative/Neutral classification
- Impact score (1-10)

#### d) **Symbol-Specific News**
- Filter news per symbol
- Aggregate news untuk portfolio symbols
- News alerts untuk subscribed coins

#### e) **Telegram Commands**
- `/news [symbol]` - Latest news untuk coin
- `/news_high_impact` - High impact news
- `/news_sentiment` - News sentiment overview
- `/subscribe_news [symbol]` - Subscribe ke news alerts

**Implementation Plan**:
1. Integrasi APIs:
   - CryptoCompare News API: https://min-api.cryptocompare.com/
   - NewsAPI.org: https://newsapi.org/
   - CryptoControl: https://cryptocontrol.io/api
2. Create `integrations/news_api.py` - News fetcher
3. Add news ke trading plan generation
4. Add sentiment scoring untuk news

**Example Integration**:
```python
# CryptoCompare News API
url = "https://min-api.cryptocompare.com/data/v2/news/"
?lang=EN&categories=BTC,ETH
```

---

### 6. ⚖️ **Portfolio Rebalancing** ⭐ MEDIUM PRIORITY

**Description**: Auto rebalance portfolio untuk maintain target allocation.

**Current Status**: Portfolio static, tidak ada auto-rebalancing.

**Features to Implement**:

#### a) **Target Allocation**
- Set target allocation per symbol/sector
- Example: BTC 40%, ETH 30%, Altcoins 30%
- Set rebalancing threshold (e.g., ±5%)

#### b) **Auto-Rebalance Trigger**
- Trigger rebalance ketika allocation menyimpang
- Calculate required trades untuk rebalance
- Generate orders untuk rebalancing

#### c) **Rebalancing Strategies**
- Time-based (rebalance weekly/monthly)
- Threshold-based (rebalance when deviation > X%)
- Volatility-based (rebalance when volatility changes)

#### d) **Telegram Commands**
- `/rebalance` - Execute rebalance now
- `/rebalance_status` - Check if rebalance needed
- `/set_allocation [symbol] [pct]` - Set target allocation
- `/rebalance_settings` - Configure rebalancing parameters

**Implementation Plan**:
1. Create `analytics/rebalancing.py` - Rebalancing calculator
2. Add `portfolio_allocations` table ke database
3. Create rebalancing scheduler job
4. Integrate dengan paper trading untuk auto-execute

**Example Logic**:
```python
current_btc_pct = btc_value / total_portfolio
target_btc_pct = 0.40

if abs(current_btc_pct - target_btc_pct) > threshold:
    # Calculate rebalance trade
    diff = total_portfolio * (target_btc_pct - current_btc_pct)
    if diff > 0:
        buy_btc(diff)  # Buy more BTC
    else:
        sell_btc(abs(diff))  # Sell some BTC
```

---

### 7. 🐋 **Whale Alert** ⭐ HIGH PRIORITY

**Description**: Tracking large transactions on-chain untuk detect whale movements.

**Current Status**: Belum ada on-chain transaction monitoring.

**Features to Implement**:

#### a) **Large Transaction Detection**
- Monitor large transfers on blockchain:
  - Bitcoin (>100 BTC)
  - Ethereum (>1,000 ETH)
  - Major altcoins (>token-specific threshold)
- Exchange inflows/outflows
- Whale wallet movements

#### b) **Whale Alert Sources**
- Whale Alert API: https://whale-alert.io/
- Glassnode API: https://glassnode.com/
- Etherscan API (for ETH)
- Blockchain.com API (for BTC)

#### c) **Alert Types**
- Large transfers to/from exchanges
- Whale accumulation (large buys)
- Whale distribution (large sells)
- Exchange inflow (potentially bearish)
- Exchange outflow (potentially bullish)

#### d) **Telegram Commands**
- `/whale_alerts` - Latest whale transactions
- `/set_whale_alert [symbol] [amount]` - Set custom threshold
- `/whale_exchange_flow` - Exchange inflows/outflows
- `/subscribe_whale [symbol]` - Subscribe ke whale alerts

**Implementation Plan**:
1. Integrasi APIs:
   - Whale Alert API (free tier available)
   - Glassnode API (7-day free trial)
   - Custom blockchain monitors
2. Create `integrations/whale_monitor.py` - Whale transaction tracker
3. Add whale alerts ke alert system
4. Add whale data ke market analysis

**Whale Alert API Example**:
```python
# Whale Alert API
url = f"https://api.whale-alert.io/v1/transaction"
?api_key={API_KEY}
&min_value=500000  # $500k+ transactions
```

**Data Points**:
- Transaction hash
- From/To addresses (exchange or wallet)
- Amount (in crypto and USD)
- Timestamp
- Symbol (BTC, ETH, etc.)

---

## 📅 Implementation Timeline

### Phase 1 (Next 1-2 weeks): HIGH PRIORITY
1. 🐋 **Whale Alert** - High value untuk market insights
2. 📊 **Trading Signals Database** - Critical untuk tracking performance
3. 💬 **Sentiment Analysis** - Boost analysis accuracy

### Phase 2 (Next 2-4 weeks): MEDIUM PRIORITY
4. 🔗 **Correlation Matrix** - Portfolio diversification
5. 📏 **Auto-Scaling Position Sizing** - Risk management
6. 📰 **News Integration** - Fundamental analysis

### Phase 3 (Next 1-2 months):
7. ⚖️ **Portfolio Rebalancing** - Advanced portfolio management

---

## 🗂️ File Structure Plan

```
crypto_trading_analyzer/
├── analytics/
│   ├── signal_tracker.py       # Signal history & outcome tracking
│   ├── correlation.py           # Correlation matrix calculator
│   ├── position_sizing.py       # Auto-scaling position sizing
│   └── rebalancing.py           # Portfolio rebalancing
├── integrations/
│   ├── sentiment.py             # Social media sentiment
│   ├── news_api.py              # News feeds
│   └── whale_monitor.py         # Whale transaction tracking
├── tg_bot/handlers/
│   ├── signals.py               # Signal history commands
│   ├── sentiment.py             # Sentiment commands
│   ├── correlation.py           # Correlation commands
│   ├── news.py                  # News commands
│   └── whale.py                 # Whale alert commands
└── database/
    └── migrations/
        └── add_signal_history.py  # Database migration
```

---

## 📝 Notes

- Semua integrasi API harus handle rate limits dengan proper
- Gunakan caching untuk reduce API calls
- Monitor API costs terutama untuk paid services
- Log semua whale transactions dan signals untuk analysis
- Consider self-hosted solutions untuk data collection (reduce dependency)

---

## 🔗 API Resources

### Whale Alert
- Website: https://whale-alert.io/
- API Docs: https://docs.whale-alert.io/
- Free tier: 100 calls/day

### Sentiment Analysis
- LunarCrush: https://lunarcrush.com/ (free tier available)
- CryptoCompare Social: https://min-api.cryptocompare.com/
- Santiment: https://santiment.net/

### News APIs
- CryptoCompare: https://min-api.cryptocompare.com/
- NewsAPI: https://newsapi.org/
- CryptoControl: https://cryptocontrol.io/

### Correlation Data
- Calculate internally from price data
- No external API needed

---

**Last Updated**: 2026-01-03
**Status**: Market Screening selesai. Next: Implementasi 7 fitur prioritas.
