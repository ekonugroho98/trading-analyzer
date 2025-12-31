#!/bin/bash

# ============================================
# Crypto Trading Analyzer - Deployment Script
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Crypto Trading Analyzer Deployment ===${NC}\n"

# Configuration
USERNAME=$(whoami)
APP_DIR="/opt/crypto-trading-analyzer"
DB_DIR="/var/lib/crypto-trading-analyzer"
SERVICE_NAME="crypto-trading-bot"

# ============================================
# Step 1: System Preparation
# ============================================
echo -e "${YELLOW}[Step 1/9] System Preparation${NC}"
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git sqlite3 supervisor

echo -e "${GREEN}✓ System preparation complete${NC}\n"

# ============================================
# Step 2: Create Directories
# ============================================
echo -e "${YELLOW}[Step 2/9] Creating Directories${NC}"
echo "Creating application directory: $APP_DIR"
echo "Creating database directory: $DB_DIR"

sudo mkdir -p $APP_DIR $DB_DIR
sudo chown $USERNAME:$USERNAME $APP_DIR $DB_DIR

echo -e "${GREEN}✓ Directories created${NC}\n"

# ============================================
# Step 3: Clone Repository
# ============================================
echo -e "${YELLOW}[Step 3/9] Setting up Repository${NC}"

if [ ! -d "$APP_DIR/.git" ]; then
    echo "Cloning repository from GitHub..."
    git clone https://github.com/ekonugroho98/trading-analyzer.git $APP_DIR
else
    echo "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull origin main
fi

echo -e "${GREEN}✓ Repository setup complete${NC}\n"

# ============================================
# Step 4: Create Virtual Environment
# ============================================
echo -e "${YELLOW}[Step 4/9] Creating Python Virtual Environment${NC}"

cd $APP_DIR

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo -e "${GREEN}✓ Virtual environment ready${NC}\n"

# ============================================
# Step 5: Install Dependencies
# ============================================
echo -e "${YELLOW}[Step 5/9] Installing Python Dependencies${NC}"

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}\n"
else
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    exit 1
fi

# ============================================
# Step 6: Initialize Database
# ============================================
echo -e "${YELLOW}[Step 6/9] Initializing Database${NC}"

echo "Creating database tables..."
python3 << 'EOF'
import sys
try:
    from tg_bot.database import Database
    db = Database()
    db.init_db()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database initialized${NC}\n"
else
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi

# ============================================
# Step 7: Configure Environment
# ============================================
echo -e "${YELLOW}[Step 7/9] Environment Configuration${NC}"

if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env

        echo -e "${RED}===========================================${NC}"
        echo -e "${RED}IMPORTANT: Please configure your .env file!${NC}"
        echo -e "${RED}===========================================${NC}"
        echo ""
        echo "Required configuration:"
        echo "  - TELEGRAM_BOT_TOKEN=your_bot_token_here"
        echo "  - BINANCE_API_KEY=your_binance_api_key"
        echo "  - BINANCE_API_SECRET=your_binance_api_secret"
        echo "  - DEEPSEEK_API_KEY=your_deepseek_api_key"
        echo ""
        read -p "Press Enter to open .env file with nano editor..."
        nano .env
    else
        echo -e "${YELLOW}Warning: .env.example not found, creating empty .env${NC}"
        touch .env
    fi
else
    echo ".env file already exists, skipping configuration"
fi

echo -e "${GREEN}✓ Environment configured${NC}\n"

# ============================================
# Step 8: Create Systemd Service
# ============================================
echo -e "${YELLOW}[Step 8/9] Creating Systemd Service${NC}"

echo "Creating service file: /etc/systemd/system/${SERVICE_NAME}.service"

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
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

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling service to start on boot..."
sudo systemctl enable ${SERVICE_NAME}.service

echo -e "${GREEN}✓ Systemd service created${NC}\n"

# ============================================
# Step 9: Start Service
# ============================================
echo -e "${YELLOW}[Step 9/9] Starting Service${NC}"

echo "Starting ${SERVICE_NAME} service..."
sudo systemctl start ${SERVICE_NAME}.service

echo "Waiting for service to initialize..."
sleep 3

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}\n"

# Show service status
echo "Service Status:"
sudo systemctl status ${SERVICE_NAME}.service --no-pager || true

echo ""
echo -e "${GREEN}=== Useful Commands ===${NC}"
echo "View logs:           sudo journalctl -u ${SERVICE_NAME}.service -f"
echo "Restart service:     sudo systemctl restart ${SERVICE_NAME}.service"
echo "Stop service:        sudo systemctl stop ${SERVICE_NAME}.service"
echo "Check status:        sudo systemctl status ${SERVICE_NAME}.service"
echo ""
echo -e "${YELLOW}=== Next Steps ===${NC}"
echo "1. Test your bot in Telegram with /start command"
echo "2. Configure .env file if not done yet"
echo "3. Set up database backups (see DEPLOYMENT.md)"
echo "4. Configure log rotation (see DEPLOYMENT.md)"
echo ""
echo -e "${GREEN}Deployment successful! Happy trading! 🚀${NC}"
