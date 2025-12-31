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

*PORTFOLIO* (Coming Soon)
/myportfolio - Show portfolio summary

*Need more help?*
Contact @admin for support
{TelegramFormatter.EMOJI['rocket']}
"""

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

            message = f"""{TelegramFormatter.EMOJI['robot']} *AI Trading Plan*
{TelegramFormatter.EMOJI['chart']} *{plan.symbol}* - {plan.generated_at.strftime('%Y-%m-%d %H:%M')}

*Signal*: {plan.overall_signal.signal_type} {signal_emoji}
*Confidence*: {plan.overall_signal.confidence:.1%}
*Trend*: {plan.trend} {trend_emoji}

*Entry Levels*:
"""

            # Entry levels
            for i, entry in enumerate(plan.entries, 1):
                message += f"{TelegramFormatter.EMOJI['money']} ${entry.level:,.2f} ({entry.weight:.0%})\n"

            message += "\n*Take Profits*:\n"
            # Take profits
            for tp in plan.take_profits:
                message += f"{TelegramFormatter.EMOJI['target']} ${tp.level:,.2f} (R:R {tp.reward_ratio:.1f}x)\n"

            # Stop loss
            message += f"\n*Stop Loss*: ${plan.stop_loss:,.2f}"
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
