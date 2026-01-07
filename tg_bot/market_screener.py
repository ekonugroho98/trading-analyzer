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
        """Get top USDT pairs by volume from Bybit"""
        try:
            # Fetch all USDT pairs from Bybit
            import requests
            url = "https://api.bybit.com/v5/market/tickers"
            params = {
                "category": "spot"
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('retCode') == 0 and 'result' in data:
                # Get all USDT pairs
                all_symbols = []
                for ticker in data['result']['list']:
                    symbol = ticker['symbol']
                    # Filter only USDT pairs
                    if symbol.endswith('USDT'):
                        all_symbols.append(symbol)

                logger.info(f"Fetched {len(all_symbols)} USDT pairs from Bybit")
                return all_symbols[:limit] if limit else all_symbols
            else:
                logger.warning(f"Failed to fetch from Bybit: {data.get('retMsg', 'Unknown error')}, using fallback list")
                return TOP_USDT_PAIRS[:limit]

        except Exception as e:
            logger.error(f"Error getting top symbols from Bybit: {e}")
            # Return static list as fallback
            symbols = TOP_USDT_PAIRS[:limit]
            logger.info(f"Using fallback list with {len(symbols)} symbols")
            return symbols

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

    async def screen_market_multi_tf(
        self,
        primary_tf: str = '1d',
        secondary_tfs: List[str] = None,
        limit: int = 100,
        min_score: float = 5.0,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """Screen market using multi-timeframe analysis

        Args:
            primary_tf: Primary timeframe for analysis (default: 1d)
            secondary_tfs: List of secondary timeframes (default: ['4h', '2h'])
            limit: Number of symbols to screen
            min_score: Minimum score to pass
            max_results: Maximum results to return

        Returns:
            Dict with primary_results, secondary_results, and multi_tf_signals
        """
        if secondary_tfs is None:
            secondary_tfs = ['4h', '2h']

        try:
            # Get symbols to screen
            symbols = await self.get_top_symbols(limit)

            if not symbols:
                logger.error("No symbols to screen")
                return {
                    'primary_results': [],
                    'secondary_results': {},
                    'multi_tf_signals': [],
                    'summary': {}
                }

            logger.info(
                f"Multi-TF Screening: {len(symbols)} symbols | "
                f"Primary: {primary_tf} | Secondary: {secondary_tfs}"
            )

            # Screen on primary timeframe
            primary_results = await self.screen_market(
                timeframe=primary_tf,
                limit=limit,
                min_score=min_score,
                max_results=max_results
            )

            # Screen on secondary timeframes (only for coins that passed primary)
            secondary_results = {}
            multi_tf_signals = []

            if primary_results:
                # Get unique symbols from primary results
                primary_symbols = [r.symbol for r in primary_results[:min(20, len(primary_results))]]

                for sec_tf in secondary_tfs:
                    logger.info(f"Screening {len(primary_symbols)} symbols on {sec_tf} timeframe...")

                    sec_results = []
                    batch_size = 10

                    for i in range(0, len(primary_symbols), batch_size):
                        batch = primary_symbols[i:i + batch_size]

                        tasks = [
                            self.screen_coin(symbol, sec_tf)
                            for symbol in batch
                        ]
                        batch_results = await asyncio.gather(*tasks)

                        for result in batch_results:
                            if result and result.score >= min_score:
                                sec_results.append(result)

                        if i + batch_size < len(primary_symbols):
                            await asyncio.sleep(0.5)

                    # Sort by score
                    sec_results.sort(key=lambda x: x.score, reverse=True)
                    secondary_results[sec_tf] = sec_results[:max_results]

                # Find multi-timeframe confluences
                # Coins that scored well on primary AND at least one secondary TF
                primary_symbol_scores = {r.symbol: r.score for r in primary_results}

                for sec_tf, sec_res_list in secondary_results.items():
                    for sec_res in sec_res_list:
                        if sec_res.symbol in primary_symbol_scores:
                            # This coin passed on both timeframes!
                            primary_score = primary_symbol_scores[sec_res.symbol]
                            avg_score = (primary_score + sec_res.score) / 2

                            multi_tf_signals.append({
                                'symbol': sec_res.symbol,
                                'primary_tf': primary_tf,
                                'primary_score': primary_score,
                                'secondary_tf': sec_tf,
                                'secondary_score': sec_res.score,
                                'avg_score': avg_score,
                                'trend': sec_res.trend,
                                'signals': sec_res.signals,
                                'current_price': sec_res.current_price,
                                'change_24h': sec_res.change_24h
                            })

                # Sort multi-TF signals by average score
                multi_tf_signals.sort(key=lambda x: x['avg_score'], reverse=True)

            # Generate summary
            summary = {
                'total_symbols_screened': len(symbols),
                'primary_tf': primary_tf,
                'primary_passed': len(primary_results),
                'secondary_tfs': secondary_tfs,
                'secondary_passed': {tf: len(res) for tf, res in secondary_results.items()},
                'multi_tf_confluences': len(multi_tf_signals),
                'timestamp': datetime.now()
            }

            logger.info(
                f"Multi-TF Screening Complete | "
                f"Primary: {len(primary_results)} | "
                f"Multi-TF: {len(multi_tf_signals)} confluences"
            )

            return {
                'primary_results': primary_results,
                'secondary_results': secondary_results,
                'multi_tf_signals': multi_tf_signals,
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Error in screen_market_multi_tf: {e}", exc_info=True)
            return {
                'primary_results': [],
                'secondary_results': {},
                'multi_tf_signals': [],
                'summary': {'error': str(e)}
            }


# Global screener instance
_screener_instance = None


def get_screener() -> MarketScreener:
    """Get global screener instance"""
    global _screener_instance
    if _screener_instance is None:
        _screener_instance = MarketScreener()
    return _screener_instance
