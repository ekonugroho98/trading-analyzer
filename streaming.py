"""
REAL-TIME STREAMING MODULE - Binance & Bybit WebSocket
"""

import websocket
import json
import threading
import time
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import pandas as pd
import logging
from dataclasses import dataclass, field
from enum import Enum
import pickle
import zlib

from config import config, Exchange

logger = logging.getLogger(__name__)

# ============ DATA STRUCTURES ============
@dataclass
class StreamData:
    """Data structure for streaming data"""
    symbol: str
    exchange: str
    timestamp: datetime
    price: float
    volume: float
    bid: float
    ask: float
    data_type: str  # 'trade', 'kline', 'depth'
    raw_data: dict = field(default_factory=dict)

@dataclass
class KlineData:
    """Candlestick data structure"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool

class StreamType(Enum):
    TRADES = "trades"
    KLINE = "kline"
    DEPTH = "depth"
    TICKER = "ticker"

# ============ MAIN STREAMING CLASS ============
class CryptoStreamer:
    """
    Real-time cryptocurrency data streamer
    Supports Binance and Bybit WebSocket connections
    """
    
    def __init__(self, exchange: Exchange = Exchange.BINANCE, market_type: str = "spot"):
        self.exchange = exchange
        self.market_type = market_type
        self.exchange_config = config.get_exchange_config(exchange, market_type)
        self.ws = None
        self.connected = False
        self.subscriptions = set()
        self.callbacks = {}
        self.data_buffer = {}
        self.max_buffer_size = 1000

        # Statistics
        self.messages_received = 0
        self.errors = 0
        self.start_time = None

        # Threading
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        self.stop_flag = False

        # Data storage
        self.data_storage = {}

        logger.info(f"Initialized CryptoStreamer for {exchange} ({market_type})")
    
    # ============ WEBSOCKET METHODS ============
    def connect(self):
        """Establish WebSocket connection"""
        if self.connected:
            logger.warning("Already connected")
            return True
        
        try:
            logger.info(f"Connecting to {self.exchange} WebSocket...")
            
            # Set up WebSocket
            self.ws = websocket.WebSocketApp(
                self.exchange_config.get('ws_url', 'wss://stream.binance.com:9443/ws'),
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            for _ in range(30):  # Wait up to 3 seconds
                if self.connected:
                    break
                time.sleep(0.1)
            
            if self.connected:
                logger.info(f"Connected to {self.exchange} WebSocket")
                self.start_time = datetime.now()
                self.reconnect_attempts = 0
                return True
            else:
                logger.error("Failed to establish connection")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _on_open(self, ws):
        """WebSocket on_open handler"""
        self.connected = True
        logger.info("WebSocket connection opened")
        
        # Resubscribe to previous subscriptions
        if self.subscriptions:
            self._resubscribe()
    
    def _on_message(self, ws, message):
        """WebSocket on_message handler"""
        try:
            self.messages_received += 1

            # Handle byte messages
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            # Parse message
            data = json.loads(message)

            # Process based on exchange
            if self.exchange == Exchange.BINANCE:
                self._process_binance_message(data)
            elif self.exchange == Exchange.BYBIT:
                self._process_bybit_message(data)

            # Log statistics periodically
            if self.messages_received % 100 == 0:
                self._log_statistics()

        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode error: {e}")
            self.errors += 1
        except Exception as e:
            logger.debug(f"Message processing error: {e}")
            self.errors += 1
    
    def _on_error(self, ws, error):
        """WebSocket on_error handler"""
        logger.error(f"WebSocket error: {error}")
        self.errors += 1
        self.connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket on_close handler"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False
        
        # Attempt reconnection
        if not self.stop_flag:
            self._reconnect()
    
    def _reconnect(self):
        """Attempt to reconnect"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        time.sleep(self.reconnect_delay * self.reconnect_attempts)
        
        if not self.stop_flag:
            self.connect()
    
    # ============ SUBSCRIPTION METHODS ============
    def subscribe(self, stream_type: StreamType, symbols: List[str], 
                 interval: str = None, callback: Callable = None):
        """
        Subscribe to data streams
        
        Args:
            stream_type: Type of stream (trades, kline, depth)
            symbols: List of trading pairs
            interval: Kline interval (for kline streams)
            callback: Function to call when data arrives
        """
        subscriptions = []
        
        for symbol in symbols:
            stream_name = self._get_stream_name(stream_type, symbol, interval)
            
            if stream_name not in self.subscriptions:
                self.subscriptions.add(stream_name)
                subscriptions.append(stream_name)
                
                # Store callback
                if callback:
                    self.callbacks[stream_name] = callback
                
                logger.info(f"Subscribed to {stream_name}")
        
        # Send subscription message if connected
        if self.connected and subscriptions:
            self._send_subscription(subscriptions)
    
    def unsubscribe(self, stream_type: StreamType, symbols: List[str], 
                   interval: str = None):
        """Unsubscribe from streams"""
        for symbol in symbols:
            stream_name = self._get_stream_name(stream_type, symbol, interval)
            
            if stream_name in self.subscriptions:
                self.subscriptions.remove(stream_name)
                self.callbacks.pop(stream_name, None)
                logger.info(f"Unsubscribed from {stream_name}")
    
    def _get_stream_name(self, stream_type: StreamType, symbol: str, 
                        interval: str = None) -> str:
        """Generate stream name for subscription"""
        symbol = symbol.lower()
        
        if self.exchange == Exchange.BINANCE:
            if stream_type == StreamType.TRADES:
                return f"{symbol}@trade"
            elif stream_type == StreamType.KLINE:
                return f"{symbol}@kline_{interval}"
            elif stream_type == StreamType.DEPTH:
                return f"{symbol}@depth20@100ms"
            elif stream_type == StreamType.TICKER:
                return f"{symbol}@ticker"
                
        elif self.exchange == Exchange.BYBIT:
            if stream_type == StreamType.TRADES:
                return f"publicTrade.{symbol}"
            elif stream_type == StreamType.KLINE:
                return f"kline.{interval}.{symbol}"
            elif stream_type == StreamType.DEPTH:
                return f"orderbook.20.{symbol}"
        
        raise ValueError(f"Unsupported stream type: {stream_type}")
    
    def _send_subscription(self, streams: List[str]):
        """Send subscription message to exchange"""
        if self.exchange == Exchange.BINANCE:
            # Binance uses combined streams
            stream_param = "/".join(streams)
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": 1
            }
            self.ws.send(json.dumps(subscribe_msg))
            
        elif self.exchange == Exchange.BYBIT:
            # Bybit subscription format
            for stream in streams:
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [stream]
                }
                self.ws.send(json.dumps(subscribe_msg))
    
    def _resubscribe(self):
        """Resubscribe to all previous streams"""
        if self.subscriptions:
            logger.info("Resubscribing to previous streams...")
            streams = list(self.subscriptions)
            
            # Clear and resubscribe
            self.subscriptions.clear()
            
            # Parse streams and resubscribe
            for stream in streams:
                # Parse stream name to extract parameters
                # This is simplified - you'd need proper parsing
                if "@" in stream:  # Binance format
                    parts = stream.split("@")
                    symbol = parts[0].upper()
                    
                    if "kline" in stream:
                        stream_type = StreamType.KLINE
                        interval = parts[1].split("_")[1]
                    elif "trade" in stream:
                        stream_type = StreamType.TRADES
                        interval = None
                    
                    self.subscribe(stream_type, [symbol], interval)
    
    # ============ DATA PROCESSING ============
    def _process_binance_message(self, data: dict):
        """Process Binance WebSocket message"""
        if 'e' in data:  # Event type
            event_type = data['e']
            
            if event_type == 'kline':
                self._process_binance_kline(data)
            elif event_type == 'trade':
                self._process_binance_trade(data)
            elif event_type == 'depthUpdate':
                self._process_binance_depth(data)
            elif event_type == '24hrTicker':
                self._process_binance_ticker(data)
                
        elif 'result' in data:  # Subscription confirmation
            logger.debug(f"Subscription confirmed: {data}")
    
    def _process_bybit_message(self, data: dict):
        """Process Bybit WebSocket message"""
        if 'topic' in data:
            topic = data['topic']
            
            if 'kline' in topic:
                self._process_bybit_kline(data)
            elif 'trade' in topic:
                self._process_bybit_trade(data)
            elif 'orderbook' in topic:
                self._process_bybit_depth(data)
                
        elif 'success' in data:  # Subscription confirmation
            logger.debug(f"Subscription confirmed: {data}")
    
    def _process_binance_kline(self, data: dict):
        """Process Binance kline data"""
        kline = data['k']
        symbol = data['s']
        stream_name = f"{symbol.lower()}@kline_{kline['i']}"
        
        kline_data = KlineData(
            symbol=symbol,
            interval=kline['i'],
            open_time=datetime.fromtimestamp(kline['t'] / 1000),
            close_time=datetime.fromtimestamp(kline['T'] / 1000),
            open=float(kline['o']),
            high=float(kline['h']),
            low=float(kline['l']),
            close=float(kline['c']),
            volume=float(kline['v']),
            is_closed=kline['x']
        )
        
        # Store in buffer
        self._store_data(stream_name, kline_data)
        
        # Execute callback
        if stream_name in self.callbacks:
            try:
                self.callbacks[stream_name](kline_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _process_bybit_kline(self, data: dict):
        """Process Bybit kline data"""
        topic = data['topic']
        symbol = data['data'][0]['symbol']
        kline = data['data'][0]
        
        kline_data = KlineData(
            symbol=symbol,
            interval=kline['interval'],
            open_time=datetime.fromtimestamp(int(kline['start']) / 1000),
            close_time=datetime.fromtimestamp(int(kline['end']) / 1000),
            open=float(kline['open']),
            high=float(kline['high']),
            low=float(kline['low']),
            close=float(kline['close']),
            volume=float(kline['volume']),
            is_closed=kline['confirm']
        )
        
        # Store in buffer
        self._store_data(topic, kline_data)
        
        # Execute callback
        if topic in self.callbacks:
            try:
                self.callbacks[topic](kline_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _process_binance_trade(self, data: dict):
        """Process Binance trade data"""
        stream_data = StreamData(
            symbol=data['s'],
            exchange="binance",
            timestamp=datetime.fromtimestamp(data['T'] / 1000),
            price=float(data['p']),
            volume=float(data['q']),
            bid=float(data['b']),
            ask=float(data['a']),
            data_type="trade",
            raw_data=data
        )
        
        stream_name = f"{data['s'].lower()}@trade"
        self._store_data(stream_name, stream_data)
        
        if stream_name in self.callbacks:
            try:
                self.callbacks[stream_name](stream_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _process_bybit_trade(self, data: dict):
        """Process Bybit trade data"""
        topic = data['topic']
        trades = data['data']
        
        for trade in trades:
            stream_data = StreamData(
                symbol=trade['s'],
                exchange="bybit",
                timestamp=datetime.fromtimestamp(int(trade['T']) / 1000),
                price=float(trade['p']),
                volume=float(trade['v']),
                bid=float(trade.get('b', 0)),
                ask=float(trade.get('a', 0)),
                data_type="trade",
                raw_data=trade
            )
            
            self._store_data(topic, stream_data)
            
            if topic in self.callbacks:
                try:
                    self.callbacks[topic](stream_data)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
    
    def _process_binance_depth(self, data: dict):
        """Process order book depth data"""
        # Implement depth processing
        pass
    
    def _process_bybit_depth(self, data: dict):
        """Process Bybit order book data"""
        # Implement depth processing
        pass
    
    def _process_binance_ticker(self, data: dict):
        """Process 24hr ticker data"""
        # Implement ticker processing
        pass
    
    # ============ DATA STORAGE ============
    def _store_data(self, stream_name: str, data: Any):
        """Store data in buffer"""
        if stream_name not in self.data_buffer:
            self.data_buffer[stream_name] = []
        
        self.data_buffer[stream_name].append(data)
        
        # Limit buffer size
        if len(self.data_buffer[stream_name]) > self.max_buffer_size:
            self.data_buffer[stream_name] = self.data_buffer[stream_name][-self.max_buffer_size:]
    
    def get_recent_data(self, stream_name: str, limit: int = 100) -> List:
        """Get recent data from buffer"""
        if stream_name in self.data_buffer:
            return self.data_buffer[stream_name][-limit:]
        return []
    
    def clear_buffer(self, stream_name: str = None):
        """Clear data buffer"""
        if stream_name:
            self.data_buffer.pop(stream_name, None)
        else:
            self.data_buffer.clear()
    
    # ============ UTILITY METHODS ============
    def _log_statistics(self):
        """Log streaming statistics"""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        logger.info(
            f"Streaming Statistics - "
            f"Uptime: {uptime}, "
            f"Messages: {self.messages_received}, "
            f"Errors: {self.errors}, "
            f"Subscriptions: {len(self.subscriptions)}"
        )
    
    def disconnect(self):
        """Disconnect WebSocket"""
        logger.info("Disconnecting WebSocket...")
        self.stop_flag = True
        
        if self.ws:
            self.ws.close()
        
        self.connected = False
        logger.info("Disconnected")
    
    def get_status(self) -> Dict:
        """Get current streamer status"""
        return {
            "exchange": self.exchange,
            "connected": self.connected,
            "subscriptions": list(self.subscriptions),
            "messages_received": self.messages_received,
            "errors": self.errors,
            "uptime": str(datetime.now() - self.start_time) if self.start_time else "0"
        }

# ============ ASYNC STREAMER (OPTIONAL) ============
class AsyncCryptoStreamer:
    """Async version of CryptoStreamer using websockets library"""
    
    def __init__(self, exchange: Exchange = Exchange.BINANCE):
        self.exchange = exchange
        self.exchange_config = config.get_exchange_config(exchange)
        self.connected = False
        self.websocket = None
        self.subscriptions = set()
        self.callbacks = {}
        
    async def connect(self):
        """Async connection"""
        import websockets
        
        try:
            logger.info(f"Async connecting to {self.exchange}...")
            self.websocket = await websockets.connect(self.exchange_config.ws_url)
            self.connected = True
            logger.info("Async WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"Async connection error: {e}")
            return False
    
    async def subscribe_async(self, stream_type: StreamType, symbols: List[str], 
                            interval: str = None, callback: Callable = None):
        """Async subscription"""
        # Similar to sync version but async
        pass
    
    async def listen(self):
        """Listen for messages"""
        try:
            async for message in self.websocket:
                await self._process_message_async(message)
        except Exception as e:
            logger.error(f"Async listen error: {e}")
    
    async def _process_message_async(self, message: str):
        """Process async message"""
        # Process message asynchronously
        pass

# ============ STREAM MANAGER ============
class StreamManager:
    """Manager for multiple streamers"""
    
    def __init__(self):
        self.streamers = {}
        self.data_aggregator = DataAggregator()
        
    def add_streamer(self, exchange: Exchange) -> CryptoStreamer:
        """Add and start a streamer for exchange"""
        if exchange in self.streamers:
            return self.streamers[exchange]
        
        streamer = CryptoStreamer(exchange)
        streamer.connect()
        self.streamers[exchange] = streamer
        
        logger.info(f"Added streamer for {str(exchange)}")
        return streamer
    
    def subscribe_all(self, symbols: List[str], stream_types: List[StreamType]):
        """Subscribe to all active streamers"""
        for exchange, streamer in self.streamers.items():
            if streamer.connected:
                for stream_type in stream_types:
                    streamer.subscribe(stream_type, symbols)
    
    def get_aggregated_data(self, symbol: str, data_type: str = "price") -> Dict:
        """Get aggregated data from all streamers"""
        return self.data_aggregator.get_aggregated_data(symbol, data_type)
    
    def stop_all(self):
        """Stop all streamers"""
        for streamer in self.streamers.values():
            streamer.disconnect()
        self.streamers.clear()
        logger.info("All streamers stopped")

# ============ DATA AGGREGATOR ============
class DataAggregator:
    """Aggregate data from multiple sources"""
    
    def __init__(self):
        self.data_store = {}
        
    def add_data(self, exchange: str, symbol: str, data_type: str, data: Any):
        """Add data to aggregator"""
        key = f"{exchange}_{symbol}_{data_type}"
        
        if key not in self.data_store:
            self.data_store[key] = []
        
        self.data_store[key].append({
            "timestamp": datetime.now(),
            "data": data
        })
        
        # Keep only last 1000 entries
        if len(self.data_store[key]) > 1000:
            self.data_store[key] = self.data_store[key][-1000:]
    
    def get_aggregated_data(self, symbol: str, data_type: str) -> Dict:
        """Get aggregated data for symbol"""
        result = {}
        
        for key, data_list in self.data_store.items():
            if symbol in key and data_type in key:
                exchange = key.split("_")[0]
                result[exchange] = data_list[-1]["data"] if data_list else None
        
        return result

# ============ EXAMPLE USAGE ============
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("CRYPTO STREAMING MODULE - REAL-TIME DATA")
    print("=" * 60)
    
    # Example 1: Single exchange streaming
    def kline_callback(kline_data: KlineData):
        """Example callback for kline data"""
        print(f"[{kline_data.close_time}] {kline_data.symbol} "
              f"Close: ${kline_data.close:.2f} "
              f"Volume: {kline_data.volume:.2f}")
    
    # Create and start streamer
    streamer = CryptoStreamer(Exchange.BINANCE)
    
    if streamer.connect():
        # Subscribe to BTC and ETH klines
        streamer.subscribe(
            stream_type=StreamType.KLINE,
            symbols=["BTCUSDT", "ETHUSDT"],
            interval="1m",
            callback=kline_callback
        )
        
        print("\n🎯 Streaming started! Press Ctrl+C to stop.")
        print("Receiving real-time data...")
        
        try:
            # Keep running
            while True:
                time.sleep(1)
                
                # Print status every 30 seconds
                if int(time.time()) % 30 == 0:
                    status = streamer.get_status()
                    print(f"\n📊 Status: {status['messages_received']} messages, "
                          f"{status['subscriptions']} subscriptions")
                        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping streamer...")
            streamer.disconnect()
            print("✅ Streamer stopped")
    
    print("\n" + "=" * 60)