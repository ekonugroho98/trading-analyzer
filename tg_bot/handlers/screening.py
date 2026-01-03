"""
Market Screening Handlers
Handle market screening commands
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.market_screener import get_screener
from tg_bot.formatter import (
    format_screening_loading,
    format_screening_results,
    format_screening_error,
    format_screener_help
)

logger = logging.getLogger(__name__)


async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Screen market for good trading setups"""
    if not update.effective_message or not update.effective_chat:
        return

    # Parse arguments
    timeframe = '4h'  # default
    limit = 100  # default

    if context.args:
        if len(context.args) >= 1:
            timeframe = context.args[0].lower()
            # Validate timeframe
            if timeframe not in ['1h', '4h']:
                await update.effective_message.reply_text(
                    f"❌ Invalid timeframe: {timeframe}\n\n"
                    f"Use 1h or 4h"
                )
                return

        if len(context.args) >= 2:
            try:
                limit = int(context.args[1])
                if limit < 10 or limit > 500:
                    await update.effective_message.reply_text(
                        f"❌ Invalid limit: {limit}\n\n"
                        f"Limit must be between 10 and 500"
                    )
                    return
            except ValueError:
                await update.effective_message.reply_text(
                    f"❌ Invalid limit: {context.args[1]}\n\n"
                    f"Limit must be a number"
                )
                return

    # Send loading message
    loading_msg = await update.effective_message.reply_text(
        format_screening_loading(timeframe, limit),
        parse_mode='Markdown'
    )

    try:
        # Get screener instance
        screener = get_screener()

        # Run screening
        logger.info(f"Starting market screening: {timeframe} timeframe, {limit} coins")

        results = await screener.screen_market(
            timeframe=timeframe,
            limit=limit,
            min_score=7.0,
            max_results=20
        )

        # Get summary
        summary = await screener.get_screening_summary(results, timeframe)

        # Delete loading message
        await loading_msg.delete()

        # Send results
        if results:
            result_msg = format_screening_results(results, summary)
            await update.effective_message.reply_text(
                result_msg,
                parse_mode='Markdown'
            )

            logger.info(f"Screening complete: {len(results)} coins found")
        else:
            await update.effective_message.reply_text(
                format_screening_results(results, summary),
                parse_mode='Markdown'
            )

            logger.info("Screening complete: No coins passed")

    except Exception as e:
        logger.error(f"Error in screen_command: {e}", exc_info=True)

        # Delete loading message
        try:
            await loading_msg.delete()
        except:
            pass

        # Send error message
        await update.effective_message.reply_text(
            format_screening_error(str(e)),
            parse_mode='Markdown'
        )


async def screener_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show screener help"""
    if not update.effective_message:
        return

    await update.effective_message.reply_text(
        format_screener_help(),
        parse_mode='Markdown'
    )
