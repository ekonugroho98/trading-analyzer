"""
Settings Handlers
Handle user-specific settings like default exchange
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.database import db

logger = logging.getLogger(__name__)


async def set_exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set default exchange preference"""
    if not update.effective_message or not update.effective_chat:
        return

    # Parse arguments
    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text(
            "❌ *Missing Exchange*\n\n"
            "Usage: /set_exchange [binance|bybit]\n\n"
            "Example: /set_exchange bybit\n\n"
            "This will set your default exchange for trading plan analysis.\n"
            "If the selected exchange doesn't have data for a symbol, it will automatically fallback to the other exchange.",
            parse_mode='Markdown'
        )
        return

    exchange = context.args[0].lower()

    # Validate exchange
    if exchange not in ['binance', 'bybit']:
        await update.effective_message.reply_text(
            f"❌ *Invalid Exchange*\n\n"
            f"'{exchange}' is not a valid exchange.\n\n"
            f"Valid options: binance, bybit\n\n"
            f"Example: /set_exchange bybit",
            parse_mode='Markdown'
        )
        return

    chat_id = update.effective_chat.id

    # Save to database
    if db.set_user_preference(chat_id, 'default_exchange', exchange):
        await update.effective_message.reply_text(
            f"✅ *Default Exchange Updated*\n\n"
            f"Your default exchange is now: *{exchange.upper()}*\n\n"
            f"Trading plans will use {exchange.upper()} as the primary data source.\n"
            f"If data is unavailable, it will automatically fallback to {'BINANCE' if exchange == 'bybit' else 'BYBIT'}.\n\n"
            f"Use /my_exchange to view your current setting.",
            parse_mode='Markdown'
        )
        logger.info(f"User {chat_id} set default exchange to {exchange}")
    else:
        await update.effective_message.reply_text("❌ Failed to update exchange preference")


async def my_exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current exchange preference"""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id

    # Get user preference
    exchange = db.get_user_preference(chat_id, 'default_exchange', default='bybit')

    await update.effective_message.reply_text(
        f"💱 *Your Exchange Settings*\n\n"
        f"Default Exchange: *{exchange.upper()}*\n\n"
        f"Your trading plans will use {exchange.upper()} as the primary data source.\n"
        f"If data is unavailable, it will automatically fallback to {'BINANCE' if exchange == 'bybit' else 'BYBIT'}.\n\n"
        f"To change your default exchange:\n"
        f"/set_exchange [binance|bybit]",
        parse_mode='Markdown'
    )


