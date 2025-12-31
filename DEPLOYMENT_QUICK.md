# Quick Deployment Guide

Fast-track deployment for Crypto Trading Analyzer Bot.

## 🚀 Quick Deploy (One Command)

```bash
bash <(curl -s https://raw.githubusercontent.com/ekonugroho98/trading-analyzer/main/deploy.sh)
```

## 📋 Manual Deploy Steps

### 1. System Requirements
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git sqlite3
```

### 2. Clone Repository
```bash
cd /opt
sudo mkdir crypto-trading-analyzer
sudo chown $USER:$USER crypto-trading-analyzer
cd crypto-trading-analyzer
git clone https://github.com/ekonugroho98/trading-analyzer.git .
```

### 3. Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initialize Database
```bash
python3 -c "from tg_bot.database import Database; db = Database(); db.init_db()"
```

### 5. Configure Environment
```bash
cp .env.example .env
nano .env

# Add your credentials:
TELEGRAM_BOT_TOKEN=your_token_here
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
DEEPSEEK_API_KEY=your_deepseek_key
```

### 6. Create Systemd Service
```bash
sudo nano /etc/systemd/system/crypto-trading-bot.service
```

Paste this:
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

[Install]
WantedBy=multi-user.target
```

### 7. Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-trading-bot
sudo systemctl start crypto-trading-bot
```

### 8. Check Status
```bash
sudo systemctl status crypto-trading-bot
sudo journalctl -u crypto-trading-bot -f
```

## 🔧 Useful Commands

```bash
# Service Management
sudo systemctl start crypto-trading-bot      # Start service
sudo systemctl stop crypto-trading-bot       # Stop service
sudo systemctl restart crypto-trading-bot    # Restart service
sudo systemctl status crypto-trading-bot     # Check status

# View Logs
sudo journalctl -u crypto-trading-bot -f                    # Follow logs
sudo journalctl -u crypto-trading-bot -n 100                # Last 100 lines
sudo journalctl -u crypto-trading-bot --since "1 hour ago"  # Last hour

# Update Application
cd /opt/crypto-trading-analyzer
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crypto-trading-bot

# Database Backup
chmod +x backup-db.sh
./backup-db.sh
```

## 📱 Get Bot Credentials

### Telegram Bot Token
1. Open Telegram → @BotFather
2. Send: `/newbot`
3. Follow instructions
4. Copy token

### Chat ID
1. Send message to your bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `chat_id` in response

## 🔍 Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u crypto-trading-bot -n 50

# Kill existing processes
sudo pkill -f "python.*run_telegram_bot.py"

# Restart
sudo systemctl restart crypto-trading-bot
```

### Database errors
```bash
# Check database
ls -lh /var/lib/crypto-trading-analyzer/trading_bot.db

# Fix permissions
sudo chown $USER:$USER /var/lib/crypto-trading-analyzer/trading_bot.db
```

### Bot not responding
```bash
# Verify token
grep TELEGRAM_BOT_TOKEN /opt/crypto-trading-analyzer/.env

# Test API
curl https://api.telegram.org/bot<TOKEN>/getMe
```

## 📚 Full Documentation

See `DEPLOYMENT.md` for complete deployment guide.

## 🛡️ Security Checklist

- [ ] Strong passwords/keys
- [ ] `.env` not in git
- [ ] Firewall configured
- [ ] Regular backups
- [ ] Log rotation enabled
- [ ] System updates applied

## 📞 Support

GitHub: https://github.com/ekonugroho98/trading-analyzer/issues
