"""
Configuration management for crypto trading analyzer.
Handles loading and validation of configuration settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============ TRADING CONFIG ============
@dataclass
class TradingConfig:
    """Trading configuration loaded from JSON"""
    
    @staticmethod
    def load_from_json(filepath: Path) -> Dict:
        """Load trading config from JSON file"""
        if not filepath.exists():
            logger.warning(f"Trading config not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Loaded trading config from {filepath}")
            return config
        except Exception as e:
            logger.error(f"Failed to load trading config: {e}")
            return {}


# ============ CONFIG CLASS ============
class Config:
    """Configuration manager for the application."""
    
    # Base directories
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / "config"
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    
    def __init__(self):
        """Initialize configuration"""
        self._trading_config = None
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        # Load trading config from JSON
        self._trading_config = self.load_trading_config()
        
        # Set up TRADING namespace
        trading_data = self._trading_config.get("trading", {})
        self.TRADING = type('TradingNamespace', (), {
            'default_symbols': trading_data.get("default_symbols", ["BTCUSDT", "ETHUSDT"]),
            'high_priority_symbols': trading_data.get("high_priority_symbols", ["BTCUSDT", "ETHUSDT"]),
            'timeframes': trading_data.get("timeframes", {}),
            'risk_management': trading_data.get("risk_management", {}),
        })()
        
        # Set up ALERTS namespace
        alerts_data = self._trading_config.get("alerts", {})
        self.ALERTS = type('AlertsNamespace', (), {
            'enable_slack': alerts_data.get("enable_slack", False),
            'enable_telegram': alerts_data.get("enable_telegram", False),
            'enable_email': alerts_data.get("enable_email", False),
        })()

        # Set up TELEGRAM namespace
        self.TELEGRAM = type('TelegramNamespace', (), {
            'bot_token': os.getenv("TELEGRAM_BOT_TOKEN", ""),
            'admin_chat_ids': [
                int(cid) for cid in os.getenv("TELEGRAM_ADMIN_CHAT_IDS", "").split(",")
                if cid.strip()
            ],
            'max_requests_per_minute': int(os.getenv("TELEGRAM_MAX_REQUESTS_PER_MINUTE", "20")),
            'enable_notifications': os.getenv("TELEGRAM_ENABLE_NOTIFICATIONS", "true").lower() == "true",
            'daily_plan_time': os.getenv("TELEGRAM_DAILY_PLAN_TIME", "09:00"),
            'weekly_report_day': os.getenv("TELEGRAM_WEEKLY_REPORT_DAY", "sunday"),
            'max_subscriptions_per_user': int(os.getenv("TELEGRAM_MAX_SUBSCRIPTIONS", "10")),
            'signal_check_interval_minutes': int(os.getenv("TELEGRAM_SIGNAL_CHECK_INTERVAL", "30")),
        })()

        # Set up DEEPSEEK namespace
        self.DEEPSEEK = type('DeepSeekNamespace', (), {
            'api_key': os.getenv("DEEPSEEK_API_KEY", ""),
            'base_url': "https://api.deepseek.com/v1",
            'model': "deepseek-chat",
            'max_tokens': 4000,
            'temperature': 0.7,
            'timeout': 30,
        })()
    
    @classmethod
    def load_trading_config(cls) -> Dict:
        """Load trading configuration from JSON"""
        config_file = cls.CONFIG_DIR / "trading_config.json"
        return TradingConfig.load_from_json(config_file)
    
    @property
    def TRADING_CONFIG(self) -> Dict:
        """Get trading configuration dictionary"""
        if self._trading_config is None:
            self._trading_config = self.load_trading_config()
        return self._trading_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value from trading config.
        
        Args:
            key: Configuration key (supports dot notation like "trading.timeframes.daily_analysis")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.TRADING_CONFIG
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def validate(self) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if configuration is valid, False otherwise
        """
        required_dirs = [
            self.DATA_DIR,
            self.LOGS_DIR,
            self.CONFIG_DIR
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                logger.warning(f"Directory does not exist: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)

        return True

    def get_exchange_config(self, exchange: str, market_type: str = "spot") -> Dict:
        """
        Get exchange configuration.

        Args:
            exchange: Exchange name (binance, bybit, etc.)
            market_type: Market type - "spot", "futures", or "delivery" (default: "spot")
                        For Binance: "spot" uses api.binance.com, "futures" uses fapi.binance.com (USD-M),
                                     "delivery" uses dapi.binance.com (Coin-M)

        Returns:
            Exchange configuration dictionary
        """
        exchanges = {
            "binance": {
                "spot": {
                    "name": "Binance Spot",
                    "base_url": "https://api.binance.com",
                    "ws_url": "wss://stream.binance.com:9443/ws",
                    "api_key": os.getenv("BINANCE_API_KEY", ""),
                    "api_secret": os.getenv("BINANCE_API_SECRET", ""),
                },
                "futures": {
                    "name": "Binance USD-M Futures",
                    "base_url": "https://fapi.binance.com",
                    "ws_url": "wss://fstream.binance.com/ws",
                    "api_key": os.getenv("BINANCE_FUTURES_API_KEY", os.getenv("BINANCE_API_KEY", "")),
                    "api_secret": os.getenv("BINANCE_FUTURES_API_SECRET", os.getenv("BINANCE_API_SECRET", "")),
                },
                "delivery": {
                    "name": "Binance Coin-M Futures",
                    "base_url": "https://dapi.binance.com",
                    "ws_url": "wss://dstream.binance.com/ws",
                    "api_key": os.getenv("BINANCE_DELIVERY_API_KEY", os.getenv("BINANCE_API_KEY", "")),
                    "api_secret": os.getenv("BINANCE_DELIVERY_API_SECRET", os.getenv("BINANCE_API_SECRET", "")),
                }
            },
            "bybit": {
                "spot": {
                    "name": "Bybit Spot",
                    "base_url": "https://api.bybit.com",
                    "ws_url": "wss://stream.bybit.com/v5/public/spot",
                    "api_key": os.getenv("BYBIT_API_KEY", ""),
                    "api_secret": os.getenv("BYBIT_API_SECRET", ""),
                },
                "futures": {
                    "name": "Bybit Linear Futures",
                    "base_url": "https://api.bybit.com",
                    "ws_url": "wss://stream.bybit.com/v5/public/linear",
                    "api_key": os.getenv("BYBIT_FUTURES_API_KEY", os.getenv("BYBIT_API_KEY", "")),
                    "api_secret": os.getenv("BYBIT_FUTURES_API_SECRET", os.getenv("BYBIT_API_SECRET", "")),
                },
                "inverse": {
                    "name": "Bybit Inverse Futures",
                    "base_url": "https://api.bybit.com",
                    "ws_url": "wss://stream.bybit.com/v5/public/inverse",
                    "api_key": os.getenv("BYBIT_INVERSE_API_KEY", os.getenv("BYBIT_API_KEY", "")),
                    "api_secret": os.getenv("BYBIT_INVERSE_API_SECRET", os.getenv("BYBIT_API_SECRET", "")),
                }
            },
            "okex": {
                "spot": {
                    "name": "OKEx Spot",
                    "base_url": "https://www.okex.com",
                    "ws_url": "wss://ws.okex.com:8443/ws/v5/public",
                    "api_key": os.getenv("OKEX_API_KEY", ""),
                    "api_secret": os.getenv("OKEX_API_SECRET", ""),
                },
                "futures": {
                    "name": "OKEx Futures",
                    "base_url": "https://www.okex.com",
                    "ws_url": "wss://ws.okex.com:8443/ws/v5/public",
                    "api_key": os.getenv("OKEX_FUTURES_API_KEY", os.getenv("OKEX_API_KEY", "")),
                    "api_secret": os.getenv("OKEX_FUTURES_API_SECRET", os.getenv("OKEX_API_SECRET", "")),
                }
            }
        }

        exchange_config = exchanges.get(exchange.lower(), {})
        
        # Return specific market type or default to spot
        if isinstance(exchange_config, dict) and market_type in exchange_config:
            return exchange_config[market_type]
        elif isinstance(exchange_config, dict) and "spot" in exchange_config:
            # Fallback to spot if market_type not found
            return exchange_config.get("spot", {})
        else:
            # Legacy format (old config without market types)
            return exchange_config if isinstance(exchange_config, dict) and "base_url" in exchange_config else {}


# ============ ENUMS ============
class Exchange:
    """Exchange constants"""
    BINANCE = "binance"
    BYBIT = "bybit"
    OKEX = "okex"

class MarketType:
    """Market type for trading"""
    AUTO = "auto"    # Auto-detect futures first, then spot
    SPOT = "spot"    # Spot market only
    FUTURES = "futures"  # Futures market only

class Timeframe:
    """Timeframe constants"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"


# ============ GLOBAL INSTANCE ============
# Create global config instance
config = Config()

# Validate on import
config.validate()

