"""
Market Screening Handlers
Handle market screening commands and scheduled screening
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.market_screener import get_screener
from tg_bot.database import db
from tg_bot.formatter import (
    format_screening_loading,
    format_screening_results,
    format_screening_error,
    format_screener_help
)
from tg_bot.screening_profiles import (
    get_profile, format_profile_list, format_profile_info,
    is_valid_interval, format_interval_choices
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
            min_score=5.0,  # Lebih longgar - 5.0+ sudah cukup menarik
            max_results=30  # Tampilkan lebih banyak results
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


async def schedule_screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule periodic market screening"""
    if not update.effective_message or not update.effective_chat:
        return

    # Parse arguments
    # Usage: /schedule_screen [timeframe] [interval_minutes] [min_score]
    timeframe = '4h'  # default
    interval_minutes = 120  # default: 2 hours
    min_score = 7.0  # default

    if context.args and len(context.args) >= 1:
        timeframe = context.args[0].lower()
        if timeframe not in ['1h', '4h']:
            await update.effective_message.reply_text(
                "❌ Invalid timeframe\n\n"
                "Usage: /schedule_screen [timeframe] [interval_minutes] [min_score]\n"
                "Example: /schedule_screen 4h 120 7.0\n\n"
                "timeframe: 1h or 4h\n"
                "interval_minutes: 15, 30, 60, 120, 180, 240, 360, 720, or 1440\n"
                "min_score: 0-10 (default: 7.0)\n\n"
                "Tip: Use /profiles for preset configurations"
            )
            return

    if len(context.args) >= 2:
        try:
            interval_minutes = int(context.args[1])
            if not is_valid_interval(interval_minutes):
                await update.effective_message.reply_text(
                    f"❌ Invalid interval_minutes: {interval_minutes}\n\n"
                    f"{format_interval_choices()}"
                )
                return
        except ValueError:
            await update.effective_message.reply_text("❌ interval_minutes must be a number")
            return

    if len(context.args) >= 3:
        try:
            min_score = float(context.args[2])
            if min_score < 0 or min_score > 10:
                await update.effective_message.reply_text("❌ min_score must be between 0 and 10")
                return
        except ValueError:
            await update.effective_message.reply_text("❌ min_score must be a number")
            return

    # Add schedule to database
    chat_id = update.effective_chat.id
    if db.add_screening_schedule(chat_id, timeframe, interval_minutes, min_score):
        await update.effective_message.reply_text(
            f"✅ *Scheduled Screening Active*\n\n"
            f"🔍 Timeframe: {timeframe}\n"
            f"⏰ Interval: Every {interval_minutes} minutes\n"
            f"📊 Min Score: {min_score}/10\n\n"
            f"You'll receive screening results automatically!\n\n"
            f"Use /my_schedules to view your schedules\n"
            f"Use /unschedule_screen [timeframe] to stop",
            parse_mode='Markdown'
        )
        logger.info(f"Screening scheduled: chat_id={chat_id}, timeframe={timeframe}, interval={interval_minutes}min")
    else:
        await update.effective_message.reply_text("❌ Failed to schedule screening")


async def unschedule_screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove scheduled screening"""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    timeframe = None

    # Parse arguments
    if context.args and len(context.args) >= 1:
        timeframe = context.args[0].lower()
        if timeframe not in ['1h', '4h']:
            await update.effective_message.reply_text(
                "❌ Invalid timeframe\n\n"
                "Usage: /unschedule_screen [timeframe]\n"
                "Example: /unschedule_screen 4h\n\n"
                "Omit timeframe to remove all schedules"
            )
            return

    # Remove schedule
    if db.remove_screening_schedule(chat_id, timeframe):
        if timeframe:
            await update.effective_message.reply_text(
                f"✅ Removed {timeframe} screening schedule"
            )
        else:
            await update.effective_message.reply_text(
                "✅ Removed all screening schedules"
            )
        logger.info(f"Screening unscheduled: chat_id={chat_id}, timeframe={timeframe}")
    else:
        await update.effective_message.reply_text(
            "❌ No active screening schedule found"
        )


async def my_schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show your screening schedules"""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    schedules = db.get_screening_schedules(chat_id)

    if not schedules:
        await update.effective_message.reply_text(
            "📅 *Your Screening Schedules*\n\n"
            "No active screening schedules.\n\n"
            "Use /schedule_screen to set up automatic screening:\n"
            "/schedule_screen 4h 120 7.0\n\n"
            "Or use preset profiles:\n"
            "/profile_moderate\n\n"
            "This will screen 4h timeframe every 2 hours and send coins with score >= 7.0",
            parse_mode='Markdown'
        )
        return

    # Format schedules
    message = "📅 *Your Screening Schedules*\n\n"

    for sched in schedules:
        interval = sched.get('interval_minutes', 120)
        # Format interval nicely
        if interval >= 60:
            hours = interval // 60
            mins = interval % 60
            if mins == 0:
                interval_str = f"{hours}h"
            else:
                interval_str = f"{hours}h {mins}m"
        else:
            interval_str = f"{interval}m"

        message += f"""*{sched['timeframe'].upper()}*
⏰ Every {interval_str}
📊 Min Score: {sched['min_score']}/10
✅ Enabled

"""

    message += f"\nTotal: {len(schedules)} schedule(s)\n\n"
    message += "Use /unschedule_screen [timeframe] to stop a schedule"

    await update.effective_message.reply_text(message, parse_mode='Markdown')


# Profile commands
async def profile_conservative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set conservative screening profile"""
    await _apply_profile(update, 'conservative')


async def profile_moderate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set moderate screening profile"""
    await _apply_profile(update, 'moderate')


async def profile_aggressive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set aggressive screening profile"""
    await _apply_profile(update, 'aggressive')


async def profile_scalper_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set scalper screening profile"""
    await _apply_profile(update, 'scalper')


async def profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available screening profiles"""
    if not update.effective_message:
        return

    await update.effective_message.reply_text(
        format_profile_list(),
        parse_mode='Markdown'
    )


async def profile_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed info about a specific profile"""
    if not update.effective_message:
        return

    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text(
            "Usage: /profile_info [profile_name]\n\n"
            "Available profiles: conservative, moderate, aggressive, scalper\n\n"
            "Example: /profile_info moderate"
        )
        return

    profile_name = context.args[0].lower()
    await update.effective_message.reply_text(
        format_profile_info(profile_name),
        parse_mode='Markdown'
    )


async def _apply_profile(update: Update, profile_name: str):
    """Apply a screening profile"""
    if not update.effective_message or not update.effective_chat:
        return

    profile = get_profile(profile_name)

    if not profile:
        await update.effective_message.reply_text(
            f"❌ Profile '{profile_name}' not found"
        )
        return

    chat_id = update.effective_chat.id

    if db.add_screening_schedule(
        chat_id=chat_id,
        timeframe=profile['timeframe'],
        interval_minutes=profile['interval_minutes'],
        min_score=profile['min_score']
    ):
        await update.effective_message.reply_text(
            f"✅ *{profile['name'].upper()} Profile Activated*\n\n"
            f"{profile['description']}\n\n"
            f"⚙️ *Configuration:*\n"
            f"• Timeframe: {profile['timeframe']}\n"
            f"• Interval: Every {profile['interval_minutes']} minutes\n"
            f"• Min Score: {profile['min_score']}/10\n"
            f"• Max Results: {profile['max_results']}\n\n"
            f"You'll receive screening results automatically!\n\n"
            f"Use /my_schedules to view your schedules",
            parse_mode='Markdown'
        )
        logger.info(f"Profile applied: chat_id={chat_id}, profile={profile_name}")
    else:
        await update.effective_message.reply_text("❌ Failed to activate profile")
