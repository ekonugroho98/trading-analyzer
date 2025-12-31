#!/usr/bin/env python3
"""
SYSTEM INITIALIZATION SCRIPT
Membuat folder structure dan file konfigurasi otomatis
"""

import os
import json
import sys
from pathlib import Path
import shutil
from datetime import datetime

class SystemInitializer:
    """Initialize trading system directory structure"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.config = {}
        
    def create_directory_structure(self):
        """Create all required directories"""
        directories = [
            # Data directories
            "data",
            "data/binance",
            "data/bybit",
            "data/analysis",
            "data/reports",
            "data/trading_plans",
            "data/backups",
            "data/cache",
            "data/cache/binance",
            "data/cache/bybit",
            
            # Log directories
            "logs",
            "logs/trading_plans",
            "logs/data_collection",
            "logs/errors",
            "logs/performance",
            
            # Config directories
            "configs",
            
            # Temporary directories
            "tmp",
            "tmp/uploads",
            "tmp/exports",
            
            # Output directories
            "output",
            "output/charts",
            "output/reports",
            "output/backtests",
            
            # Script directories
            "scripts",
            "scripts/utils",
            "scripts/backup",
            
            # Documentation
            "docs",
            "docs/api",
            "docs/guides",
            
            # Tests
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/data"
        ]
        
        print("📁 Creating directory structure...")
        
        for directory in directories:
            dir_path = self.base_dir / directory
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ Created: {directory}")
                
                # Add .gitkeep file to empty directories
                gitkeep_file = dir_path / ".gitkeep"
                if not list(dir_path.iterdir()):  # If directory is empty
                    gitkeep_file.touch()
                    
            except Exception as e:
                print(f"  ✗ Failed to create {directory}: {e}")
        
        print(f"✅ Directory structure created in: {self.base_dir}")
    
    def create_config_files(self):
        """Create configuration files"""
        print("\n⚙️ Creating configuration files...")
        
        # 1. Main trading config
        trading_config = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "trading": {
                "default_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
                "risk_per_trade": 0.02,
                "max_open_trades": 5
            },
            "analysis": {
                "timeframes": ["1h", "4h", "1d"],
                "confidence_threshold": 0.65
            }
        }
        
        config_path = self.base_dir / "configs" / "trading_config.json"
        with open(config_path, 'w') as f:
            json.dump(trading_config, f, indent=2)
        print(f"  ✓ Created: configs/trading_config.json")
        
        # 2. .env template
        env_template = """# API Keys (Required)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_here
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_SECRET_KEY=your_bybit_secret_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_trading
DB_USER=postgres
DB_PASS=password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASS=

# Trading Configuration
RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.05
DEFAULT_TIMEFRAME=4h

# Alert Configuration
ENABLE_SLACK=false
ENABLE_TELEGRAM=false
ENABLE_EMAIL=false
CRITICAL_PRICE_CHANGE=0.05

# DeepSeek Configuration
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4000
DEEPSEEK_TEMPERATURE=0.7

# Logging Configuration
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_MAX_SIZE_MB=10

# Scheduler Configuration
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=UTC

# Development Settings
DEBUG=false
TEST_MODE=false
"""
        
        env_path = self.base_dir / ".env.template"
        with open(env_path, 'w') as f:
            f.write(env_template)
        print(f"  ✓ Created: .env.template")
        
        # 3. requirements.txt
        requirements = """# Core Dependencies
requests>=2.31.0
pandas>=2.0.0
numpy>=1.24.0
python-dateutil>=2.8.2
websocket-client>=1.6.0
ccxt>=4.0.0

# WebSocket & Async
websockets>=12.0
aiohttp>=3.9.0
asyncio>=3.4.3

# Scheduling
schedule>=1.2.0
APScheduler>=3.10.0

# Data Analysis
ta>=0.10.0
scipy>=1.11.0

# Utilities
python-dotenv>=1.0.0
colorlog>=6.7.0
tqdm>=4.65.0

# Development
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
"""
        
        req_path = self.base_dir / "requirements.txt"
        with open(req_path, 'w') as f:
            f.write(requirements)
        print(f"  ✓ Created: requirements.txt")
        
