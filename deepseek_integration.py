"""
DEEPSEEK TRADING PLAN GENERATOR
Output terstruktur untuk trading plan lengkap
"""

import requests
import json
import time
from datetime import datetime
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
    
    # ============ TRADING PLAN PROMPT ============
    def _create_trading_plan_prompt(self, df: pd.DataFrame, request: AnalysisRequest) -> str:
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

        prompt = f"""
        Anda adalah TRADING PLAN SPECIALIST dengan spesialisasi cryptocurrency.

        BUATKAN TRADING PLAN LENGKAP untuk {request.symbol} pada timeframe {request.timeframe}.

        DATA TEKNIKAL SAAT INI:
        - Current Price: {price_format}
        - 24h High: ${high_24h:.{price_precision}f}
        - 24h Low: ${low_24h:.{price_precision}f}
        - Support Levels: {', '.join([f'${s:.{price_precision}f}' for s in support_levels[:3]])}
        - Resistance Levels: {', '.join([f'${r:.{price_precision}f}' for r in resistance_levels[:3]])}
        - RSI (14): {rsi:.2f}
        - MACD: {macd:.4f}, Signal: {signal:.4f}

        FORMAT OUTPUT YANG DIHARAPKAN (WAJIB DALAM JSON):
        {{
            "symbol": "{request.symbol}",
            "timeframe": "{request.timeframe}",
            "trend": "BULLISH/BEARISH/SIDEWAYS",
            "overall_signal": {{
                "signal": "BUY/SELL/HOLD",
                "confidence": 0.85,
                "reason": "Alasan singkat"
            }},
            "entries": [
                {{
                    "level": 50000.1234,
                    "weight": 0.4,
                    "risk_score": 2,
                    "description": "Entry pertama pada support kuat"
                }},
                {{
                    "level": 49500.5678,
                    "weight": 0.4,
                    "risk_score": 3,
                    "description": "Entry kedua jika retest support"
                }},
                {{
                    "level": 49000.9012,
                    "weight": 0.2,
                    "risk_score": 5,
                    "description": "Entry agresif jika breakdown"
                }}
            ],
            "take_profits": [
                {{
                    "level": 51000.3456,
                    "reward_ratio": 1.5,
                    "percentage_gain": 2.0,
                    "description": "TP1 - Resistance minor"
                }},
                {{
                    "level": 52000.7890,
                    "reward_ratio": 2.0,
                    "percentage_gain": 4.0,
                    "description": "TP2 - Resistance utama"
                }},
                {{
                    "level": 53000.1234,
                    "reward_ratio": 3.0,
                    "percentage_gain": 6.0,
                    "description": "TP3 - Target Fibonacci"
                }}
            ],
            "stop_loss": {{
                "level": 48500.0000,
                "reason": "Di bawah support kunci"
            }},
            "position_size": 0.05,
            "risk_per_trade": 0.02,
            "max_drawdown": 0.1,
            "support_levels": [50000.1234, 49500.5678, 49000.9012],
            "resistance_levels": [51000.3456, 52000.7890, 53000.1234],
            "risk_reward_ratio": 2.5,
            "probability_of_success": 0.65,
            "expected_return": 0.04,
            "market_conditions": "Kondisi pasar saat ini...",
            "notes": [
                "Monitor volume breakout",
                "Perhatikan news FOMC besok",
                "BTC dominance sedang naik"
            ],
            "warnings": [
                "Hindari trade jika volume rendah",
                "SL wajib dipasang"
            ]
        }}

        INSTRUKSI SPESIFIK:
        1. Tentukan DIRECTION: LONG (BUY) atau SHORT (SELL) berdasarkan analisis teknikal
        2. Jika signal = BUY/LONG:
           - Entry levels harus DI BAWAH current price (buy saat dip)
           - Take profit levels harus DI ATAS entry (jual saat profit)
           - Stop loss harus DI BAWAH entry
        3. Jika signal = SELL/SHORT:
           - Entry levels harus DI ATAS current price (short saat mahal)
           - Take profit levels harus DI BAWAH entry (buyback saat profit)
           - Stop loss harus DI ATAS entry
        4. Berikan 2-3 ENTRY POINT dengan weighting yang jelas
        5. Berikan 3 TAKE PROFIT LEVEL dengan Risk/Reward ratio
        6. Tentukan STOP LOSS yang jelas dengan alasan
        7. Hitung Risk/Reward Ratio minimal 1:1.5
        8. Berikan probability of success berdasarkan data
        9. Sertakan analisis kondisi pasar
        10. Berikan catatan dan peringatan penting

        ⚠️ PENTING - DIRECTION & POSITION:
        - Signal BUY = Long position (expecting price to go UP)
          * Entry: Buy at lower prices
          * TP: Sell at higher prices
          * SL: Below entry

        - Signal SELL = Short position (expecting price to go DOWN)
          * Entry: Short/sell at higher prices
          * TP: Buy back at lower prices
          * SL: Above entry

        ⚠️ PENTING - PRECISION REQUIREMENT:
        - Gunakan minimal 4-6 angka di belakang koma untuk semua level harga
        - Contoh yang BENAR: 1.6425, 1.5987, 1.5532
        - Contoh yang SALAH: 1.64, 1.60, 1.55
        - Ini sangat penting untuk akurasi trading plan

        CONTEMPLATE CONTOH TRADING PLAN:

        📌 CONTOH 1: LONG POSITION (BUY Signal)
        {{
            "trend": "BULLISH",
            "overall_signal": {{
                "signal": "BUY",
                "confidence": 0.85,
                "reason": "Strong bounce dari support, RSI oversold"
            }},
            "entries": [
                {{"level": 98000.5000, "weight": 0.5, "description": "Entry utama di support"}},
                {{"level": 97500.2500, "weight": 0.3, "description": "Entry tambahan jika dip"}}
            ],
            "take_profits": [
                {{"level": 99000.0000, "reward_ratio": 1.5, "description": "TP1 - Resistance minor"}},
                {{"level": 100000.0000, "reward_ratio": 2.5, "description": "TP2 - Resistance utama"}}
            ],
            "stop_loss": {{
                "level": 97000.0000,
                "reason": "Di bawah support kunci"
            }}
        }}

        📌 CONTOH 2: SHORT POSITION (SELL Signal)
        {{
            "trend": "BEARISH",
            "overall_signal": {{
                "signal": "SELL",
                "confidence": 0.75,
                "reason": "Rejection di resistance, RSI overbought, bearish divergence"
            }},
            "entries": [
                {{"level": 99500.0000, "weight": 0.5, "description": "Short di resistance kuat"}},
                {{"level": 100000.0000, "weight": 0.3, "description": "Short tambahan jika pump"}}
            ],
            "take_profits": [
                {{"level": 98500.0000, "reward_ratio": 1.5, "description": "TP1 - Support minor"}},
                {{"level": 97500.0000, "reward_ratio": 2.5, "description": "TP2 - Support utama"}}
            ],
            "stop_loss": {{
                "level": 100500.0000,
                "reason": "Di atas resistance, breakdown confirmation"
            }}
        }}

        Risk Profile: {request.risk_profile.upper()}

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

            if request.symbol.endswith('USDT'):
                # Use auto-detect to support both spot and futures
                df = self.collector.get_binance_klines_auto(
                    symbol=request.symbol,
                    interval=request.timeframe,
                    limit=request.data_points
                )
            else:
                df = self.collector.get_bybit_klines(
                    symbol=request.symbol,
                    interval=request.timeframe,
                    limit=min(request.data_points, 200)
                )
            
            if df is None or len(df) < 20:
                raise ValueError(f"Insufficient data for {request.symbol}")
            
            # Create prompt
            prompt = self._create_trading_plan_prompt(df, request)
            
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
            stop_loss=plan_data.get('stop_loss', {}).get('level', 0.0),
            stop_loss_reason=plan_data.get('stop_loss', {}).get('reason', ''),
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
            raw_analysis=""
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