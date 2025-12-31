"""
Portfolio Handler
Commands for managing trading portfolio and tracking P/L
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.database import db
from tg_bot.formatter import TelegramFormatter
from collector import CryptoDataCollector
from deepseek_integration import TradingPlanGenerator, AnalysisRequest

logger = logging.getLogger(__name__)


class PortfolioHandler:
    """Portfolio management commands"""

    def __init__(self):
        self.collector = CryptoDataCollector()

    async def my_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's portfolio - /myportfolio"""
        try:
            chat_id = update.effective_chat.id

            # Get user's open positions
            positions = db.get_user_positions(chat_id, status='open')

            if not positions:
                await update.message.reply_text(
                    f"{TelegramFormatter.EMOJI['info']} *Your Portfolio*\n\n"
                    f"You don't have any open positions.\n\n"
                    f"Use /addposition to track your trades!",
                    parse_mode='Markdown'
                )
                return

            # Update current prices for all positions
            for pos in positions:
                try:
                    # Fetch current price from exchange
                    if pos['symbol'].endswith('USDT'):
                        df = self.collector.get_binance_klines_auto(
                            pos['symbol'], "1h", limit=1
                        )
                        if df is not None and len(df) > 0:
                            current_price = df['close'].iloc[-1]
                            db.update_position_price(pos['id'], current_price)
                except Exception as e:
                    logger.warning(f"Failed to update price for {pos['symbol']}: {e}")

            # Refresh positions with updated prices
            positions = db.get_user_positions(chat_id, status='open')

            # Get portfolio summary
            summary = db.get_portfolio_summary(chat_id)

            # Format message
            message = f"💼 *Your Portfolio*\n\n"

            # Summary
            total_pnl_emoji = "📈" if summary['total_pnl'] >= 0 else "📉"
            message += f"*Summary:*\n"
            message += f"📊 Open Positions: {summary['total_positions']}\n"
            message += f"💰 Total Value: ${summary['total_value']:,.2f}\n"
            message += f"{total_pnl_emoji} Total P/L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_percent']:+.2f}%)\n\n"

            # Individual positions
            message += "*Open Positions:*\n\n"

            for pos in positions:
                # Calculate P/L
                if pos['position_type'] == 'LONG':
                    pnl = (pos['current_price'] - pos['entry_price']) * pos['quantity']
                    pnl_percent = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
                else:  # SHORT
                    pnl = (pos['entry_price'] - pos['current_price']) * pos['quantity']
                    pnl_percent = ((pos['entry_price'] - pos['current_price']) / pos['entry_price']) * 100

                pnl_emoji = "🟢" if pnl >= 0 else "🔴"

                message += f"*{pos['symbol']}* - {pos['position_type']} {pnl_emoji}\n"
                message += f"  Entry: ${pos['entry_price']:,.4f}\n"
                message += f"  Current: ${pos['current_price']:,.4f}\n"
                message += f"  Quantity: {pos['quantity']:.4f}\n"
                message += f"  Value: ${pos['total_value']:,.2f}\n"
                message += f"  P/L: ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"

                if pos['stop_loss']:
                    message += f"  SL: ${pos['stop_loss']:,.4f}\n"
                if pos['take_profit']:
                    message += f"  TP: ${pos['take_profit']:,.4f}\n"

                if pos['notes']:
                    message += f"  📝 {pos['notes']}\n"

                message += f"  ID: `{pos['id']}`\n\n"

            message += f"Use /closeposition [id] to close a position"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in my_portfolio: {e}")
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Failed to load portfolio: {e}")
            )

    async def add_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add new position - /addposition SYMBOL TYPE ENTRY_QTY ENTRY_PRICE [SL] [TP] [NOTES]"""
        try:
            chat_id = update.effective_chat.id

            # Validate arguments
            if not context.args or len(context.args) < 4:
                await update.message.reply_text(
                    f"❌ *Invalid Format*\n\n"
                    f"Usage: `/addposition SYMBOL TYPE QTY ENTRY_PRICE [SL] [TP] [NOTES]`\n\n"
                    f"*Examples:*\n"
                    f"• `/addposition BTCUSDT LONG 0.5 95000`\n"
                    f"• `/addposition ETHUSDT SHORT 10 3500 3400`\n"
                    f"• `/addposition SOLUSDT LONG 50 100 95 110 swing trade`\n\n"
                    f"*Parameters:*\n"
                    f"• SYMBOL: Trading pair (e.g., BTCUSDT)\n"
                    f"• TYPE: LONG or SHORT\n"
                    f"• QTY: Quantity in base currency\n"
                    f"• ENTRY: Entry price in USDT\n"
                    f"• SL (optional): Stop loss price\n"
                    f"• TP (optional): Take profit price\n"
                    f"• NOTES (optional): Any notes",
                    parse_mode='Markdown'
                )
                return

            # Parse arguments
            symbol = context.args[0].upper()
            pos_type = context.args[1].upper()

            if pos_type not in ['LONG', 'SHORT']:
                await update.message.reply_text("❌ Type must be LONG or SHORT")
                return

            try:
                quantity = float(context.args[2])
                entry_price = float(context.args[3])
            except ValueError:
                await update.message.reply_text("❌ Invalid quantity or price format")
                return

            stop_loss = None
            take_profit = None
            notes = None

            # Parse optional parameters
            if len(context.args) >= 5:
                try:
                    stop_loss = float(context.args[4])
                except ValueError:
                    # It might be notes
                    notes = ' '.join(context.args[4:])

            if len(context.args) >= 6:
                try:
                    take_profit = float(context.args[5])
                except ValueError:
                    # It might be notes
                    notes = ' '.join(context.args[5:])

            if len(context.args) >= 7:
                notes = ' '.join(context.args[6:])

            # Add position to database
            position_id = db.add_position(
                chat_id=chat_id,
                symbol=symbol,
                position_type=pos_type,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                notes=notes
            )

            if position_id:
                # Add transaction to history
                db.add_transaction(
                    chat_id=chat_id,
                    symbol=symbol,
                    transaction_type='BUY' if pos_type == 'LONG' else 'SELL',
                    price=entry_price,
                    quantity=quantity,
                    notes=f"Position ID: {position_id}"
                )

                total_value = entry_price * quantity

                message = f"✅ *Position Added*\n\n"
                message += f"*{symbol}* - {pos_type}\n"
                message += f"Entry: ${entry_price:,.4f}\n"
                message += f"Quantity: {quantity}\n"
                message += f"Total Value: ${total_value:,.2f}\n"

                if stop_loss:
                    message += f"Stop Loss: ${stop_loss:,.4f}\n"
                if take_profit:
                    message += f"Take Profit: ${take_profit:,.4f}\n"
                if notes:
                    message += f"Notes: {notes}\n"

                message += f"\nPosition ID: `{position_id}`"

                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to add position")

        except Exception as e:
            logger.error(f"Error in add_position: {e}")
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Failed to add position: {e}")
            )

    async def close_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close position - /closeposition POSITION_ID [CLOSE_PRICE]"""
        try:
            chat_id = update.effective_chat.id

            # Validate arguments
            if not context.args:
                # Show positions if no arguments
                positions = db.get_user_positions(chat_id, status='open')

                if not positions:
                    await update.message.reply_text(
                        f"{TelegramFormatter.EMOJI['info']} *No Open Positions*\n\n"
                        f"You don't have any open positions.\n\n"
                        f"Usage: `/closeposition POSITION_ID [CLOSE_PRICE]`",
                        parse_mode='Markdown'
                    )
                    return

                message = f"*Your Open Positions:*\n\n"
                for pos in positions:
                    message += f"ID `{pos['id']}`: {pos['symbol']} - {pos['position_type']}\n"
                    message += f"  Entry: ${pos['entry_price']:,.4f} | Qty: {pos['quantity']}\n\n"

                message += f"\nUsage: `/closeposition POSITION_ID [CLOSE_PRICE]`\n\n"
                message += f"If CLOSE_PRICE is not provided, current market price will be used."

                await update.message.reply_text(message, parse_mode='Markdown')
                return

            position_id = int(context.args[0])
            close_price = None

            # Parse optional close price
            if len(context.args) >= 2:
                try:
                    close_price = float(context.args[1])
                except ValueError:
                    await update.message.reply_text("❌ Invalid close price format")
                    return

            # Get position
            position = db.get_position(position_id, chat_id)

            if not position:
                await update.message.reply_text(f"❌ Position not found: {position_id}")
                return

            # If no close price provided, fetch from exchange
            if close_price is None:
                try:
                    if position['symbol'].endswith('USDT'):
                        df = self.collector.get_binance_klines_auto(
                            position['symbol'], "1h", limit=1
                        )
                        if df is not None and len(df) > 0:
                            close_price = df['close'].iloc[-1]
                        else:
                            await update.message.reply_text(
                                f"❌ Could not fetch current price. "
                                f"Please provide close price: /closeposition {position_id} <price>"
                            )
                            return
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ Failed to fetch current price: {e}\n"
                        f"Please provide: /closeposition {position_id} <price>"
                    )
                    return

            # Calculate final P/L
            if position['position_type'] == 'LONG':
                pnl = (close_price - position['entry_price']) * position['quantity']
                pnl_percent = ((close_price - position['entry_price']) / position['entry_price']) * 100
            else:  # SHORT
                pnl = (position['entry_price'] - close_price) * position['quantity']
                pnl_percent = ((position['entry_price'] - close_price) / position['entry_price']) * 100

            # Close position
            if db.close_position(position_id, close_price, chat_id):
                # Add transaction to history
                db.add_transaction(
                    chat_id=chat_id,
                    symbol=position['symbol'],
                    transaction_type='SELL' if position['position_type'] == 'LONG' else 'BUY',
                    price=close_price,
                    quantity=position['quantity'],
                    notes=f"Close Position ID: {position_id} | P/L: ${pnl:,.2f}"
                )

                pnl_emoji = "📈" if pnl >= 0 else "📉"
                pnl_color = "🟢" if pnl >= 0 else "🔴"

                message = f"{pnl_color} *Position Closed*\n\n"
                message += f"*{position['symbol']}* - {position['position_type']}\n"
                message += f"Entry: ${position['entry_price']:,.4f}\n"
                message += f"Close: ${close_price:,.4f}\n"
                message += f"Quantity: {position['quantity']}\n\n"
                message += f"{pnl_emoji} *P/L: ${pnl:,.2f} ({pnl_percent:+.2f}%)*\n"

                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to close position")

        except ValueError:
            await update.message.reply_text("❌ Invalid position ID. Use: /closeposition POSITION_ID")
        except Exception as e:
            logger.error(f"Error in close_position: {e}")
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Failed to close position: {e}")
            )

    async def delete_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete position permanently - /deleteposition POSITION_ID"""
        try:
            chat_id = update.effective_chat.id

            if not context.args:
                await update.message.reply_text(
                    "Usage: `/deleteposition POSITION_ID`\n\n"
                    "⚠️ This will permanently delete the position. Use /closeposition to properly close positions.",
                    parse_mode='Markdown'
                )
                return

            position_id = int(context.args[0])

            # Confirm deletion
            position = db.get_position(position_id, chat_id)
            if not position:
                await update.message.reply_text(f"❌ Position not found: {position_id}")
                return

            # Delete position
            if db.delete_position(position_id, chat_id):
                await update.message.reply_text(
                    f"✅ Position deleted: {position_id}\n"
                    f"Symbol: {position['symbol']}"
                )
            else:
                await update.message.reply_text("❌ Failed to delete position")

        except ValueError:
            await update.message.reply_text("❌ Invalid position ID")
        except Exception as e:
            logger.error(f"Error in delete_position: {e}")
            await update.message.reply_text(
                TelegramFormatter.error_message(f"Failed to delete position: {e}")
            )

    async def add_from_plan_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback query from 'Add to Portfolio' button"""
        try:
            query = update.callback_query

            # Answer callback immediately to prevent timeout
            await query.answer(text="⏳ Processing your request...")

            chat_id = update.effective_chat.id

            # Parse callback data
            # Format: add_portfolio_SYMBOL_TREND_MESSAGE_ID
            callback_data = query.data
            if not callback_data.startswith("add_portfolio_"):
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except:
                    pass
                await query.message.reply_text("❌ Invalid callback data")
                return

            parts = callback_data.split("_")
            if len(parts) < 5:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except:
                    pass
                await query.message.reply_text("❌ Invalid callback format")
                return

            symbol = parts[2]
            trend = parts[3]
            message_id = int(parts[4])

            # Try to get stored plan from bot_data
            plan_key = f"{message_id}_{chat_id}"
            stored_plan = None

            if context.bot_data and 'trading_plans' in context.bot_data:
                import time
                plan_data = context.bot_data['trading_plans'].get(plan_key)
                if plan_data:
                    # Check if plan is still valid (5 minutes)
                    if time.time() - plan_data['timestamp'] < 300:
                        stored_plan = plan_data['plan']
                        logger.info(f"Using cached trading plan for {symbol}")

            # Remove the button to prevent double-clicks
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception as e:
                logger.warning(f"Could not edit message reply markup: {e}")

            # If we have stored plan, use it directly (no regeneration needed!)
            if stored_plan:
                logger.info(f"Using cached plan - skipping regeneration for {symbol}")

                # Use first entry point as entry price
                entry_point = stored_plan.entries[0]
                entry_price = entry_point.level

                # Calculate quantity (example: 10% of position)
                quantity = 0.1  # Default, user can edit later

                # Determine position type from trend
                position_type = 'LONG' if trend.upper() == 'BULLISH' else 'SHORT'

                # Get stop loss and take profit from plan
                stop_loss = stored_plan.stop_loss if hasattr(stored_plan, 'stop_loss') else None
                take_profit = stored_plan.take_profits[0].level if stored_plan.take_profits else None

                # Add position to database
                position_id = db.add_position(
                    chat_id=chat_id,
                    symbol=symbol,
                    position_type=position_type,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    notes=f"From AI trading plan - {stored_plan.trend} trend"
                )

                if position_id:
                    # Add transaction to history
                    db.add_transaction(
                        chat_id=chat_id,
                        symbol=symbol,
                        transaction_type='BUY' if position_type == 'LONG' else 'SELL',
                        price=entry_price,
                        quantity=quantity,
                        notes=f"Position ID: {position_id} (from AI plan)"
                    )

                    total_value = entry_price * quantity

                    message = f"✅ *Position Added from Trading Plan*\n\n"
                    message += f"*{symbol}* - {position_type}\n"
                    message += f"Entry: ${entry_price:,.4f}\n"
                    message += f"Quantity: {quantity} (please edit with actual quantity)\n"
                    message += f"Total Value: ${total_value:,.2f}\n"

                    if stop_loss:
                        message += f"Stop Loss: ${stop_loss:,.4f}\n"
                    if take_profit:
                        message += f"Take Profit: ${take_profit:,.4f}\n"

                    message += f"\nPosition ID: `{position_id}`\n\n"
                    message += f"⚠️ Please edit quantity with: /deleteposition {position_id}\n"
                    message += f"Then add again with correct quantity using /addposition"

                    await query.message.reply_text(message, parse_mode='Markdown')
                else:
                    await query.message.reply_text("❌ Failed to add position to database")

                return  # Done! No need to regenerate

            # If no stored plan or expired, fallback to regeneration
            # Send loading message (new message)
            loading_msg = await query.message.reply_text(
                f"⏳ Plan data expired, regenerating for {symbol}...\nThis may take 20-30 seconds..."
            )

            # Regenerate trading plan to get full data
            try:
                generator = TradingPlanGenerator()
                request = AnalysisRequest(
                    symbol=symbol,
                    timeframe="4h",
                    data_points=100,
                    analysis_type="trading_plan"
                )

                loop = asyncio.get_event_loop()
                plan = await loop.run_in_executor(None, generator.generate_trading_plan, request)

                if not plan or not plan.entries:
                    await loading_msg.edit_text(
                        f"❌ Failed to generate trading plan for {symbol}\n\n"
                        f"Please use /addposition manually:\n"
                        f"`/addposition {symbol} LONG QTY ENTRY_PRICE`",
                        parse_mode='Markdown'
                    )
                    return

                # Use first entry point as entry price
                entry_point = plan.entries[0]
                entry_price = entry_point.level

                # Calculate quantity (example: 10% of position)
                # User should adjust this based on their capital
                quantity = 0.1  # Default, user can edit later

                # Determine position type from trend
                position_type = 'LONG' if trend.upper() == 'BULLISH' else 'SHORT'

                # Get stop loss and take profit from plan
                stop_loss = plan.stop_loss if hasattr(plan, 'stop_loss') else None
                take_profit = plan.take_profits[0].level if plan.take_profits else None

                # Add position to database
                position_id = db.add_position(
                    chat_id=chat_id,
                    symbol=symbol,
                    position_type=position_type,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    notes=f"From AI trading plan - {plan.trend} trend"
                )

                if position_id:
                    # Add transaction to history
                    db.add_transaction(
                        chat_id=chat_id,
                        symbol=symbol,
                        transaction_type='BUY' if position_type == 'LONG' else 'SELL',
                        price=entry_price,
                        quantity=quantity,
                        notes=f"Position ID: {position_id} (from AI plan)"
                    )

                    total_value = entry_price * quantity

                    message = f"✅ *Position Added from Trading Plan*\n\n"
                    message += f"*{symbol}* - {position_type}\n"
                    message += f"Entry: ${entry_price:,.4f}\n"
                    message += f"Quantity: {quantity} (please edit with actual quantity)\n"
                    message += f"Total Value: ${total_value:,.2f}\n"

                    if stop_loss:
                        message += f"Stop Loss: ${stop_loss:,.4f}\n"
                    if take_profit:
                        message += f"Take Profit: ${take_profit:,.4f}\n"

                    message += f"\nPosition ID: `{position_id}`\n\n"
                    message += f"⚠️ Please edit quantity with: /deleteposition {position_id}\n"
                    message += f"Then add again with correct quantity using /addposition"

                    await loading_msg.edit_text(message, parse_mode='Markdown')
                else:
                    await loading_msg.edit_text("❌ Failed to add position to database")

            except Exception as e:
                logger.error(f"Error generating plan for portfolio: {e}")
                await loading_msg.edit_text(
                    f"❌ Error: {str(e)}\n\n"
                    f"Please add position manually:\n"
                    f"`/addposition {symbol} LONG QTY ENTRY_PRICE`",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in add_from_plan_callback: {e}")
            try:
                await update.effective_message.reply_text(
                    TelegramFormatter.error_message(f"Failed to add position: {e}")
                )
            except:
                pass
