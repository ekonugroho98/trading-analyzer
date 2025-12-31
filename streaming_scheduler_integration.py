"""
INTEGRATED STREAMING-SCHEDULER SYSTEM
Kombinasi real-time data dengan scheduled tasks
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from queue import Queue

from streaming import CryptoStreamer, StreamType, KlineData
from scheduler import TradingScheduler, TaskPriority
from config import config, Exchange

logger = logging.getLogger(__name__)

class IntegratedTradingSystem:
    """
    Sistem trading terintegrasi: Streaming + Scheduler
    """
    
    def __init__(self):
        # Initialize components
        self.streamer = CryptoStreamer(Exchange.BINANCE)
        self.scheduler = TradingScheduler()
        
        # Communication bridge
        self.event_queue = Queue()
        self.data_buffer = {}
        self.running = False
        
        # Alert thresholds
        self.alert_thresholds = {
            'price_change_5min': 0.03,  # 3% in 5 minutes
            'volume_spike': 2.5,        # 2.5x average volume
            'rsi_extreme': 70,          # RSI > 70 or < 30
            'volatility_spike': 2.0     # 2x average volatility
        }
        
        # Statistics
        self.events_processed = 0
        self.alerts_triggered = 0
        
        logger.info("Integrated Trading System initialized")
    
    def start(self):
        """Start integrated system"""
        logger.info("🚀 Starting Integrated Trading System...")
        
        # 1. Start streaming first
        if self.streamer.connect():
            logger.info("✅ Streaming connected")
            
            # Subscribe to data streams
            self._setup_streaming_subscriptions()
            
            # 2. Setup scheduler tasks
            self._setup_integrated_tasks()
            
            # 3. Start event processor
            self.running = True
            self.event_processor_thread = threading.Thread(
                target=self._process_events,
                name="EventProcessor",
                daemon=True
            )
            self.event_processor_thread.start()
            
            # 4. Start scheduler
            self.scheduler.start(background=True)
            
            logger.info("✅ Integrated system started successfully")
            return True
        else:
            logger.error("❌ Failed to start streaming")
            return False
    
    def _setup_streaming_subscriptions(self):
        """Setup streaming subscriptions with callbacks"""
        # Subscribe to major pairs
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        # Kline data callback
        def kline_callback(kline_data: KlineData):
            if kline_data.is_closed:
                self._on_new_candle(kline_data)
        
        # Trade data callback  
        def trade_callback(trade_data):
            self._on_trade_update(trade_data)
        
        # Subscribe to streams
        self.streamer.subscribe(
            stream_type=StreamType.KLINE,
            symbols=symbols,
            interval="1m",
            callback=kline_callback
        )
        
        self.streamer.subscribe(
            stream_type=StreamType.TRADES,
            symbols=symbols,
            callback=trade_callback
        )
        
        logger.info(f"Subscribed to {len(symbols)} symbols")
    
    def _setup_integrated_tasks(self):
        """Setup tasks that integrate streaming data"""
        
        # 1. Real-time Monitoring Task (runs every minute)
        self.scheduler.register_task(
            name="realtime_monitoring",
            function=self._realtime_monitoring_task,
            interval="1m",
            priority=TaskPriority.HIGH
        )
        
        # 2. Buffer Analysis Task (every 5 minutes)
        self.scheduler.register_task(
            name="buffer_analysis",
            function=self._analyze_data_buffer,
            interval="5m",
            priority=TaskPriority.MEDIUM
        )
        
        # 3. Stream Health Check (every 15 minutes)
        self.scheduler.register_task(
            name="stream_health_check",
            function=self._check_stream_health,
            interval="15m",
            priority=TaskPriority.LOW
        )
        
        # 4. Emergency Analysis (triggered by events)
        self.scheduler.register_task(
            name="emergency_analysis",
            function=self._emergency_analysis,
            interval="hourly",  # Will be triggered manually
            priority=TaskPriority.CRITICAL
        )
        
        logger.info("Integrated tasks registered")
    
    # ============ STREAMING CALLBACKS ============
    def _on_new_candle(self, kline_data: KlineData):
        """Called when new candle closes"""
        event = {
            'type': 'new_candle',
            'symbol': kline_data.symbol,
            'timeframe': kline_data.interval,
            'data': kline_data,
            'timestamp': datetime.now()
        }
        
        # Add to event queue
        self.event_queue.put(event)
        
        # Store in buffer
        key = f"{kline_data.symbol}_{kline_data.interval}"
        if key not in self.data_buffer:
            self.data_buffer[key] = []
        
        self.data_buffer[key].append(kline_data)
        
        # Keep only recent data
        if len(self.data_buffer[key]) > 1000:
            self.data_buffer[key] = self.data_buffer[key][-1000:]
        
        logger.debug(f"New candle: {kline_data.symbol} {kline_data.close}")
    
    def _on_trade_update(self, trade_data):
        """Called on each trade"""
        event = {
            'type': 'trade',
            'symbol': trade_data.symbol,
            'price': trade_data.price,
            'volume': trade_data.volume,
            'timestamp': datetime.now()
        }
        
        self.event_queue.put(event)
        
        # Check for significant trades (whale alerts)
        if trade_data.volume > 10:  # 10 BTC equivalent
            self._detect_whale_activity(trade_data)
    
    # ============ EVENT PROCESSING ============
    def _process_events(self):
        """Process events from streaming"""
        logger.info("Event processor started")
        
        while self.running:
            try:
                # Get event with timeout
                event = self.event_queue.get(timeout=1.0)
                self.events_processed += 1
                
                # Process based on event type
                if event['type'] == 'new_candle':
                    self._process_new_candle(event)
                elif event['type'] == 'trade':
                    self._process_trade(event)
                
                # Log statistics periodically
                if self.events_processed % 100 == 0:
                    self._log_processing_stats()
                    
            except Exception as e:
                # Timeout is expected, other errors are logged
                if "timeout" not in str(e).lower():
                    logger.error(f"Event processing error: {e}")
    
    def _process_new_candle(self, event):
        """Process new candle event"""
        kline_data = event['data']
        symbol = kline_data.symbol
        
        # Check for price movements
        price_change = self._calculate_price_change(symbol, kline_data)
        
        if abs(price_change) > self.alert_thresholds['price_change_5min']:
            # Significant move detected
            alert_msg = f"🚨 {symbol}: Price moved {price_change:.2%} in 5min"
            logger.warning(alert_msg)
            
            # Trigger emergency analysis
            self._trigger_emergency_analysis(symbol, 'price_spike')
            
            # Send alert
            self._send_alert(alert_msg)
    
    def _process_trade(self, event):
        """Process trade event"""
        # Check for volume spikes
        symbol = event['symbol']
        volume = event['volume']
        
        avg_volume = self._get_average_volume(symbol)
        
        if avg_volume > 0 and volume > avg_volume * self.alert_thresholds['volume_spike']:
            # Volume spike detected
            logger.warning(f"Volume spike: {symbol} {volume:.2f} vs avg {avg_volume:.2f}")
            
            # Can trigger additional analysis
            self._trigger_volume_analysis(symbol)
    
    # ============ SCHEDULED TASKS ============
    def _realtime_monitoring_task(self):
        """Task: Real-time market monitoring"""
        logger.debug("Running real-time monitoring...")
        
        # Check all active streams
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            # Get latest data from buffer
            recent_candles = self._get_recent_candles(symbol, "1m", 30)
            
            if len(recent_candles) >= 10:
                # Calculate metrics
                volatility = self._calculate_volatility(recent_candles)
                trend = self._determine_trend(recent_candles)
                
                # Check thresholds
                if volatility > self.alert_thresholds['volatility_spike']:
                    logger.warning(f"High volatility: {symbol} = {volatility:.2f}")
                
                # Update dashboard metrics
                self._update_dashboard_metrics(symbol, {
                    'volatility': volatility,
                    'trend': trend,
                    'last_update': datetime.now()
                })
    
    def _analyze_data_buffer(self):
        """Task: Analyze accumulated data buffer"""
        logger.info("Analyzing data buffer...")
        
        for key, data_list in self.data_buffer.items():
            if len(data_list) >= 100:
                symbol = key.split('_')[0]
                
                # Perform technical analysis
                analysis = self._perform_technical_analysis(data_list[-100:])
                
                # Check for patterns
                patterns = self._detect_chart_patterns(data_list[-50:])
                
                if patterns:
                    logger.info(f"Patterns detected for {symbol}: {patterns}")
                    
                    # Generate trading plan if pattern detected
                    if 'breakout' in patterns or 'reversal' in patterns:
                        self._generate_pattern_based_plan(symbol, patterns)
    
    def _check_stream_health(self):
        """Task: Check streaming health"""
        stream_status = self.streamer.get_status()
        
        if not stream_status['connected']:
            logger.error("Stream disconnected! Attempting reconnect...")
            self.streamer.connect()
        
        # Log statistics
        logger.info(
            f"Stream Health: {stream_status['messages_received']} msgs, "
            f"{stream_status['errors']} errors, "
            f"Uptime: {stream_status['uptime']}"
        )
    
    def _emergency_analysis(self, symbol: str, reason: str):
        """Emergency analysis triggered by events"""
        logger.warning(f"🚨 EMERGENCY ANALYSIS: {symbol} - {reason}")

    # ============ HELPER METHODS ============
    def _calculate_price_change(self, symbol: str, kline_data):
        """Calculate price change for kline data"""
        # Simple implementation - returns 0 for now
        return 0.0

    def _get_average_volume(self, symbol: str):
        """Get average volume from buffer"""
        key = f"{symbol}_1m"
        if key in self.data_buffer and len(self.data_buffer[key]) > 0:
            volumes = [getattr(k, 'volume', 0) for k in self.data_buffer[key][-100:]]
            return sum(volumes) / len(volumes) if volumes else 0
        return 0

    def _detect_whale_activity(self, trade_data):
        """Detect whale activity from large trades"""
        logger.debug(f"Whale activity detected: {trade_data.symbol} - {trade_data.volume}")

    def _trigger_volume_analysis(self, symbol: str):
        """Trigger volume analysis"""
        logger.info(f"Volume analysis triggered for {symbol}")

    def _get_recent_candles(self, symbol: str, interval: str, count: int):
        """Get recent candles from buffer"""
        key = f"{symbol}_{interval}"
        if key in self.data_buffer:
            return self.data_buffer[key][-count:]
        return []

    def _calculate_volatility(self, candles):
        """Calculate volatility from candles"""
        if not candles or len(candles) < 2:
            return 0.0
        closes = [float(getattr(c, 'close', 0)) for c in candles]
        import statistics
        return statistics.stdev(closes) if len(closes) > 1 else 0.0

    def _determine_trend(self, candles):
        """Determine trend from candles"""
        if not candles or len(candles) < 2:
            return "NEUTRAL"
        first = float(getattr(candles[0], 'close', 0))
        last = float(getattr(candles[-1], 'close', 0))
        if last > first * 1.01:
            return "BULLISH"
        elif last < first * 0.99:
            return "BEARISH"
        return "NEUTRAL"

    def _update_dashboard_metrics(self, symbol: str, metrics: dict):
        """Update dashboard metrics"""
        logger.debug(f"Dashboard metrics updated for {symbol}: {metrics}")

    def _perform_technical_analysis(self, data_list):
        """Perform technical analysis on data"""
        return {}

    def _detect_chart_patterns(self, data_list):
        """Detect chart patterns"""
        return []

    def _generate_pattern_based_plan(self, symbol: str, patterns: list):
        """Generate trading plan based on patterns"""
        logger.info(f"Pattern-based plan generated for {symbol}: {patterns}")

    def _trigger_emergency_analysis(self, symbol: str, reason: str):
        """Trigger emergency analysis task"""
        logger.warning(f"Emergency analysis triggered: {symbol} - {reason}")

    def _send_alert(self, message: str):
        """Send alert notification"""
        logger.warning(f"ALERT: {message}")
