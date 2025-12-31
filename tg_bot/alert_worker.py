"""
Alert Notification Worker
Periodically checks price alerts and sends notifications when triggered
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from config import config
from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from collector import CryptoDataCollector

logger = logging.getLogger(__name__)


class AlertWorker:
    """Background worker for checking and triggering price alerts"""

    def __init__(self, bot_token: str):
        """Initialize alert worker"""
        self.bot = Bot(token=bot_token)
        self.collector = CryptoDataCollector()

    def format_alert_message(self, symbol: str, alert_type: str,
                           target_price: float, current_price: float) -> str:
        """Format alert notification message"""
        # Calculate difference
        diff = current_price - target_price
        diff_pct = (diff / target_price) * 100

        # Determine direction
        if alert_type == 'above':
            direction = "📈 CROSSED ABOVE!"
            if current_price > target_price:
                status = "✅ TRIGGERED"
            else:
                status = "⏳ PENDING"
        else:  # below
            direction = "📉 CROSSED BELOW!"
            if current_price < target_price:
                status = "✅ TRIGGERED"
            else:
                status = "⏳ PENDING"

        return f"""{TelegramFormatter.EMOJI['alert']} *Price Alert Triggered!*

🪙 *{symbol}*
{direction}

💰 *Target Price*: ${target_price:,.2f}
💵 *Current Price*: ${current_price:,.2f}
📊 *Difference*: {diff:+,.2f} ({diff_pct:+.2f}%)

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{status}
"""

    async def check_all_alerts(self):
        """Check and trigger all active alerts"""
        try:
            logger.info("Starting alert check cycle...")

            # Get all active alerts from database
            import sqlite3
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chat_id, symbol, alert_type, target_price
                FROM alerts
                WHERE triggered = 0
                ORDER BY created_at ASC
            """)
            alerts = cursor.fetchall()
            conn.close()

            if not alerts:
                logger.info("No active alerts found")
                return

            logger.info(f"Checking {len(alerts)} active alerts")

            triggered_count = 0

            for alert_id, chat_id, symbol, alert_type, target_price in alerts:
                try:
                    # Get user preferences for this alert
                    market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
                    exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

                    # Fetch current price based on user preferences
                    df = None
                    if exchange_pref == 'bybit':
                        df = self.collector.get_bybit_klines(symbol, "1m", limit=1)
                    else:  # binance
                        if market_pref == 'futures':
                            df = self.collector._get_binance_futures_klines(symbol, "1m", limit=1)
                        elif market_pref == 'spot':
                            df = self.collector.get_binance_klines(symbol, "1m", limit=1,
                                                                   use_cache=False, save_cache=False)
                        else:  # auto
                            df = self.collector.get_binance_klines_auto(symbol, "1m", limit=1)

                    if df is None or len(df) == 0:
                        logger.warning(f"Could not fetch price for {symbol} (alert_id: {alert_id})")
                        continue

                    current_price = df.iloc[-1]['close']

                    # Check if alert is triggered
                    triggered = False
                    if alert_type == 'above' and current_price >= target_price:
                        triggered = True
                    elif alert_type == 'below' and current_price <= target_price:
                        triggered = True

                    if triggered:
                        # Send notification
                        message = self.format_alert_message(
                            symbol, alert_type, target_price, current_price
                        )

                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )

                        # Mark alert as triggered in database
                        conn = sqlite3.connect(db.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE alerts
                            SET triggered = 1
                            WHERE id = ?
                        """, (alert_id,))
                        conn.commit()
                        conn.close()

                        triggered_count += 1
                        logger.info(f"Alert #{alert_id} triggered: {symbol} {alert_type} ${target_price:,.2f}")

                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                    else:
                        logger.debug(f"Alert #{alert_id} not triggered: {symbol} @ ${current_price:,.2f}")

                except Exception as e:
                    logger.error(f"Error processing alert #{alert_id}: {e}")
                    continue

            logger.info(f"Alert check cycle completed. Triggered {triggered_count}/{len(alerts)} alerts")

        except Exception as e:
            logger.error(f"Error in alert check cycle: {e}")

    async def check_user_alerts(self, chat_id: int) -> int:
        """Check alerts for specific user only"""
        try:
            # Get user's active alerts
            alerts = db.get_user_alerts(chat_id, active_only=True)

            if not alerts:
                return 0

            triggered_count = 0

            for alert in alerts:
                try:
                    alert_id = alert['id']
                    symbol = alert['symbol']
                    alert_type = alert['alert_type']
                    target_price = alert['target_price']

                    # Get user preferences
                    market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
                    exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

                    # Fetch current price
                    df = None
                    if exchange_pref == 'bybit':
                        df = self.collector.get_bybit_klines(symbol, "1m", limit=1)
                    else:  # binance
                        if market_pref == 'futures':
                            df = self.collector._get_binance_futures_klines(symbol, "1m", limit=1)
                        elif market_pref == 'spot':
                            df = self.collector.get_binance_klines(symbol, "1m", limit=1,
                                                                   use_cache=False, save_cache=False)
                        else:  # auto
                            df = self.collector.get_binance_klines_auto(symbol, "1m", limit=1)

                    if df is None or len(df) == 0:
                        logger.warning(f"Could not fetch price for {symbol}")
                        continue

                    current_price = df.iloc[-1]['close']

                    # Check if triggered
                    triggered = False
                    if alert_type == 'above' and current_price >= target_price:
                        triggered = True
                    elif alert_type == 'below' and current_price <= target_price:
                        triggered = True

                    if triggered:
                        # Send notification
                        message = self.format_alert_message(
                            symbol, alert_type, target_price, current_price
                        )

                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )

                        # Mark as triggered
                        db.delete_alert(alert_id, chat_id)  # Or use a method to mark as triggered

                        triggered_count += 1
                        logger.info(f"Alert triggered for {chat_id}: {symbol} {alert_type} ${target_price}")

                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing alert for {chat_id}: {e}")
                    continue

            return triggered_count

        except Exception as e:
            logger.error(f"Error checking alerts for {chat_id}: {e}")
            return 0


# Global instance
_alert_worker: Optional[AlertWorker] = None


def get_alert_worker() -> Optional[AlertWorker]:
    """Get or create alert worker instance"""
    global _alert_worker
    if _alert_worker is None:
        bot_token = config.TELEGRAM.bot_token
        if not bot_token:
            logger.error("Telegram bot token not configured")
            return None
        _alert_worker = AlertWorker(bot_token)
        logger.info("Alert worker initialized")
    return _alert_worker
