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
from tg_bot.screening_worker import init_screening_worker, get_screening_worker
from tg_bot.paper_trading import PaperTradingManager

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

        # Portfolio commands (admin only)
        from tg_bot.handlers.portfolio import PortfolioHandler
        from tg_bot.permissions import require_admin
        portfolio_handler = PortfolioHandler()

        @require_admin
        async def myportfolio_wrapper(update, context):
            return await portfolio_handler.my_portfolio(update, context)

        @require_admin
        async def addposition_wrapper(update, context):
            return await portfolio_handler.add_position(update, context)

        @require_admin
        async def closeposition_wrapper(update, context):
            return await portfolio_handler.close_position(update, context)

        @require_admin
        async def deleteposition_wrapper(update, context):
            return await portfolio_handler.delete_position(update, context)

        app.add_handler(CommandHandler("myportfolio", myportfolio_wrapper))
        app.add_handler(CommandHandler("addposition", addposition_wrapper))
        app.add_handler(CommandHandler("closeposition", closeposition_wrapper))
        app.add_handler(CommandHandler("deleteposition", deleteposition_wrapper))

        # Paper trading commands (NEW)
        from tg_bot.handlers.paper_trading import (
            portfolio_start, portfolio_add, portfolio_close,
            portfolio_list, portfolio_help,
            portfolio_confirm_callback, portfolio_cancel_callback
        )
        app.add_handler(CommandHandler("portfolio", portfolio_start))
        app.add_handler(CommandHandler("portfolio_add", portfolio_add))
        app.add_handler(CommandHandler("portfolio_close", portfolio_close))
        app.add_handler(CommandHandler("portfolio_list", portfolio_list))
        app.add_handler(CommandHandler("portfolio_help", portfolio_help))

        # Market screening commands (NEW)
        from tg_bot.handlers.screening import (
            screen_command, screener_help_command, screen_auto_command,
            schedule_screen_command, unschedule_screen_command, my_schedules_command,
            profile_conservative_command, profile_moderate_command,
            profile_aggressive_command, profile_scalper_command,
            profiles_command, profile_info_command
        )
        app.add_handler(CommandHandler("screen", screen_command))
        app.add_handler(CommandHandler("screen_auto", screen_auto_command))
        app.add_handler(CommandHandler("screener_help", screener_help_command))
        app.add_handler(CommandHandler("schedule_screen", schedule_screen_command))
        app.add_handler(CommandHandler("unschedule_screen", unschedule_screen_command))
        app.add_handler(CommandHandler("my_schedules", my_schedules_command))

        # Profile commands (NEW)
        app.add_handler(CommandHandler("profile_conservative", profile_conservative_command))
        app.add_handler(CommandHandler("profile_moderate", profile_moderate_command))
        app.add_handler(CommandHandler("profile_aggressive", profile_aggressive_command))
        app.add_handler(CommandHandler("profile_scalper", profile_scalper_command))
        app.add_handler(CommandHandler("profiles", profiles_command))
        app.add_handler(CommandHandler("profile_info", profile_info_command))

        # Whale alert commands (NEW)
        from tg_bot.handlers.whale import (
            whale_alerts_command, whale_exchange_flow_command,
            whale_subscribe_command, whale_unsubscribe_command, whale_list_command
        )
        app.add_handler(CommandHandler("whale_alerts", whale_alerts_command))
        app.add_handler(CommandHandler("whale_flow", whale_exchange_flow_command))
        app.add_handler(CommandHandler("whale_subscribe", whale_subscribe_command))
        app.add_handler(CommandHandler("whale_unsubscribe", whale_unsubscribe_command))
        app.add_handler(CommandHandler("whale_list", whale_list_command))

        # Signal history commands (NEW)
        from tg_bot.handlers.signal_history import (
            signal_history_command, signal_stats_command,
            best_signals_command, worst_signals_command, signal_accuracy_command
        )
        app.add_handler(CommandHandler("signal_history", signal_history_command))
        app.add_handler(CommandHandler("signal_stats", signal_stats_command))
        app.add_handler(CommandHandler("best_signals", best_signals_command))
        app.add_handler(CommandHandler("worst_signals", worst_signals_command))
        app.add_handler(CommandHandler("signal_accuracy", signal_accuracy_command))

        # Settings commands (NEW)
        from tg_bot.handlers.settings import (
            set_exchange_command, my_exchange_command
        )
        app.add_handler(CommandHandler("set_exchange", set_exchange_command))
        app.add_handler(CommandHandler("my_exchange", my_exchange_command))

        # Admin commands (NEW)
        from tg_bot.handlers.admin import (
            users_command, ban_command, unban_command, promote_command, demote_command,
            set_tier_command, grant_feature_command, revoke_feature_command,
            subscription_history_command, stats_command, broadcast_command
        )
        app.add_handler(CommandHandler("users", users_command))
        app.add_handler(CommandHandler("ban", ban_command))
        app.add_handler(CommandHandler("unban", unban_command))
        app.add_handler(CommandHandler("promote", promote_command))
        app.add_handler(CommandHandler("demote", demote_command))
        app.add_handler(CommandHandler("set_tier", set_tier_command))
        app.add_handler(CommandHandler("grant_feature", grant_feature_command))
        app.add_handler(CommandHandler("revoke_feature", revoke_feature_command))
        app.add_handler(CommandHandler("subscription_history", subscription_history_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("broadcast", broadcast_command))

        # Callback query handlers for inline keyboards
        app.add_handler(CallbackQueryHandler(portfolio_handler.add_from_plan_callback, pattern="^add_portfolio_"))
        app.add_handler(CallbackQueryHandler(portfolio_confirm_callback, pattern="^portfolio_confirm_"))
        app.add_handler(CallbackQueryHandler(portfolio_cancel_callback, pattern="^portfolio_cancel$"))

        logger.info("All handlers registered")

    async def post_init(self, application: Application) -> None:
        """Post-initialization callback"""
        logger.info("Bot application initialized")

        # Initialize paper trading manager
        paper_trading = PaperTradingManager(db)
        application.bot_data['paper_trading'] = paper_trading
        logger.info("Paper trading manager initialized")

        # Initialize screening worker
        screening_worker = init_screening_worker(application.bot)
        application.bot_data['screening_worker'] = screening_worker
        logger.info("Screening worker initialized")

        # Setup signal check scheduler
        self.setup_signal_scheduler()

        # TODO: Send startup notification to admin

    def setup_signal_scheduler(self):
        """Setup periodic signal check, alert check, and screening schedulers"""
        try:
            # Get workers
            signal_worker = get_signal_worker()
            alert_worker = get_alert_worker()
            screening_worker = get_screening_worker()

            if not signal_worker and not alert_worker and not screening_worker:
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

            # Setup screening job (runs every hour to check for scheduled screenings)
            if screening_worker:
                scheduler.add_job(
                    screening_worker.run_scheduled_screening,
                    'interval',
                    minutes=60,
                    id='screening_check',
                    name='Screening Check Job',
                    replace_existing=True
                )
                logger.info("Screening scheduler registered (interval: 60 minutes)")

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
