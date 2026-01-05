"""
Whale Alert Handlers
Telegram commands for whale transaction monitoring
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from integrations.whale_monitor import get_whale_monitor, WhaleTransaction
from tg_bot.formatter import TelegramFormatter

logger = logging.getLogger(__name__)


async def whale_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show latest whale transactions"""
    if not update.effective_message or not update.effective_chat:
        return

    # Parse arguments
    symbol = None
    limit = 10

    if context.args and len(context.args) >= 1:
        symbol = context.args[0].upper()
        if len(context.args) >= 2:
            try:
                limit = min(int(context.args[1]), 20)
            except ValueError:
                await update.effective_message.reply_text(
                    "❌ Invalid limit number\n\nUsage: /whale_alerts [symbol] [limit]\nExample: /whale_alerts BTC 10"
                )
                return

    try:
        # Get whale monitor
        monitor = get_whale_monitor()

        # Get transactions
        logger.info(f"Fetching whale transactions: symbol={symbol}, limit={limit}")
        transactions = await monitor.get_transactions(symbol=symbol, limit=limit)

        if not transactions:
            message = f"""🐋 *Whale Alerts*

{'No recent whale transactions found.' if not symbol else f'No recent whale transactions found for {symbol}.'}

Try again later or check whale-alert.io for more info.
"""
            await update.effective_message.reply_text(message, parse_mode='Markdown')
            return

        # Format transactions
        message = f"🐋 *Recent Whale Transactions*\n\n"

        for i, tx in enumerate(transactions[:limit], 1):
            # Analyze transaction
            impact = monitor.analyze_transaction(tx)

            # Direction emoji
            direction_emoji = {
                'BULLISH': '🟢',
                'BEARISH': '🔴',
                'NEUTRAL': '⚪'
            }.get(impact['direction'], '⚪')

            # Significance emoji
            significance_emoji = {
                'HIGH': '🔥',
                'MEDIUM': '⚡',
                'LOW': '💧'
            }.get(impact['significance'], '💧')

            # Format amount
            if tx.amount >= 1000:
                amount_str = f"{tx.amount:,.2f}"
            else:
                amount_str = f"{tx.amount:.4f}"

            message += f"""*{i}. {tx.symbol}* {direction_emoji} {significance_emoji}
💰 {amount_str} {tx.symbol} (${tx.amount_usd:,.0f})
🔄 {tx.from_owner} → {tx.to_owner}
📅 {tx.timestamp.strftime('%H:%M:%S')}
_📝 {impact['reason']}_

"""

        message += f"\n_Data from Whale Alert_"

        await update.effective_message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Whale alerts sent: {len(transactions)} transactions")

    except Exception as e:
        logger.error(f"Error in whale_alerts_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error fetching whale alerts: {str(e)}"
        )


async def whale_exchange_flow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show exchange inflows/outflows"""
    if not update.effective_message:
        return

    try:
        monitor = get_whale_monitor()

        # Get recent transactions
        transactions = await monitor.get_transactions(limit=50)

        # Filter exchange transactions
        exchange_txs = [
            tx for tx in transactions
            if tx.to_owner == 'exchange' or tx.from_owner == 'exchange'
        ]

        if not exchange_txs:
            await update.effective_message.reply_text(
                "🐋 *Exchange Flows*\n\nNo recent exchange transactions found.",
                parse_mode='Markdown'
            )
            return

        # Group by direction
        inflows = [tx for tx in exchange_txs if tx.to_owner == 'exchange']
        outflows = [tx for tx in exchange_txs if tx.from_owner == 'exchange']

        # Calculate totals
        total_inflow = sum(tx.amount_usd for tx in inflows)
        total_outflow = sum(tx.amount_usd for tx in outflows)
        net_flow = total_outflow - total_inflow

        # Format message
        direction = "🟢 Bullish (Outflow > Inflow)" if net_flow > 0 else "🔴 Bearish (Inflow > Outflow)" if net_flow < 0 else "⚪ Neutral"

        message = f"""🐋 *Exchange Flows (Last 60 min)*

📊 *Net Flow*: {direction}
💵 Total: ${abs(net_flow):,.0f}

📥 *Inflows* (Potential Selling):
   Count: {len(inflows)} transactions
   Value: ${total_inflow:,.0f}

📤 *Outflows* (Potential Buying):
   Count: {len(outflows)} transactions
   Value: ${total_outflow:,.0f}

*Recent Inflows*:
"""

        for tx in inflows[:5]:
            if tx.amount >= 1000:
                amount_str = f"{tx.amount:,.2f}"
            else:
                amount_str = f"{tx.amount:.4f}"
            message += f"• {tx.symbol}: {amount_str} (${tx.amount_usd:,.0f})\n"

        message += "\n*Recent Outflows*:\n"
        for tx in outflows[:5]:
            if tx.amount >= 1000:
                amount_str = f"{tx.amount:,.2f}"
            else:
                amount_str = f"{tx.amount:.4f}"
            message += f"• {tx.symbol}: {amount_str} (${tx.amount_usd:,.0f})\n"

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in whale_exchange_flow_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error fetching exchange flows: {str(e)}"
        )


async def whale_subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to whale alerts for a symbol"""
    if not update.effective_message or not update.effective_chat:
        return

    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text(
            "❌ Missing symbol\n\nUsage: /whale_subscribe [symbol]\nExample: /whale_subscribe BTC"
        )
        return

    symbol = context.args[0].upper()

    # Save to user preferences (re-use existing preference system)
    from tg_bot.database import db

    # Get current whale subscriptions
    whale_subs = db.get_user_preference(update.effective_chat.id, 'whale_subscriptions', '')
    subs = whale_subs.split(',') if whale_subs else []

    if symbol in subs:
        await update.effective_message.reply_text(
            f"ℹ️ You're already subscribed to whale alerts for {symbol}"
        )
        return

    subs.append(symbol)
    db.set_user_preference(update.effective_chat.id, 'whale_subscriptions', ','.join(subs))

    await update.effective_message.reply_text(
        f"✅ Subscribed to whale alerts for {symbol}!\n\n"
        f"You'll receive notifications when large transactions (> $500k) are detected."
    )
    logger.info(f"User {update.effective_chat.id} subscribed to whale alerts for {symbol}")


async def whale_unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from whale alerts for a symbol"""
    if not update.effective_message or not update.effective_chat:
        return

    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text(
            "❌ Missing symbol\n\nUsage: /whale_unsubscribe [symbol]\nExample: /whale_unsubscribe BTC"
        )
        return

    symbol = context.args[0].upper()

    from tg_bot.database import db

    # Get current whale subscriptions
    whale_subs = db.get_user_preference(update.effective_chat.id, 'whale_subscriptions', '')
    subs = whale_subs.split(',') if whale_subs else []

    if symbol not in subs:
        await update.effective_message.reply_text(
            f"ℹ️ You're not subscribed to whale alerts for {symbol}"
        )
        return

    subs.remove(symbol)
    db.set_user_preference(update.effective_chat.id, 'whale_subscriptions', ','.join(subs))

    await update.effective_message.reply_text(
        f"✅ Unsubscribed from whale alerts for {symbol}"
    )
    logger.info(f"User {update.effective_chat.id} unsubscribed from whale alerts for {symbol}")


async def whale_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List whale alert subscriptions"""
    if not update.effective_message:
        return

    from tg_bot.database import db

    whale_subs = db.get_user_preference(update.effective_chat.id, 'whale_subscriptions', '')
    subs = whale_subs.split(',') if whale_subs else []

    if not subs:
        message = """🐋 *Whale Alert Subscriptions*

You don't have any active whale alert subscriptions.

Use /whale_subscribe [symbol] to subscribe to whale alerts for a specific coin.
"""
    else:
        message = f"""🐋 *Whale Alert Subscriptions*

You're subscribed to whale alerts for:

"""
        for symbol in subs:
            message += f"• {symbol}\n"

        message += f"\nTotal: {len(subs)} symbol(s)\n\n"
        message += "Use /whale_unsubscribe [symbol] to unsubscribe."

    await update.effective_message.reply_text(message, parse_mode='Markdown')
