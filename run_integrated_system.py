#!/usr/bin/env python3
"""
INTEGRATED STREAMING-SCHEDULER RUNNER
Run sistem trading terintegrasi
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import signal
from datetime import datetime

from streaming_scheduler_integration import IntegratedTradingSystem

def main():
    """Main function untuk run integrated system"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Create integrated system
    system = IntegratedTradingSystem()

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutting down integrated system...")
        system.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start system
    logger.info("🚀 Starting Integrated Trading System...")
    logger.info("=" * 60)

    if system.start():
        logger.info("✅ System started successfully!")
        logger.info("\n📊 System Components:")
        logger.info("  - Real-time Streaming: ACTIVE")
        logger.info("  - Scheduled Tasks: ACTIVE")
        logger.info("  - Event Processing: ACTIVE")
        logger.info("\n🔍 Monitoring Symbols: BTCUSDT, ETHUSDT, BNBUSDT")
        logger.info("\n⚡ Alert Thresholds:")
        logger.info("  - Price Change: 3% in 5min")
        logger.info("  - Volume Spike: 2.5x average")
        logger.info("  - Volatility Spike: 2x average")
        logger.info("\nPress Ctrl+C to stop\n")

        try:
            # Keep main thread alive
            while system.running:
                import time
                time.sleep(1)

        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        logger.error("❌ Failed to start system")
        sys.exit(1)

if __name__ == "__main__":
    main()
