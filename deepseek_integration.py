"""
DEEPSEEK TRADING PLAN GENERATOR
Output terstruktur untuk trading plan lengkap
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass, field
from enum import Enum

from config import config
from collector import CryptoDataCollector

logger = logging.getLogger(__name__)

# ============ DATA STRUCTURES ============
@dataclass
class TradingSignal:
    """Individual trading signal"""
    signal_type: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    reason: str
    timestamp: datetime

@dataclass
class EntryPoint:
    """Entry point structure"""
    level: float
    weight: float  # 0.0 - 1.0 (percentage dari position)
    risk_score: float  # 1-10, 1 = paling aman
    description: str

@dataclass
class TakeProfit:
    """Take profit target"""
    level: float
    reward_ratio: float  # Risk/Reward ratio
    percentage_gain: float  # Percentage gain from entry
    description: str

@dataclass
class TradingPlan:
    """Complete trading plan"""
    symbol: str
    timeframe: str
    generated_at: datetime
    current_price: float  # Current market price saat plan dibuat
    trend: str  # BULLISH, BEARISH, SIDEWAYS
    overall_signal: TradingSignal

    # Entry Points (bisa multiple entries)
    entries: List[EntryPoint]
    primary_entry: Optional[float] = None  # Entry utama

    # Take Profit Targets
    take_profits: List[TakeProfit] = field(default_factory=list)

    # Stop Loss
    stop_loss: float = 0.0
    stop_loss_reason: str = ""

    # Risk Management
    position_size: float = 0.0  # Dalam persen atau USD
    risk_per_trade: float = 2.0  # 1-5%
    max_drawdown: float = 10.0

    # Support & Resistance
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)

    # Additional Info
    indicators: Dict[str, Any] = field(default_factory=dict)
    market_conditions: str = ""
    timeframe_analysis: Dict[str, str] = field(default_factory=dict)  # Analisis multi-timeframe

    # Risk Metrics
    risk_reward_ratio: float = 0.0
    probability_of_success: float = 0.0
    expected_return: float = 0.0

    # Trading Psychology
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Raw Analysis
    raw_analysis: str = ""

    # Signal Validity
    expires_at: Optional[datetime] = None  # Waktu kadaluarsa sinyal

@dataclass
class TimeframeAnalysis:
    """Multi-timeframe analysis result"""
    timeframe: str
    trend: str  # BULLISH, BEARISH, SIDEWAYS
    current_price: float
    sma_trend: str  # ABOVE SMA, BELOW SMA
    momentum: str  # STRONG, WEAK, NEUTRAL
    summary: str

@dataclass
class AnalysisRequest:
    """Analysis request structure"""
    symbol: str
    timeframe: str
    data_points: int = 100
    analysis_type: str = "trading_plan"  # Now focused on trading plan
    include_multi_timeframe: bool = True
    custom_prompt: str = None
    risk_profile: str = "moderate"  # conservative, moderate, aggressive
    preferred_exchange: str = "bybit"  # bybit or binance - user's default exchange
    enable_scalping: bool = True  # Enable scalping mode for sideways/choppy markets

# ============ TRADING PLAN GENERATOR ============
class TradingPlanGenerator:
    """
    Generate detailed trading plans using DeepSeek AI
    """
    
    def __init__(self, deepseek_config=None):
        self.config = deepseek_config or config.DEEPSEEK
        self.collector = CryptoDataCollector()
        self.session = requests.Session()
        
        # Setup session
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.request_delay = 1.0
        
        logger.info("Trading Plan Generator initialized")
    
    def _rate_limit(self):
        """Rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

        self.last_request_time = time.time()

    def _get_tf_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes for sorting"""
        tf_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080
        }
        return tf_map.get(timeframe, 0)

    def _check_scalping_opportunity(self, df: pd.DataFrame, rsi: float, adx: float) -> Dict[str, Any]:
        """
        Check if market conditions are suitable for scalping

        Returns dict with:
        - is_scalpable: bool
        - scalp_type: str ('support_bounce', 'resistance_reject', 'range_bound')
        - nearest_level: float (nearest support or resistance)
        - distance_pct: float (distance to nearest level in %)
        - reason: str
        """
        current_price = df['close'].iloc[-1]
        support_levels = self._calculate_support_levels(df)
        resistance_levels = self._calculate_resistance_levels(df)

        # Check if conditions are suitable for scalping
        is_sideways = adx < 25  # Low trend strength
        is_neutral_rsi = 40 <= rsi <= 60  # Neutral momentum
        has_clear_levels = len(support_levels) > 0 and len(resistance_levels) > 0

        if not (is_sideways and is_neutral_rsi and has_clear_levels):
            return {
                'is_scalpable': False,
                'scalp_type': None,
                'nearest_level': None,
                'distance_pct': None,
                'reason': 'Market conditions not suitable for scalping (requires: ADX<25, RSI 40-60, clear S/R levels)'
            }

        # Find nearest support/resistance level
        nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))

        distance_to_support = abs((current_price - nearest_support) / current_price * 100)
        distance_to_resistance = abs((nearest_resistance - current_price) / current_price * 100)

        # Determine scalping type
        if distance_to_support < 0.5:  # Within 0.5% of support
            return {
                'is_scalpable': True,
                'scalp_type': 'support_bounce',
                'nearest_level': nearest_support,
                'distance_pct': distance_to_support,
                'reason': f'Price near support (${nearest_support:.6f}) - potential LONG scalp bounce'
            }
        elif distance_to_resistance < 0.5:  # Within 0.5% of resistance
            return {
                'is_scalpable': True,
                'scalp_type': 'resistance_reject',
                'nearest_level': nearest_resistance,
                'distance_pct': distance_to_resistance,
                'reason': f'Price near resistance (${nearest_resistance:.6f}) - potential SHORT scalp rejection'
            }
        elif distance_to_support < 1.0 or distance_to_resistance < 1.0:  # Within 1% of either level
            return {
                'is_scalpable': True,
                'scalp_type': 'range_bound',
                'nearest_level': nearest_support if distance_to_support < distance_to_resistance else nearest_resistance,
                'distance_pct': min(distance_to_support, distance_to_resistance),
                'reason': f'Range-bound between ${nearest_support:.6f} and ${nearest_resistance:.6f} - scalping opportunities'
            }
        else:
            return {
                'is_scalpable': False,
                'scalp_type': None,
                'nearest_level': None,
                'distance_pct': None,
                'reason': f'Price too far from levels (support: {distance_to_support:.2f}%, resistance: {distance_to_resistance:.2f}%)'
            }

    # ============ TRADING PLAN PROMPT ============
    def _create_trading_plan_prompt(self, df: pd.DataFrame, request: AnalysisRequest,
                                    mtf_data: List[TimeframeAnalysis] = None,
                                    scalping_info: Dict[str, Any] = None) -> str:
        """
        Create specialized prompt untuk trading plan
        """
        # Calculate technical levels
        current_price = df['close'].iloc[-1]
        high_24h = df['high'].tail(24).max()
        low_24h = df['low'].tail(24).min()

        # Support & Resistance
        support_levels = self._calculate_support_levels(df)
        resistance_levels = self._calculate_resistance_levels(df)

        # Indicators
        rsi = self._calculate_rsi(df)
        macd, signal = self._calculate_macd(df)
        adx = self._calculate_adx(df)

        # Determine precision based on price
        if current_price >= 1000:
            price_precision = 2
            price_format = f"${current_price:.2f}"
        elif current_price >= 1:
            price_precision = 4
            price_format = f"${current_price:.4f}"
        else:
            price_precision = 6
            price_format = f"${current_price:.6f}"

        # Build scalping section if applicable
        scalping_section = ""
        if scalping_info and scalping_info.get('is_scalpable'):
            scalp_type = scalping_info.get('scalp_type', '')
            nearest_level = scalping_info.get('nearest_level', 0)
            distance_pct = scalping_info.get('distance_pct', 0)
            reason = scalping_info.get('reason', '')

            scalping_section = f"""
        🔥 SCALPING MODE ACTIVATED - SIDEWAYS MARKET OPPORTUNITY:
        • Type: {scalp_type.upper().replace('_', ' ')}
        • Nearest Level: ${nearest_level:.{price_precision}f}
        • Distance: {distance_pct:.2f}%
        • Reason: {reason}

        SCALPING STRATEGY:
        • SMALL TARGETS: 0.5-1.5% profit per trade
        • TIGHT STOP LOSS: 0.3-0.5% from entry
        • QUICK EXIT: Don't be greedy, take profit quickly
        • SUPPORT BOUNCE: Buy near support, sell at resistance
        • RESISTANCE REJECT: Short near resistance, cover at support
        • RANGE TRADING: Buy low, sell high within the range

        ⚠️ SCALPING RULES:
        1. Position size: MAX 1-2% per scalp trade
        2. Multiple small profits > one big loss
        3. Exit immediately if price breaks the level
        4. Don't scalp more than 3 times in same level
        5. Best timeframes: 5m, 15m, 30m for quick entries/exits
"""

        # Build multi-timeframe section
        mtf_section = ""
        if mtf_data:
            mtf_section = "\n        MULTI-TIMEFRAME ANALYSIS (Confluence Check):\n"
            for tf_analysis in mtf_data:
                mtf_section += f"        • {tf_analysis.timeframe.upper()}: {tf_analysis.summary}\n"

            # Check confluence with higher TF priority
            if len(mtf_data) >= 2:
                # Sort timeframes by length (longer TF = higher priority)
                sorted_tfs = sorted(mtf_data, key=lambda x: self._get_tf_minutes(x.timeframe), reverse=True)
                trends = [tf.trend for tf in sorted_tfs]

                # Check if higher timeframes align
                higher_tf_bullish = trends[0] == "BULLISH"  # Primary TF trend
                all_aligned = all(t == trends[0] for t in trends)

                if all_aligned and higher_tf_bullish:
                    mtf_section += "        ✅ STRONG BULLISH CONFLUENCE - All timeframes aligned bullish\n"
                elif all_aligned and not higher_tf_bullish:
                    mtf_section += "        ✅ STRONG BEARISH CONFLUENCE - All timeframes aligned bearish\n"
                elif higher_tf_bullish and trends.count("BULLISH") >= len(trends) / 2:
                    mtf_section += "        ⚠️ PARTIAL BULLISH CONFLUENCE - Higher TF bullish, some lower TFs bearish\n"
                elif not higher_tf_bullish and trends.count("BEARISH") >= len(trends) / 2:
                    mtf_section += "        ⚠️ PARTIAL BEARISH CONFLUENCE - Higher TF bearish, some lower TFs bullish\n"
                else:
                    mtf_section += "        ❌ NO CLEAR CONFLUENCE - Timeframes showing mixed signals\n"

                # Add priority warning
                mtf_section += f"\n        ⚠️ PRIORITY: {sorted_tfs[0].timeframe.upper()} (higher timeframe) overrides lower TFs for trend direction\n"

        prompt = f"""
        Anda adalah CONSERVATIVE TRADING SPECIALIST dengan pendekatan RISK-ADVERSE.
        {scalping_section}
        ⚠️ FILTRI KUALITAS SETUP (WAJIB DICEK SEBELUM MEMBUAT PLAN):
        JANGAN BUAT TRADING PLAN jika:
        1. ADX < 20 (Market terlalu choppy/sideways) - KECUALI scalping mode aktif
        2. RSI di antara 40-60 (No clear momentum) - KECUALI scalping mode aktif
        3. Volume below 20 SMA (Low participation)
        4. Price terlalu dekat dengan support/resistance (<0.5%) - KECUALI scalping mode aktif
        5. Timeframe adalah 1h di luar market hours (00:00-08:00 UTC)

        Jika kondisi di atas terpenuhi, return HOLD signal.
        {f'''
        ⚠️ SCALPING MODE OVERRIDE:
        Karena scalping mode aktif, abaikan filter #1, #2, dan #4.
        Buat SCALPING SIGNAL (BUY/SELL) dengan:
        - SMALL ENTRY: 0.5-1% dari current price
        - TIGHT STOP: 0.3-0.5% dari entry
        - QUICK TP: 0.5-1.5% dari entry
        - Signal type: SCALP_LONG atau SCALP_SHORT
        ''' if scalping_info and scalping_info.get('is_scalpable') else ''}

        ⚠️ TIMEFRAME PRIORITY (PENTING):
        • HIGHER TIMEFRAME (Primary) > LOWER TIMEFRAME (Secondary)
        • Primary TF menentukan TREND DIRECTION
        • Secondary TF HANYA untuk entry timing confirmation
        • Jangan buat signal berlawanan dengan higher timeframe!

        CONTOH:
        - 4H BULLISH, 1H BEARISH → Tetap BUY (tunggu pullback ke 4H support)
        - 4H BEARISH, 1H BULLISH → Tetap SELL atau WAIT (jangan counter-trend)
        - Hanya buat BUY jika minimal 2 TFs aligned bullish
        - Hanya buat SELL jika minimal 2 TFs aligned bearish

        BUATKAN CONSERVATIVE TRADING PLAN untuk {request.symbol} pada timeframe {request.timeframe}.

        ⚠️ ATURAN LOGIKA ENTRY (WAJIB DIPAHAMI):
        • LONG/BUY: Entry di BAWAH atau DEKAT current price (tunggu pullback ke support)
        • SHORT/SELL: Entry di ATAS atau DEKAT current price (tunggu retrace/naik ke resistance untuk short)
        • Entry TIDAK BOLEH lebih dari 1.5% dari current price
        • Untuk SHORT: Current Price < Entry < Stop Loss, Take Profit < Entry (profit dari turun)
        • Untuk LONG: Take Profit > Entry > Stop Loss (profit dari naik)

        DATA TEKNIKAL SAAT INI:
        - Current Price: {price_format}
        - 24h High: ${high_24h:.{price_precision}f}
        - 24h Low: ${low_24h:.{price_precision}f}
        - Support Levels: {', '.join([f'${s:.{price_precision}f}' for s in support_levels[:3]])}
        - Resistance Levels: {', '.join([f'${r:.{price_precision}f}' for r in resistance_levels[:3]])}
        - RSI (14): {rsi:.2f}
        - MACD: {macd:.4f}, Signal: {signal:.4f}
{mtf_section}
        REQUIREMENT MINIMAL UNTUK SIGNAL:
        ✅ MINIMAL 2 INDIKATOR HARUS ALIGN (Confluence):
           - Trend direction (MA alignment)
           - Momentum indicator (RSI/MACD)
           - Volume confirmation
           - Support/Resistance level

        ✅ RISK/REWARD MINIMAL 1:2 untuk entry pertama
        ✅ Probability of success minimal 65%
        ✅ Entry tidak boleh lebih dari 1.5% dari current price
        ✅ Stop loss maximal 1.5% dari entry

        FORMAT OUTPUT YANG DIHARAPKAN (WAJIB DALAM JSON):
        {{
            "symbol": "{request.symbol}",
            "timeframe": "{request.timeframe}",
            "trend": "BULLISH/BEARISH/SIDEWAYS",
            "quality_score": {{
                "overall": 7.5,
                "confluence_count": 3,
                "factors": {{
                    "trend_alignment": 8,
                    "support_resistance": 7,
                    "momentum": 6,
                    "volume_quality": 5
                }},
                "recommendation": "GOOD SETUP"
            }},
            "overall_signal": {{
                "signal": "BUY/SELL/HOLD/WAIT",
                "confidence": 0.75,
                "reason": "Alasan dengan konfirmasi indikator"
            }},
            "entry_confirmation": {{
                "candlestick_pattern": "Hammer/Engulfing/Doji/None",
                "volume_confirmation": true/false,
                "momentum_confirmation": true/false,
                "trend_alignment": true/false,
                "ready_to_enter": true/false
            }},
            "entries": [
                {{
                    "level": 50000.1234,
                    "weight": 0.6,
                    "risk_score": 2,
                    "distance_from_current": "0.8%",
                    "description": "Entry MAKSIMAL 1-2 entry saja, fokus kualitas"
                }}
            ],
            "take_profits": [
                {{
                    "level": 51000.3456,
                    "reward_ratio": 2.0,
                    "percentage_gain": 2.0,
                    "description": "TP1 - Conservative target"
                }},
                {{
                    "level": 52000.7890,
                    "reward_ratio": 3.0,
                    "percentage_gain": 4.0,
                    "description": "TP2 - Aggressive target"
                }}
            ],
            "stop_loss": {{
                "level": 48500.0000,
                "percentage": "1.5%",
                "reason": "Support invalidation dengan buffer"
            }},
            "invalidation_triggers": [
                "Close candle below entry -0.5%",
                "Volume drops below average",
                "BTC drops >3% while in position"
            ],
            "position_size": 0.03,
            "risk_per_trade": 0.015,
            "risk_reward_ratio": 2.5,
            "probability_of_success": 0.70,
            "expected_return": 0.03,
            "market_conditions": "Asumsikan volatilitas sedang",
            "confluence_factors": [
                "RSI oversold + divergence",
                "Support level tested 2x",
                "Volume spike pada rejection"
            ],
            "notes": [
                "TUNGGU konfirmasi candle close",
                "Masuk gradual, bukan all-in",
                "SL wajib, jangan diubah"
            ],
            "warnings": [
                "HINDARI entry jika candle belum close",
                "PATIENCE - tunggu konfirmasi penuh",
                "NO FOMO - skip jika terlewat"
            ]
        }}

        ⚠️ CRITICAL RULES (WAJIB):
        1. MAKSIMAL 1-2 ENTRY ONLY (Quality over quantity)
        2. Entry harus ada MINIMAL 2 confirmations:
           - Candlestick pattern (hammer, engulfing, doji)
           - Volume spike (>1.5x average)
           - Indicator alignment (RSI + MACD)
        3. Risk/Reward minimal 1:2
        4. Entry tidak boleh >1.5% dari current price
        5. Stop loss maximal 1.5% from entry
        6. Jika tidak ada confluence yang jelas -> RETURN HOLD
        7. Jika market choppy (ADX<20) -> RETURN HOLD
        8. Jika volume rendah -> RETURN HOLD

        📌 CONTOH 1: HIGH QUALITY LONG SETUP
        {{
            "trend": "BULLISH",
            "quality_score": {{"overall": 8.0, "confluence_count": 3}},
            "overall_signal": {{
                "signal": "BUY",
                "confidence": 0.80,
                "reason": "3 confluence: Support tested 2x + Hammer candle + RSI oversold bounce"
            }},
            "entry_confirmation": {{
                "candlestick_pattern": "Hammer",
                "volume_confirmation": true,
                "momentum_confirmation": true,
                "ready_to_enter": true
            }},
            "entries": [
                {{"level": 98000.5000, "weight": 1.0, "distance": "0.6%"}}
            ],
            "take_profits": [
                {{"level": 99500.0000, "reward_ratio": 2.0}},
                {{"level": 101000.0000, "reward_ratio": 3.0}}
            ],
            "stop_loss": {{"level": 97200.0000, "percentage": "0.8%"}},
            "risk_reward_ratio": 2.5,
            "probability_of_success": 0.75,
            "confluence_factors": [
                "Support level tested twice",
                "Hammer rejection candle",
                "RSI bounced from oversold",
                "Volume above average"
            ]
        }}

        📌 CONTOH 2: HIGH QUALITY SHORT SETUP
        {{# Asumsikan current price = $93,500, resistance dekat $94,000 #}}
        {{
            "trend": "BEARISH",
            "quality_score": {{"overall": 8.5, "confluence_count": 3}},
            "overall_signal": {{
                "signal": "SELL",
                "confidence": 0.75,
                "reason": "3 confluence: Resistance tested 2x + Shooting Star candle + RSI overbought rejection"
            }},
            "entry_confirmation": {{
                "candlestick_pattern": "Shooting Star",
                "volume_confirmation": true,
                "momentum_confirmation": true,
                "ready_to_enter": true
            }},
            "entries": [
                {{"level": 94000.0000, "weight": 0.7, "distance": "0.5%"}},
                {{"level": 93850.0000, "weight": 0.3, "distance": "0.4%"}}
            ],
            "take_profits": [
                {{"level": 92800.0000, "reward_ratio": 2.0}},
                {{"level": 91800.0000, "reward_ratio": 3.5}}
            ],
            "stop_loss": {{"level": 94800.0000, "percentage": "1.0%"}},
            "risk_reward_ratio": 2.0,
            "probability_of_success": 0.70,
            "confluence_factors": [
                "Resistance level tested twice",
                "Shooting Star rejection candle",
                "RSI rejected from overbought",
                "Volume above average"
            ]
        }}

        📌 CONTOH 3: LOW QUALITY - RETURN HOLD
        {{
            "trend": "SIDEWAYS",
            "quality_score": {{"overall": 4.0, "confluence_count": 1}},
            "overall_signal": {{
                "signal": "HOLD",
                "confidence": 0.40,
                "reason": "Choppy market, ADX 18, no clear confluence, low volume"
            }},
            "notes": ["Wait for better setup", "Market tidak menarik untuk trade"]
        }}

        ⚠️ CRITICAL SHORT ENTRY RULES:
        - Untuk SELL/SHORT signal: Entry level harus DI ATAS current price (tunggu retrace ke resistance)
        - Contoh: Current price $93,800 → Entry di $94,000 atau $94,200 (di atas current price!)
        - Logika: Kita tunggu harga naik sedikit ke level resistance untuk entry short dengan harga lebih baik
        - Take Profit harus DI BAWAH entry price (untuk profit dari harga turun)
        - Stop Loss harus DI ATAS entry price (untuk proteksi jika harga naik terus)

        Risk Profile: {request.risk_profile.upper()}

        SEKARANG TUGAS ANDA:
        1. CEK semua quality filters di atas
        2. Jika tidak memenuhi minimal 2 confluence -> RETURN HOLD
        3. Jika memenuhi, buat plan dengan MAKSIMAL 2 ENTRY
        4. Fokus pada KUALITAS, bukan kuantitas

        RESPOND HANYA DENGAN JSON, TANPA TEKS LAINNYA.
        """
        
        return prompt
    
    # ============ TECHNICAL CALCULATIONS ============
    def _calculate_support_levels(self, df: pd.DataFrame, num_levels: int = 5) -> List[float]:
        """Calculate support levels"""
        if len(df) < 50:
            return []
        
        # Recent lows
        recent_lows = df['low'].tail(100).values
        # Use clustering to find significant levels
        from sklearn.cluster import KMeans
        if len(recent_lows) >= num_levels:
            kmeans = KMeans(n_clusters=num_levels, random_state=42)
            kmeans.fit(recent_lows.reshape(-1, 1))
            centers = sorted(kmeans.cluster_centers_.flatten().tolist())
            return [float(c) for c in centers]
        return []
    
    def _calculate_resistance_levels(self, df: pd.DataFrame, num_levels: int = 5) -> List[float]:
        """Calculate resistance levels"""
        if len(df) < 50:
            return []
        
        recent_highs = df['high'].tail(100).values
        from sklearn.cluster import KMeans
        if len(recent_highs) >= num_levels:
            kmeans = KMeans(n_clusters=num_levels, random_state=42)
            kmeans.fit(recent_highs.reshape(-1, 1))
            centers = sorted(kmeans.cluster_centers_.flatten().tolist())
            return [float(c) for c in centers]
        return []
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        if len(df) < period:
            return 50.0
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _calculate_macd(self, df: pd.DataFrame) -> tuple:
        """Calculate MACD"""
        if len(df) < 26:
            return 0.0, 0.0

        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return float(macd.iloc[-1]), float(signal.iloc[-1])

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)"""
        if len(df) < period * 2:
            return 25.0  # Default moderate value

        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # Calculate smoothed TR, +DM, -DM
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 25.0

    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        """Quick trend analysis for a timeframe"""
        current_price = float(df['close'].iloc[-1])

        # Calculate SMA 20
        if len(df) >= 20:
            sma_20 = df['close'].rolling(window=20).mean().iloc[-1]
            sma_trend = "ABOVE SMA" if current_price > sma_20 else "BELOW SMA"
        else:
            sma_trend = "INSUFFICIENT DATA"

        # Determine trend based on price action
        if len(df) >= 10:
            recent_highs = df['high'].tail(10).max()
            recent_lows = df['low'].tail(10).min()

            if current_price > (recent_highs + recent_lows) / 2:
                trend = "BULLISH"
            elif current_price < (recent_highs + recent_lows) / 2:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"
        else:
            trend = "SIDEWAYS"

        # Determine momentum using RSI
        rsi = self._calculate_rsi(df)
        if rsi > 60:
            momentum = "STRONG" if trend == "BULLISH" else "WEAK"
        elif rsi < 40:
            momentum = "STRONG" if trend == "BEARISH" else "WEAK"
        else:
            momentum = "NEUTRAL"

        # Create summary
        summary = f"{trend} - Price {sma_trend}, Momentum {momentum}"

        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            current_price=current_price,
            sma_trend=sma_trend,
            momentum=momentum,
            summary=summary
        )

    def _get_multi_timeframe_data(self, request: AnalysisRequest) -> List[TimeframeAnalysis]:
        """Get data from multiple timeframes for confluence analysis"""
        mtf_data = []

        if not request.include_multi_timeframe:
            return mtf_data

        # Define timeframe hierarchy (CONSERVATIVE - avoid 30m/15m for lower timeframes)
        # Removed 30m/15m for 4h and below to reduce signal volatility
        timeframe_map = {
            '1m': [],
            '5m': ['1m'],
            '15m': [],  # 15m too volatile for multi-TF
            '30m': [],  # 30m too volatile for multi-TF
            '1h': [],  # 1h is the lowest for reliable multi-TF
            '2h': ['1h'],  # Only 1H lower TF
            '4h': ['1h'],  # Only 1H lower TF (removed 30m/15m - too volatile!)
            '1d': ['4h', '1h']  # Daily: 4H + 1H only (removed 30m)
        }

        additional_timeframes = timeframe_map.get(request.timeframe, [])

        for tf in additional_timeframes:
            try:
                # Fetch 20 candles for additional timeframes (trend summary only)
                # Use user's preferred exchange, fallback to other if unavailable
                preferred_exchange = request.preferred_exchange.lower()
                fallback_exchange = "binance" if preferred_exchange == "bybit" else "bybit"

                # Try preferred exchange first
                if preferred_exchange == "binance":
                    df_tf = self.collector.get_binance_klines_auto(
                        symbol=request.symbol,
                        interval=tf,
                        limit=20
                    )
                else:  # bybit
                    df_tf = self.collector.get_bybit_klines(
                        symbol=request.symbol,
                        interval=tf,
                        limit=20
                    )

                # Fallback to other exchange if preferred fails
                if df_tf is None or len(df_tf) < 10:
                    if fallback_exchange == "binance":
                        df_tf = self.collector.get_binance_klines_auto(
                            symbol=request.symbol,
                            interval=tf,
                            limit=20
                        )
                    else:  # bybit
                        df_tf = self.collector.get_bybit_klines(
                            symbol=request.symbol,
                            interval=tf,
                            limit=20
                        )

                if df_tf is not None and len(df_tf) >= 10:
                    analysis = self._analyze_timeframe(df_tf, tf)
                    mtf_data.append(analysis)
                    logger.info(f"Analyzed {tf} timeframe for {request.symbol}")

            except Exception as e:
                logger.warning(f"Failed to analyze {tf} timeframe: {e}")
                continue

        return mtf_data

    # ============ GENERATE TRADING PLAN ============
    def generate_trading_plan(self, request: AnalysisRequest) -> TradingPlan:
        """
        Generate complete trading plan
        """
        start_time = time.time()

        try:
            # Rate limit
            self._rate_limit()

            # Get data
            logger.info(f"Generating trading plan for {request.symbol} ({request.timeframe})...")

            # Use user's preferred exchange, fallback to other if unavailable
            preferred_exchange = request.preferred_exchange.lower()
            fallback_exchange = "binance" if preferred_exchange == "bybit" else "bybit"

            # Try preferred exchange first
            if preferred_exchange == "binance":
                df = self.collector.get_binance_klines_auto(
                    symbol=request.symbol,
                    interval=request.timeframe,
                    limit=request.data_points
                )
            else:  # bybit
                df = self.collector.get_bybit_klines(
                    symbol=request.symbol,
                    interval=request.timeframe,
                    limit=min(request.data_points, 200)
                )

            # Fallback to other exchange if preferred fails
            if df is None or len(df) < 20:
                logger.info(f"{preferred_exchange.capitalize()} data unavailable for {request.symbol}, trying {fallback_exchange.capitalize()}...")
                if fallback_exchange == "binance":
                    df = self.collector.get_binance_klines_auto(
                        symbol=request.symbol,
                        interval=request.timeframe,
                        limit=request.data_points
                    )
                else:  # bybit
                    df = self.collector.get_bybit_klines(
                        symbol=request.symbol,
                        interval=request.timeframe,
                        limit=min(request.data_points, 200)
                    )

            if df is None or len(df) < 20:
                raise ValueError(f"Insufficient data for {request.symbol}")

            # Calculate indicators for scalping check
            rsi = self._calculate_rsi(df)
            adx = self._calculate_adx(df)

            # Check for scalping opportunity if enabled
            scalping_info = None
            if request.enable_scalping:
                scalping_info = self._check_scalping_opportunity(df, rsi, adx)
                logger.info(f"Scalping check for {request.symbol}: {scalping_info}")

            # Get multi-timeframe data
            mtf_data = self._get_multi_timeframe_data(request)
            logger.info(f"Collected {len(mtf_data)} additional timeframe(s) for analysis")

            # Create prompt with scalping info if applicable
            prompt = self._create_trading_plan_prompt(df, request, mtf_data, scalping_info)
            
            # Prepare API request
            payload = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional cryptocurrency trading analyst. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": 0.3,  # Lower temperature untuk konsistensi
                "response_format": {"type": "json_object"}
            }
            
            # Send request
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code}")
            
            result_data = response.json()
            plan_json = json.loads(result_data['choices'][0]['message']['content'])
            
            # Convert to TradingPlan object
            trading_plan = self._parse_trading_plan_json(plan_json, df, request)
            trading_plan.raw_analysis = result_data['choices'][0]['message']['content']
            
            logger.info(f"Trading plan generated in {time.time() - start_time:.2f}s")
            return trading_plan
            
        except Exception as e:
            logger.error(f"Failed to generate trading plan: {e}")
            # Return minimal plan
            return self._create_minimal_plan(request, str(e))
    
    def _parse_trading_plan_json(self, plan_data: Dict, df: pd.DataFrame, 
                                request: AnalysisRequest) -> TradingPlan:
        """Parse JSON response to TradingPlan object"""
        
        # Create signal
        signal_data = plan_data.get('overall_signal', {})
        signal = TradingSignal(
            signal_type=signal_data.get('signal', 'HOLD'),
            confidence=signal_data.get('confidence', 0.5),
            reason=signal_data.get('reason', ''),
            timestamp=datetime.now()
        )
        
        # Create entries
        entries = []
        for entry_data in plan_data.get('entries', []):
            entry = EntryPoint(
                level=entry_data.get('level', 0.0),
                weight=entry_data.get('weight', 0.0),
                risk_score=entry_data.get('risk_score', 5),
                description=entry_data.get('description', '')
            )
            entries.append(entry)
        
        # Create take profits
        take_profits = []
        for tp_data in plan_data.get('take_profits', []):
            tp = TakeProfit(
                level=tp_data.get('level', 0.0),
                reward_ratio=tp_data.get('reward_ratio', 1.0),
                percentage_gain=tp_data.get('percentage_gain', 0.0),
                description=tp_data.get('description', '')
            )
            take_profits.append(tp)
        
        # Calculate primary entry
        primary_entry = None
        if entries:
            # Pilih entry dengan weight tertinggi
            primary_entry = max(entries, key=lambda x: x.weight).level

        # Get current price from latest candle
        current_price = float(df['close'].iloc[-1])

        # Calculate signal expiration based on timeframe
        # 1h timeframe = 3 hours valid, 4h timeframe = 6 hours valid
        timeframe_hours = {
            '1h': 3,
            '2h': 4,
            '4h': 6,
            '1d': 12
        }
        valid_hours = timeframe_hours.get(request.timeframe, 6)
        expires_at = datetime.now() + timedelta(hours=valid_hours)

        # Safely extract stop_loss data
        stop_loss_data = plan_data.get('stop_loss')
        if isinstance(stop_loss_data, dict):
            stop_loss = stop_loss_data.get('level', 0.0)
            stop_loss_reason = stop_loss_data.get('reason', '')
        else:
            stop_loss = 0.0
            stop_loss_reason = ''

        # Create trading plan
        plan = TradingPlan(
            symbol=plan_data.get('symbol', request.symbol),
            timeframe=plan_data.get('timeframe', request.timeframe),
            generated_at=datetime.now(),
            current_price=current_price,
            trend=plan_data.get('trend', 'SIDEWAYS'),
            overall_signal=signal,
            entries=entries,
            primary_entry=primary_entry,
            take_profits=take_profits,
            stop_loss=stop_loss,
            stop_loss_reason=stop_loss_reason,
            position_size=plan_data.get('position_size', 0.02),
            risk_per_trade=plan_data.get('risk_per_trade', 0.02),
            max_drawdown=plan_data.get('max_drawdown', 0.1),
            support_levels=plan_data.get('support_levels', []),
            resistance_levels=plan_data.get('resistance_levels', []),
            indicators={},  # Will be populated from data
            market_conditions=plan_data.get('market_conditions', ''),
            timeframe_analysis={},
            risk_reward_ratio=plan_data.get('risk_reward_ratio', 1.5),
            probability_of_success=plan_data.get('probability_of_success', 0.5),
            expected_return=plan_data.get('expected_return', 0.0),
            notes=plan_data.get('notes', []),
            warnings=plan_data.get('warnings', []),
            raw_analysis="",
            expires_at=expires_at
        )

        return plan
    
    def _create_minimal_plan(self, request: AnalysisRequest, error_msg: str) -> TradingPlan:
        """Create minimal plan when generation fails"""
        current_time = datetime.now()
        
        signal = TradingSignal(
            signal_type="HOLD",
            confidence=0.0,
            reason=f"Error: {error_msg}",
            timestamp=current_time
        )
        
        return TradingPlan(
            symbol=request.symbol,
            timeframe=request.timeframe,
            generated_at=current_time,
            current_price=0.0,  # Unknown since error occurred
            trend="UNKNOWN",
            overall_signal=signal,
            entries=[],
            take_profits=[],
            stop_loss=0.0,
            stop_loss_reason="N/A",
            position_size=0.0,
            risk_per_trade=0.0,
            max_drawdown=0.0,
            support_levels=[],
            resistance_levels=[],
            indicators={},
            market_conditions="Analysis failed",
            timeframe_analysis={},
            risk_reward_ratio=0.0,
            probability_of_success=0.0,
            expected_return=0.0,
            notes=[f"Error occurred: {error_msg}"],
            warnings=["Do not trade based on this plan"]
        )
    
    # ============ VISUALIZATION & OUTPUT ============
    def print_trading_plan(self, plan: TradingPlan):
        """Print trading plan in beautiful format"""
        print("\n" + "="*70)
        print(f"🎯 TRADING PLAN - {plan.symbol} ({plan.timeframe})")
        print("="*70)
        
        # Header
        print(f"\n📊 GENERATED: {plan.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 TREND: {plan.trend}")
        print(f"🚦 SIGNAL: {plan.overall_signal.signal_type} "
              f"(Confidence: {plan.overall_signal.confidence:.1%})")
        print(f"💡 REASON: {plan.overall_signal.reason}")
        
        # Current Price (if available)
        if hasattr(plan, 'current_price'):
            print(f"💰 CURRENT PRICE: ${plan.current_price:.2f}")
        
        # Entries Section
        print(f"\n{'='*40}")
        print("🎯 ENTRY POINTS")
        print(f"{'='*40}")
        
        if plan.entries:
            for i, entry in enumerate(plan.entries, 1):
                print(f"\n📍 ENTRY {i}:")
                print(f"   Price: ${entry.level:,.2f}")
                print(f"   Weight: {entry.weight:.0%} of position")
                print(f"   Risk Score: {entry.risk_score}/10")
                print(f"   Description: {entry.description}")
        else:
            print("   No entry points defined")
        
        # Take Profits Section
        print(f"\n{'='*40}")
        print("🎯 TAKE PROFIT TARGETS")
        print(f"{'='*40}")
        
        if plan.take_profits:
            # Calculate from primary entry if available
            base_price = plan.primary_entry if plan.primary_entry else plan.entries[0].level if plan.entries else 0
            
            for i, tp in enumerate(plan.take_profits, 1):
                gain_pct = ((tp.level - base_price) / base_price * 100) if base_price > 0 else 0
                
                print(f"\n✅ TP{i}:")
                print(f"   Target: ${tp.level:,.2f}")
                print(f"   R/R Ratio: 1:{tp.reward_ratio:.1f}")
                print(f"   Gain: {gain_pct:.1f}% from entry")
                print(f"   Description: {tp.description}")
        else:
            print("   No take profit targets defined")
        
        # Stop Loss
        print(f"\n{'='*40}")
        print("🛑 STOP LOSS")
        print(f"{'='*40}")
        
        if plan.stop_loss > 0:
            if plan.primary_entry:
                loss_pct = abs((plan.stop_loss - plan.primary_entry) / plan.primary_entry * 100)
                print(f"   Level: ${plan.stop_loss:,.2f}")
                print(f"   Loss: {loss_pct:.1f}% from entry")
            else:
                print(f"   Level: ${plan.stop_loss:,.2f}")
            print(f"   Reason: {plan.stop_loss_reason}")
        else:
            print("   No stop loss defined")
        
        # Risk Management
        print(f"\n{'='*40}")
        print("📊 RISK MANAGEMENT")
        print(f"{'='*40}")
        
        print(f"   Position Size: {plan.position_size:.1%}")
        print(f"   Risk per Trade: {plan.risk_per_trade:.1%}")
        print(f"   Max Drawdown: {plan.max_drawdown:.1%}")
        print(f"   Risk/Reward Ratio: 1:{plan.risk_reward_ratio:.1f}")
        print(f"   Probability of Success: {plan.probability_of_success:.1%}")
        print(f"   Expected Return: {plan.expected_return:.1%}")
        
        # Support & Resistance
        print(f"\n{'='*40}")
        print("📈 SUPPORT & RESISTANCE")
        print(f"{'='*40}")
        
        if plan.support_levels:
            print(f"   Support Levels:")
            for i, level in enumerate(plan.support_levels[:3], 1):
                print(f"     S{i}: ${level:,.2f}")
        
        if plan.resistance_levels:
            print(f"   Resistance Levels:")
            for i, level in enumerate(plan.resistance_levels[:3], 1):
                print(f"     R{i}: ${level:,.2f}")
        
        # Market Conditions
        print(f"\n{'='*40}")
        print("🌐 MARKET CONDITIONS")
        print(f"{'='*40}")
        print(f"   {plan.market_conditions}")
        
        # Notes
        if plan.notes:
            print(f"\n{'='*40}")
            print("📝 IMPORTANT NOTES")
            print(f"{'='*40}")
            for note in plan.notes:
                print(f"   • {note}")
        
        # Warnings
        if plan.warnings:
            print(f"\n{'='*40}")
            print("⚠️  WARNINGS")
            print(f"{'='*40}")
            for warning in plan.warnings:
                print(f"   ⚠ {warning}")
        
        print(f"\n{'='*70}")
        print("✅ TRADING PLAN COMPLETE")
        print(f"{'='*70}")
    
    def save_trading_plan(self, plan: TradingPlan, filename: str = None):
        """Save trading plan to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_plan_{plan.symbol}_{timestamp}.json"
        
        filepath = config.DATA_DIR / "trading_plans" / filename
        filepath.parent.mkdir(exist_ok=True)
        
        # Convert to dict
        plan_dict = {
            "symbol": plan.symbol,
            "timeframe": plan.timeframe,
            "generated_at": plan.generated_at.isoformat(),
            "trend": plan.trend,
            "overall_signal": {
                "signal": plan.overall_signal.signal_type,
                "confidence": plan.overall_signal.confidence,
                "reason": plan.overall_signal.reason,
                "timestamp": plan.overall_signal.timestamp.isoformat()
            },
            "entries": [
                {
                    "level": entry.level,
                    "weight": entry.weight,
                    "risk_score": entry.risk_score,
                    "description": entry.description
                }
                for entry in plan.entries
            ],
            "take_profits": [
                {
                    "level": tp.level,
                    "reward_ratio": tp.reward_ratio,
                    "percentage_gain": tp.percentage_gain,
                    "description": tp.description
                }
                for tp in plan.take_profits
            ],
            "stop_loss": {
                "level": plan.stop_loss,
                "reason": plan.stop_loss_reason
            },
            "position_size": plan.position_size,
            "risk_per_trade": plan.risk_per_trade,
            "max_drawdown": plan.max_drawdown,
            "support_levels": plan.support_levels,
            "resistance_levels": plan.resistance_levels,
            "risk_reward_ratio": plan.risk_reward_ratio,
            "probability_of_success": plan.probability_of_success,
            "expected_return": plan.expected_return,
            "market_conditions": plan.market_conditions,
            "notes": plan.notes,
            "warnings": plan.warnings,
            "raw_analysis": plan.raw_analysis
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Trading plan saved to {filepath}")
        return filepath
    
    def export_to_csv(self, plan: TradingPlan):
        """Export trading plan to CSV format"""
        import csv
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trading_plan_{plan.symbol}_{timestamp}.csv"
        filepath = config.DATA_DIR / "trading_plans" / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(["TRADING PLAN", plan.symbol, plan.timeframe])
            writer.writerow(["Generated", plan.generated_at])
            writer.writerow([])
            
            # Signal
            writer.writerow(["SIGNAL", "CONFIDENCE", "REASON"])
            writer.writerow([
                plan.overall_signal.signal_type,
                f"{plan.overall_signal.confidence:.1%}",
                plan.overall_signal.reason
            ])
            writer.writerow([])
            
            # Entries
            writer.writerow(["ENTRY POINTS", "PRICE", "WEIGHT", "RISK SCORE", "DESCRIPTION"])
            for i, entry in enumerate(plan.entries, 1):
                writer.writerow([
                    f"ENTRY {i}",
                    f"${entry.level:,.2f}",
                    f"{entry.weight:.0%}",
                    entry.risk_score,
                    entry.description
                ])
            writer.writerow([])
            
            # Take Profits
            writer.writerow(["TAKE PROFITS", "TARGET", "R/R", "GAIN%", "DESCRIPTION"])
            for i, tp in enumerate(plan.take_profits, 1):
                writer.writerow([
                    f"TP{i}",
                    f"${tp.level:,.2f}",
                    f"1:{tp.reward_ratio:.1f}",
                    f"{tp.percentage_gain:.1f}%",
                    tp.description
                ])
            writer.writerow([])
            
            # Stop Loss
            writer.writerow(["STOP LOSS", "LEVEL", "REASON"])
            writer.writerow([
                "SL",
                f"${plan.stop_loss:,.2f}",
                plan.stop_loss_reason
            ])
        
        logger.info(f"Trading plan exported to CSV: {filepath}")
        return filepath

# ============ QUICK SCREENING GENERATOR ============
async def generate_quick_screening(
    symbol: str,
    timeframe: str,
    indicators: Dict[str, Any],
    current_price: float
) -> Dict[str, Any]:
    """
    Generate quick screening result for a coin
    Faster than full trading plan, used for market screening
    """
    import asyncio

    try:
        # Create simple screening prompt
        prompt = f"""
        Anda adalah LENIENT MARKET SCREENER untuk cryptocurrency.

        Buat QUICK SCREENING untuk {symbol} pada timeframe {timeframe}.

        DATA TEKNIKAL:
        - Current Price: ${current_price:.8f}
        - RSI: {indicators.get('rsi', 50):.2f}
        - MACD: {indicators.get('macd', 0):.4f}
        - EMA 20: {indicators.get('ema_20', 0):.8f}
        - EMA 50: {indicators.get('ema_50', 0):.8f}
        - EMA 200: {indicators.get('ema_200', 0):.8f}
        - Volume 24h: ${indicators.get('volume_24h', 0):,.0f}

        BERIKAN SCORE DALAM FORMAT JSON:
        {{
            "score": 6.0,
            "trend": "BULLISH",
            "signals": [
                "Price near EMA 20 support",
                "Momentum building up",
                "Good volume presence"
            ],
            "analysis": "Decent setup, worth monitoring for potential entry"
        }}

        SCORING CRITERIA (LEBIH LONGGAR - 0-10):
        - Trend Direction (bukan harus strong, cukup ada arah): 2 points
        - EMA Position (harga dekat atau di atas EMA short-term): 2 points
        - Basic Momentum (RSI tidak extreme <30 atau >70): 2 points
        - Volume presence (ada aktivitas trading): 2 points
        - Price action (ada pembentukan level interesting): 2 points

        CATATAN PENTING:
        - Screening ini LEBIH LONGGAR dari trading plan AI
        - Tidak harus perfect setup, cukup "menarik untuk di-review"
        - Score 5.0+ sudah cukup untuk di-include dalam hasil screening
        - Fokus: temukan POTENTIAL coins, bukan CONFIRMED setups
        - Lebih baik banyak coin medium quality daripada sedikit coin perfect

        RESPOND HANYA DENGAN JSON, TANPA TEKS LAINNYA.
        """

        # Make API request
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {config.DEEPSEEK.api_key}",
            "Content-Type": "application/json"
        })

        payload = {
            "model": config.DEEPSEEK.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency market screener. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 500,
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        # Run in thread pool to avoid blocking
        response = await asyncio.to_thread(
            session.post,
            f"{config.DEEPSEEK.base_url}/chat/completions",
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"API Error for {symbol}: {response.status_code}")
            return _create_fallback_screening(symbol, current_price)

        result_data = response.json()
        screening_json = json.loads(result_data['choices'][0]['message']['content'])

        return screening_json

    except Exception as e:
        logger.error(f"Error generating quick screening for {symbol}: {e}")
        return _create_fallback_screening(symbol, current_price)


def _create_fallback_screening(symbol: str, current_price: float) -> Dict[str, Any]:
    """Create fallback screening when AI fails"""
    return {
        "score": 5.0,
        "trend": "NEUTRAL",
        "signals": ["Unable to analyze"],
        "analysis": "Analysis failed, manual review needed"
    }


# ============ EXAMPLE USAGE ============
def main():
    """Example of generating and displaying trading plan"""
    logging.basicConfig(level=logging.INFO)

    print("🚀 TRADING PLAN GENERATOR")
    print("="*60)

    # Initialize generator
    generator = TradingPlanGenerator()

    # Create analysis request
    request = AnalysisRequest(
        symbol="BTCUSDT",
        timeframe="4h",
        data_points=200,
        analysis_type="trading_plan",
        risk_profile="moderate"
    )

    # Generate trading plan
    print(f"\n📊 Generating trading plan for {request.symbol}...")
    trading_plan = generator.generate_trading_plan(request)

    # Print trading plan
    generator.print_trading_plan(trading_plan)

    # Save to files
    json_file = generator.save_trading_plan(trading_plan)
    csv_file = generator.export_to_csv(trading_plan)

    print(f"\n💾 Files saved:")
    print(f"   JSON: {json_file}")
    print(f"   CSV: {csv_file}")

    # Display simple summary
    print(f"\n📋 QUICK SUMMARY:")
    print(f"   Signal: {trading_plan.overall_signal.signal_type}")
    print(f"   Entries: {len(trading_plan.entries)} points")
    print(f"   Take Profits: {len(trading_plan.take_profits)} targets")
    print(f"   Stop Loss: ${trading_plan.stop_loss:,.2f}")
    print(f"   Risk/Reward: 1:{trading_plan.risk_reward_ratio:.1f}")

if __name__ == "__main__":
    main()