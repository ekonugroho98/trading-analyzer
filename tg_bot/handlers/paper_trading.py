"""
Paper Trading Handlers
Handle paper trading commands - simulation mode without real money
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from tg_bot.paper_trading import PaperTradingManager, PositionType, PositionStatus

logger = logging.getLogger(__name__)


async def portfolio_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start portfolio interaction - show portfolio summary"""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await update.effective_message.reply_text(
            "❌ Paper trading not initialized. Please contact admin."
        )
        return

    # Get portfolio summary
    summary = paper_trading.get_portfolio_summary(chat_id)

    if summary['total_positions'] == 0:
        await update.effective_message.reply_text(
            "📊 **Portfolio Kosong**\n\n"
            "Anda belum memiliki posisi terbuka.\n"
            "Gunakan /portfolio_add untuk membuka posisi baru."
        )
        return

    # Format portfolio summary
    from tg_bot.formatter import format_portfolio_summary
    message = format_portfolio_summary(summary)

    await update.effective_message.reply_text(
        message,
        parse_mode='Markdown'
    )


async def portfolio_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding new position - interactive flow"""
    if not update.effective_message or not update.effective_chat:
        return

    await update.effective_message.reply_text(
        "📝 **Buka Posisi Baru**\n\n"
        "Untuk membuka posisi, gunakan format berikut:\n"
        "```\n"
        "/portfolio_add SYMBOL TYPE ENTRY QTY [SL] [TP1,TP2,...]\n"
        "```\n\n"
        "**Parameter:**\n"
        "• SYMBOL - Contoh: BTCUSDT, ETHUSDT\n"
        "• TYPE - LONG (beli) atau SHORT (jual)\n"
        "• ENTRY - Harga entry dalam USDT\n"
        "• QTY - Jumlah koin (contoh: 0.001 BTC)\n"
        "• SL - Stop loss (opsional)\n"
        "• TP - Take profit levels, pisahkan dengan koma (opsional)\n\n"
        "**Contoh:**\n"
        "/portfolio_add BTCUSDT LONG 98000 0.001 97000 99000,100000\n"
        "/portfolio_add ETHUSDT SHORT 3500 0.5 3600\n\n"
        "📌 *Penjelasan:*\n"
        "- LONG = Profit jika harga NAIK\n"
        "- SHORT = Profit jika harga TURUN\n"
        "- QTY = Quantity/jumlah koin",
        parse_mode='Markdown'
    )


async def portfolio_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new paper trading position"""
    if not update.effective_message or not update.effective_chat:
        return

    if not context.args or len(context.args) < 4:
        await portfolio_add_start(update, context)
        return

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await update.effective_message.reply_text(
            "❌ Paper trading not initialized. Please contact admin."
        )
        return

    try:
        # Parse arguments
        symbol = context.args[0].upper()
        position_type = context.args[1].upper()

        # Validate position type
        if position_type not in [PositionType.LONG.value, PositionType.SHORT.value]:
            await update.effective_message.reply_text(
                f"❌ Tipe posisi tidak valid: {position_type}\n"
                f"Gunakan LONG atau SHORT"
            )
            return

        entry_price = float(context.args[2])
        quantity = float(context.args[3])

        # Optional parameters
        stop_loss = None
        take_profits = []

        if len(context.args) > 4:
            stop_loss = float(context.args[4])

        if len(context.args) > 5:
            # Parse take profits: "99000,100000" -> [{"level": 99000}, {"level": 100000}]
            tp_str = context.args[5]
            tp_levels = [float(x.strip()) for x in tp_str.split(',')]

            # Divide quantity equally among TPs
            if tp_levels:
                tp_percentage = 1.0 / len(tp_levels)
                take_profits = [
                    {"level": level, "percentage": tp_percentage, "filled": False}
                    for level in tp_levels
                ]

        # Create pending position
        position = paper_trading.create_pending_position(
            chat_id=chat_id,
            symbol=symbol,
            position_type=position_type,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profits=take_profits
        )

        # Format confirmation message
        from tg_bot.formatter import format_position_confirmation
        message = format_position_confirmation(position)

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Konfirmasi", callback_data=f"portfolio_confirm_{position.symbol}"),
                InlineKeyboardButton("❌ Batal", callback_data="portfolio_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.effective_message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        logger.info(f"Created pending position: {symbol} {position_type} for chat_id {chat_id}")

    except ValueError as e:
        await update.effective_message.reply_text(
            f"❌ Format angka tidak valid: {e}\n\n"
            "Pastikan harga dan quantity menggunakan angka yang valid."
        )
        logger.error(f"Value error in portfolio_add: {e}")
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ Error: {str(e)}"
        )
        logger.error(f"Error in portfolio_add: {e}", exc_info=True)


async def portfolio_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle position confirmation callback"""
    if not update.callback_query or not update.effective_chat:
        return

    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await query.edit_message_text("❌ Paper trading not initialized.")
        return

    # Confirm position
    position = paper_trading.confirm_position(chat_id)

    if not position:
        await query.edit_message_text(
            "❌ Tidak ada posisi pending untuk dikonfirmasi."
        )
        return

    # Format success message
    from tg_bot.formatter import format_position_opened
    message = format_position_opened(position)

    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )

    logger.info(f"Position confirmed: #{position.id} for chat_id {chat_id}")


async def portfolio_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle position cancellation callback"""
    if not update.callback_query or not update.effective_chat:
        return

    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await query.edit_message_text("❌ Paper trading not initialized.")
        return

    # Cancel pending position
    cancelled = paper_trading.cancel_pending_position(chat_id)

    if cancelled:
        await query.edit_message_text(
            "❌ Posisi dibatalkan."
        )
        logger.info(f"Position cancelled for chat_id {chat_id}")
    else:
        await query.edit_message_text(
            "❌ Tidak ada posisi pending untuk dibatalkan."
        )


async def portfolio_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close existing position"""
    if not update.effective_message or not update.effective_chat:
        return

    if not context.args or len(context.args) < 2:
        await update.effective_message.reply_text(
            "❌ Format tidak valid.\n\n"
            "Gunakan: /portfolio_close POSITION_ID CLOSE_PRICE\n\n"
            "Contoh: /portfolio_close 1 99000"
        )
        return

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await update.effective_message.reply_text(
            "❌ Paper trading not initialized. Please contact admin."
        )
        return

    try:
        position_id = int(context.args[0])
        close_price = float(context.args[1])

        # Close position
        success = paper_trading.close_position(position_id, close_price, chat_id)

        if success:
            await update.effective_message.reply_text(
                f"✅ Posisi #{position_id} ditutup pada harga ${close_price:,.2f}\n\n"
                "Gunakan /portfolio untuk melihat P&L.",
                parse_mode='Markdown'
            )
            logger.info(f"Position #{position_id} closed by chat_id {chat_id}")
        else:
            await update.effective_message.reply_text(
                f"❌ Gagal menutup posisi #{position_id}\n"
                "Pastikan ID posisi benar dan milik Anda."
            )

    except ValueError:
        await update.effective_message.reply_text(
            "❌ Format tidak valid.\n\n"
            "Gunakan angka untuk POSITION_ID dan CLOSE_PRICE.\n"
            "Contoh: /portfolio_close 1 99000"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in portfolio_close: {e}", exc_info=True)


async def portfolio_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all open positions"""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    paper_trading = context.bot_data.get('paper_trading')

    if not paper_trading:
        await update.effective_message.reply_text(
            "❌ Paper trading not initialized. Please contact admin."
        )
        return

    positions = paper_trading.get_open_positions(chat_id)

    if not positions:
        await update.effective_message.reply_text(
            "📊 **Tidak Ada Posisi Terbuka**\n\n"
            "Gunakan /portfolio_add untuk membuka posisi baru.",
            parse_mode='Markdown'
        )
        return

    # Format positions list
    from tg_bot.formatter import format_positions_list
    message = format_positions_list(positions)

    await update.effective_message.reply_text(
        message,
        parse_mode='Markdown'
    )


async def portfolio_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show portfolio help"""
    if not update.effective_message:
        return

    help_text = """📖 **Portfolio Commands Help**

**Portfolio Management:**
• `/portfolio` - Lihat ringkasan portfolio
• `/portfolio_add` - Buka posisi baru
• `/portfolio_list` - Lihat semua posisi terbuka
• `/portfolio_close ID PRICE` - Tutup posisi

**Format Command:**

📝 *Buka Posisi Baru*
```
/portfolio_add SYMBOL TYPE ENTRY QTY [SL] [TPs]
```

**Parameter:**
• SYMBOL - Contoh: BTCUSDT, ETHUSDT
• TYPE - LONG (beli) atau SHORT (jual)
• ENTRY - Harga entry (dalam USDT)
• QTY - Jumlah koin (contoh: 0.001 BTC)
• SL - Stop loss (opsional)
• TPs - Take profit levels, pisahkan dengan koma (opsional)

**Contoh:**
```
/portfolio_add BTCUSDT LONG 98000 0.001 97000 99000,100000
/portfolio_add ETHUSDT SHORT 3500 0.5 3600
```

📌 *Penjelasan:*
- LONG = Profit jika harga NAIK
- SHORT = Profit jika harga TURUN
- QTY = Quantity/jumlah koin yang dibeli
- Leverage = 1x (non-leverage)

**Tutup Posisi:**
```
/portfolio_close POSITION_ID CLOSE_PRICE
```

⚠️ *Paper Trading Mode:*
Semua transaksi adalah SIMULASI tanpa uang sungguhan.
Gunakan untuk testing strategi trading Anda.
"""

    await update.effective_message.reply_text(
        help_text,
        parse_mode='Markdown'
    )
