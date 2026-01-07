"""
Permission system for Telegram bot commands.
Implements role-based access control (RBAC) with tier-based permissions.
"""

from functools import wraps
from typing import Callable, List, Optional
import logging

from tg_bot.database import db
from config import config

logger = logging.getLogger(__name__)


def check_permission(chat_id: int, feature: str) -> bool:
    """
    Check if user has permission to access a feature.

    Args:
        chat_id: User's Telegram chat ID
        feature: Feature name to check access for

    Returns:
        True if user has access, False otherwise
    """
    try:
        # Check if user exists and is enabled
        user = db.get_user(chat_id)
        if not user:
            logger.warning(f"User {chat_id} not found in database")
            return False

        if not user.get('enabled', False):
            logger.warning(f"User {chat_id} is disabled")
            return False

        # Check feature access using database method
        has_access = db.has_feature_access(chat_id, feature)

        if not has_access:
            logger.info(f"User {chat_id} (tier: {user.get('tier', 'free')}) denied access to feature: {feature}")

        return has_access

    except Exception as e:
        logger.error(f"Error checking permission for user {chat_id}, feature {feature}: {e}")
        return False


def require_feature(feature: str):
    """
    Decorator to require specific feature access for command execution.

    Usage:
        @require_feature('plan')
        async def plan_command(update, context):
            # Command logic here
            pass

    Args:
        feature: Feature name (must exist in config.FEATURE_ACCESS)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            if not update.effective_chat:
                await update.message.reply_text("Error: Unable to identify user.")
                return

            chat_id = update.effective_chat.id

            # Check permission
            if not check_permission(chat_id, feature):
                # Get user tier for better error message
                user = db.get_user(chat_id)
                tier = user.get('tier', 'free') if user else 'free'

                feature_info = config.FEATURE_ACCESS.get(feature, {})
                description = feature_info.get('description', 'this feature')

                # Provide helpful error message
                if tier == 'free':
                    message = (
                        f"❌ *Access Denied*\n\n"
                        f"'{description}' is not available for Free tier users.\n\n"
                        f"👤 *Your Info:*\n"
                        f"• Chat ID: `{chat_id}`\n"
                        f"• Tier: {tier.capitalize()}\n\n"
                        f"📈 *Upgrade to Premium* to access:\n"
                        f"• Technical Analysis\n"
                        f"• AI Trading Plans\n"
                        f"• Price Alerts\n"
                        f"• And much more!\n\n"
                        f"💬 Contact @admin with your Chat ID for subscription info."
                    )
                else:
                    message = (
                        f"❌ *Access Denied*\n\n"
                        f"You don't have permission to access '{description}'.\n\n"
                        f"👤 *Your Info:*\n"
                        f"• Chat ID: `{chat_id}`\n"
                        f"• Tier: {tier.capitalize()}\n\n"
                        f"If you believe this is an error, please contact admin with your Chat ID."
                    )

                await update.message.reply_text(message, parse_mode='Markdown')
                return

            # Permission granted, execute the function
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def require_admin(func: Callable):
    """
    Decorator to require admin role for command execution.

    Usage:
        @require_admin
        async def admin_command(update, context):
            # Admin-only logic here
            pass
    """
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        if not update.effective_chat:
            await update.message.reply_text("Error: Unable to identify user.")
            return

        chat_id = update.effective_chat.id

        # Check if user is admin
        if not db.is_admin(chat_id):
            await update.message.reply_text(
                "❌ *Admin Only*\n\n"
                "This command is restricted to administrators only.",
                parse_mode='Markdown'
            )
            return

        # Admin permission granted, execute the function
        return await func(update, context, *args, **kwargs)

    return wrapper


def require_tier(minimum_tier: str):
    """
    Decorator to require minimum tier level for command execution.

    Tier hierarchy: free < premium < admin

    Usage:
        @require_tier('premium')
        async def premium_command(update, context):
            # Premium+ logic here
            pass

    Args:
        minimum_tier: Minimum tier required ('free', 'premium', or 'admin')
    """
    tier_hierarchy = {'free': 0, 'premium': 1, 'admin': 2}

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            if not update.effective_chat:
                await update.message.reply_text("Error: Unable to identify user.")
                return

            chat_id = update.effective_chat.id

            # Get user tier
            user_tier = db.get_user_tier(chat_id)

            # Check if user meets tier requirement
            if tier_hierarchy.get(user_tier, 0) < tier_hierarchy.get(minimum_tier, 0):
                tier_names = {
                    'free': 'Free',
                    'premium': 'Premium',
                    'admin': 'Admin'
                }

                message = (
                    f"❌ *Access Denied*\n\n"
                    f"This command requires {tier_names.get(minimum_tier, minimum_tier)} tier or higher.\n\n"
                    f"👤 *Your Info:*\n"
                    f"• Chat ID: `{chat_id}`\n"
                    f"• Current Tier: {tier_names.get(user_tier, user_tier)}\n"
                    f"• Required Tier: {tier_names.get(minimum_tier, minimum_tier)}"
                )

                if minimum_tier == 'premium':
                    message += "\n\n💬 Contact @admin with your Chat ID to upgrade your subscription."

                await update.message.reply_text(message, parse_mode='Markdown')
                return

            # Tier requirement met, execute the function
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def check_subscription_limits(chat_id: int, feature: str) -> tuple[bool, str]:
    """
    Check if user has not exceeded their subscription limits.

    Args:
        chat_id: User's Telegram chat ID
        feature: Feature type ('signals', 'alerts', 'subscriptions')

    Returns:
        Tuple of (has_limit: bool, error_message: str)
    """
    try:
        user_tier = db.get_user_tier(chat_id)
        user = db.get_user(chat_id)

        if not user:
            return False, "User not found"

        # Admins have unlimited access
        if db.is_admin(chat_id):
            return True, ""

        # Get limits from config
        if feature == 'signals':
            # Check daily signals limit (not implemented yet, placeholder)
            if user_tier == 'free':
                limit = config.SUBSCRIPTION.free_daily_signals_limit
                if limit > 0:  # -1 means unlimited
                    # TODO: Implement daily signal tracking
                    pass

        elif feature == 'alerts':
            # Check max alerts
            current_alerts = len(db.get_user_alerts(chat_id, active_only=True))

            if user_tier == 'free':
                max_alerts = config.SUBSCRIPTION.free_max_alerts
                if current_alerts >= max_alerts:
                    return False, f"Free tier limited to {max_alerts} alerts. Upgrade to Premium for up to {config.SUBSCRIPTION.premium_max_alerts} alerts."

            elif user_tier == 'premium':
                max_alerts = config.SUBSCRIPTION.premium_max_alerts
                if current_alerts >= max_alerts:
                    return False, f"Maximum alert limit reached ({max_alerts})."

        elif feature == 'subscriptions':
            # Check max symbol subscriptions
            current_subs = len(db.get_user_subscriptions(chat_id))

            if user_tier == 'free':
                max_subs = config.SUBSCRIPTION.free_max_subscriptions
                if current_subs >= max_subs:
                    return False, f"Free tier limited to {max_subs} subscriptions. Upgrade to Premium for up to {config.SUBSCRIPTION.premium_max_subscriptions} subscriptions."

            elif user_tier == 'premium':
                max_subs = config.SUBSCRIPTION.premium_max_subscriptions
                if current_subs >= max_subs:
                    return False, f"Maximum subscription limit reached ({max_subs})."

        return True, ""

    except Exception as e:
        logger.error(f"Error checking subscription limits for user {chat_id}, feature {feature}: {e}")
        return True, ""  # Allow on error to not block users


def get_available_features(chat_id: int) -> List[str]:
    """
    Get list of available features for a user based on their tier.

    Args:
        chat_id: User's Telegram chat ID

    Returns:
        List of feature names available to the user
    """
    try:
        user_tier = db.get_user_tier(chat_id)

        available_features = []
        for feature_name, feature_config in config.FEATURE_ACCESS.items():
            allowed_tiers = feature_config.get('allowed_tiers', [])
            if user_tier in allowed_tiers or db.is_admin(chat_id):
                available_features.append(feature_name)

        return available_features

    except Exception as e:
        logger.error(f"Error getting available features for user {chat_id}: {e}")
        return []


def format_feature_list_by_tier(tier: str = 'free') -> str:
    """
    Format a list of features available for a specific tier.

    Args:
        tier: Tier to get features for ('free', 'premium', 'admin')

    Returns:
        Formatted string with feature list
    """
    try:
        features_by_category = {
            'Basic': [],
            'Trading Analysis': [],
            'Market Screening': [],
            'Portfolio & Trading': [],
            'Alerts & Monitoring': [],
            'User Management': [],
            'System & Admin': [],
        }

        for feature_name, feature_config in config.FEATURE_ACCESS.items():
            if tier in feature_config.get('allowed_tiers', []):
                description = feature_config.get('description', feature_name)

                # Categorize features
                if feature_name in ['price', 'help', 'start', 'status', 'settings', 'signals', 'trending']:
                    features_by_category['Basic'].append(f"• {description}")
                elif feature_name in ['analyze', 'ta', 'plan']:
                    features_by_category['Trading Analysis'].append(f"• {description}")
                elif feature_name in ['screen', 'screen_auto', 'signal_history', 'whale_alerts']:
                    features_by_category['Market Screening'].append(f"• {description}")
                elif feature_name in ['portfolio', 'add_position', 'close_position', 'update_position']:
                    features_by_category['Portfolio & Trading'].append(f"• {description}")
                elif feature_name in ['add_alert', 'list_alerts', 'delete_alert', 'subscribe', 'unsubscribe', 'list_subscriptions']:
                    features_by_category['Alerts & Monitoring'].append(f"• {description}")
                elif feature_name in ['users', 'ban', 'unban', 'promote', 'demote', 'set_tier', 'grant_feature', 'revoke_feature']:
                    features_by_category['User Management'].append(f"• {description}")
                elif feature_name in ['config', 'broadcast', 'stats', 'subscription_history']:
                    features_by_category['System & Admin'].append(f"• {description}")

        # Format output
        output = f"*{tier.upper()} Tier Features*\n\n"

        for category, features in features_by_category.items():
            if features:
                output += f"📌 *{category}*\n"
                output += "\n".join(features)
                output += "\n\n"

        return output

    except Exception as e:
        logger.error(f"Error formatting feature list for tier {tier}: {e}")
        return "Error loading features."
