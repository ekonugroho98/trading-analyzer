"""
Basic Command Handlers
Handle /start, /help, /status commands
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from tg_bot.permissions import require_feature

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Register user in database
        db.add_user(
            chat_id=chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Send welcome message
        welcome_msg = TelegramFormatter.welcome(user.username if user.username else user.first_name)
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

        logger.info(f"User started bot: {chat_id} (@{user.username})")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        # Update last active
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Send help message (plain text, no formatting)
        help_msg = TelegramFormatter.help_command()
        await update.message.reply_text(help_msg)

    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        # Update last active
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get system status
        status = {
            'running': True,
            'streaming': False,  # TODO: Check actual streaming status
            'scheduler': False,  # TODO: Check actual scheduler status
            'total_users': len(db.get_all_users()),
            'messages_processed': 0,  # TODO: Track messages
            'uptime': 'Unknown'  # TODO: Track uptime
        }

        status_msg = TelegramFormatter.system_status(status)
        await update.message.reply_text(status_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


@require_feature('subscribe')
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    try:
        from config import config

        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /subscribe [symbol]\nExample: /subscribe BTCUSDT"
            )
            return

        symbol = context.args[0].upper()

        # Check subscription limit
        current_subs = db.get_user_subscriptions(chat_id)
        max_subs = config.TELEGRAM.max_subscriptions_per_user

        if len(current_subs) >= max_subs:
            await update.message.reply_text(
                TelegramFormatter.error_message(
                    f"Subscription limit reached ({max_subs}). "
                    f"Use /unsubscribe to remove some first."
                )
            )
            return

        # Add subscription
        if db.add_subscription(chat_id, symbol):
            await update.message.reply_text(
                TelegramFormatter.success_message(
                    f"Subscribed to {symbol}\n"
                    f"({len(current_subs) + 1}/{max_subs} subscriptions)"
                )
            )
        else:
            await update.message.reply_text(
                TelegramFormatter.error_message("Failed to subscribe")
            )

    except Exception as e:
        logger.error(f"Error in subscribe_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


@require_feature('subscribe')
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unsubscribe command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /unsubscribe [symbol]\nExample: /unsubscribe BTCUSDT"
            )
            return

        symbol = context.args[0].upper()

        # Remove subscription
        if db.remove_subscription(chat_id, symbol):
            await update.message.reply_text(
                TelegramFormatter.success_message(f"Unsubscribed from {symbol}")
            )
        else:
            await update.message.reply_text(
                TelegramFormatter.error_message("Failed to unsubscribe")
            )

    except Exception as e:
        logger.error(f"Error in unsubscribe_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


@require_feature('subscribe')
async def mysubscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mysubscriptions command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get user subscriptions
        subscriptions = db.get_user_subscriptions(chat_id)

        # Format and send
        subs_msg = TelegramFormatter.subscriptions_list(subscriptions)
        await update.message.reply_text(subs_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in mysubscriptions_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


@require_feature('list_alerts')
async def myalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myalerts command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get user alerts
        alerts = db.get_user_alerts(chat_id, active_only=True)

        # Format and send
        alerts_msg = TelegramFormatter.alerts_list(alerts)
        await update.message.reply_text(alerts_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in myalerts_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


@require_feature('add_alert')
async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setalert command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Parse args: /setalert [symbol] [above/below] [price]
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /setalert [symbol] [above/below] [price]\n"
                "Example: /setalert BTCUSDT above 90000"
            )
            return

        symbol = context.args[0].upper()
        alert_type = context.args[1].lower()

        if alert_type not in ['above', 'below']:
            await update.message.reply_text(
                "Alert type must be 'above' or 'below'\n"
                "Example: /setalert BTCUSDT above 90000"
            )
            return

        try:
            target_price = float(context.args[2])
        except ValueError:
            await update.message.reply_text("Invalid price format. Use: /setalert BTCUSDT above 90000")
            return

        # Add alert
        alert_id = db.add_alert(chat_id, symbol, alert_type, target_price)

        if alert_id:
            await update.message.reply_text(
                TelegramFormatter.success_message(
                    f"Alert set: {symbol} {alert_type} ${target_price:,.2f} (ID: {alert_id})"
                )
            )
        else:
            await update.message.reply_text(
                TelegramFormatter.error_message("Failed to set alert")
            )

    except Exception as e:
        logger.error(f"Error in setalert_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def delalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delalert command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get alert ID from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /delalert [alert_id]\nExample: /delalert 123"
            )
            return

        try:
            alert_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid alert ID. Use: /delalert 123")
            return

        # Delete alert
        if db.delete_alert(alert_id, chat_id):
            await update.message.reply_text(
                TelegramFormatter.success_message(f"Alert #{alert_id} deleted")
            )
        else:
            await update.message.reply_text(
                TelegramFormatter.error_message("Failed to delete alert or alert not found")
            )

    except Exception as e:
        logger.error(f"Error in delalert_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def clearalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearalerts command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Clear all alerts
        if db.clear_user_alerts(chat_id):
            await update.message.reply_text(
                TelegramFormatter.success_message("All alerts cleared")
            )
        else:
            await update.message.reply_text(
                TelegramFormatter.error_message("Failed to clear alerts")
            )

    except Exception as e:
        logger.error(f"Error in clearalerts_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - View and change user settings"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get current settings
        user = db.get_user(chat_id)
        if not user:
            await update.message.reply_text(
                TelegramFormatter.error_message("Please start the bot first with /start")
            )
            return

        # Check if user wants to change setting
        if context.args and len(context.args) > 0:
            setting_type = context.args[0].lower()

            # Market type settings
            if setting_type in ['auto', 'spot', 'futures']:
                db.set_user_preference(chat_id, 'market_type', setting_type)
                await update.message.reply_text(
                    TelegramFormatter.success_message(
                        f"Market type changed to: {setting_type.upper()}"
                    )
                )
                return

            # Exchange settings
            elif setting_type in ['binance', 'bybit']:
                db.set_user_preference(chat_id, 'exchange', setting_type)
                await update.message.reply_text(
                    TelegramFormatter.success_message(
                        f"Exchange changed to: {setting_type.upper()}"
                    )
                )
                return

            else:
                await update.message.reply_text(
                    TelegramFormatter.error_message(
                        f"Invalid setting: {setting_type}\n\n"
                        "Valid options:\n"
                        "• Market type: auto, spot, futures\n"
                        "• Exchange: binance, bybit\n\n"
                        "Usage: /settings [option]\n"
                        "Example: /settings binance"
                    )
                )
                return

        # Get current preferences
        market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
        exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

        settings_text = f"""⚙️ *Your Settings*

📊 *Market Type*: {market_pref.upper()}
🏦 *Exchange*: {exchange_pref.upper()}

*Market Type Options:*
• auto - Auto-detect (try futures first, then spot)
• spot - Spot market only
• futures - Futures market only

*Exchange Options:*
• binance - Binance (default)
• bybit - Bybit

*Usage:*
/settings [option]

*Examples:*
/settings futures  - Set market to futures
/settings binance  - Set exchange to Binance
/settings bybit    - Set exchange to Bybit
/settings auto     - Set market to auto

*Commands Using These Settings:*
• /plan - Generate trading plan
• /price - Get current price
• /analyze - Technical analysis"""

        await update.message.reply_text(settings_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in settings_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )
