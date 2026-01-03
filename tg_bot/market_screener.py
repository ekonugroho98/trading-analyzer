"""
Market Screener
Quick screening for coins with good market structure setup
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from collector import CryptoDataCollector
from deepseek_integration import generate_quick_screening

logger = logging.getLogger(__name__)


# Top 50 USDT pairs by volume (static list for demo)
TOP_USDT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT",
    "LINKUSDT", "SHIBUSDT", "LTCUSDT", "BCHUSDT", "UNIUSDT",
    "ATOMUSDT", "XLMUSDT", "ETCUSDT", "XMRUSDT", "AAVEUSDT",
    "MKRUSDT", "COMPUSDT", "SUSHIUSDT", "CRVUSDT", "YFIUSDT",
    "FILUSDT", "VETUSDT", "THETAUSDT", "ICPUSDT", "TRXUSDT",
    "EOSUSDT", "XEMUSDT", "NEOUSDT", "FTMUSDT", "KAVAUSDT",
    "ROSEUSDT", "AXSUSDT", "SANDUSDT", "MANAUSDT", "GALAUSDT",
    "ENJUSDT", "CHZUSDT", "SNXUSDT", "RUNEUSDT", "1INCHUSDT"
]


@dataclass
class ScreenResult:
    """Result from screening a coin"""
    symbol: str
    score: float
    signals: List[str]
    current_price: float
    volume_24h: float
    change_24h: float
    trend: str
    analysis: str


class MarketScreener:
    """Screen coins based on market structure and technical setup"""

    def __init__(self):
        """Initialize market screener"""
        self.collector = CryptoDataCollector()

    async def get_top_symbols(self, limit: int = 100) -> List[str]:
        """Get top USDT pairs by volume"""
        try:
            # Return static list for now
            # In production, you would fetch from Binance API
            symbols = TOP_USDT_PAIRS[:limit]

            logger.info(f"Retrieved {len(symbols)} top USDT pairs")
            return symbols

        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            return []

    async def screen_coin(
        self,
        symbol: str,
        timeframe: str = '4h'
    ) -> Optional[ScreenResult]:
        """Quick screen a single coin"""
        try:
            # Get historical data using collector
            df = self.collector.get_binance_klines_auto(
                symbol=symbol,
                interval=timeframe,
                limit=100
            )

            if df is None or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None

            # Get latest price and volume
            current_price = float(df['close'].iloc[-1])
            volume_24h = float(df['volume'].iloc[-1])

            # Calculate 24h change
            change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100

            # Simple indicators dict (calculate basic values from df)
            indicators = {
                'rsi': 50.0,  # Placeholder
                'macd': 0.0,
                'ema_20': float(df['close'].iloc[-1]),
                'ema_50': float(df['close'].iloc[-1]),
                'ema_200': float(df['close'].iloc[-1]),
                'volume_24h': volume_24h
            }

            # Quick AI screening
            screening = await generate_quick_screening(
                symbol=symbol,
                timeframe=timeframe,
                indicators=indicators,
                current_price=current_price
            )

            # Create result
            result = ScreenResult(
                symbol=symbol,
                score=screening.get('score', 0.0),
                signals=screening.get('signals', []),
                current_price=current_price,
                volume_24h=volume_24h,
                change_24h=change_24h,
                trend=screening.get('trend', 'NEUTRAL'),
                analysis=screening.get('analysis', '')
            )

            return result

        except Exception as e:
            logger.error(f"Error screening {symbol}: {e}")
            return None

    async def screen_market(
        self,
        timeframe: str = '4h',
        limit: int = 100,
        min_score: float = 7.0,
        max_results: int = 20
    ) -> List[ScreenResult]:
        """Screen market and return top coins"""
        try:
            # Get symbols to screen
            symbols = await self.get_top_symbols(limit)

            if not symbols:
                logger.error("No symbols to screen")
                return []

            logger.info(f"Screening {len(symbols)} symbols on {timeframe} timeframe...")

            # Screen coins concurrently (in batches)
            results = []
            batch_size = 10  # Process 10 coins at a time

            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]

                # Screen batch concurrently
                tasks = [
                    self.screen_coin(symbol, timeframe)
                    for symbol in batch
                ]
                batch_results = await asyncio.gather(*tasks)

                # Add successful results
                for result in batch_results:
                    if result and result.score >= min_score:
                        results.append(result)

                # Small delay to avoid rate limits
                if i + batch_size < len(symbols):
                    await asyncio.sleep(1)

            # Sort by score (descending)
            results.sort(key=lambda x: x.score, reverse=True)

            # Limit results
            final_results = results[:max_results]

            logger.info(
                f"Screening complete: {len(final_results)} coins passed "
                f"(score >= {min_score})"
            )

            return final_results

        except Exception as e:
            logger.error(f"Error in screen_market: {e}")
            return []

    async def get_screening_summary(
        self,
        results: List[ScreenResult],
        timeframe: str
    ) -> Dict[str, Any]:
        """Generate screening summary"""
        if not results:
            return {
                'total': 0,
                'avg_score': 0.0,
                'top_score': 0.0,
                'bullish': 0,
                'bearish': 0,
                'neutral': 0
            }

        total = len(results)
        avg_score = sum(r.score for r in results) / total
        top_score = results[0].score

        bullish = sum(1 for r in results if r.trend == 'BULLISH')
        bearish = sum(1 for r in results if r.trend == 'BEARISH')
        neutral = sum(1 for r in results if r.trend == 'NEUTRAL')

        return {
            'total': total,
            'avg_score': avg_score,
            'top_score': top_score,
            'bullish': bullish,
            'bearish': bearish,
            'neutral': neutral,
            'timeframe': timeframe,
            'timestamp': datetime.now()
        }


# Global screener instance
_screener_instance = None


def get_screener() -> MarketScreener:
    """Get global screener instance"""
    global _screener_instance
    if _screener_instance is None:
        _screener_instance = MarketScreener()
    return _screener_instance
