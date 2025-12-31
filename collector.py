"""
CRYPTO DATA COLLECTOR - BINANCE & BYBIT
Author: DeepSeek Assistant
Version: 2.0
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ CONFIGURATION ============
@dataclass
class ExchangeConfig:
    name: str
    base_url: str
    kline_endpoint: str
    max_limit: int
    rate_limit: float

class Exchange(Enum):
    BINANCE = ExchangeConfig(
        name="binance",
        base_url="https://api.binance.com",
        kline_endpoint="/api/v3/klines",
        max_limit=1000,
        rate_limit=0.1  # seconds between requests
    )
    
    BYBIT = ExchangeConfig(
        name="bybit",
        base_url="https://api.bybit.com",
        kline_endpoint="/v5/market/kline",
        max_limit=200,
        rate_limit=0.2
    )

# ============ MAIN COLLECTOR CLASS ============
class CryptoDataCollector:
    """
    Collector data OHLCV dari multiple crypto exchanges.
    Support: Binance, Bybit
    """
    
    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = cache_dir
        self.last_request_time = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "binance"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "bybit"), exist_ok=True)
        
        logger.info(f"Data Collector initialized. Cache dir: {cache_dir}")
    
    def _rate_limit(self, exchange: Exchange):
        """Implement rate limiting"""
        exchange_name = exchange.value.name
        current_time = time.time()
        
        if exchange_name in self.last_request_time:
            elapsed = current_time - self.last_request_time[exchange_name]
            if elapsed < exchange.value.rate_limit:
                sleep_time = exchange.value.rate_limit - elapsed
                time.sleep(sleep_time)
        
        self.last_request_time[exchange_name] = time.time()
    
    def _save_to_cache(self, df: pd.DataFrame, exchange: str, symbol: str, 
                      interval: str, filename: str = None):
        """Save data to cache file"""
        if df is None or len(df) == 0:
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{exchange}_{symbol}_{interval}_{timestamp}.csv"
        
        filepath = os.path.join(self.cache_dir, exchange, filename)
        df.to_csv(filepath, index=False)
        logger.debug(f"Data saved to cache: {filepath}")
        return filepath
    
    def _load_from_cache(self, exchange: str, symbol: str, interval: str, 
                        hours: int = 24):
        """Load recent data from cache"""
        cache_dir = os.path.join(self.cache_dir, exchange)
        if not os.path.exists(cache_dir):
            return None
        
        # Find recent files
        files = [f for f in os.listdir(cache_dir) 
                if f.startswith(f"{exchange}_{symbol}_{interval}")]
        
        if not files:
            return None
        
        # Get latest file
        latest_file = max(files)
        filepath = os.path.join(cache_dir, latest_file)
        
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by time
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_df = df[df['timestamp'] >= cutoff]
            
            if len(recent_df) > 0:
                logger.info(f"Loaded {len(recent_df)} candles from cache")
                return recent_df
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
        
        return None
    
    # ============ BINANCE METHODS ============
    def get_binance_klines(self, symbol: str = "BTCUSDT", 
                          interval: str = "1h",
                          limit: int = 500,
                          use_cache: bool = True,
                          save_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data from Binance
        
        Parameters:
        -----------
        symbol : str
            Trading pair (e.g., "BTCUSDT", "ETHUSDT")
        interval : str
            Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
        limit : int
            Number of candles to fetch (max 1000)
        use_cache : bool
            Use cached data if available
        save_cache : bool
            Save fetched data to cache
        
        Returns:
        --------
        pd.DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Apply rate limiting
        self._rate_limit(Exchange.BINANCE)
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache("binance", symbol, interval)
            if cached_data is not None and len(cached_data) >= limit:
                return cached_data.tail(limit)
        
        # Prepare request
        url = f"{Exchange.BINANCE.value.base_url}{Exchange.BINANCE.value.kline_endpoint}"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, Exchange.BINANCE.value.max_limit)
        }
        
        try:
            logger.info(f"Fetching Binance data: {symbol} {interval} x{limit}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Parse response
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert data types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Select and reorder columns
            result_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            
            # Calculate additional metrics
            result_df['price_change'] = result_df['close'].pct_change() * 100
            result_df['volume_change'] = result_df['volume'].pct_change() * 100
            
            logger.info(f"Successfully fetched {len(result_df)} candles from Binance")
            
            # Save to cache
            if save_cache and len(result_df) > 0:
                self._save_to_cache(result_df, "binance", symbol, interval)
            
            return result_df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Binance data: {e}")
            return None

    def get_binance_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get 24-hour ticker data from Binance

        Parameters:
        -----------
        symbol : str
            Trading pair (e.g., "BTCUSDT", "ETHUSDT")

        Returns:
        --------
        Dict with 24h statistics including volume, price change, etc.
        """
        # Apply rate limiting
        self._rate_limit(Exchange.BINANCE)

        # Prepare request
        url = f"{Exchange.BINANCE.value.base_url}/api/v3/ticker/24hr"
        params = {"symbol": symbol.upper()}

        try:
            logger.info(f"Fetching Binance 24h ticker: {symbol}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            # Parse relevant data
            ticker_data = {
                'symbol': data.get('symbol'),
                'price_change': float(data.get('priceChange', 0)),
                'price_change_percent': float(data.get('priceChangePercent', 0)),
                'weighted_avg_price': float(data.get('weightedAvgPrice', 0)),
                'prev_close_price': float(data.get('prevClosePrice', 0)),
                'last_price': float(data.get('lastPrice', 0)),
                'last_qty': float(data.get('lastQty', 0)),
                'bid_price': float(data.get('bidPrice', 0)),
                'bid_qty': float(data.get('bidQty', 0)),
                'ask_price': float(data.get('askPrice', 0)),
                'ask_qty': float(data.get('askQty', 0)),
                'open_price': float(data.get('openPrice', 0)),
                'high_price': float(data.get('highPrice', 0)),
                'low_price': float(data.get('lowPrice', 0)),
                'volume': float(data.get('volume', 0)),
                'quote_volume': float(data.get('quoteVolume', 0)),
                'open_time': int(data.get('openTime', 0)),
                'close_time': int(data.get('closeTime', 0)),
                'first_id': int(data.get('firstId', 0)),
                'last_id': int(data.get('lastId', 0)),
                'trades': int(data.get('count', 0))
            }

            logger.debug(f"Successfully fetched 24h ticker for {symbol}")
            return ticker_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching Binance 24h ticker: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Binance 24h ticker: {e}")
            return None

    # ============ BYBIT METHODS ============
    def get_bybit_klines(self, symbol: str = "BTCUSDT",
                        interval: str = "1h",
                        limit: int = 200,
                        category: str = "spot",
                        use_cache: bool = True,
                        save_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data from Bybit
        
        Parameters:
        -----------
        symbol : str
            Trading pair (e.g., "BTCUSDT", "ETHUSDT")
        interval : str
            Kline interval (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
        limit : int
            Number of candles to fetch (max 200)
        category : str
            Product type: spot, linear, inverse
        """
        # Apply rate limiting
        self._rate_limit(Exchange.BYBIT)
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache("bybit", symbol, interval)
            if cached_data is not None and len(cached_data) >= limit:
                return cached_data.tail(limit)
        
        # Prepare request
        url = f"{Exchange.BYBIT.value.base_url}{Exchange.BYBIT.value.kline_endpoint}"
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, Exchange.BYBIT.value.max_limit)
        }
        
        try:
            logger.info(f"Fetching Bybit data: {symbol} {interval} x{limit}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return None
            
            klines = data['result']['list']
            
            if not klines:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Parse response (Bybit returns reversed: newest first)
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # Convert data types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype('int64'), unit='ms')
            
            # Sort by timestamp (oldest to newest)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Select and reorder columns
            result_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            
            # Calculate additional metrics
            result_df['price_change'] = result_df['close'].pct_change() * 100
            result_df['volume_change'] = result_df['volume'].pct_change() * 100
            
            logger.info(f"Successfully fetched {len(result_df)} candles from Bybit")
            
            # Save to cache
            if save_cache and len(result_df) > 0:
                self._save_to_cache(result_df, "bybit", symbol, interval)
            
            return result_df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Bybit API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Bybit data: {e}")
            return None
    
    # ============ BATCH COLLECTION ============
    def collect_multiple(self, 
                        exchange: str,
                        symbols: List[str],
                        interval: str = "1h",
                        limit: int = 100,
                        parallel: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Collect data for multiple symbols
        
        Returns:
        --------
        Dict with symbol as key and DataFrame as value
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Collecting {symbol} from {exchange}...")
            
            if exchange.lower() == "binance":
                data = self.get_binance_klines(symbol, interval, limit)
            elif exchange.lower() == "bybit":
                data = self.get_bybit_klines(symbol, interval, limit)
            else:
                logger.error(f"Unsupported exchange: {exchange}")
                continue
            
            if data is not None:
                results[symbol] = data
                logger.info(f"  ✓ {symbol}: {len(data)} candles")
            else:
                logger.warning(f"  ✗ {symbol}: Failed to fetch data")
            
            # Small delay between requests
            if not parallel:
                time.sleep(0.5)
        
        return results
    
    # ============ TECHNICAL INDICATORS ============
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic technical indicators"""
        if df is None or len(df) < 20:
            return df
        
        df = df.copy()
        
        # Moving Averages
        df['MA7'] = df['close'].rolling(window=7).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # Volume indicators
        df['volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_MA20']
        
        return df
    
    # ============ DEEPSEEK PREPARATION ============
    def prepare_for_deepseek(self, 
                           df: pd.DataFrame,
                           symbol: str = "BTCUSDT",
                           exchange: str = "binance",
                           interval: str = "1h",
                           include_indicators: bool = True,
                           analysis_request: str = None) -> Dict:
        """
        Prepare data for DeepSeek API analysis
        
        Returns:
        --------
        Dict with formatted payload
        """
        if df is None or len(df) == 0:
            logger.error("No data to prepare for DeepSeek")
            return None
        
        # Calculate indicators if requested
        if include_indicators and len(df) >= 50:
            df_with_indicators = self.calculate_indicators(df)
        else:
            df_with_indicators = df.copy()
        
        # Prepare candle data
        candles = []
        for _, row in df_with_indicators.iterrows():
            candle = {
                "timestamp": row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') 
                          else str(row['timestamp']),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume'])
            }
            
            # Add indicators if available
            if include_indicators:
                indicator_fields = ['MA7', 'MA20', 'MA50', 'RSI', 'MACD', 
                                  'BB_upper', 'BB_middle', 'BB_lower']
                for field in indicator_fields:
                    if field in row and not pd.isna(row[field]):
                        candle[field.lower()] = float(row[field])
            
            candles.append(candle)
        
        # Default analysis request
        if analysis_request is None:
            analysis_request = f"""
            Berikan analisis trading untuk {symbol} di timeframe {interval}:
            1. Identifikasi trend dan momentum
            2. Level support/resistance penting
            3. Sinyal dari indikator teknikal
            4. Potensi entry/exit points
            5. Risk management suggestions
            """
        
        # Create payload
        payload = {
            "metadata": {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": interval,
                "total_candles": len(candles),
                "data_range": {
                    "start": df['timestamp'].min().isoformat(),
                    "end": df['timestamp'].max().isoformat()
                },
                "collected_at": datetime.now().isoformat()
            },
            "candles": candles,
            "analysis_config": {
                "request": analysis_request.strip(),
                "include_summary": True,
                "include_signals": True,
                "timeframes_to_analyze": ["current", "higher"],
                "risk_profile": "moderate"
            }
        }
        
        logger.info(f"Prepared DeepSeek payload: {len(candles)} candles")
        return payload
    
    def save_payload(self, payload: Dict, filename: str = None):
        """Save payload to JSON file"""
        if filename is None:
            symbol = payload['metadata']['symbol']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deepseek_payload_{symbol}_{timestamp}.json"
        
        filepath = os.path.join(self.cache_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Payload saved to: {filepath}")
        return filepath

    def get_binance_klines_auto(self, symbol: str = "BTCUSDT",
                                interval: str = "1h",
                                limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Auto-detect and fetch from Binance Spot or Futures
        Tries futures first, then spot if futures fails
        """
        # Try Futures first
        df = self._get_binance_futures_klines(symbol, interval, limit)
        if df is not None and len(df) > 0:
            logger.info(f"Data fetched from Binance Futures for {symbol}")
            return df

        # Try Spot as fallback
        df = self.get_binance_klines(symbol, interval, limit, use_cache=False, save_cache=False)
        if df is not None and len(df) > 0:
            logger.info(f"Data fetched from Binance Spot for {symbol}")
            return df

        logger.error(f"Failed to fetch data for {symbol} from both Spot and Futures")
        return None

    def _get_binance_futures_klines(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from Binance Futures API"""
        try:
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": min(limit, 1500)
            }

            logger.info(f"Trying Binance Futures: {symbol}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            if not data or isinstance(data, dict) and 'code' in data:
                logger.warning(f"Futures API error for {symbol}: {data}")
                return None

            # Parse response
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert data types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Select and reorder columns
            result_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

            # Calculate additional metrics
            result_df['price_change'] = result_df['close'].pct_change() * 100
            result_df['volume_change'] = result_df['volume'].pct_change() * 100

            logger.info(f"Successfully fetched {len(result_df)} candles from Binance Futures")
            return result_df

        except requests.exceptions.RequestException as e:
            logger.warning(f"Binance Futures API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching Binance Futures data for {symbol}: {e}")
            return None

# ============ HELPER FUNCTIONS ============
def get_common_pairs() -> Dict[str, List[str]]:
    """Get commonly traded pairs"""
    return {
        "majors": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
        "defi": ["LINKUSDT", "UNIUSDT", "AAVEUSDT", "AVAXUSDT", "DOTUSDT"],
        "memes": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT"]
    }

def print_data_summary(df: pd.DataFrame, symbol: str):
    """Print summary of collected data"""
    if df is None:
        print(f"\n❌ No data for {symbol}")
        return
    
    print(f"\n📊 {symbol} Data Summary:")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Total candles: {len(df)}")
    print(f"   Latest price: ${df.iloc[-1]['close']:.2f}")
    print(f"   24h change: {df['price_change'].iloc[-1]:.2f}%" if 'price_change' in df.columns else "")
    print(f"   Volume: {df.iloc[-1]['volume']:.2f}")

# ============ MAIN EXECUTION ============
if __name__ == "__main__":
    """
    Example usage of the CryptoDataCollector
    """
    print("=" * 60)
    print("CRYPTO DATA COLLECTOR - BINANCE & BYBIT")
    print("=" * 60)
    
    # Initialize collector
    collector = CryptoDataCollector()
    
    # Example 1: Get Bitcoin data from Binance
    print("\n1. Fetching BTC/USDT from Binance...")
    btc_binance = collector.get_binance_klines("BTCUSDT", "1h", 100)
    print_data_summary(btc_binance, "BTC/USDT (Binance)")
    
    # Example 2: Get Ethereum data from Bybit
    print("\n2. Fetching ETH/USDT from Bybit...")
    eth_bybit = collector.get_bybit_klines("ETHUSDT", "1h", 100)
    print_data_summary(eth_bybit, "ETH/USDT (Bybit)")
    
    # Example 3: Prepare for DeepSeek
    if btc_binance is not None:
        print("\n3. Preparing DeepSeek payload...")
        payload = collector.prepare_for_deepseek(
            btc_binance,
            symbol="BTCUSDT",
            exchange="binance",
            interval="1h",
            analysis_request="Analisis teknikal BTC/USDT untuk trading hari ini"
        )
        
        if payload:
            # Save sample payload
            collector.save_payload(payload, "sample_payload.json")
            print(f"   ✓ Payload prepared: {len(payload['candles'])} candles")
            print(f"   ✓ Saved to: sample_payload.json")
    
    # Example 4: Batch collection
    print("\n4. Batch collection from Binance...")
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    results = collector.collect_multiple("binance", symbols, "4h", 50)
    
    print(f"\n📈 Collection Summary:")
    for symbol, data in results.items():
        if data is not None:
            latest_price = data.iloc[-1]['close']
            print(f"   {symbol}: ${latest_price:.2f} ({len(data)} candles)")
    
    print("\n" + "=" * 60)
    print("✅ Data collection completed!")
    print("Check 'data_cache' folder for saved data")
    print("=" * 60)
