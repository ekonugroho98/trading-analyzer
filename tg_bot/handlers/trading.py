"""
Trading Command Handlers
Handle /plan, /price, /analyze commands
"""

import logging
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from deepseek_integration import TradingPlanGenerator, AnalysisRequest
from collector import CryptoDataCollector

logger = logging.getLogger(__name__)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /price command"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /price [symbol]\nExample: /price BTCUSDT"
            )
            return

        symbol = context.args[0].upper()

        # Get user's preferences
        market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
        exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message(f"Fetching {symbol} price from {exchange_pref.upper()}")
        )

        # Fetch price data using user's exchange and market preference
        collector = CryptoDataCollector()
        try:
            df = None

            # Use selected exchange
            if exchange_pref == 'bybit':
                df = collector.get_bybit_klines(symbol, "1m", limit=1)
            else:  # binance (default)
                # Apply market preference for Binance
                if market_pref == 'futures':
                    df = collector._get_binance_futures_klines(symbol, "1m", limit=1)
                elif market_pref == 'spot':
                    df = collector.get_binance_klines(symbol, "1m", limit=1, use_cache=False, save_cache=False)
                else:  # auto
                    df = collector.get_binance_klines_auto(symbol, "1m", limit=1)

            if df is not None and len(df) > 0:
                latest = df.iloc[-1]

                price_data = {
                    'price': latest['close'],
                    'change_24h': ((latest['close'] - latest['open']) / latest['open']) * 100,
                    'volume_24h': latest['volume'],
                    'high_24h': latest['high'],
                    'low_24h': latest['low'],
                }

                # Delete loading message and send price info
                await loading_msg.delete()
                await update.message.reply_text(
                    TelegramFormatter.price_info(symbol, price_data),
                    parse_mode='Markdown'
                )
            else:
                await loading_msg.delete()
                await update.message.reply_text(
                    TelegramFormatter.error_message(f"Failed to fetch data for {symbol} from {exchange_pref.upper()}")
                )

        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            await loading_msg.delete()
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Error: {str(e)}"),
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in price_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /plan command - Generate AI trading plan"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /plan [symbol] [timeframe]\n"
                "Example: /plan BTCUSDT\n"
                "         /plan ETHUSDT 1h"
            )
            return

        symbol = context.args[0].upper()
        timeframe = context.args[1] if len(context.args) > 1 else "4h"

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message(f"Generating AI trading plan for {symbol}")
        )

        # Generate trading plan
        try:
            generator = TradingPlanGenerator()

            request = AnalysisRequest(
                symbol=symbol,
                timeframe=timeframe,
                data_points=100,
                analysis_type="trading_plan"
            )

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            # Use auto-detect method for better compatibility
            from collector import CryptoDataCollector
            collector = CryptoDataCollector()

            # Pre-fetch data using auto-detect to ensure it's available
            df_test = collector.get_binance_klines_auto(symbol, timeframe, limit=100)

            if df_test is None or len(df_test) < 50:
                await loading_msg.delete()
                await update.message.reply_text(
                    TelegramFormatter.error_message(
                        f"Insufficient data for {symbol}. "
                        f"Symbol may not be available or has low liquidity."
                    )
                )
                return

            plan = await loop.run_in_executor(None, generator.generate_trading_plan, request)

            # Delete loading message
            await loading_msg.delete()

            if plan:
                # Store plan data in bot_data for callback handler to use
                # Use message_id as key to store the plan temporarily (expires after 5 minutes)
                if context.bot_data is None:
                    context.bot_data = {}
                if 'trading_plans' not in context.bot_data:
                    context.bot_data['trading_plans'] = {}

                # Store plan with timestamp
                import time
                plan_key = f"{update.effective_message.message_id}_{chat_id}"
                context.bot_data['trading_plans'][plan_key] = {
                    'plan': plan,
                    'timestamp': time.time()
                }

                # Create inline keyboard with "Add to Portfolio" button
                # Include message_id in callback data to retrieve stored plan
                callback_data = f"add_portfolio_{plan.symbol}_{plan.trend}_{update.effective_message.message_id}"

                keyboard = [[InlineKeyboardButton("➕ Add to Portfolio", callback_data=callback_data)]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send trading plan with inline keyboard
                await update.message.reply_text(
                    TelegramFormatter.trading_plan(plan),
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    TelegramFormatter.error_message(f"Failed to generate trading plan for {symbol}")
                )

        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            await loading_msg.delete()
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Error: {str(e)}"),
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in plan_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command - Quick technical analysis"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /analyze [symbol]\nExample: /analyze BTCUSDT"
            )
            return

        symbol = context.args[0].upper()

        # Get user's preferences
        market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
        exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message(f"Analyzing {symbol} from {exchange_pref.upper()}")
        )

        # Fetch data and perform analysis using user's exchange and market preference
        collector = CryptoDataCollector()
        try:
            df = None

            # Use selected exchange
            if exchange_pref == 'bybit':
                df = collector.get_bybit_klines(symbol, "4h", limit=100)
            else:  # binance (default)
                # Apply market preference for Binance
                if market_pref == 'futures':
                    df = collector._get_binance_futures_klines(symbol, "4h", limit=100)
                elif market_pref == 'spot':
                    df = collector.get_binance_klines(symbol, "4h", limit=100, use_cache=False, save_cache=False)
                else:  # auto
                    df = collector.get_binance_klines_auto(symbol, "4h", limit=100)

            if df is not None and len(df) > 50:
                # Calculate indicators
                df = collector.calculate_indicators(df)

                latest = df.iloc[-1]
                current_price = latest['close']

                # Quick Trend Analysis
                sma_20 = df['MA20'].iloc[-1]
                sma_50 = df['MA50'].iloc[-1]

                if current_price > sma_20 > sma_50:
                    trend = "BULLISH 📈"
                elif current_price < sma_20 < sma_50:
                    trend = "BEARISH 📉"
                else:
                    trend = "NEUTRAL ⚪"

                # RSI Quick Check
                rsi = latest['RSI']
                if rsi > 70:
                    rsi_status = "Overbought"
                elif rsi < 30:
                    rsi_status = "Oversold"
                else:
                    rsi_status = "Neutral"

                # Volume Analysis
                volume = latest['volume']
                volume_ma = latest['volume_MA20']
                volume_ratio = latest['volume_ratio']

                # Quick analysis message
                analysis = f"""{TelegramFormatter.EMOJI['chart']} *Quick Analysis: {symbol}*

💰 *Price*: ${current_price:,.2f}
📊 *Trend*: {trend}
📉 *RSI*: {rsi:.1f} ({rsi_status})
📦 *Volume*: {volume:,.0f} ({volume_ratio:.1f}x avg)

*MA20*: ${sma_20:,.2f}
*MA50*: ${sma_50:,.2f}

*Data Source*: {exchange_pref.upper()} | *Market*: {market_pref.upper()}

Use /ta {symbol} for detailed technical analysis! {TelegramFormatter.EMOJI['robot']}
"""

                await loading_msg.delete()
                await update.message.reply_text(analysis, parse_mode='Markdown')
            else:
                await loading_msg.delete()
                await update.message.reply_text(
                    TelegramFormatter.error_message(
                        f"Insufficient data for {symbol} from {exchange_pref.upper()}. "
                        f"Need at least 50 candles, got {len(df) if df is not None else 0}."
                    )
                )

        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            await loading_msg.delete()
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Error: {str(e)}"),
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in analyze_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def ta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ta command - Comprehensive technical analysis"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get symbol from args
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /ta [symbol]\nExample: /ta BTCUSDT"
            )
            return

        symbol = context.args[0].upper()

        # Get user's preferences
        market_pref = db.get_user_preference(chat_id, 'market_type', default='auto')
        exchange_pref = db.get_user_preference(chat_id, 'exchange', default='binance')

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message(f"Performing comprehensive analysis for {symbol}")
        )

        # Fetch data and perform analysis using user's exchange and market preference
        collector = CryptoDataCollector()
        try:
            df = None

            # Use selected exchange
            if exchange_pref == 'bybit':
                df = collector.get_bybit_klines(symbol, "4h", limit=100)
            else:  # binance (default)
                # Apply market preference for Binance
                if market_pref == 'futures':
                    df = collector._get_binance_futures_klines(symbol, "4h", limit=100)
                elif market_pref == 'spot':
                    df = collector.get_binance_klines(symbol, "4h", limit=100, use_cache=False, save_cache=False)
                else:  # auto
                    df = collector.get_binance_klines_auto(symbol, "4h", limit=100)

            if df is not None and len(df) > 50:
                # Calculate indicators
                df = collector.calculate_indicators(df)

                latest = df.iloc[-1]
                current_price = latest['close']

                # Trend Analysis
                sma_20 = df['MA20'].iloc[-1]
                sma_50 = df['MA50'].iloc[-1]
                sma_7 = df['MA7'].iloc[-1]

                trend = "NEUTRAL ⚪"
                trend_strength = "Weak"
                if current_price > sma_7 > sma_20 > sma_50:
                    trend = "STRONG BULLISH 🚀"
                    trend_strength = "Strong"
                elif current_price > sma_20 > sma_50:
                    trend = "BULLISH 📈"
                    trend_strength = "Moderate"
                elif current_price < sma_7 < sma_20 < sma_50:
                    trend = "STRONG BEARISH 🔻"
                    trend_strength = "Strong"
                elif current_price < sma_20 < sma_50:
                    trend = "BEARISH 📉"
                    trend_strength = "Moderate"

                # RSI Analysis
                rsi = latest['RSI']
                rsi_signal = "NEUTRAL"
                if rsi > 70:
                    rsi_signal = "OVERBOUGHT 🔴"
                elif rsi > 60:
                    rsi_signal = "STRONG 🟢"
                elif rsi < 30:
                    rsi_signal = "OVERSOLD 🟢"
                elif rsi < 40:
                    rsi_signal = "WEAK 🔴"
                else:
                    rsi_signal = "NEUTRAL ⚪"

                # MACD Analysis
                macd = latest['MACD']
                macd_signal = latest['MACD_signal']
                macd_hist = latest['MACD_hist']
                macd_trend = "BULLISH" if macd_hist > 0 else "BEARISH"
                macd_status = f"{macd_trend} {'📈' if macd_hist > 0 else '📉'}"

                # Bollinger Bands
                bb_upper = latest['BB_upper']
                bb_lower = latest['BB_lower']
                bb_middle = latest['BB_middle']
                bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100

                bb_signal = "MIDDLE"
                if bb_position > 80:
                    bb_signal = "UPPER BAND (Overbought)"
                elif bb_position < 20:
                    bb_signal = "LOWER BAND (Oversold)"

                # Support & Resistance (using recent lows/highs)
                recent_high = df['high'].tail(20).max()
                recent_low = df['low'].tail(20).min()

                # Volume Analysis
                volume = latest['volume']
                volume_ma = latest['volume_MA20']
                volume_ratio = latest['volume_ratio']
                volume_status = "NORMAL"
                if volume_ratio > 2:
                    volume_status = "HIGH 🔥"
                elif volume_ratio < 0.5:
                    volume_status = "LOW 📉"

                # Calculate changes
                change_1h = ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100 if len(df) >= 2 else 0
                change_4h = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100 if len(df) >= 5 else 0
                change_24h = ((latest['close'] - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100 if len(df) >= 24 else 0

                # Overall Signal
                signals = []
                if trend == "STRONG BULLISH 🚀" or trend == "BULLISH 📈":
                    signals.append(1)
                elif trend == "STRONG BEARISH 🔻" or trend == "BEARISH 📉":
                    signals.append(-1)
                else:
                    signals.append(0)

                if rsi < 30:
                    signals.append(1)  # Oversold = bullish
                elif rsi > 70:
                    signals.append(-1)  # Overbought = bearish
                else:
                    signals.append(0)

                if macd_hist > 0:
                    signals.append(1)
                else:
                    signals.append(-1)

                signal_sum = sum(signals)
                if signal_sum >= 2:
                    overall_signal = "BUY 🟢"
                elif signal_sum <= -2:
                    overall_signal = "SELL 🔴"
                else:
                    overall_signal = "HOLD 🟡"

                # Format comprehensive analysis message
                analysis = f"""{TelegramFormatter.EMOJI['chart']} *Technical Analysis: {symbol}*

💰 *Price Information*
• Current: ${current_price:,.2f}
• 1H Change: {change_1h:+.2f}%
• 4H Change: {change_4h:+.2f}%
• 24H Change: {change_24h:+.2f}%
• 24H High: ${latest['high']:,.2f}
• 24H Low: ${latest['low']:,.2f}

📊 *Trend Analysis*
• Overall: {trend}
• Strength: {trend_strength}
• Signal: {overall_signal}

📈 *Moving Averages*
• MA7: ${sma_7:,.2f}
• MA20: ${sma_20:,.2f}
• MA50: ${sma_50:,.2f}

📉 *RSI*: {rsi:.1f} ({rsi_signal})
💹 *MACD*: {macd_status}
📊 *Bollinger*: {bb_position:.1f}% ({bb_signal})
📦 *Volume*: {volume:,.0f} ({volume_status})

🎯 *Key Levels*
• Resistance: ${recent_high:,.2f}
• Support: ${recent_low:,.2f}

*Data Source*: {exchange_pref.upper()} | *Market*: {market_pref.upper()}

Use /plan {symbol} for AI trading plan! {TelegramFormatter.EMOJI['robot']}
"""

                await loading_msg.delete()
                await update.message.reply_text(analysis, parse_mode='Markdown')
            else:
                await loading_msg.delete()
                await update.message.reply_text(
                    TelegramFormatter.error_message(
                        f"Insufficient data for {symbol} from {exchange_pref.upper()}. "
                        f"Need at least 50 candles, got {len(df) if df is not None else 0}."
                    )
                )

        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            await loading_msg.delete()
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Error: {str(e)}"),
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in ta_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /signals command - Get signals for subscriptions"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Get user subscriptions
        subscriptions = db.get_user_subscriptions(chat_id)

        if not subscriptions:
            await update.message.reply_text(
                "You don't have any subscriptions.\n"
                "Use /subscribe [symbol] to start monitoring a coin!"
            )
            return

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message("Fetching signals")
        )

        # Fetch signals for each subscription
        signals_text = f"{TelegramFormatter.EMOJI['chart']} *Your Trading Signals*\n\n"

        collector = CryptoDataCollector()

        for sub in subscriptions[:5]:  # Limit to 5 subscriptions
            try:
                symbol = sub['symbol']
                df = collector.get_binance_klines(symbol, "4h", limit=50)

                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    current_price = latest['close']

                    # Simple signal logic
                    sma_20 = df['close'].rolling(20).mean().iloc[-1]

                    if current_price > sma_20:
                        signal = "BUY 🟢"
                    elif current_price < sma_20:
                        signal = "SELL 🔴"
                    else:
                        signal = "HOLD 🟡"

                    signals_text += f"*{symbol}*: {signal} (${current_price:,.2f})\n"

            except Exception as e:
                logger.error(f"Error fetching signal for {sub['symbol']}: {e}")
                continue

        await loading_msg.delete()
        await update.message.reply_text(signals_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in signals_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def subscribeall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribeall command - Subscribe to all major pairs"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Major pairs
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

        added = 0
        for symbol in symbols:
            if db.add_subscription(chat_id, symbol):
                added += 1

        await update.message.reply_text(
            TelegramFormatter.success_message(f"Subscribed to {added} major pairs")
        )

    except Exception as e:
        logger.error(f"Error in subscribeall_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )


async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trending command - Show trending coins from Binance Futures"""
    try:
        chat_id = update.effective_chat.id
        db.update_last_active(chat_id)

        # Send loading message
        loading_msg = await update.message.reply_text(
            TelegramFormatter.loading_message("Fetching trending coins from Binance Futures")
        )

        import requests

        # Fetch top 20 by volume from Binance Futures
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Filter USDT pairs and sort by volume
        usdt_tickers = [
            {
                'symbol': t['symbol'],
                'volume': float(t['quoteVolume']),
                'change': float(t['priceChangePercent'])
            }
            for t in data
            if t['symbol'].endswith('USDT')
        ]

        # Sort by volume (descending)
        usdt_tickers.sort(key=lambda x: x['volume'], reverse=True)

        # Get top 15
        top_tickers = usdt_tickers[:15]

        # Format message
        trend_msg = f"{TelegramFormatter.EMOJI['fire']} *Top 15 Futures by Volume (24h)*\n\n"

        for i, ticker in enumerate(top_tickers, 1):
            volume_str = f"${ticker['volume']:,.0f}"
            change_str = f"{ticker['change']:+.2f}%"
            emoji = "🟢" if ticker['change'] >= 0 else "🔴"
            trend_msg += f"{i}. *{ticker['symbol']}* {emoji} {change_str}\n"

        await loading_msg.delete()
        await update.message.reply_text(trend_msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in trending_command: {e}")
        await update.message.reply_text(
            TelegramFormatter.error_message(str(e)),
            parse_mode='Markdown'
        )
