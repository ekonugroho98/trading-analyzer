"""
Signal Notification Worker
Periodically checks subscriptions and sends notifications for trading signals
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Bot
from telegram.error import TelegramError

from config import config
from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from collector import CryptoDataCollector

logger = logging.getLogger(__name__)


class SignalWorker:
    """Background worker for checking and sending trading signals"""

    def __init__(self, bot_token: str):
        """Initialize signal worker"""
        self.bot = Bot(token=bot_token)
        self.collector = CryptoDataCollector()
        self.last_signals: Dict[int, Dict[str, str]] = {}  # Track last signals per user

    def get_overall_signal(self, df) -> str:
        """Calculate overall trading signal from dataframe"""
        if df is None or len(df) < 50:
            return "HOLD"

        # Calculate indicators
        df = self.collector.calculate_indicators(df)
        latest = df.iloc[-1]
        current_price = latest['close']

        # Trend Analysis
        sma_20 = df['MA20'].iloc[-1]
        sma_50 = df['MA50'].iloc[-1]
        sma_7 = df['MA7'].iloc[-1]

        trend = "NEUTRAL"
        if current_price > sma_7 > sma_20 > sma_50:
            trend = "STRONG BULLISH"
        elif current_price > sma_20 > sma_50:
            trend = "BULLISH"
        elif current_price < sma_7 < sma_20 < sma_50:
            trend = "STRONG BEARISH"
        elif current_price < sma_20 < sma_50:
            trend = "BEARISH"

        # RSI Analysis
        rsi = latest['RSI']

        # MACD Analysis
        macd_hist = latest['MACD_hist']

        # Calculate overall signal
        signals = []
        if trend in ["STRONG BULLISH", "BULLISH"]:
            signals.append(1)
        elif trend in ["STRONG BEARISH", "BEARISH"]:
            signals.append(-1)
        else:
            signals.append(0)

        if rsi < 30:
            signals.append(1)  # Oversold = bullish
        elif rsi > 70:
            signals.append(-1)  # Overbought = bearish
        else:
            signals.append(0)

        if macd_hist > 0:
            signals.append(1)
        else:
            signals.append(-1)

        signal_sum = sum(signals)
        if signal_sum >= 2:
            return "BUY"
        elif signal_sum <= -2:
            return "SELL"
        else:
            return "HOLD"

    def format_signal_message(self, symbol: str, signal: str, price: float,
                             rsi: float, trend: str) -> str:
        """Format signal notification message"""
        emoji = {
            'BUY': '🟢',
            'SELL': '🔴',
            'HOLD': '🟡'
        }.get(signal, '⚪')

        return f"""{TelegramFormatter.EMOJI['alert']} *Trading Signal Alert*

🪙 *{symbol}*
{emoji} *Signal*: {signal}
💰 *Price*: ${price:,.2f}
📊 *Trend*: {trend}
📉 *RSI*: {rsi:.1f}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Use /ta {symbol} for detailed analysis!
"""

    async def check_user_subscriptions(self, chat_id: int) -> int:
        """Check and send signals for user's subscriptions"""
        try:
            # Get user's subscriptions
            subscriptions = db.get_user_subscriptions(chat_id)

            if not subscriptions:
                return 0

            # Get user preferences
            market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
            exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

            signals_sent = 0

            # Initialize last_signals for this user if not exists
            if chat_id not in self.last_signals:
                self.last_signals[chat_id] = {}

            for sub in subscriptions:
                try:
                    symbol = sub['symbol']

                    # Skip if we already sent this signal recently (prevent spam)
                    # Check if signal changed from last time
                    if symbol in self.last_signals[chat_id]:
                        # We'll track signals to only notify on changes
                        pass

                    # Fetch data based on user preferences
                    df = None
                    if exchange_pref == 'bybit':
                        df = self.collector.get_bybit_klines(symbol, "4h", limit=100)
                    else:  # binance
                        if market_pref == 'futures':
                            df = self.collector._get_binance_futures_klines(symbol, "4h", limit=100)
                        elif market_pref == 'spot':
                            df = self.collector.get_binance_klines(symbol, "4h", limit=100,
                                                                   use_cache=False, save_cache=False)
                        else:  # auto
                            df = self.collector.get_binance_klines_auto(symbol, "4h", limit=100)

                    if df is None or len(df) < 50:
                        logger.warning(f"Insufficient data for {symbol} (chat_id: {chat_id})")
                        continue

                    # Calculate signal
                    signal = self.get_overall_signal(df)

                    # Only send BUY or SELL signals (not HOLD)
                    if signal not in ['BUY', 'SELL']:
                        logger.debug(f"No signal for {symbol}: {signal}")
                        continue

                    # Check if signal changed from last time
                    last_signal = self.last_signals[chat_id].get(symbol, '')
                    if last_signal == signal:
                        logger.debug(f"Signal unchanged for {symbol}: {signal}")
                        continue

                    # Get additional info
                    latest = df.iloc[-1]
                    current_price = latest['close']
                    rsi = latest['RSI']

                    # Determine trend
                    sma_20 = df['MA20'].iloc[-1]
                    sma_50 = df['MA50'].iloc[-1]
                    if current_price > sma_20 > sma_50:
                        trend = "BULLISH 📈"
                    elif current_price < sma_20 < sma_50:
                        trend = "BEARISH 📉"
                    else:
                        trend = "NEUTRAL ⚪"

                    # Format and send message
                    message = self.format_signal_message(
                        symbol, signal, current_price, rsi, trend
                    )

                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )

                    # Update last signal
                    self.last_signals[chat_id][symbol] = signal
                    signals_sent += 1

                    logger.info(f"Signal sent to {chat_id}: {symbol} - {signal}")

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing {sub.get('symbol', 'unknown')}: {e}")
                    continue

            return signals_sent

        except Exception as e:
            logger.error(f"Error checking subscriptions for {chat_id}: {e}")
            return 0

    async def run_signal_check(self):
        """Run signal check for all users"""
        try:
            logger.info("Starting signal check cycle...")

            # Get all active subscriptions grouped by user
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT chat_id
                FROM subscriptions
            """)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                logger.info("No active subscriptions found")
                return

            chat_ids = [row[0] for row in rows]
            logger.info(f"Checking signals for {len(chat_ids)} users")

            total_signals = 0
            for chat_id in chat_ids:
                try:
                    signals_sent = await self.check_user_subscriptions(chat_id)
                    total_signals += signals_sent
                except Exception as e:
                    logger.error(f"Error processing chat_id {chat_id}: {e}")
                    continue

            logger.info(f"Signal check cycle completed. Sent {total_signals} signals")

        except Exception as e:
            logger.error(f"Error in signal check cycle: {e}")


# Global instance
_signal_worker: Optional[SignalWorker] = None


def get_signal_worker() -> Optional[SignalWorker]:
    """Get or create signal worker instance"""
    global _signal_worker
    if _signal_worker is None:
        bot_token = config.TELEGRAM.bot_token
        if not bot_token:
            logger.error("Telegram bot token not configured")
            return None
        _signal_worker = SignalWorker(bot_token)
        logger.info("Signal worker initialized")
    return _signal_worker
