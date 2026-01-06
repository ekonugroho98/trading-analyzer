"""
Admin command handlers for Telegram bot.
Handles user management, tier management, and system administration.
"""

import logging
from datetime import datetime
from telegram import Update, ParseMode
from telegram.ext import ContextTypes

from tg_bot.database import db
from tg_bot.permissions import require_admin, require_feature
from config import config

logger = logging.getLogger(__name__)


@require_admin
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users in the system"""
    try:
        users = db.get_all_users(enabled_only=False)

        if not users:
            await update.message.reply_text("No users found in the system.")
            return

        # Group users by tier
        tier_groups = {'free': [], 'premium': [], 'admin': []}
        disabled_users = []

        for user in users:
            user_info = f"{'🔴' if not user['enabled'] else '🟢'} "
            user_info += f"@{user['username'] or 'N/A'} "
            user_info += f"(ID: `{user['chat_id']}`)\n"
            user_info += f"  └ Tier: {user['tier']} | Role: {user['role']}"

            if not user['enabled']:
                disabled_users.append(user_info)
            else:
                tier_groups[user['tier']].append(user_info)

        # Format message
        message = "*👥 User Management*\n\n"

        message += f"📊 *Statistics*\n"
        message += f"• Total Users: {len(users)}\n"
        message += f"• Free Tier: {len(tier_groups['free'])}\n"
        message += f"• Premium Tier: {len(tier_groups['premium'])}\n"
        message += f"• Admins: {len(tier_groups['admin'])}\n"
        message += f"• Disabled: {len(disabled_users)}\n\n"

        # Show users by tier
        if tier_groups['admin']:
            message += "*👑 Admins*\n" + "\n".join(tier_groups['admin'][:5]) + "\n\n"

        if tier_groups['premium']:
            message += f"*⭐ Premium Users ({len(tier_groups['premium'])})*\n"
            message += "\n".join(tier_groups['premium'][:10])
            if len(tier_groups['premium']) > 10:
                message += f"\n  ... and {len(tier_groups['premium']) - 10} more"
            message += "\n\n"

        if tier_groups['free']:
            message += f"*👤 Free Users ({len(tier_groups['free'])})*\n"
            message += "\n".join(tier_groups['free'][:10])
            if len(tier_groups['free']) > 10:
                message += f"\n  ... and {len(tier_groups['free']) - 10} more"
            message += "\n\n"

        if disabled_users:
            message += f"*🔴 Disabled Users ({len(disabled_users)})*\n"
            message += "\n".join(disabled_users[:5])
            if len(disabled_users) > 5:
                message += f"\n  ... and {len(disabled_users) - 5} more"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in users_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the bot"""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: `/ban <chat_id_or_username> [reason]`\n\n"
                "Example: `/ban 123456789 spamming`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Disable user
        success = db.enable_user(chat_id, enabled=False)

        if success:
            logger.info(f"User {chat_id} banned by admin {update.effective_chat.id}. Reason: {reason}")
            await update.message.reply_text(
                f"✅ User `{chat_id}` has been banned.\n"
                f"Reason: {reason}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to ban user.")

    except Exception as e:
        logger.error(f"Error in ban_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user"""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: `/unban <chat_id_or_username>`\n\n"
                "Example: `/unban 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Enable user
        success = db.enable_user(chat_id, enabled=True)

        if success:
            logger.info(f"User {chat_id} unbanned by admin {update.effective_chat.id}")
            await update.message.reply_text(
                f"✅ User `{chat_id}` has been unbanned.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to unban user.")

    except Exception as e:
        logger.error(f"Error in unban_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin role"""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: `/promote <chat_id_or_username>`\n\n"
                "Example: `/promote 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Update user role to admin
        success = db.update_user_role(chat_id, 'admin')

        if success:
            logger.info(f"User {chat_id} promoted to admin by {update.effective_chat.id}")
            await update.message.reply_text(
                f"✅ User `{chat_id}` has been promoted to *admin* role.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to promote user.")

    except Exception as e:
        logger.error(f"Error in promote_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote an admin to user role"""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: `/demote <chat_id_or_username>`\n\n"
                "Example: `/demote 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Update user role to user
        success = db.update_user_role(chat_id, 'user')

        if success:
            logger.info(f"User {chat_id} demoted to user by {update.effective_chat.id}")
            await update.message.reply_text(
                f"✅ User `{chat_id}` has been demoted to *user* role.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to demote user.")

    except Exception as e:
        logger.error(f"Error in demote_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def set_tier_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user subscription tier"""
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/set_tier <chat_id_or_username> <tier> [duration_days] [payment_amount] [notes]`\n\n"
                "Tiers: `free`, `premium`\n\n"
                "Example: `/set_tier 123456789 premium 30 50.00 Monthly subscription`\n"
                "Example: `/set_tier @username free`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]
        tier = context.args[1].lower()
        duration_days = int(context.args[2]) if len(context.args) > 2 and context.args[2].isdigit() else None
        payment_amount = float(context.args[3]) if len(context.args) > 3 else None
        notes = " ".join(context.args[4:]) if len(context.args) > 4 else None

        # Validate tier
        if tier not in ['free', 'premium']:
            await update.message.reply_text("❌ Invalid tier. Must be 'free' or 'premium'.")
            return

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Set user tier
        success = db.set_user_tier(
            chat_id=chat_id,
            tier=tier,
            duration_days=duration_days,
            payment_amount=payment_amount,
            payment_method="manual",
            notes=notes,
            admin_chat_id=update.effective_chat.id
        )

        if success:
            logger.info(f"User {chat_id} tier set to {tier} by admin {update.effective_chat.id}")

            message = f"✅ User `{chat_id}` tier set to *{tier.upper()}*"

            if tier == 'premium' and duration_days:
                from datetime import timedelta
                expire_date = datetime.now() + timedelta(days=duration_days)
                message += f"\n📅 Expires: {expire_date.strftime('%Y-%m-%d')}"

                if payment_amount:
                    message += f"\n💰 Payment: ${payment_amount}"

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Failed to set user tier.")

    except Exception as e:
        logger.error(f"Error in set_tier_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def grant_feature_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant specific feature access to a user"""
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/grant_feature <chat_id_or_username> <feature_name> [duration_days]`\n\n"
                "Example: `/grant_feature 123456789 screen 30`\n"
                "Example: `/grant_feature @username plan`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]
        feature = context.args[1]
        duration_days = int(context.args[2]) if len(context.args) > 2 and context.args[2].isdigit() else None

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Grant feature
        success = db.grant_feature(
            chat_id=chat_id,
            feature=feature,
            duration_days=duration_days,
            admin_chat_id=update.effective_chat.id
        )

        if success:
            logger.info(f"Feature '{feature}' granted to {chat_id} by admin {update.effective_chat.id}")

            message = f"✅ Feature '{feature}' granted to user `{chat_id}`"

            if duration_days:
                from datetime import timedelta
                expire_date = datetime.now() + timedelta(days=duration_days)
                message += f"\n📅 Expires: {expire_date.strftime('%Y-%m-%d')}"

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Failed to grant feature.")

    except Exception as e:
        logger.error(f"Error in grant_feature_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def revoke_feature_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revoke specific feature access from a user"""
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/revoke_feature <chat_id_or_username> <feature_name>`\n\n"
                "Example: `/revoke_feature 123456789 screen`\n"
                "Example: `/revoke_feature @username plan`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        identifier = context.args[0]
        feature = context.args[1]

        # Try to parse as chat_id (supports @username)
        if identifier.startswith('@'):
            # Search by username
            users = db.get_all_users(enabled_only=False)
            target_user = None
            for user in users:
                if user['username'] and user['username'].lower() == identifier[1:].lower():
                    target_user = user
                    break

            if not target_user:
                await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                return

            chat_id = target_user['chat_id']
        else:
            # Use as chat_id
            try:
                chat_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format.")
                return

        # Revoke feature
        success = db.revoke_feature(chat_id, feature)

        if success:
            logger.info(f"Feature '{feature}' revoked from {chat_id} by admin {update.effective_chat.id}")
            await update.message.reply_text(
                f"✅ Feature '{feature}' revoked from user `{chat_id}`.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to revoke feature.")

    except Exception as e:
        logger.error(f"Error in revoke_feature_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def subscription_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View subscription history"""
    try:
        chat_id_filter = None

        # Optional: filter by specific user
        if context.args and len(context.args) > 0:
            identifier = context.args[0]

            if identifier.startswith('@'):
                # Search by username
                users = db.get_all_users(enabled_only=False)
                target_user = None
                for user in users:
                    if user['username'] and user['username'].lower() == identifier[1:].lower():
                        target_user = user
                        break

                if not target_user:
                    await update.message.reply_text(f"❌ User '@{identifier[1:]}' not found.")
                    return

                chat_id_filter = target_user['chat_id']
            else:
                try:
                    chat_id_filter = int(identifier)
                except ValueError:
                    await update.message.reply_text("❌ Invalid chat ID format.")
                    return

        # Get subscription history
        history = db.get_subscription_history(chat_id=chat_id_filter, limit=20)

        if not history:
            await update.message.reply_text("No subscription history found.")
            return

        # Format message
        message = "*📜 Subscription History*\n\n"

        for record in history:
            message += f"🆔 ID: {record['id']}\n"
            message += f"👤 User: `{record['chat_id']}`\n"
            message += f"⭐ Tier: {record['tier'].upper()}\n"
            message += f"📝 Action: {record['action']}\n"

            if record['duration_days']:
                message += f"⏱ Duration: {record['duration_days']} days\n"

            if record['payment_amount']:
                message += f"💰 Amount: ${record['payment_amount']}\n"

            if record['notes']:
                message += f"📌 Notes: {record['notes']}\n"

            message += f"📅 Date: {record['created_at']}\n"
            message += "\n"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in subscription_history_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View system statistics"""
    try:
        users = db.get_all_users(enabled_only=False)

        # Count by tier
        tier_counts = {'free': 0, 'premium': 0, 'admin': 0}
        disabled_count = 0

        for user in users:
            if not user['enabled']:
                disabled_count += 1
            else:
                tier_counts[user['tier']] += 1

        # Format message
        message = "*📊 System Statistics*\n\n"

        message += "*👥 Users*\n"
        message += f"• Total: {len(users)}\n"
        message += f"• Active: {len(users) - disabled_count}\n"
        message += f"• Disabled: {disabled_count}\n\n"

        message += "*⭐ Tier Distribution*\n"
        message += f"• Free: {tier_counts['free']}\n"
        message += f"• Premium: {tier_counts['premium']}\n"
        message += f"• Admin: {tier_counts['admin']}\n\n"

        # Get subscription history count
        history = db.get_subscription_history(limit=1000)
        if history:
            message += f"*💰 Subscriptions*\n"
            message += f"• Total Transactions: {len(history)}\n"

            # Calculate revenue
            revenue = sum([h['payment_amount'] for h in history if h['payment_amount']])
            if revenue > 0:
                message += f"• Total Revenue: ${revenue:.2f}\n"
            message += "\n"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_admin
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all enabled users"""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/broadcast <message>`\n\n"
                "Example: `/broadcast System maintenance in 1 hour`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        message_content = " ".join(context.args)

        # Get all enabled users
        users = db.get_all_users(enabled_only=True)

        if not users:
            await update.message.reply_text("No users to broadcast to.")
            return

        # Send broadcast
        success_count = 0
        failed_count = 0

        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['chat_id'],
                    text=f"📢 *Broadcast Message*\n\n{message_content}",
                    parse_mode=ParseMode.MARKDOWN
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['chat_id']}: {e}")
                failed_count += 1

        # Report results
        result_message = (
            f"✅ Broadcast sent!\n\n"
            f"• Success: {success_count}\n"
            f"• Failed: {failed_count}\n"
            f"• Total: {len(users)}"
        )

        await update.message.reply_text(result_message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Broadcast sent by admin {update.effective_chat.id}. Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in broadcast_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
