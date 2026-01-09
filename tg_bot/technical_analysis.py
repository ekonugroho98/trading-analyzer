"""
Technical Analysis Library
Pure logic-based technical indicators for hybrid screening
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)"""
    try:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]
    except:
        return 50.0


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_macd(df: pd.DataFrame) -> tuple:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    try:
        ema_12 = calculate_ema(df, 12)
        ema_26 = calculate_ema(df, 26)

        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    except:
        return 0.0, 0.0, 0.0


def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Calculate ADX (Average Directional Index)"""
    try:
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx.iloc[-1]
    except:
        return 25.0


def quick_technical_score(df: pd.DataFrame) -> dict:
    """
    Quick technical filter using pure logic (NO AI)

    Returns:
        dict: {
            'score': 0-100,
            'passed': bool,
            'signals': [],
            'trend': str,
            'metrics': dict
        }
    """
    try:
        if df is None or len(df) < 50:
            return {'score': 0, 'passed': False, 'signals': [], 'trend': 'NEUTRAL', 'metrics': {}}

        score = 0
        signals = []

        # Calculate indicators
        current_price = float(df['close'].iloc[-1])
        rsi = calculate_rsi(df)
        ema_20 = calculate_ema(df, 20)
        ema_50 = calculate_ema(df, 50)
        ema_200 = calculate_ema(df, 200)
        macd_line, signal_line, histogram = calculate_macd(df)
        adx = calculate_adx(df)

        # 1. Trend Analysis (30 points max)
        if current_price > ema_20.iloc[-1] > ema_50.iloc[-1]:
            score += 30
            signals.append("Strong uptrend (price > EMA20 > EMA50)")
            trend = "BULLISH"
        elif current_price > ema_20.iloc[-1]:
            score += 20
            signals.append("Moderate uptrend (price > EMA20)")
            trend = "BULLISH"
        elif current_price < ema_20.iloc[-1] < ema_50.iloc[-1]:
            score -= 10
            signals.append("Downtrend (price < EMA20 < EMA50)")
            trend = "BEARISH"
        else:
            score += 10
            trend = "NEUTRAL"

        # 2. RSI Analysis (20 points max)
        if 40 <= rsi <= 60:
            score += 20
            signals.append(f"RSI in healthy zone ({rsi:.1f})")
        elif 30 <= rsi < 40:
            score += 15
            signals.append(f"RSI approaching oversold ({rsi:.1f})")
        elif 60 < rsi <= 70:
            score += 15
            signals.append(f"RSI approaching overbought ({rsi:.1f})")
        elif rsi < 30:
            score += 5
            signals.append(f"RSI oversold ({rsi:.1f}) - potential reversal")
        else:  # rsi > 70
            score += 0
            signals.append(f"RSI overbought ({rsi:.1f})")

        # 3. MACD Analysis (15 points max)
        if histogram > 0 and macd_line > signal_line:
            score += 15
            signals.append("MACD bullish (momentum up)")
        elif histogram > 0:
            score += 10
            signals.append("MACD momentum building")
        elif histogram < 0:
            score += 0
            signals.append("MACD bearish (momentum down)")

        # 4. ADX Strength (10 points max)
        if adx > 25:
            score += 10
            signals.append(f"Strong trend (ADX {adx:.1f})")
        elif adx > 20:
            score += 5
            signals.append(f"Moderate trend (ADX {adx:.1f})")

        # 5. Volume Analysis (15 points max)
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]

        if current_volume > avg_volume * 1.5:
            score += 15
            signals.append("High volume (1.5x average)")
        elif current_volume > avg_volume:
            score += 10
            signals.append("Above average volume")

        # 6. Price Action (10 points max)
        if current_price > df['close'].iloc[-5]:
            score += 10
            signals.append("Price moving up (5-period)")
        elif current_price > df['close'].iloc[-10]:
            score += 5
            signals.append("Price stable up (10-period)")

        # Determine if passed minimum threshold
        passed = score >= 60

        return {
            'score': score,
            'passed': passed,
            'signals': signals,
            'trend': trend,
            'metrics': {
                'rsi': rsi,
                'macd': macd_line,
                'macd_signal': signal_line,
                'macd_histogram': histogram,
                'adx': adx,
                'ema_20': ema_20.iloc[-1],
                'ema_50': ema_50.iloc[-1],
                'ema_200': ema_200.iloc[-1],
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1
            }
        }

    except Exception as e:
        logger.error(f"Error in quick_technical_score: {e}")
        return {'score': 0, 'passed': False, 'signals': [], 'trend': 'NEUTRAL', 'metrics': {}}
