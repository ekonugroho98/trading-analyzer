"""
Scheduled Screening Worker
Handles periodic market screening and notifications
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from telegram import Bot

from tg_bot.market_screener import get_screener
from tg_bot.database import db
from tg_bot.formatter import format_screening_results

logger = logging.getLogger(__name__)


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

                            except Exception as e:
                                logger.error(f"Failed to send screening results to user {chat_id}: {e}")

                        else:
                            logger.debug(f"No coins passed min_score {min_score} for user {chat_id}")

                except Exception as e:
                    logger.error(f"Error in {timeframe} scheduled screening: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in run_scheduled_screening: {e}", exc_info=True)


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
