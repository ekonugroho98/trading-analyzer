"""
Scheduled Screening Worker
Handles periodic market screening and notifications
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from telegram import Bot

from tg_bot.market_screener import get_screener
from tg_bot.database import db
from tg_bot.formatter import format_screening_results, TelegramFormatter
from deepseek_integration import TradingPlanGenerator, AnalysisRequest

logger = logging.getLogger(__name__)


def is_actionable_signal(trading_plan) -> bool:
    """Check if trading plan signal is actionable (not HOLD/WAIT)

    Args:
        trading_plan: TradingPlan object

    Returns:
        True if signal is BUY or SELL, False if HOLD/WAIT
    """
    signal_type = trading_plan.overall_signal.signal_type.upper()
    return signal_type in ['BUY', 'SELL']


class ScreeningWorker:
    """Manage scheduled market screening tasks"""

    def __init__(self, bot: Bot):
        """Initialize screening worker

        Args:
            bot: Telegram bot instance for sending notifications
        """
        self.bot = bot
        self.screener = get_screener()
        logger.info("Screening worker initialized")

    async def run_scheduled_screening(self):
        """Run scheduled market screening for all subscribed users"""
        try:
            # Get all users with screening schedules
            schedules = db.get_all_screening_schedules()

            if not schedules:
                logger.debug("No screening schedules found")
                return

            logger.info(f"Running scheduled screening for {len(schedules)} users")

            # Group schedules by timeframe to reduce API calls
            schedules_by_timeframe: Dict[str, List[Dict]] = {
                '1h': [],
                '4h': []
            }

            for schedule in schedules:
                timeframe = schedule.get('timeframe', '4h')
                if timeframe in schedules_by_timeframe:
                    schedules_by_timeframe[timeframe].append(schedule)

            # Run screening for each timeframe
            for timeframe, user_schedules in schedules_by_timeframe.items():
                if not user_schedules:
                    continue

                try:
                    logger.info(f"Running {timeframe} screening for {len(user_schedules)} users")

                    # Run market screening once per timeframe
                    results = await self.screener.screen_market(
                        timeframe=timeframe,
                        limit=100,
                        min_score=7.0,
                        max_results=20
                    )

                    # Get summary
                    summary = await self.screener.get_screening_summary(results, timeframe)

                    # Send results to each subscribed user
                    for schedule in user_schedules:
                        chat_id = schedule['user_id']
                        min_score = schedule.get('min_score', 7.0)

                        # Filter results by user's min score
                        filtered_results = [
                            r for r in results
                            if r.get('score', 0) >= min_score
                        ]

                        if filtered_results:
                            try:
                                # Send screening results
                                message = format_screening_results(filtered_results, summary)
                                await self.bot.send_message(
                                    chat_id=chat_id,
                                    text=message,
                                    parse_mode='Markdown'
                                )
                                logger.info(f"Sent {timeframe} screening results to user {chat_id}: {len(filtered_results)} coins")

                                # Auto-generate trading plans for top coins
                                # Create background task to generate and send actionable signals
                                asyncio.create_task(
                                    self._generate_and_send_plans_scheduled(
                                        filtered_results, timeframe, chat_id
                                    )
                                )

                            except Exception as e:
                                logger.error(f"Failed to send screening results to user {chat_id}: {e}")

                        else:
                            logger.debug(f"No coins passed min_score {min_score} for user {chat_id}")

                except Exception as e:
                    logger.error(f"Error in {timeframe} scheduled screening: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in run_scheduled_screening: {e}", exc_info=True)

    async def _generate_and_send_plans_scheduled(
        self,
        results: list,
        timeframe: str,
        chat_id: int
    ):
        """Generate trading plans for scheduled screening and send actionable ones

        Args:
            results: List of screening results
            timeframe: Timeframe used for screening
            chat_id: Telegram chat ID to send plans to
        """
        if not results:
            return

        # Limit to top 5 results for scheduled screenings (to avoid overwhelming)
        top_results = results[:5]

        # Get user's preferred exchange
        preferred_exchange = db.get_user_preference(chat_id, 'default_exchange', default='bybit')

        generator = TradingPlanGenerator()
        loop = asyncio.get_event_loop()

        logger.info(f"Generating trading plans for scheduled screening: {len(top_results)} coins for user {chat_id}")

        actionable_count = 0

        for i, result in enumerate(top_results, 1):
            try:
                symbol = result.get('symbol', '')
                if not symbol:
                    continue

                logger.info(f"Generating plan {i}/{len(top_results)}: {symbol}")

                # Create analysis request
                request = AnalysisRequest(
                    symbol=symbol,
                    timeframe=timeframe,
                    data_points=100,
                    preferred_exchange=preferred_exchange,
                    analysis_type="trading_plan"
                )

                # Generate trading plan
                plan = await loop.run_in_executor(None, generator.generate_trading_plan, request)

                # Check if signal is actionable (not HOLD/WAIT)
                if plan and is_actionable_signal(plan):
                    try:
                        # Send the trading plan
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=TelegramFormatter.trading_plan(plan),
                            parse_mode='Markdown'
                        )
                        actionable_count += 1
                        logger.info(f"Sent actionable plan for {symbol}: {plan.overall_signal.signal_type}")

                        # Small delay between messages to avoid rate limiting
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Failed to send plan for {symbol}: {e}")
                else:
                    logger.info(f"Skipping {symbol} - signal is {plan.overall_signal.signal_type if plan else 'FAILED'}")

            except Exception as e:
                logger.error(f"Failed to generate plan for {result.get('symbol', 'unknown')}: {e}")
                continue

        # Send summary
        summary_msg = f"""✅ *Scheduled Auto-Plans Complete*

Generated plans for {len(top_results)} coins
Sent {actionable_count} actionable signals

⏱️ Timeframe: {timeframe}
💱 Exchange: {preferred_exchange.upper()}

*Note*: Only BUY/SELL signals are sent. HOLD/WAIT signals are filtered out automatically."""

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=summary_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send summary: {e}")


# Global screening worker instance
_screening_worker: Optional[ScreeningWorker] = None


def get_screening_worker() -> Optional[ScreeningWorker]:
    """Get global screening worker instance

    Returns:
        ScreeningWorker instance or None if not initialized
    """
    return _screening_worker


def init_screening_worker(bot: Bot) -> ScreeningWorker:
    """Initialize global screening worker

    Args:
        bot: Telegram bot instance

    Returns:
        ScreeningWorker instance
    """
    global _screening_worker
    _screening_worker = ScreeningWorker(bot)
    return _screening_worker
