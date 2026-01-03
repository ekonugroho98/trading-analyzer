"""
Telegram Message Formatter
Format and style messages for Telegram bot
"""

from typing import Dict, List, Any
from datetime import datetime

from config import config


class TelegramFormatter:
    """Format messages for Telegram with markdown and emojis"""

    # Emojis
    EMOJI = {
        'buy': '🟢',
        'sell': '🔴',
        'hold': '🟡',
        'bullish': '📈',
        'bearish': '📉',
        'neutral': '➡️',
        'alert': '🚨',
        'rocket': '🚀',
        'money': '💰',
        'target': '🎯',
        'chart': '📊',
        'robot': '🤖',
        'bell': '🔔',
        'info': 'ℹ️',
        'warning': '⚠️',
        'check': '✅',
        'cross': '❌',
        'fire': '🔥',
        'sparkles': '✨',
    }

    @staticmethod
    def welcome(username: str = None) -> str:
        """Welcome message for /start"""
        name = username or "Trader"
        return f"""👋 *Welcome to Crypto Trading Analyzer, {name}!*

{TelegramFormatter.EMOJI['robot']} *I'm your AI-powered trading assistant*

Here's what I can do for you:

*Basic Commands:*
/help - Show all commands
/status - Check system status
/price [symbol] - Get current price

*Trading Analysis:*
/plan [symbol] - Generate AI trading plan
/analyze [symbol] - Quick technical analysis

*Subscriptions:*
/subscribe [symbol] - Subscribe to updates
/mysubscriptions - List your subscriptions

*Alerts:*
/setalert [symbol] [above/below] [price] - Set price alert
/myalerts - List your alerts

*Example:*
/plan BTCUSDT
/subscribe SOLUSDT
/setalert BTCUSDT above 90000

{TelegramFormatter.EMOJI['info']} *Start with /help to see all available commands!*
"""

    @staticmethod
    def help_command() -> str:
        """Help message with all commands"""
        return f"""*📚 Crypto Trading Analyzer - Help*

*BASIC COMMANDS*
/start - Initialize bot
/help - Show this help message
/status - System status check

*MARKET DATA*
/price [symbol] - Get current price & info
Example: `/price BTCUSDT`

*TRADING ANALYSIS*
/plan [symbol] - Generate AI trading plan
/plan [symbol] [timeframe] - Plan with timeframe
Example: `/plan ETHUSDT 1h`

/analyze [symbol] - Quick technical analysis
/ta [symbol] - Comprehensive technical analysis
/signals - Get current signals for subscriptions
/trending - Show trending coins

*MARKET SCREENING*
/screen [timeframe] [limit] - Screen market for setups
/screener_help - Show screening help

*SUBSCRIPTIONS*
/subscribe [symbol] - Subscribe to symbol updates
/unsubscribe [symbol] - Unsubscribe
/mysubscriptions - List your subscriptions
/subscribeall - Subscribe to all major pairs

*ALERTS*
/setalert [symbol] [above/below] [price] - Set price alert
Example: `/setalert BTCUSDT above 90000`

/myalerts - List your alerts
/delalert [alert_id] - Delete alert
/clearalerts - Clear all alerts

*PAPER TRADING* (Simulasi Tanpa Modal)
/portfolio - View portfolio summary
/portfolio_add - Add new paper trading position
/portfolio_list - List all open positions
/portfolio_close - Close position
/portfolio_help - Show paper trading help

*PORTFOLIO MANAGEMENT*
/myportfolio - Show real portfolio summary
/addposition - Add real position
/closeposition - Close real position

*Need more help?*
Contact @admin for support
{TelegramFormatter.EMOJI['rocket']}
"""

    @staticmethod
    def _format_price(price: float) -> str:
        """Format price with appropriate precision based on value"""
        if price >= 1000:
            # High-priced coins (BTC): show 2 decimals
            return f"${price:,.2f}"
        elif price >= 1:
            # Medium-priced coins: show 4 decimals
            return f"${price:,.4f}"
        else:
            # Low-priced coins (shitcoins): show 6-8 decimals
            return f"${price:,.8f}".rstrip('0').rstrip('.')

    @staticmethod
    def trading_plan(plan: Any) -> str:
        """Format trading plan notification"""
        try:
            # Signal emoji
            signal_emoji = {
                'BUY': TelegramFormatter.EMOJI['buy'],
                'SELL': TelegramFormatter.EMOJI['sell'],
                'HOLD': TelegramFormatter.EMOJI['hold'],
            }.get(plan.overall_signal.signal_type.upper(), TelegramFormatter.EMOJI['hold'])

            # Trend emoji
            trend_emoji = {
                'BULLISH': TelegramFormatter.EMOJI['bullish'],
                'BEARISH': TelegramFormatter.EMOJI['bearish'],
                'SIDEWAYS': TelegramFormatter.EMOJI['neutral'],
            }.get(plan.trend.upper(), TelegramFormatter.EMOJI['neutral'])

            # Format current price
            formatted_current_price = TelegramFormatter._format_price(plan.current_price)

            message = f"""{TelegramFormatter.EMOJI['robot']} *AI Trading Plan*
{TelegramFormatter.EMOJI['chart']} *{plan.symbol}* - {plan.generated_at.strftime('%Y-%m-%d %H:%M')}

*Current Price*: {formatted_current_price} {TelegramFormatter.EMOJI['money']}
*Signal*: {plan.overall_signal.signal_type} {signal_emoji}
*Confidence*: {plan.overall_signal.confidence:.1%}
*Trend*: {plan.trend} {trend_emoji}

*Entry Levels*:
"""

            # Entry levels
            for i, entry in enumerate(plan.entries, 1):
                formatted_price = TelegramFormatter._format_price(entry.level)
                message += f"{TelegramFormatter.EMOJI['money']} {formatted_price} ({entry.weight:.0%})\n"

            message += "\n*Take Profits*:\n"
            # Take profits
            for tp in plan.take_profits:
                formatted_price = TelegramFormatter._format_price(tp.level)
                message += f"{TelegramFormatter.EMOJI['target']} {formatted_price} (R:R {tp.reward_ratio:.1f}x)\n"

            # Stop loss
            formatted_sl = TelegramFormatter._format_price(plan.stop_loss)
            message += f"\n*Stop Loss*: {formatted_sl}"
            message += f"\n*Risk/Reward*: {plan.risk_reward_ratio:.2f}"

            # Reason
            if plan.overall_signal.reason:
                message += f"\n\n_Reason: {plan.overall_signal.reason}_"

            # Warnings
            if plan.warnings:
                message += f"\n\n{TelegramFormatter.EMOJI['warning']} *Warnings*:\n"
                for warning in plan.warnings[:3]:  # Max 3 warnings
                    message += f"• {warning}\n"

            return message
        except Exception as e:
            return f"Error formatting trading plan: {e}"

    @staticmethod
    def price_info(symbol: str, price_data: Dict) -> str:
        """Format price information"""
        try:
            change_emoji = TelegramFormatter.EMOJI['bullish'] if price_data.get('change_24h', 0) >= 0 else TelegramFormatter.EMOJI['bearish']

            message = f"""{TelegramFormatter.EMOJI['chart']} *{symbol}*

*Price*: ${price_data.get('price', 0):,.2f}
*Change 24h*: {change_emoji} {price_data.get('change_24h', 0):+.2f}%
*Volume 24h*: ${price_data.get('volume_24h', 0):,.0f}

*High 24h*: ${price_data.get('high_24h', 0):,.2f}
*Low 24h*: ${price_data.get('low_24h', 0):,.2f}

_Updated: {datetime.now().strftime('%H:%M:%S')}_
"""
            return message
        except Exception as e:
            return f"Error formatting price info: {e}"

    @staticmethod
    def price_alert(symbol: str, alert_type: str, target_price: float, current_price: float, change_percent: float = None) -> str:
        """Format price alert notification"""
        direction = "above" if alert_type == "above" else "below"
        direction_emoji = TelegramFormatter.EMOJI['fire'] if direction == "above" else TelegramFormatter.EMOJI['sparkles']

        message = f"""{TelegramFormatter.EMOJI['alert']} *Price Alert Triggered*
{TelegramFormatter.EMOJI['chart']} *{symbol}*

{direction_emoji} Price broke {direction} ${target_price:,.2f}!

*Current Price*: ${current_price:,.2f}
"""

        if change_percent is not None:
            change_emoji = TelegramFormatter.EMOJI['bullish'] if change_percent >= 0 else TelegramFormatter.EMOJI['bearish']
            message += f"*Change*: {change_emoji} {change_percent:+.2f}%\n"

        message += f"\nConsider taking profits or adjusting stops! {TelegramFormatter.EMOJI['target']}"

        return message

    @staticmethod
    def signal_change(symbol: str, timeframe: str, old_signal: str, new_signal: str, price: float = None) -> str:
        """Format signal change notification"""
        old_emoji = {
            'BUY': TelegramFormatter.EMOJI['buy'],
            'SELL': TelegramFormatter.EMOJI['sell'],
            'HOLD': TelegramFormatter.EMOJI['hold'],
        }.get(old_signal.upper(), '')

        new_emoji = {
            'BUY': TelegramFormatter.EMOJI['buy'],
            'SELL': TelegramFormatter.EMOJI['sell'],
            'HOLD': TelegramFormatter.EMOJI['hold'],
        }.get(new_signal.upper(), '')

        message = f"""{TelegramFormatter.EMOJI['warning']} *Signal Change Alert*
{TelegramFormatter.EMOJI['chart']} *{symbol}* - {timeframe}

*Previous*: {old_signal} {old_emoji}
*Current*: {new_signal} {new_emoji}
"""

        if price:
            message += f"\n*Current Price*: ${price:,.2f}"

        message += f"\n\nCheck /plan {symbol} for detailed analysis! {TelegramFormatter.EMOJI['robot']}"

        return message

    @staticmethod
    def subscriptions_list(subscriptions: List[Dict]) -> str:
        """Format user subscriptions list"""
        if not subscriptions:
            return f"""{TelegramFormatter.EMOJI['info']} *Your Subscriptions*

You don't have any active subscriptions.

Use /subscribe [symbol] to start monitoring a coin!
"""

        message = f"{TelegramFormatter.EMOJI['bell']} *Your Subscriptions*\n\n"

        for sub in subscriptions:
            message += f"{TelegramFormatter.EMOJI['chart']} *{sub['symbol']}* - {sub['timeframe']}\n"

        message += f"\n*Total*: {len(subscriptions)} symbol(s)"
        return message

    @staticmethod
    def alerts_list(alerts: List[Dict]) -> str:
        """Format user alerts list"""
        if not alerts:
            return f"""{TelegramFormatter.EMOJI['info']} *Your Alerts*

You don't have any active alerts.

Use /setalert [symbol] [above/below] [price] to set an alert!
"""

        message = f"{TelegramFormatter.EMOJI['alert']} *Your Active Alerts*\n\n"

        for alert in alerts:
            direction = "↑" if alert['alert_type'] == 'above' else "↓"
            message += f"*{alert['id']}*. {alert['symbol']} {direction} ${alert['target_price']:,.2f}\n"

        message += f"\n*Total*: {len(alerts)} active alert(s)"
        return message

    @staticmethod
    def system_status(status: Dict) -> str:
        """Format system status message"""
        emoji_status = TelegramFormatter.EMOJI['check'] if status.get('running', False) else TelegramFormatter.EMOJI['cross']

        message = f"""{TelegramFormatter.EMOJI['info']} *System Status*

*Trading System*: {emoji_status}
*Streaming*: {'Active' if status.get('streaming', False) else 'Inactive'}
*Scheduler*: {'Active' if status.get('scheduler', False) else 'Inactive'}

*Active Users*: {status.get('total_users', 0)}
*Messages Processed*: {status.get('messages_processed', 0)}

*Uptime*: {status.get('uptime', 'Unknown')}
"""

        return message

    @staticmethod
    def error_message(error: str) -> str:
        """Format error message"""
        return f"""{TelegramFormatter.EMOJI['cross']} *Error*

{error}

Please try again or use /help for assistance.
"""

    @staticmethod
    def success_message(message: str) -> str:
        """Format success message"""
        return f"{TelegramFormatter.EMOJI['check']} {message}"

    @staticmethod
    def info_message(message: str) -> str:
        """Format info message"""
        return f"{TelegramFormatter.EMOJI['info']} {message}"

    @staticmethod
    def loading_message(action: str) -> str:
        """Format loading/processing message"""
        return f"⏳ {action}. Please wait..."


def format_portfolio_summary(summary: Dict) -> str:
    """Format portfolio summary message"""
    if summary['total_positions'] == 0:
        return """📊 **Portfolio Kosong**

Anda belum memiliki posisi terbuka.
Gunakan /portfolio_add untuk membuka posisi baru.
"""

    message = f"""📊 **Portfolio Summary**

📈 *Total Posisi*: {summary['total_positions']}
💰 *Total Value*: ${summary['total_value']:,.2f}
📉 *Total P&L*: ${summary['total_pnl']:,.2f}

**Posisi Terbuka**:
"""

    for pos in summary['positions']:
        pos_type_emoji = "🟢" if pos.position_type == "LONG" else "🔴"
        message += f"\n{pos_type_emoji} *{pos.symbol}* - {pos.position_type}\n"
        message += f"  Entry: ${pos.entry_price:,.4f}\n"
        message += f"  Qty: {pos.quantity:.4f}\n"
        message += f"  Value: ${pos.total_value:,.2f}\n"

        if pos.stop_loss:
            message += f"  SL: ${pos.stop_loss:,.4f}\n"

        if pos.take_profits:
            message += f"  TPs: "
            tp_levels = [f"${tp['level']:,.2f}" for tp in pos.take_profits]
            message += ", ".join(tp_levels) + "\n"

        if pos.notes:
            message += f"  📝 {pos.notes}\n"

    return message


def format_position_confirmation(position) -> str:
    """Format position confirmation message"""
    pos_type_emoji = "🟢" if position.position_type == "LONG" else "🔴"

    message = f"""📝 **Konfirmasi Posisi Baru**

{pos_type_emoji} *{position.symbol}* - {position.position_type}

💰 *Entry*: ${position.entry_price:,.4f}
📊 *Quantity*: {position.quantity:.4f}
💵 *Total Value*: ${position.total_value:,.2f}
"""

    if position.stop_loss:
        message += f"🛑 *Stop Loss*: ${position.stop_loss:,.4f}\n"

    if position.take_profits:
        message += f"🎯 *Take Profits*:\n"
        for i, tp in enumerate(position.take_profits, 1):
            pct = tp.get('percentage', 1.0) * 100
            message += f"  TP{i}: ${tp['level']:,.2f} ({pct:.0f}%)\n"

    if position.notes:
        message += f"📝 *Catatan*: {position.notes}\n"

    message += """
⚠️ *Paper Trading Mode*
Semua transaksi adalah SIMULASI tanpa uang sungguhan.

Konfirmasi untuk membuka posisi?
"""

    return message


def format_position_opened(position) -> str:
    """Format position opened message"""
    pos_type_emoji = "🟢" if position.position_type == "LONG" else "🔴"

    message = f"""✅ **Posisi Dibuka**

{pos_type_emoji} *{position.symbol}* - {position.position_type}
ID: `{position.id}`

💰 *Entry*: ${position.entry_price:,.4f}
📊 *Quantity*: {position.quantity:.4f}
💵 *Value*: ${position.total_value:,.2f}
"""

    if position.stop_loss:
        message += f"🛑 *Stop Loss*: ${position.stop_loss:,.4f}\n"

    if position.take_profits:
        message += f"🎯 *Take Profits*: "
        tp_levels = [f"${tp['level']:,.2f}" for tp in position.take_profits]
        message += ", ".join(tp_levels) + "\n"

    message += f"\n⏰ *Opened*: {position.opened_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "\nGunakan /portfolio_close ID PRICE untuk menutup posisi"

    return message


def format_positions_list(positions: List) -> str:
    """Format list of positions"""
    message = f"📊 **Daftar Posisi ({len(positions)})**\n\n"

    for pos in positions:
        pos_type_emoji = "🟢" if pos.position_type == "LONG" else "🔴"

        message += f"*{pos.symbol}* - {pos.position_type} {pos_type_emoji}\n"
        message += f"  ID: `{pos.id}`\n"
        message += f"  Entry: ${pos.entry_price:,.4f} | Qty: {pos.quantity:.4f}\n"
        message += f"  Value: ${pos.total_value:,.2f}\n"

        if pos.stop_loss:
            message += f"  SL: ${pos.stop_loss:,.4f}\n"

        if pos.take_profits:
            tp_str = ", ".join([f"${tp['level']:,.2f}" for tp in pos.take_profits])
            message += f"  TPs: {tp_str}\n"

        message += "\n"

    message += "Gunakan /portfolio_close ID PRICE untuk menutup posisi"

    return message


def format_screening_results(results: List, summary: Dict) -> str:
    """Format market screening results"""
    if not results:
        return f"""{TelegramFormatter.EMOJI['info']} *Market Screening Results*

No coins passed the screening criteria.

Try lowering the minimum score or screening more coins.
"""

    timeframe = summary.get('timeframe', 'Unknown')
    total = len(results)
    avg_score = summary.get('avg_score', 0)
    top_score = summary.get('top_score', 0)
    bullish_count = summary.get('bullish', 0)
    bearish_count = summary.get('bearish', 0)

    message = f"""{TelegramFormatter.EMOJI['chart']} *Market Screening Results* - {timeframe.upper()}

{TelegramFormatter.EMOJI['target']} *Top {total} Coins Passed*
{TelegramFormatter.EMOJI['sparkles']} *Avg Score*: {avg_score:.1f}/10
{TelegramFormatter.EMOJI['fire']} *Top Score*: {top_score:.1f}/10
{TelegramFormatter.EMOJI['bullish']} *Bullish*: {bullish_count} | {TelegramFormatter.EMOJI['bearish']} *Bearish*: {bearish_count}

"""

    for i, result in enumerate(results[:20], 1):  # Max 20 results
        # Score stars
        if result.score >= 9.0:
            stars = "⭐⭐⭐"
        elif result.score >= 8.0:
            stars = "⭐⭐"
        elif result.score >= 7.0:
            stars = "⭐"
        else:
            stars = ""

        # Trend emoji
        trend_emoji = {
            'BULLISH': TelegramFormatter.EMOJI['bullish'],
            'BEARISH': TelegramFormatter.EMOJI['bearish'],
            'NEUTRAL': TelegramFormatter.EMOJI['neutral']
        }.get(result.trend, TelegramFormatter.EMOJI['neutral'])

        # Format price
        formatted_price = TelegramFormatter._format_price(result.current_price)

        message += f"""*{i}. {result.symbol}* {stars}
💎 Score: {result.score:.1f}/10 {trend_emoji}
💰 Price: {formatted_price}
📊 24h: {result.change_24h:+.2f}%
📈 {result.trend}
🔑 {', '.join(result.signals[:3])}

"""

    message += f"""_{summary.get('timestamp', datetime.now()).strftime('%H:%M:%S')}_

Use /plan [symbol] for full trading plan! {TelegramFormatter.EMOJI['robot']}
"""

    return message


def format_screening_loading(timeframe: str, limit: int) -> str:
    """Format screening loading message"""
    return f"""⏳ *Market Screening Started*

🔍 Screening {limit} top USDT pairs
📊 Timeframe: {timeframe.upper()}
⚡ AI-powered analysis

This may take 2-5 minutes. Please wait...
"""


def format_screening_error(error: str) -> str:
    """Format screening error message"""
    return f"""{TelegramFormatter.EMOJI['cross']} *Screening Error*

{error}

Please try again or use /screener_help for more information.
"""


def format_screener_help() -> str:
    """Format screener help message"""
    return f"""{TelegramFormatter.EMOJI['info']} *Market Screener Help*

📊 *Quick Market Screening*

Screen top coins based on market structure and technical setup.

*COMMANDS:*
/screen [timeframe] [limit] - Screen market
• timeframe: 1h or 4h (default: 4h)
• limit: Number of coins to screen (default: 100)

*EXAMPLES:*
/screen 4h 100 - Screen top 100 on 4h
/screen 1h 50 - Screen top 50 on 1h

*SCORING SYSTEM (0-10):*
• Trend Structure (BOS, HH/HL): 3 points
• EMA Alignment: 2 points
• Momentum (RSI, MACD): 2 points
• Volume confluence: 2 points
• Support/Resistance: 1 point

*OUTPUT:*
• List of top 20 coins with score >= 7.0
• Ranked by score (highest first)
• Brief analysis for each coin

*NEXT STEPS:*
• /plan [symbol] - Get full trading plan
• /analyze [symbol] - Quick technical analysis

⚠️ *Note:* Screening is on-demand only, not scheduled.
"""
