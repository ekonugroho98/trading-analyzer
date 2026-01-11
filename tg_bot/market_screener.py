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
            # Fetch all USDT pairs from Bybit Futures
            import requests
            url = "https://api.bybit.com/v5/market/tickers"
            params = {
                "category": "linear"  # Use USDT Perpetual Futures, not Spot
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

    def get_bybit_klines(self, symbol: str, interval: str = '4h', limit: int = 100):
        """
        Get kline data from Bybit with fallback to Binance

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Timeframe ('1', '3', '5', '15', '30', '60', '120', '240', '360', '480', '720', 'D', 'W', 'M')
            limit: Number of candles (max 1000)

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            import requests
            import pandas as pd

            # Map timeframe to Bybit interval
            interval_map = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '480',
                '1d': 'D', '1w': 'W', '1M': 'M'
            }

            bybit_interval = interval_map.get(interval, interval)

            url = "https://api.bybit.com/v5/market/kline"
            params = {
                "category": "linear",  # Use USDT Perpetual Futures, not Spot
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": str(min(limit, 1000))
            }

            response = requests.get(url, params=params, timeout=10)

            # Check if response is valid JSON (not HTML error)
            try:
                data = response.json()
            except:
                logger.warning(f"Bybit returned non-JSON response for {symbol}, trying Binance...")
                return self._get_binance_klines_fallback(symbol, interval, limit)

            if data.get('retCode') == 0 and 'result' in data:
                klines = data['result']['list']

                # Check number of columns in response
                # Bybit spot kline returns: [timestamp, open, high, low, close, volume, turnover]
                num_columns = len(klines[0]) if klines else 0

                if num_columns == 7:
                    # Standard Bybit format: timestamp, open, high, low, close, volume, turnover
                    df = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
                    ])
                elif num_columns == 6:
                    # Alternative format: timestamp, open, high, low, close, volume
                    df = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume'
                    ])
                else:
                    logger.warning(f"Unexpected Bybit kline format: {num_columns} columns")
                    return self._get_binance_klines_fallback(symbol, interval, limit)

                # Convert types
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = df[col].astype(float)

                # Sort by timestamp (newest first from Bybit, reverse it)
                df = df.sort_values('timestamp').reset_index(drop=True)

                # Keep only OHLCV
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

                return df
            else:
                logger.warning(f"Bybit API error for {symbol}: {data.get('retMsg', 'Unknown')}, trying Binance...")
                return self._get_binance_klines_fallback(symbol, interval, limit)

        except Exception as e:
            logger.error(f"Error fetching Bybit klines for {symbol}: {e}, trying Binance...")
            return self._get_binance_klines_fallback(symbol, interval, limit)

    def _get_binance_klines_fallback(self, symbol: str, interval: str = '4h', limit: int = 100):
        """
        Get kline data from Binance as fallback

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Timeframe
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            from collector import CryptoDataCollector
            collector = CryptoDataCollector()
            df = collector.get_binance_klines_auto(symbol, interval, limit)
            if df is not None:
                logger.debug(f"Successfully fetched {symbol} from Binance (fallback)")
            return df
        except Exception as e:
            logger.error(f"Error fetching Binance klines for {symbol}: {e}")
            return None

    async def screen_coin(
        self,
        symbol: str,
        timeframe: str = '4h',
        use_ai: bool = False,
        min_volume_24h: float = 15_000_000,  # $15M minimum 24h volume in USDT
        preferred_exchange: str = 'bybit'
    ) -> Optional[ScreenResult]:
        """
        Quick screen a single coin with HYBRID approach

        Args:
            symbol: Coin symbol
            timeframe: Timeframe for analysis
            use_ai: If True, skip technical filter and go straight to AI
            min_volume_24h: Minimum 24h volume in USDT (default: $15M)
            preferred_exchange: User's preferred exchange ('binance' or 'bybit')
        """
        try:
            # Get historical data using user's preferred exchange with fallback
            preferred_exchange = preferred_exchange.lower()
            fallback_exchange = "binance" if preferred_exchange == "bybit" else "bybit"

            # Try preferred exchange first
            if preferred_exchange == "bybit":
                df = self.get_bybit_klines(
                    symbol=symbol,
                    interval=timeframe,
                    limit=100
                )
            else:  # binance
                df = self._get_binance_klines_fallback(
                    symbol=symbol,
                    interval=timeframe,
                    limit=100
                )

            # Fallback to other exchange if preferred fails
            if df is None or len(df) < 50:
                logger.info(f"{preferred_exchange.capitalize()} data unavailable for {symbol}, trying {fallback_exchange.capitalize()}...")
                if fallback_exchange == "bybit":
                    df = self.get_bybit_klines(
                        symbol=symbol,
                        interval=timeframe,
                        limit=100
                    )
                else:  # binance
                    df = self._get_binance_klines_fallback(
                        symbol=symbol,
                        interval=timeframe,
                        limit=100
                    )

            if df is None or len(df) < 50:
                logger.debug(f"Insufficient data for {symbol}")
                return None

            # Get latest price and volume
            current_price = float(df['close'].iloc[-1])
            volume_24h_usdt = float(df['volume'].iloc[-1]) * current_price  # Convert to USDT value

            # FILTER 1: Minimum 24h Volume (must be > $15M USDT)
            if volume_24h_usdt < min_volume_24h:
                logger.debug(f"{symbol} failed volume filter: ${volume_24h_usdt:,.0f} < ${min_volume_24h:,.0f}")
                return None

            # Calculate 24h change
            change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100

            # TIER 1: Quick Technical Filter (Pure Logic - NO AI)
            from tg_bot.technical_analysis import quick_technical_score

            if not use_ai:
                tech_result = quick_technical_score(df)

                # If doesn't pass technical filter, skip AI analysis
                if not tech_result['passed']:
                    logger.debug(f"{symbol} failed technical filter (score: {tech_result['score']})")
                    return None

                # Passed filter - create preliminary result
                result = ScreenResult(
                    symbol=symbol,
                    score=tech_result['score'] / 10.0,  # Convert to 0-10 scale
                    signals=tech_result['signals'],
                    current_price=current_price,
                    volume_24h=volume_24h_usdt,  # Use USDT value
                    change_24h=change_24h,
                    trend=tech_result['trend'],
                    analysis=f"Technical score: {tech_result['score']}/100. Pending AI analysis..."
                )

                logger.debug(f"{symbol} passed technical filter (score: {tech_result['score']})")
                return result

            # TIER 2: AI Analysis (Only for manually requested or high-potential coins)
            # Prepare real indicators for AI
            from tg_bot.technical_analysis import calculate_rsi, calculate_ema, calculate_macd, calculate_adx

            rsi = calculate_rsi(df)
            ema_20 = calculate_ema(df, 20).iloc[-1]
            ema_50 = calculate_ema(df, 50).iloc[-1]
            ema_200 = calculate_ema(df, 200).iloc[-1]
            macd_line, signal_line, histogram = calculate_macd(df)

            indicators = {
                'rsi': rsi,
                'macd': macd_line,
                'ema_20': ema_20,
                'ema_50': ema_50,
                'ema_200': ema_200,
                'volume_24h': volume_24h_usdt  # Use USDT value
            }

            # Quick AI screening
            screening = await generate_quick_screening(
                symbol=symbol,
                timeframe=timeframe,
                indicators=indicators,
                current_price=current_price
            )

            # Create result from AI analysis
            result = ScreenResult(
                symbol=symbol,
                score=screening.get('score', 0.0),
                signals=screening.get('signals', []),
                current_price=current_price,
                volume_24h=volume_24h_usdt,  # Use USDT value
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

            # Screen coins sequentially to avoid rate limits and connection errors
            results = []
            total_symbols = len(symbols)

            for idx, symbol in enumerate(symbols):
                try:
                    # Screen coin individually
                    result = await self.screen_coin(symbol, timeframe)

                    # Add successful results
                    if result and result.score >= min_score:
                        results.append(result)
                        logger.debug(f"{symbol} passed with score {result.score:.1f}")
                    else:
                        logger.debug(f"{symbol} failed or below threshold")

                    # Progress update every 50 coins
                    if (idx + 1) % 50 == 0:
                        logger.info(f"Progress: {idx + 1}/{total_symbols} symbols screened ({len(results)} passed)")

                    # Small delay between requests to avoid rate limits
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error screening {symbol}: {e}")
                    continue

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

                    for symbol in primary_symbols:
                        try:
                            result = await self.screen_coin(symbol, sec_tf)
                            if result and result.score >= min_score:
                                sec_results.append(result)

                            # Small delay to avoid rate limits
                            await asyncio.sleep(0.1)

                        except Exception as e:
                            logger.error(f"Error screening {symbol} on {sec_tf}: {e}")
                            continue

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
