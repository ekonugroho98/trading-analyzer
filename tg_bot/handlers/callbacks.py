"""
Callback Query Handlers for Interactive Buttons
Handles all inline button interactions
"""

import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter

logger = logging.getLogger(__name__)


# ============ HELPER FUNCTIONS ============

async def screen_market(timeframe: str = '4h', limit: int = 20) -> list:
    """
    Screen market and return list of qualified coins

    Args:
        timeframe: Timeframe for analysis
        limit: Maximum number of coins to analyze

    Returns:
        List of dicts with coin data and scores
    """
    try:
        # Import here to avoid circular dependency
        from tg_bot.market_screener import MarketScreener

        screener = MarketScreener()

        # Get all USDT pairs from Bybit
        logger.info("Fetching all USDT symbols from Bybit...")
        symbols = await screener.get_top_symbols(limit=1000)  # Get all available

        if not symbols:
            logger.warning("No symbols fetched from Bybit, using fallback list")
            # Fallback to hardcoded list if Bybit fetch fails
            symbols = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT',
                'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'ATOMUSDT', 'NEARUSDT'
            ]

        logger.info(f"Screening {len(symbols)} symbols from Bybit...")

        # Screen each symbol
        results = []
        screened_count = 0

        for symbol in symbols:
            try:
                # Get single timeframe analysis
                screen_result = await screener.screen_coin(
                    symbol=symbol,
                    timeframe=timeframe
                )

                if screen_result:
                    # Convert ScreenResult to dict format
                    results.append({
                        'symbol': symbol,
                        'score': screen_result.score,
                        'trend': screen_result.trend,
                        'rsi': 'N/A',  # Not available in ScreenResult
                        'macd': 'NEUTRAL',  # Not available in ScreenResult
                        'adx': 'N/A',  # Not available in ScreenResult
                        'price': screen_result.current_price,
                        'signals': screen_result.signals,
                        'analysis': screen_result.analysis,
                        'volume_24h': screen_result.volume_24h,
                        'change_24h': screen_result.change_24h
                    })
                    screened_count += 1

                    # Log progress every 50 coins
                    if screened_count % 50 == 0:
                        logger.info(f"Screened {screened_count}/{len(symbols)} symbols...")

            except Exception as e:
                logger.warning(f"Error analyzing {symbol}: {e}")
                continue

        logger.info(f"Screening complete: {screened_count}/{len(symbols)} symbols analyzed, {len(results)} qualified")

        return results

    except Exception as e:
        logger.error(f"Error in screen_market: {e}")
        return []


def calculate_coin_score(analysis: dict) -> int:
    """
    Calculate score (0-100) for a coin based on analysis

    Args:
        analysis: Analysis dict from screener

    Returns:
        Score from 0-100
    """
    score = 50  # Base score

    # Trend score (30 points max)
    trend = analysis.get('trend', 'NEUTRAL')
    if trend == 'BULLISH':
        score += 30
    elif trend == 'BEARISH':
        score -= 20

    # RSI score (20 points max)
    rsi = analysis.get('rsi', 50)
    if rsi != 'N/A':
        if 30 <= rsi <= 70:  # Neutral zone - good for entry
            score += 20
        elif 20 <= rsi < 30:  # Oversold - good opportunity
            score += 15
        elif 70 < rsi <= 80:  # Overbought but momentum
            score += 5

    # MACD score (20 points max)
    macd = analysis.get('macd_signal', 'NEUTRAL')
    if macd == 'Bullish':
        score += 20
    elif macd == 'Bearish':
        score -= 15

    # ADX score (20 points max) - trend strength
    adx = analysis.get('adx', 0)
    if adx != 'N/A' and isinstance(adx, (int, float)):
        if adx > 25:  # Strong trend
            score += 20
        elif adx > 20:  # Trending
            score += 10

    # Volume score (10 points max)
    volume_signal = analysis.get('volume_signal', 'NEUTRAL')
    if volume_signal == 'HIGH':
        score += 10
    elif volume_signal == 'ABOVE_AVERAGE':
        score += 5

    # Ensure score is between 0-100
    return max(0, min(100, score))


# ============ TIMEFRAME SELECTION HANDLERS ============

async def timeframe_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection buttons"""
    query = update.callback_query
    await query.answer()

    # Parse callback data
    data = query.data
    if data.startswith('tf_'):
        timeframe = data.split('_')[1]  # Extract timeframe from "tf_4h"

        # Edit message to show loading
        await query.edit_message_text(
            f"⏳ *Screening market ({timeframe})*...\n"
            f"Analyzing coins...",
            parse_mode='Markdown'
        )

        # Perform screening
        try:
            # Get results from market screener
            results = await screen_market(timeframe=timeframe, limit=20)

            # Validate results
            if not results or not isinstance(results, list):
                await query.edit_message_text(
                    "❌ Unable to fetch market data at this time.\n"
                    "Please try again later or use a different timeframe.",
                    parse_mode='Markdown'
                )
                return

            # Filter coins with score >= 50 (lowered from 60 to get more results)
            qualified_coins = [r for r in results if isinstance(r, dict) and r.get('score', 0) >= 50]

            if len(qualified_coins) == 0:
                await query.edit_message_text(
                    "❌ No coins meet minimum criteria (score ≥ 50).\n"
                    "Try again later or use a different timeframe.",
                    parse_mode='Markdown'
                )
                return

            # Random selection of 10 coins from qualified coins
            if len(qualified_coins) > 10:
                selected_coins = random.sample(qualified_coins, 10)
            else:
                selected_coins = qualified_coins

            # Sort by score descending
            selected_coins.sort(key=lambda x: x.get('score', 0), reverse=True)

            # Format results with pagination (first page)
            await format_and_send_screening_results(
                query,
                selected_coins,
                timeframe,
                page=0
            )

        except Exception as e:
            logger.error(f"Error in screening callback: {e}")
            await query.edit_message_text(
                f"❌ Error during screening: {str(e)}\n\nPlease try again.",
                parse_mode='Markdown'
            )


async def format_and_send_screening_results(
    query,
    results: list,
    timeframe: str,
    page: int = 0,
    per_page: int = 3
):
    """Format and send screening results with action buttons and pagination"""

    total_coins = len(results)
    total_pages = (total_coins - 1) // per_page + 1

    # Get current page coins
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_coins)
    page_coins = results[start_idx:end_idx]

    # Format message
    message = f"✅ *SCREENING RESULTS* ({timeframe.upper()})\n\n"
    message += f"Found {total_coins} opportunities:\n\n"

    for idx, coin in enumerate(page_coins, start=start_idx + 1):
        symbol = coin.get('symbol', 'UNKNOWN')
        score = coin.get('score', 0)
        trend = coin.get('trend', 'NEUTRAL')
        rsi = coin.get('rsi', 'N/A')
        macd = coin.get('macd', 'N/A')
        adx = coin.get('adx', 'N/A')

        # Stars based on score
        if score >= 85:
            stars = "⭐⭐⭐"
            medal = "🥇"
        elif score >= 75:
            stars = "⭐⭐"
            medal = "🥈"
        elif score >= 65:
            stars = "⭐"
            medal = "🥉"
        else:
            stars = ""
            medal = f"{idx}."

        # Trend emoji
        trend_emoji = "📈" if trend == "BULLISH" else "📉" if trend == "BEARISH" else "➡️"

        # MACD status
        macd_emoji = "✅" if macd == "Bullish" else "❌" if macd == "Bearish" else "➡️"

        message += f"{medal} *{symbol}*\tScore: {score} {stars}\n"
        message += f"   Trend: {trend_emoji} {trend}\n"
        message += f"   RSI: {rsi} | MACD: {macd_emoji} {macd}\n"

        if adx != 'N/A':
            message += f"   ADX: {adx}\n"

        # Add inline buttons for this coin
        # We'll create a separate keyboard for each coin
        # But since Telegram has limitations, we'll use callback data with coin info

    # Add pagination info
    message += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Page {page + 1}/{total_pages} | Showing {start_idx + 1}-{end_idx} of {total_coins}\n"

    # Create inline keyboard for actions
    keyboard = []

    # Action buttons for each coin on this page
    for coin in page_coins:
        symbol = coin.get('symbol', 'UNKNOWN')
        coin_buttons = [
            InlineKeyboardButton("📊 Plan", callback_data=f"plan_{symbol}_{timeframe}"),
            InlineKeyboardButton("📉 Analysis", callback_data=f"ta_{symbol}_{timeframe}"),
            InlineKeyboardButton("🔔 Alert", callback_data=f"alert_{symbol}"),
            InlineKeyboardButton("📈 Subscribe", callback_data=f"sub_{symbol}")
        ]
        keyboard.append(coin_buttons)

    # Pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{timeframe}_{page-1}"))

    pagination_row.append(InlineKeyboardButton("🔄 Rescreen", callback_data=f"rescreen_{timeframe}"))

    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{timeframe}_{page+1}"))

    keyboard.append(pagination_row)

    # Bottom row
    keyboard.append([
        InlineKeyboardButton("⚙️ Change TF", callback_data="show_timeframes"),
        InlineKeyboardButton("❌ Close", callback_data="close_message")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def pagination_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination button clicks"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith('page_'):
        parts = data.split('_')
        timeframe = parts[1]
        page = int(parts[2])

        # Get cached results or run new screening
        # For now, we'll run new screening
        # In production, you should cache results to avoid re-screening

        await query.edit_message_text(
            f"⏳ Loading page {page + 1}...",
            parse_mode='Markdown'
        )

        # Re-run screening and show requested page
        results = await screen_market(timeframe=timeframe, limit=20)
        qualified_coins = [r for r in results if r.get('score', 0) >= 50]

        if len(qualified_coins) > 10:
            selected_coins = random.sample(qualified_coins, 10)
        else:
            selected_coins = qualified_coins

        selected_coins.sort(key=lambda x: x.get('score', 0), reverse=True)

        await format_and_send_screening_results(
            query,
            selected_coins,
            timeframe,
            page=page
        )


async def rescreen_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rescreen button"""
    query = update.callback_query
    await query.answer()

    data = query.data
    timeframe = data.split('_')[1]  # Extract timeframe from "rescreen_4h"

    # Run fresh screening
    await query.edit_message_text(
        f"⏳ Re-screening market ({timeframe})...",
        parse_mode='Markdown'
    )

    results = await screen_market(timeframe=timeframe, limit=20)
    qualified_coins = [r for r in results if r.get('score', 0) >= 60]

    if len(qualified_coins) > 10:
        selected_coins = random.sample(qualified_coins, 10)
    else:
        selected_coins = qualified_coins

    selected_coins.sort(key=lambda x: x.get('score', 0), reverse=True)

    await format_and_send_screening_results(
        query,
        selected_coins,
        timeframe,
        page=0
    )


async def show_timeframes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show timeframe selection again"""
    query = update.callback_query
    await query.answer()

    # Show timeframe selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("🚀 Scalping 15m", callback_data="tf_15m"),
            InlineKeyboardButton("⚡ Intraday 1h", callback_data="tf_1h")
        ],
        [
            InlineKeyboardButton("📈 Swing 4h", callback_data="tf_4h"),
            InlineKeyboardButton("🏢 Daily 1D", callback_data="tf_1d")
        ],
        [
            InlineKeyboardButton("⏰ Auto Screen", callback_data="autoscreen_menu"),
            InlineKeyboardButton("❌ Cancel", callback_data="close_message")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📊 *Select Timeframe*\n\n"
        "Choose timeframe for market screening:\n",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def close_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close/delete the message"""
    query = update.callback_query
    await query.answer()

    try:
        await query.edit_message_text(
            "❌ Message closed. Type /screen to start again.",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error closing message: {e}")


# ============ COIN ACTION HANDLERS ============

async def plan_from_screen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate trading plan from screening result"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')
    symbol = parts[1]
    timeframe = parts[2]

    await query.edit_message_text(
        f"⏳ Generating trading plan for {symbol}...\n"
        f"Timeframe: {timeframe.upper()}",
        parse_mode='Markdown'
    )

    # Import here to avoid circular dependency
    from tg_bot.handlers.trading import plan_command
    from telegram import Update as UpdateClass

    # Create a mock update object
    # This is a workaround - in production, refactor to share logic
    # For now, send a message directing user to use /plan command

    await query.edit_message_text(
        f"💡 *Trading Plan Request*\n\n"
        f"Symbol: {symbol}\n"
        f"Timeframe: {timeframe}\n\n"
        f"Please use this command to generate the plan:\n"
        f"`/plan {symbol} {timeframe}`\n\n"
        f"This will open up more options like Single/Multi-TF mode.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Results", callback_data=f"page_{timeframe}_0")
        ]])
    )


async def ta_from_screen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate technical analysis from screening result"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')
    symbol = parts[1]
    timeframe = parts[2]

    await query.edit_message_text(
        f"💡 *Technical Analysis Request*\n\n"
        f"Symbol: {symbol}\n"
        f"Timeframe: {timeframe}\n\n"
        f"Please use this command:\n"
        f"`/ta {symbol} {timeframe}`\n\n"
        f"This will provide detailed technical indicators and analysis.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Results", callback_data=f"page_{timeframe}_0")
        ]])
    )


async def alert_from_screen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set price alert from screening result"""
    query = update.callback_query
    await query.answer()

    data = query.data
    symbol = data.split('_')[1]

    await query.edit_message_text(
        f"💡 *Set Price Alert*\n\n"
        f"Symbol: {symbol}\n\n"
        f"Please use this command:\n"
        f"`/setalert {symbol} <PRICE>`\n\n"
        f"Example: `/setalert {symbol} 95000`\n\n"
        f"You'll be notified when price hits your target.",
        parse_mode='Markdown'
    )


async def subscribe_from_screen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to coin from screening result"""
    query = update.callback_query
    await query.answer()

    data = query.data
    symbol = data.split('_')[1]

    await query.edit_message_text(
        f"💡 *Subscribe to Coin*\n\n"
        f"Symbol: {symbol}\n\n"
        f"Please use this command:\n"
        f"`/subscribe {symbol}`\n\n"
        f"You'll receive updates and signals for this coin.",
        parse_mode='Markdown'
    )


# ============ AUTO SCREEN HANDLERS ============

async def autoscreen_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show auto-screen interval selection"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("⏰ Every 30 min", callback_data="autoscreen_30"),
            InlineKeyboardButton("⏰ Every 1 hour", callback_data="autoscreen_60")
        ],
        [
            InlineKeyboardButton("⏰ Every 4 hours", callback_data="autoscreen_240"),
            InlineKeyboardButton("⏰ Every 12 hours", callback_data="autoscreen_720")
        ],
        [
            InlineKeyboardButton("❌ Disable Auto-Screen", callback_data="autoscreen_disable"),
            InlineKeyboardButton("🔙 Back", callback_data="show_timeframes")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⏰ *Auto-Screen Setup*\n\n"
        "Select screening interval:\n\n"
        "The bot will automatically screen the market\n"
        "and send you top opportunities at the chosen interval.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def autoscreen_set_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set auto-screen interval"""
    query = update.callback_query
    await query.answer()

    data = query.data
    interval_minutes = int(data.split('_')[1])

    chat_id = update.effective_chat.id

    # Store auto-screen preference in database
    db.set_user_preference(
        chat_id,
        'autoscreen_interval',
        interval_minutes
    )

    # Convert to readable format
    if interval_minutes >= 60:
        hours = interval_minutes // 60
        interval_text = f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        interval_text = f"{interval_minutes} minutes"

    keyboard = [[
        InlineKeyboardButton("🔙 Back to Menu", callback_data="show_timeframes")
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ *Auto-Screen Enabled*\n\n"
        f"Interval: Every {interval_text}\n\n"
        f"You'll receive automatic screening results\n"
        f"with top opportunities at the chosen interval.\n\n"
        f"Use /screen_auto to manage your auto-screen settings.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def autoscreen_disable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable auto-screen"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id

    # Remove auto-screen preference
    db.set_user_preference(
        chat_id,
        'autoscreen_interval',
        None
    )

    keyboard = [[
        InlineKeyboardButton("🔙 Back to Menu", callback_data="show_timeframes")
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✅ *Auto-Screen Disabled*\n\n"
        "You won't receive automatic screening results anymore.\n\n"
        "Use /screen to manually screen the market.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============ REGISTER ALL CALLBACK HANDLERS ============

def register_callback_handlers(application):
    """Register all callback query handlers"""

    from telegram.ext import CallbackQueryHandler

    application.add_handler(CallbackQueryHandler(timeframe_callback_handler, pattern='^tf_'))
    application.add_handler(CallbackQueryHandler(pagination_callback_handler, pattern='^page_'))
    application.add_handler(CallbackQueryHandler(rescreen_callback_handler, pattern='^rescreen_'))
    application.add_handler(CallbackQueryHandler(show_timeframes_handler, pattern='^show_timeframes'))
    application.add_handler(CallbackQueryHandler(close_message_handler, pattern='^close_message'))

    application.add_handler(CallbackQueryHandler(plan_from_screen_handler, pattern='^plan_'))
    application.add_handler(CallbackQueryHandler(ta_from_screen_handler, pattern='^ta_'))
    application.add_handler(CallbackQueryHandler(alert_from_screen_handler, pattern='^alert_'))
    application.add_handler(CallbackQueryHandler(subscribe_from_screen_handler, pattern='^sub_'))

    application.add_handler(CallbackQueryHandler(autoscreen_menu_handler, pattern='^autoscreen_menu'))
    application.add_handler(CallbackQueryHandler(autoscreen_set_handler, pattern='^autoscreen_'))
    application.add_handler(CallbackQueryHandler(autoscreen_disable_handler, pattern='^autoscreen_disable'))

    logger.info("All callback handlers registered")
