# Commercial Feature Implementation Guide

## Overview
Aplikasi ini sudah dilengkapi dengan sistem **Tier-Based Access Control** untuk komersialisasi. Berikut adalah panduan implementasi fitur-fitur yang sudah dibuat.

---

## ✅ Components Implemented

### 1. Database Schema (tg_bot/database.py)
- ✅ Added `tier` column to users table (free, premium, admin)
- ✅ Added `subscription_expires_at` column for premium expiration
- ✅ New table: `user_features` - untuk grant specific feature ke user
- ✅ New table: `subscription_history` - untuk tracking payment/subscription

### 2. Feature Flag System (config.py)
- ✅ `FEATURE_ACCESS` dictionary - defines which features each tier can access
- ✅ `SUBSCRIPTION` namespace - limits untuk free vs premium users

### 3. Permission System (tg_bot/permissions.py)
- ✅ `@require_feature('feature_name')` - check specific feature access
- ✅ `@require_admin` - admin-only access
- ✅ `@require_tier('premium')` - minimum tier requirement
- ✅ `check_subscription_limits()` - validate usage limits

### 4. Admin Commands (tg_bot/handlers/admin.py)
- ✅ `/users` - List all users with tier info
- ✅ `/ban <user>` - Ban user from bot
- ✅ `/unban <user>` - Unban user
- ✅ `/promote <user>` - Promote to admin role
- ✅ `/demote <user>` - Demote to user role
- ✅ `/set_tier <user> <tier> [days] [amount]` - Set user tier
- ✅ `/grant_feature <user> <feature> [days]` - Grant specific feature
- ✅ `/revoke_feature <user> <feature>` - Revoke feature
- ✅ `/subscription_history [user]` - View subscription history
- ✅ `/stats` - System statistics
- ✅ `/broadcast <message>` - Send message to all users

---

## 🔧 How to Apply Permissions to Existing Commands

### Example 1: Basic Feature (Available to All)
```python
from tg_bot.permissions import require_feature

@require_feature('price')
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command implementation
    pass
```

### Example 2: Premium Feature
```python
from tg_bot.permissions import require_feature

@require_feature('plan')
async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only premium and admin users can access
    pass
```

### Example 3: Admin-Only Feature
```python
from tg_bot.permissions import require_admin

@require_admin
async def screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins can access
    pass
```

### Example 4: Check Subscription Limits
```python
from tg_bot.permissions import check_subscription_limits
from tg_bot.database import db

async def add_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Check if user has reached alert limit
    has_limit, error_msg = check_subscription_limits(chat_id, 'alerts')

    if not has_limit:
        await update.message.reply_text(f"❌ {error_msg}")
        return

    # Proceed with alert creation
    # ...
```

---

## 📋 Feature Categories

### Free Tier (Basic Users)
- ✅ `/price` - Get price information
- ✅ `/help` - Show help
- ✅ `/start` - Start bot
- ✅ `/status` - System status
- ✅ `/settings` - User preferences
- ✅ `/signals` - Trading signals (limited to 5/day)

### Premium Tier
- ✅ All free tier features
- ✅ `/analyze` - Technical analysis
- ✅ `/ta` - Technical analysis summary
- ✅ `/plan` - AI trading plans
- ✅ `/setalert` - Price alerts (up to 50)
- ✅ `/subscribe` - Subscribe to symbols (up to 100)
- ✅ Unlimited signals

### Admin Tier
- ✅ All premium features
- ✅ `/screen` - Market screening
- ✅ `/screen_auto` - Automated screening
- ✅ `/portfolio` - Paper trading
- ✅ `/whale_alerts` - Large transaction monitoring
- ✅ `/signal_history` - Signal performance
- ✅ User management commands
- ✅ System configuration

---

## 🔐 Setup Admins

Admins ditentukan melalui environment variable di `.env`:

```bash
TELEGRAM_ADMIN_CHAT_IDS=123456789,987654321
```

Atau set user role ke 'admin' di database:

```python
db.update_user_role(chat_id, 'admin')
```

---

## 💰 Subscription Management

### Upgrade User to Premium
```bash
/set_tier 123456789 premium 30 50.00 "Monthly subscription"
```
This will:
- Set tier to 'premium'
- Set expiration to 30 days from now
- Record $50.00 payment in history
- Add note "Monthly subscription"

### Grant Specific Feature (Alternative to Full Upgrade)
```bash
/grant_feature 123456789 screen 7
```
This will:
- Grant 'screen' feature for 7 days
- User can use screening without full premium upgrade

---

## 📊 Configuration Limits

Edit `config/trading_config.json`:

```json
{
  "subscriptions": {
    "free_daily_signals_limit": 5,
    "free_max_alerts": 3,
    "free_max_subscriptions": 5,
    "premium_daily_signals_limit": -1,  // -1 = unlimited
    "premium_max_alerts": 50,
    "premium_max_subscriptions": 100,
    "premium_trial_days": 7
  }
}
```

---

## 🎯 Next Steps

### 1. Apply Permissions to Existing Commands
Add `@require_feature()` decorators to commands in:
- `tg_bot/handlers/trading.py` - plan, analyze, ta commands
- `tg_bot/handlers/screening.py` - screen, screen_auto commands
- `tg_bot/handlers/portfolio.py` - portfolio commands
- `tg_bot/handlers/basic.py` - subscribe, setalert commands

### 2. Update Help Command
Modify help command to show available features based on user tier.

### 3. Add Payment Integration (Optional)
Integrate payment gateway for automatic premium upgrades.

### 4. Create Subscription Plans
Define pricing tiers and payment methods.

---

## 📝 Example: Updating a Command

Before:
```python
async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementation
    pass
```

After:
```python
from tg_bot.permissions import require_feature

@require_feature('plan')
async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementation
    pass
```

The decorator will:
1. Check user tier
2. Verify feature access
3. Return friendly error message if not authorized
4. Execute command if authorized

---

## 🧪 Testing

### Test as Free User:
```bash
# Try to access premium feature
/plan BTCUSDT
# Should get: "❌ Access Denied - Upgrade to Premium"
```

### Test as Premium User:
```bash
# First upgrade
/set_tier YOUR_CHAT_ID premium 30

# Try premium feature
/plan BTCUSDT
# Should work
```

### Test as Admin:
```bash
# Set yourself as admin in .env or
/promote YOUR_CHAT_ID

# Try admin feature
/screen
# Should work
```

---

## 🔍 Troubleshooting

### User can't access feature after upgrade
- Check if user's tier is updated: `/users`
- Check feature configuration in `config.FEATURE_ACCESS`
- Verify subscription_expires_at is not in the past

### Permission check always fails
- Make sure user exists in database
- Check if user is enabled (not banned)
- Verify feature name in decorator matches config

### Admin commands not working
- Verify TELEGRAM_ADMIN_CHAT_IDS in .env
- Check user role in database
- Make sure @require_admin decorator is applied

---

## 📚 Summary

Sistem ini sudah siap untuk commercial use dengan:

1. ✅ **3-Tier System**: Free, Premium, Admin
2. ✅ **Feature-Based Access Control**: Granular permission per feature
3. ✅ **User Management**: Ban/unban, promote/demote, tier management
4. ✅ **Subscription Tracking**: History, expiration, payments
5. ✅ **Flexible Permission System**: Decorators for easy implementation
6. ✅ **Admin Tools**: Complete set of management commands

Anda sekarang bisa:
- Mengatur fitur yang tersedia per tier
- Mengelola subscription dan payment
- Memberikan atau mencabut akses fitur
- Memantau statistik dan history

Untuk mengaktifkan, tinggal apply decorators ke existing commands! 🚀
