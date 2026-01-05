"""
Signal History Handlers
Telegram commands for viewing signal history and statistics
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from analytics.signal_tracker import get_signal_tracker

logger = logging.getLogger(__name__)


async def signal_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show signal history for a symbol"""
    if not update.effective_message or not update.effective_chat:
        return

    # Parse arguments
    symbol = None
    limit = 20

    if context.args and len(context.args) >= 1:
        symbol = context.args[0].upper()
        if len(context.args) >= 2:
            try:
                limit = min(int(context.args[1]), 50)
            except ValueError:
                await update.effective_message.reply_text(
                    "❌ Invalid limit number\n\nUsage: /signal_history [symbol] [limit]\nExample: /signal_history BTCUSDT 20"
                )
                return

    try:
        tracker = get_signal_tracker()
        chat_id = update.effective_chat.id

        # Get signal history
        signals = tracker.get_signal_history(
            user_id=chat_id,
            symbol=symbol,
            limit=limit
        )

        if not signals:
            message = f"""📊 *Signal History*

{'No signals found in your history.' if not symbol else f'No signals found for {symbol}.'}

Use /plan command to generate new trading signals!
"""
            await update.effective_message.reply_text(message, parse_mode='Markdown')
            return

        # Format signals
        message = f"""📊 *Signal History*

Showing {len(signals)} recent signals

"""

        for sig in signals[:limit]:
            # Signal type emoji
            signal_emoji = {
                'BUY': '🟢',
                'SELL': '🔴',
                'HOLD': '🟡'
            }.get(sig['signal_type'], '⚪')

            # Outcome emoji
            outcome_emoji = {
                'won': '✅',
                'lost': '❌',
                'breakeven': '⚪',
                'pending': '⏳'
            }.get(sig['outcome'], '⏳')

            # Format entries
            entries_str = ', '.join([f"${e:,.2f}" for e in sig['entries'][:3]])

            # Format take profits
            tps = sig['take_profits'][:2]
            tps_str = ', '.join([f"${tp['level']:,.2f}" for tp in tps])

            message += f"""*{sig['symbol']}* {sig['timeframe']} {signal_emoji} {outcome_emoji}
Signal: {sig['signal_type']} ({sig['confidence']:.0%} confidence)
Entry: {entries_str}
TPs: {tps_str}
SL: ${sig['stop_loss']:,.2f}
Outcome: {sig['outcome'].upper()}
Date: {datetime.fromisoformat(sig['generated_at']).strftime('%Y-%m-%d %H:%M')}

"""

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in signal_history_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error fetching signal history: {str(e)}"
        )


async def signal_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show signal statistics"""
    if not update.effective_message:
        return

    # Parse arguments
    days = 30

    if context.args and len(context.args) >= 1:
        try:
            days = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text(
                "❌ Invalid days number\n\nUsage: /signal_stats [days]\nExample: /signal_stats 30"
            )
            return

    try:
        tracker = get_signal_tracker()
        chat_id = update.effective_chat.id

        # Get stats
        stats = tracker.get_signal_stats(user_id=chat_id, days=days)

        # Format message
        message = f"""📈 *Signal Statistics* (Last {days} days)

*Overview*:
  Total Signals: {stats['total_signals']}
  ✅ Wins: {stats['wins']}
  ❌ Losses: {stats['losses']}
  ⚪ Breakeven: {stats['breakeven']}
  ⏳ Pending: {stats['pending']}

*Performance*:
  Win Rate: {stats['win_rate']:.1f}%
  Avg Confidence: {stats['avg_confidence']:.1%}

*Insights*:
  Avg Win Confidence: {stats['avg_win_confidence']:.1%}
  Avg Loss Confidence: {stats['avg_loss_confidence']:.1%}
"""

        # Add insights
        if stats['win_rate'] >= 60:
            message += "\n🔥 Excellent win rate! Keep it up!"
        elif stats['win_rate'] >= 50:
            message += "\n👍 Good win rate! Above breakeven."
        elif stats['win_rate'] >= 40:
            message += "\n⚠️ Win rate needs improvement."
        else:
            message += "\n❌ Low win rate. Consider adjusting strategy."

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in signal_stats_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error calculating stats: {str(e)}"
        )


async def best_signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show best performing signals"""
    if not update.effective_message:
        return

    # Parse arguments
    limit = 10

    if context.args and len(context.args) >= 1:
        try:
            limit = min(int(context.args[0]), 20)
        except ValueError:
            await update.effective_message.reply_text(
                "❌ Invalid limit number\n\nUsage: /best_signals [limit]\nExample: /best_signals 10"
            )
            return

    try:
        tracker = get_signal_tracker()
        chat_id = update.effective_chat.id

        # Get best signals
        signals = tracker.get_best_signals(user_id=chat_id, limit=limit, sort_by='confidence')

        if not signals:
            await update.effective_message.reply_text(
                "🏆 *Best Signals*\n\nNo completed signals found yet.\n\nUse /plan to generate signals and track performance!",
                parse_mode='Markdown'
            )
            return

        # Format message
        message = f"🏆 *Top {len(signals)} Best Signals*\n\n"

        for i, sig in enumerate(signals, 1):
            signal_emoji = {
                'BUY': '🟢',
                'SELL': '🔴',
                'HOLD': '🟡'
            }.get(sig['signal_type'], '⚪')

            outcome_emoji = {
                'won': '✅',
                'lost': '❌',
                'breakeven': '⚪'
            }.get(sig['outcome'], '')

            entries_str = ', '.join([f"${e:,.2f}" for e in sig['entries'][:2]])

            message += f"""*{i}. {sig['symbol']}* {sig['timeframe']} {signal_emoji} {outcome_emoji}
Signal: {sig['signal_type']} ({sig['confidence']:.0%})
Entry: {entries_str}
Outcome: {sig['outcome'].upper()}
Date: {datetime.fromisoformat(sig['generated_at']).strftime('%Y-%m-%d')}

"""

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in best_signals_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error fetching best signals: {str(e)}"
        )


async def worst_signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worst performing signals"""
    if not update.effective_message:
        return

    # Parse arguments
    limit = 10

    if context.args and len(context.args) >= 1:
        try:
            limit = min(int(context.args[0]), 20)
        except ValueError:
            await update.effective_message.reply_text(
                "❌ Invalid limit number\n\nUsage: /worst_signals [limit]\nExample: /worst_signals 10"
            )
            return

    try:
        tracker = get_signal_tracker()
        chat_id = update.effective_chat.id

        # Get worst signals
        signals = tracker.get_worst_signals(user_id=chat_id, limit=limit)

        if not signals:
            await update.effective_message.reply_text(
                "📉 *Worst Signals*\n\nNo losing signals found! That's great! 🎉",
                parse_mode='Markdown'
            )
            return

        # Format message
        message = f"📉 *Top {len(signals)} Worst Signals*\n\n"

        for i, sig in enumerate(signals, 1):
            signal_emoji = {
                'BUY': '🟢',
                'SELL': '🔴',
                'HOLD': '🟡'
            }.get(sig['signal_type'], '⚪')

            entries_str = ', '.join([f"${e:,.2f}" for e in sig['entries'][:2]])

            loss = sig.get('actual_outcome', 0)
            if loss:
                loss_str = f"Loss: ${loss:,.2f}"
            else:
                loss_str = "Loss: SL hit"

            message += f"""*{i}. {sig['symbol']}* {sig['timeframe']} {signal_emoji} ❌
Signal: {sig['signal_type']} ({sig['confidence']:.0%})
Entry: {entries_str}
{loss_str}
Date: {datetime.fromisoformat(sig['generated_at']).strftime('%Y-%m-%d')}

"""

        message += "\n💡 Analyze these losses to improve your strategy!"

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in worst_signals_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error fetching worst signals: {str(e)}"
        )


async def signal_accuracy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show signal accuracy by timeframe"""
    if not update.effective_message:
        return

    try:
        tracker = get_signal_tracker()
        chat_id = update.effective_chat.id

        # Get performance by timeframe
        timeframe_perf = tracker.get_performance_by_timeframe(user_id=chat_id, days=30)

        if not timeframe_perf:
            await update.effective_message.reply_text(
                "📊 *Signal Accuracy by Timeframe*\n\nNo data available yet.\n\nGenerate more signals to see accuracy breakdown!",
                parse_mode='Markdown'
            )
            return

        # Format message
        message = "📊 *Signal Accuracy by Timeframe*\n\n"

        for perf in timeframe_perf:
            # Performance bar
            bar_length = int(perf['win_rate'] / 10)
            bar = '█' * bar_length + '░' * (10 - bar_length)

            message += f"""*{perf['timeframe']}*
  Win Rate: {perf['win_rate']:.1f}% {bar}
  Signals: {perf['total_signals']} (W:{perf['wins']} L:{perf['losses']})
  Avg Confidence: {perf['avg_confidence']:.1%}

"""

        await update.effective_message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in signal_accuracy_command: {e}", exc_info=True)
        await update.effective_message.reply_text(
            f"❌ Error calculating accuracy: {str(e)}"
        )
