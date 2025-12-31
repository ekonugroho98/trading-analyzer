"""
Telegram Trading Bot
Main bot class with command registration
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from tg_bot.database import db
from tg_bot import handlers
from tg_bot.signal_worker import get_signal_worker
from tg_bot.alert_worker import get_alert_worker

logger = logging.getLogger(__name__)


class TelegramTradingBot:
    """Main Telegram Trading Bot"""

    def __init__(self):
        """Initialize bot"""
        self.token = config.TELEGRAM.bot_token
        self.application = None

        logger.info("Telegram Trading Bot initialized")

    def setup_handlers(self):
        """Register all command handlers"""
        app = self.application

        # Basic commands
        app.add_handler(CommandHandler("start", handlers.basic.start_command))
        app.add_handler(CommandHandler("help", handlers.basic.help_command))
        app.add_handler(CommandHandler("status", handlers.basic.status_command))
        app.add_handler(CommandHandler("settings", handlers.basic.settings_command))

        # Subscription commands
        app.add_handler(CommandHandler("subscribe", handlers.basic.subscribe_command))
        app.add_handler(CommandHandler("unsubscribe", handlers.basic.unsubscribe_command))
        app.add_handler(CommandHandler("mysubscriptions", handlers.basic.mysubscriptions_command))
        app.add_handler(CommandHandler("subscribeall", handlers.trading.subscribeall_command))

        # Alert commands
        app.add_handler(CommandHandler("setalert", handlers.basic.setalert_command))
        app.add_handler(CommandHandler("myalerts", handlers.basic.myalerts_command))
        app.add_handler(CommandHandler("delalert", handlers.basic.delalert_command))
        app.add_handler(CommandHandler("clearalerts", handlers.basic.clearalerts_command))

        # Trading commands
        app.add_handler(CommandHandler("price", handlers.trading.price_command))
        app.add_handler(CommandHandler("plan", handlers.trading.plan_command))
        app.add_handler(CommandHandler("analyze", handlers.trading.analyze_command))
        app.add_handler(CommandHandler("ta", handlers.trading.ta_command))
        app.add_handler(CommandHandler("signals", handlers.trading.signals_command))
        app.add_handler(CommandHandler("trending", handlers.trading.trending_command))

        # Portfolio commands
        from tg_bot.handlers.portfolio import PortfolioHandler
        portfolio_handler = PortfolioHandler()
        app.add_handler(CommandHandler("myportfolio", portfolio_handler.my_portfolio))
        app.add_handler(CommandHandler("addposition", portfolio_handler.add_position))
        app.add_handler(CommandHandler("closeposition", portfolio_handler.close_position))
        app.add_handler(CommandHandler("deleteposition", portfolio_handler.delete_position))

        # Callback query handlers for inline keyboards
        app.add_handler(CallbackQueryHandler(portfolio_handler.add_from_plan_callback, pattern="^add_portfolio_"))

        logger.info("All handlers registered")

    async def post_init(self, application: Application) -> None:
        """Post-initialization callback"""
        logger.info("Bot application initialized")

        # Setup signal check scheduler
        self.setup_signal_scheduler()

        # TODO: Send startup notification to admin

    def setup_signal_scheduler(self):
        """Setup periodic signal check and alert check schedulers"""
        try:
            # Get workers
            signal_worker = get_signal_worker()
            alert_worker = get_alert_worker()

            if not signal_worker and not alert_worker:
                logger.warning("No workers available, schedulers not started")
                return

            # Create scheduler
            scheduler = AsyncIOScheduler()

            # Setup signal check job
            if signal_worker:
                interval_minutes = config.TELEGRAM.signal_check_interval_minutes
                scheduler.add_job(
                    signal_worker.run_signal_check,
                    'interval',
                    minutes=interval_minutes,
                    id='signal_check',
                    name='Signal Check Job',
                    replace_existing=True
                )
                logger.info(f"Signal scheduler registered (interval: {interval_minutes} minutes)")

            # Setup alert check job (check every 1 minute for price alerts)
            if alert_worker:
                scheduler.add_job(
                    alert_worker.check_all_alerts,
                    'interval',
                    minutes=1,
                    id='alert_check',
                    name='Alert Check Job',
                    replace_existing=True
                )
                logger.info("Alert scheduler registered (interval: 1 minute)")

            # Start scheduler
            scheduler.start()
            logger.info("All schedulers started successfully")

        except Exception as e:
            logger.error(f"Failed to setup schedulers: {e}")

    async def post_shutdown(self, application: Application) -> None:
        """Post-shutdown callback"""
        logger.info("Bot application shutdown")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")

    def run(self):
        """Run the bot"""
        if not self.token:
            logger.error("Telegram bot token not configured!")
            return

        # Create application
        self.application = (
            Application.builder()
            .token(self.token)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )

        # Setup handlers
        self.setup_handlers()

        # Add error handler
        self.application.add_error_handler(self.error_handler)

        # Start bot
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


# Global bot instance
bot = TelegramTradingBot()
