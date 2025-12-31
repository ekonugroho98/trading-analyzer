#!/usr/bin/env python3
"""Test BEATUSDT analysis"""

from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from collector import CryptoDataCollector

# Simulate user with futures preference
chat_id = 788501152
symbol = 'BEATUSDT'

# Get user's market preference
market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
print(f'User market preference: {market_pref}')

# Fetch data using user's market preference
collector = CryptoDataCollector()

if market_pref == 'futures':
    print('Fetching from Binance Futures...')
    df = collector._get_binance_futures_klines(symbol, '4h', limit=100)
elif market_pref == 'spot':
    print('Fetching from Binance Spot...')
    df = collector.get_binance_klines(symbol, '4h', limit=100, use_cache=False, save_cache=False)
else:  # auto
    print('Auto-detect: Trying futures first...')
    df = collector.get_binance_klines_auto(symbol, '4h', limit=100)

if df is not None and len(df) > 0:
    print(f'Success! Got {len(df)} candles')
    latest = df.iloc[-1]
    print(f'Current price: ${latest["close"]:,.2f}')
    print(f'High: ${latest["high"]:,.2f}')
    print(f'Low: ${latest["low"]:,.2f}')
    print(f'Volume: {latest["volume"]:,.0f}')

    # Simple analysis
    sma_20 = df['close'].rolling(20).mean().iloc[-1]
    sma_50 = df['close'].rolling(50).mean().iloc[-1]

    trend = "NEUTRAL"
    if latest['close'] > sma_20 > sma_50:
        trend = "BULLISH 📈"
    elif latest['close'] < sma_20 < sma_50:
        trend = "BEARISH 📉"

    print(f'SMA 20: ${sma_20:,.2f}')
    print(f'SMA 50: ${sma_50:,.2f}')
    print(f'Trend: {trend}')
else:
    print('Failed to fetch data')
