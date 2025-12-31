#!/usr/bin/env python3
"""
Telegram Trading Bot Runner
Start the Telegram trading bot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from tg_bot.bot import TelegramTradingBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🚀 Starting Telegram Trading Bot...")
    logger.info("=" * 60)

    try:
        # Create and run bot
        bot = TelegramTradingBot()
        bot.run()

    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
