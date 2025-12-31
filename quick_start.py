# quick_start.py
#!/usr/bin/env python3
"""
QUICK START - Crypto Trading System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collector import CryptoDataCollector
from deepseek_integration import DeepSeekTradingAnalyzer, AnalysisRequest
from scheduler import TradingScheduler
import logging

def main():
    """Quick start example"""
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting Crypto Trading System...")
    
    # 1. Collect data
    print("\n1. Collecting market data...")
    collector = CryptoDataCollector()
    btc_data = collector.get_binance_klines("BTCUSDT", "1h", 100)
    
    if btc_data is not None:
        print(f"   ✓ Collected {len(btc_data)} BTC candles")
    
    # 2. Analyze with DeepSeek
    print("\n2. Analyzing with DeepSeek AI...")
    analyzer = DeepSeekTradingAnalyzer()
    
    request = AnalysisRequest(
        symbol="BTCUSDT",
        timeframe="1h",
        analysis_type="technical"
    )
    
    result = analyzer.analyze(request)
    print(f"   ✓ Analysis completed: {result.summary[:100]}...")
    
    # 3. Setup scheduler
    print("\n3. Setting up scheduler...")
    scheduler = TradingScheduler()
    scheduler.setup_default_tasks()
    
    # Start in background
    scheduler.start(background=True)
    print("   ✓ Scheduler started in background")
    
    print("\n✅ System started successfully!")
    print("\n📊 Running components:")
    print("   • Data Collector: Ready")
    print("   • DeepSeek Analyzer: Ready")
    print("   • Task Scheduler: Running")
    print("\nPress Ctrl+C to stop...")
    
    # Keep running
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping system...")
        scheduler.stop()
        print("✅ System stopped")

if __name__ == "__main__":
    main()