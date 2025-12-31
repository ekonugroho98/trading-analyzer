# Deployment Guide - Crypto Trading Analyzer

Server deployment guide for production environment.

## Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Python 3.8+
- Git
- 2GB RAM minimum
- 20GB disk space

---

## Step 1: System Preparation

### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Required Packages

```bash
sudo apt install -y python3 python3-pip python3-venv git sqlite3 supervisor nginx htop
```

---

## Step 2: Create Deployment Directory

```bash
# Create application directory
sudo mkdir -p /opt/crypto-trading-analyzer
sudo chown $USER:$USER /opt/crypto-trading-analyzer

# Navigate to directory
cd /opt/crypto-trading-analyzer
```

---

## Step 3: Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/ekonugroho98/trading-analyzer.git .

# Or if deploying from local:
# tar -czf crypto-trading-analyzer.tar.gz .
# scp crypto-trading-analyzer.tar.gz user@server:/opt/
# tar -xzf crypto-trading-analyzer.tar.gz -C /opt/crypto-trading-analyzer
```

---

## Step 4: Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

---

## Step 5: Install Dependencies

```bash
# Install all Python dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

---

## Step 6: Create Database

### 6.1 Create Database Directory

```bash
# Create database directory
sudo mkdir -p /var/lib/crypto-trading-analyzer
sudo chown $USER:$USER /var/lib/crypto-trading-analyzer
```

### 6.2 Initialize Database

```bash
# From application directory
cd /opt/crypto-trading-analyzer

# Run database initialization
python3 -c "
from tg_bot.database import Database
db = Database()
db.init_db()
print('Database initialized successfully!')
"
```

### 6.3 Verify Database

```bash
# Check database file
ls -lh /var/lib/crypto-trading-analyzer/trading_bot.db

# Or if using local database:
ls -lh data/trading_bot.db
```

---

## Step 7: Configure Environment Variables

### 7.1 Create .env File

```bash
cd /opt/crypto-trading-analyzer
cp .env.example .env
nano .env
```

### 7.2 Edit Configuration

```bash
# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# DeepSeek AI Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Optional: Admin chat ID for notifications
TELEGRAM_ADMIN_CHAT_ID=your_admin_chat_id

# Signal check interval (minutes)
SIGNAL_CHECK_INTERVAL=30
```

### 7.3 Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token

### 7.4 Get Chat ID

1. Open Telegram and search for your bot
2. Send any message to the bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your `chat_id` in the response

---

## Step 8: Test Database Connection

```bash
# Activate virtual environment
source /opt/crypto-trading-analyzer/venv/bin/activate

# Test database
python3 -c "
from tg_bot.database import Database
from config import config

db = Database()

# Test connection
result = db.get_user_subscriptions(123456789)
print(f'Database connection successful!')

# Test portfolio tables
from datetime import datetime
print('Testing portfolio tables...')
db.add_portfolio_position(
    chat_id=123456789,
    symbol='BTCUSDT',
    position_type='LONG',
    entry_price=50000.0,
    quantity=0.1
)
print('Portfolio test successful!')
"
```

---

## Step 9: Create Systemd Service

### 9.1 Create Service File

```bash
sudo nano /etc/systemd/system/crypto-trading-bot.service
```

### 9.2 Add Service Configuration

```ini
[Unit]
Description=Crypto Trading Analyzer Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/crypto-trading-analyzer
Environment="PATH=/opt/crypto-trading-analyzer/venv/bin"
ExecStart=/opt/crypto-trading-analyzer/venv/bin/python /opt/crypto-trading-analyzer/run_telegram_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Replace `YOUR_USERNAME` with your actual username.**

### 9.3 Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable crypto-trading-bot.service

# Start service
sudo systemctl start crypto-trading-bot.service

# Check status
sudo systemctl status crypto-trading-bot.service

# View logs
sudo journalctl -u crypto-trading-bot.service -f
```

---

## Step 10: Create Log Rotation

### 10.1 Create Logrotate Configuration

```bash
sudo nano /etc/logrotate.d/crypto-trading-bot
```

### 10.2 Add Logrotate Rules

```
/opt/crypto-trading-analyzer/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 YOUR_USERNAME YOUR_USERNAME
    postrotate
        systemctl reload crypto-trading-bot.service > /dev/null 2>&1 || true
    endscript
}
```

**Replace `YOUR_USERNAME` with your actual username.**

---

## Step 11: Setup Firewall (Optional)

```bash
# Enable UFW
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Check status
sudo ufw status
```

---

## Step 12: Monitoring and Maintenance

### 12.1 Check Service Status

```bash
# Check if service is running
sudo systemctl status crypto-trading-bot.service

# View real-time logs
sudo journalctl -u crypto-trading-bot.service -f

# View last 100 lines
sudo journalctl -u crypto-trading-bot.service -n 100
```

### 12.2 Restart Service

```bash
# Restart service
sudo systemctl restart crypto-trading-bot.service

# Stop service
sudo systemctl stop crypto-trading-bot.service

# Start service
sudo systemctl start crypto-trading-bot.service
```

### 12.3 Update Application

```bash
# Navigate to application directory
cd /opt/crypto-trading-analyzer

# Pull latest changes
git pull origin main

# Install new dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart crypto-trading-bot.service
```

### 12.4 Backup Database

```bash
# Create backup script
cat > /home/YOUR_USERNAME/backup-db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/YOUR_USERNAME/backups"
mkdir -p $BACKUP_DIR
cp /var/lib/crypto-trading-analyzer/trading_bot.db $BACKUP_DIR/trading_bot_$DATE.db
# Keep only last 7 days
find $BACKUP_DIR -name "trading_bot_*.db" -mtime +7 -delete
echo "Backup completed: trading_bot_$DATE.db"
EOF

# Make script executable
chmod +x /home/YOUR_USERNAME/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /home/YOUR_USERNAME/backup-db.sh
```

**Replace `YOUR_USERNAME` with your actual username.**

---

## Step 13: Troubleshooting

### Issue 1: Service Won't Start

```bash
# Check journal logs
sudo journalctl -u crypto-trading-bot.service -n 50

# Check if port is already in use
sudo netstat -tulpn | grep python

# Kill existing processes
sudo pkill -f "python.*run_telegram_bot.py"

# Restart service
sudo systemctl restart crypto-trading-bot.service
```

### Issue 2: Database Errors

```bash
# Check database file permissions
ls -lh /var/lib/crypto-trading-analyzer/trading_bot.db

# Fix permissions
sudo chown $USER:$USER /var/lib/crypto-trading-analyzer/trading_bot.db
sudo chmod 644 /var/lib/crypto-trading-analyzer/trading_bot.db

# Verify database integrity
sqlite3 /var/lib/crypto-trading-analyzer/trading_bot.db "PRAGMA integrity_check;"
```

### Issue 3: Bot Not Responding

```bash
# Check service status
sudo systemctl status crypto-trading-bot.service

# View logs
sudo journalctl -u crypto-trading-bot.service -f

# Verify bot token
grep TELEGRAM_BOT_TOKEN /opt/crypto-trading-analyzer/.env

# Test bot API
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

### Issue 4: Python Dependencies

```bash
# Reinstall all dependencies
source /opt/crypto-trading-analyzer/venv/bin/activate
pip install --upgrade -r /opt/crypto-trading-analyzer/requirements.txt

# Check for conflicts
pip check
```

---

## Quick Deploy Script

Save this as `deploy.sh` and run it:

```bash
#!/bin/bash

set -e

echo "=== Crypto Trading Analyzer Deployment ==="

# Configuration
USERNAME=$(whoami)
APP_DIR="/opt/crypto-trading-analyzer"
DB_DIR="/var/lib/crypto-trading-analyzer"

# Step 1: Create directories
echo "Creating directories..."
sudo mkdir -p $APP_DIR $DB_DIR
sudo chown $USERNAME:$USERNAME $APP_DIR $DB_DIR

# Step 2: Clone repository (if not exists)
if [ ! -d "$APP_DIR/.git" ]; then
    echo "Cloning repository..."
    git clone https://github.com/ekonugroho98/trading-analyzer.git $APP_DIR
else
    echo "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull origin main
fi

# Step 3: Create virtual environment
echo "Creating virtual environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate

# Step 4: Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Initialize database
echo "Initializing database..."
python3 -c "from tg_bot.database import Database; db = Database(); db.init_db()"

# Step 6: Configure environment
echo "Please configure .env file:"
if [ ! -f "$APP_DIR/.env" ]; then
    cp $APP_DIR/.env.example $APP_DIR/.env
    nano $APP_DIR/.env
else
    echo ".env file already exists"
fi

# Step 7: Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/crypto-trading-bot.service > /dev/null <<EOF
[Unit]
Description=Crypto Trading Analyzer Bot
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/run_telegram_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Enable and start service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable crypto-trading-bot.service
sudo systemctl start crypto-trading-bot.service

# Step 9: Show status
echo "Checking service status..."
sleep 3
sudo systemctl status crypto-trading-bot.service --no-pager

echo "=== Deployment Complete ===="
echo "Check logs: sudo journalctl -u crypto-trading-bot.service -f"
echo "Restart service: sudo systemctl restart crypto-trading-bot.service"
```

Make it executable and run:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Post-Deployment Checklist

- [ ] Bot token configured correctly
- [ ] Database initialized successfully
- [ ] Service is running (`systemctl status`)
- [ ] Bot responds to `/start` command in Telegram
- [ ] `/price` command works
- [ ] `/plan` command generates trading plans
- [ ] Portfolio commands work
- [ ] Log rotation configured
- [ ] Database backup scheduled
- [ ] Firewall configured (if needed)
- [ ] Monitoring set up

---

## Useful Commands Reference

```bash
# Service management
sudo systemctl start crypto-trading-bot.service
sudo systemctl stop crypto-trading-bot.service
sudo systemctl restart crypto-trading-bot.service
sudo systemctl status crypto-trading-bot.service

# Logs
sudo journalctl -u crypto-trading-bot.service -f      # Follow logs
sudo journalctl -u crypto-trading-bot.service -n 100   # Last 100 lines
sudo journalctl -u crypto-trading-bot.service --since "1 hour ago"  # Last hour

# Database
sqlite3 /var/lib/crypto-trading-analyzer/trading_bot.db  # Open database
.tables                                                    # List tables
.schema portfolio_positions                              # Show schema

# Manual testing
cd /opt/crypto-trading-analyzer
source venv/bin/activate
python run_telegram_bot.py                                # Run manually
```

---

## Security Recommendations

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Use strong API keys** - Rotate periodically
3. **Limit bot permissions** - Only necessary permissions
4. **Enable firewall** - Only open necessary ports
5. **Regular updates** - Keep system and dependencies updated
6. **Monitor logs** - Set up log monitoring alerts
7. **Backup regularly** - Automated daily database backups
8. **Use HTTPS** - If setting up web interface

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u crypto-trading-bot.service -n 100`
- GitHub Issues: https://github.com/ekonugroho98/trading-analyzer/issues
- Documentation: Check README.md

---

**Last Updated:** 2025-12-31
**Version:** 1.0.0
