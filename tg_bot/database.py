"""
Telegram Bot Database Operations
SQLite database for user management, subscriptions, and alerts
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)

class TelegramDatabase:
    """SQLite database for Telegram bot"""

    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            # Default path: data/telegram_users.db
            db_path = config.DATA_DIR / "telegram_users.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()
        logger.info(f"Telegram database initialized: {self.db_path}")

    def _init_database(self):
        """Create tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'user',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                symbol TEXT,
                timeframe TEXT DEFAULT '4h',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                UNIQUE(chat_id, symbol)
            )
        """)

        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                symbol TEXT,
                alert_type TEXT,
                target_price REAL,
                triggered BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                preference_key TEXT,
                preference_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                UNIQUE(chat_id, preference_key)
            )
        """)

        # Portfolio positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                symbol TEXT,
                position_type TEXT,
                entry_price REAL,
                current_price REAL,
                quantity REAL,
                total_value REAL,
                stop_loss REAL,
                take_profit REAL,
                notes TEXT,
                status TEXT DEFAULT 'open',
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        # Portfolio transactions table (for tracking history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                symbol TEXT,
                transaction_type TEXT,
                price REAL,
                quantity REAL,
                total_value REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_chat_id ON subscriptions(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_chat_id ON alerts(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_chat_id ON user_preferences(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_chat_id ON portfolio_positions(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON portfolio_positions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_chat_id ON portfolio_transactions(chat_id)")

        conn.commit()
        conn.close()

    # ============ USER MANAGEMENT ============
    def add_user(self, chat_id: int, username: str = None, first_name: str = None,
                 last_name: str = None, role: str = "user") -> bool:
        """Add new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO users (chat_id, username, first_name, last_name, role, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, username, first_name, last_name, role))

            conn.commit()
            conn.close()
            logger.info(f"User added/updated: {chat_id} (@{username})")
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_user(self, chat_id: int) -> Optional[Dict]:
        """Get user by chat_id"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT chat_id, username, first_name, last_name, role, enabled, created_at, last_active
                FROM users WHERE chat_id = ?
            """, (chat_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'chat_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'role': row[4],
                    'enabled': bool(row[5]),
                    'created_at': row[6],
                    'last_active': row[7]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def update_last_active(self, chat_id: int):
        """Update user last active timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE chat_id = ?
            """, (chat_id,))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating last active: {e}")

    def get_all_users(self, enabled_only: bool = True) -> List[Dict]:
        """Get all users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if enabled_only:
                cursor.execute("""
                    SELECT chat_id, username, first_name, last_name, role, enabled, created_at, last_active
                    FROM users WHERE enabled = 1
                """)
            else:
                cursor.execute("""
                    SELECT chat_id, username, first_name, last_name, role, enabled, created_at, last_active
                    FROM users
                """)

            rows = cursor.fetchall()
            conn.close()

            users = []
            for row in rows:
                users.append({
                    'chat_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'role': row[4],
                    'enabled': bool(row[5]),
                    'created_at': row[6],
                    'last_active': row[7]
                })

            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def is_admin(self, chat_id: int) -> bool:
        """Check if user is admin"""
        user = self.get_user(chat_id)
        if user and user.get('role') == 'admin':
            return True
        # Also check config admin list
        return chat_id in config.TELEGRAM.admin_chat_ids

    def enable_user(self, chat_id: int, enabled: bool = True) -> bool:
        """Enable/disable user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("UPDATE users SET enabled = ? WHERE chat_id = ?", (int(enabled), chat_id))

            conn.commit()
            conn.close()
            logger.info(f"User {chat_id} {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error enabling/disabling user: {e}")
            return False

    # ============ SUBSCRIPTIONS ============
    def add_subscription(self, chat_id: int, symbol: str, timeframe: str = "4h") -> bool:
        """Add subscription"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO subscriptions (chat_id, symbol, timeframe)
                VALUES (?, ?, ?)
            """, (chat_id, symbol.upper(), timeframe))

            conn.commit()
            conn.close()
            logger.info(f"Subscription added: {chat_id} -> {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error adding subscription: {e}")
            return False

    def remove_subscription(self, chat_id: int, symbol: str) -> bool:
        """Remove subscription"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM subscriptions WHERE chat_id = ? AND symbol = ?
            """, (chat_id, symbol.upper()))

            conn.commit()
            conn.close()
            logger.info(f"Subscription removed: {chat_id} -> {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error removing subscription: {e}")
            return False

    def get_user_subscriptions(self, chat_id: int) -> List[Dict]:
        """Get user subscriptions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, symbol, timeframe, created_at
                FROM subscriptions WHERE chat_id = ?
                ORDER BY symbol
            """, (chat_id,))

            rows = cursor.fetchall()
            conn.close()

            subscriptions = []
            for row in rows:
                subscriptions.append({
                    'id': row[0],
                    'symbol': row[1],
                    'timeframe': row[2],
                    'created_at': row[3]
                })

            return subscriptions
        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            return []

    def get_subscribers_for_symbol(self, symbol: str) -> List[int]:
        """Get all chat_ids subscribed to a symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT u.chat_id
                FROM users u
                JOIN subscriptions s ON u.chat_id = s.chat_id
                WHERE u.enabled = 1 AND s.symbol = ?
            """, (symbol.upper(),))

            rows = cursor.fetchall()
            conn.close()

            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return []

    # ============ ALERTS ============
    def add_alert(self, chat_id: int, symbol: str, alert_type: str,
                  target_price: float) -> Optional[int]:
        """Add price alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO alerts (chat_id, symbol, alert_type, target_price)
                VALUES (?, ?, ?, ?)
            """, (chat_id, symbol.upper(), alert_type, target_price))

            conn.commit()
            alert_id = cursor.lastrowid
            conn.close()

            logger.info(f"Alert added: {alert_id} - {symbol} {alert_type} {target_price}")
            return alert_id
        except Exception as e:
            logger.error(f"Error adding alert: {e}")
            return None

    def get_user_alerts(self, chat_id: int, active_only: bool = True) -> List[Dict]:
        """Get user alerts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if active_only:
                cursor.execute("""
                    SELECT id, symbol, alert_type, target_price, created_at
                    FROM alerts WHERE chat_id = ? AND triggered = 0
                    ORDER BY created_at DESC
                """, (chat_id,))
            else:
                cursor.execute("""
                    SELECT id, symbol, alert_type, target_price, triggered, created_at
                    FROM alerts WHERE chat_id = ?
                    ORDER BY created_at DESC
                """, (chat_id,))

            rows = cursor.fetchall()
            conn.close()

            alerts = []
            for row in rows:
                alerts.append({
                    'id': row[0],
                    'symbol': row[1],
                    'alert_type': row[2],
                    'target_price': row[3],
                    'created_at': row[4] if active_only else row[5]
                })

            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    def trigger_alert(self, alert_id: int) -> bool:
        """Mark alert as triggered"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("UPDATE alerts SET triggered = 1 WHERE id = ?", (alert_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
            return False

    def delete_alert(self, alert_id: int, chat_id: int = None) -> bool:
        """Delete alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if chat_id:
                cursor.execute("DELETE FROM alerts WHERE id = ? AND chat_id = ?", (alert_id, chat_id))
            else:
                cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

            conn.commit()
            conn.close()
            logger.info(f"Alert deleted: {alert_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return False

    def clear_user_alerts(self, chat_id: int) -> bool:
        """Clear all user alerts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM alerts WHERE chat_id = ?", (chat_id,))

            conn.commit()
            conn.close()
            logger.info(f"All alerts cleared for user: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing alerts: {e}")
            return False

    # ============ USER PREFERENCES ============
    def get_user_preference(self, chat_id: int, key: str, default: Any = None) -> Any:
        """Get user preference value"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT preference_value
                FROM user_preferences
                WHERE chat_id = ? AND preference_key = ?
            """, (chat_id, key))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]
            return default
        except Exception as e:
            logger.error(f"Error getting user preference: {e}")
            return default

    def set_user_preference(self, chat_id: int, key: str, value: Any) -> bool:
        """Set user preference value"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (chat_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, key, str(value)))

            conn.commit()
            conn.close()
            logger.info(f"User preference set: {chat_id} -> {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting user preference: {e}")
            return False

    # ============ PORTFOLIO POSITIONS ============
    def add_position(self, chat_id: int, symbol: str, position_type: str,
                     entry_price: float, quantity: float, stop_loss: float = None,
                     take_profit: float = None, notes: str = None) -> Optional[int]:
        """Add new position to portfolio"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            total_value = entry_price * quantity

            cursor.execute("""
                INSERT INTO portfolio_positions
                (chat_id, symbol, position_type, entry_price, current_price, quantity,
                 total_value, stop_loss, take_profit, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """, (chat_id, symbol.upper(), position_type.upper(), entry_price,
                  entry_price, quantity, total_value, stop_loss, take_profit, notes))

            conn.commit()
            position_id = cursor.lastrowid
            conn.close()

            logger.info(f"Position added: {position_id} - {symbol} {position_type} @{entry_price}")
            return position_id
        except Exception as e:
            logger.error(f"Error adding position: {e}")
            return None

    def get_user_positions(self, chat_id: int, status: str = 'open') -> List[Dict]:
        """Get user positions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT id, symbol, position_type, entry_price, current_price,
                           quantity, total_value, stop_loss, take_profit, notes,
                           opened_at, closed_at
                    FROM portfolio_positions
                    WHERE chat_id = ? AND status = ?
                    ORDER BY opened_at DESC
                """, (chat_id, status))
            else:
                cursor.execute("""
                    SELECT id, symbol, position_type, entry_price, current_price,
                           quantity, total_value, stop_loss, take_profit, notes,
                           opened_at, closed_at
                    FROM portfolio_positions
                    WHERE chat_id = ?
                    ORDER BY opened_at DESC
                """, (chat_id,))

            rows = cursor.fetchall()
            conn.close()

            positions = []
            for row in rows:
                positions.append({
                    'id': row[0],
                    'symbol': row[1],
                    'position_type': row[2],
                    'entry_price': row[3],
                    'current_price': row[4],
                    'quantity': row[5],
                    'total_value': row[6],
                    'stop_loss': row[7],
                    'take_profit': row[8],
                    'notes': row[9],
                    'opened_at': row[10],
                    'closed_at': row[11]
                })

            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_position(self, position_id: int, chat_id: int = None) -> Optional[Dict]:
        """Get specific position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if chat_id:
                cursor.execute("""
                    SELECT id, symbol, position_type, entry_price, current_price,
                           quantity, total_value, stop_loss, take_profit, notes,
                           opened_at, closed_at, status
                    FROM portfolio_positions
                    WHERE id = ? AND chat_id = ?
                """, (position_id, chat_id))
            else:
                cursor.execute("""
                    SELECT id, symbol, position_type, entry_price, current_price,
                           quantity, total_value, stop_loss, take_profit, notes,
                           opened_at, closed_at, status
                    FROM portfolio_positions
                    WHERE id = ?
                """, (position_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'id': row[0],
                    'symbol': row[1],
                    'position_type': row[2],
                    'entry_price': row[3],
                    'current_price': row[4],
                    'quantity': row[5],
                    'total_value': row[6],
                    'stop_loss': row[7],
                    'take_profit': row[8],
                    'notes': row[9],
                    'opened_at': row[10],
                    'closed_at': row[11],
                    'status': row[12]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    def update_position_price(self, position_id: int, current_price: float) -> bool:
        """Update current price of position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get quantity first
            cursor.execute("SELECT quantity FROM portfolio_positions WHERE id = ?", (position_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            quantity = row[0]
            total_value = current_price * quantity

            cursor.execute("""
                UPDATE portfolio_positions
                SET current_price = ?, total_value = ?
                WHERE id = ?
            """, (current_price, total_value, position_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating position price: {e}")
            return False

    def close_position(self, position_id: int, close_price: float = None,
                      chat_id: int = None) -> bool:
        """Close position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if close_price:
                # Update current price and calculate final P/L
                cursor.execute("""
                    SELECT quantity FROM portfolio_positions
                    WHERE id = ?
                """, (position_id,))
                row = cursor.fetchone()
                if row:
                    quantity = row[0]
                    total_value = close_price * quantity
                    cursor.execute("""
                        UPDATE portfolio_positions
                        SET current_price = ?, total_value = ?, status = 'closed',
                            closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (close_price, total_value, position_id))
                else:
                    cursor.execute("""
                        UPDATE portfolio_positions
                        SET status = 'closed', closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (position_id,))
            else:
                cursor.execute("""
                    UPDATE portfolio_positions
                    SET status = 'closed', closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (position_id,))

            conn.commit()
            conn.close()
            logger.info(f"Position closed: {position_id}")
            return True
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    def delete_position(self, position_id: int, chat_id: int = None) -> bool:
        """Delete position permanently"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if chat_id:
                cursor.execute("DELETE FROM portfolio_positions WHERE id = ? AND chat_id = ?",
                             (position_id, chat_id))
            else:
                cursor.execute("DELETE FROM portfolio_positions WHERE id = ?", (position_id,))

            conn.commit()
            conn.close()
            logger.info(f"Position deleted: {position_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting position: {e}")
            return False

    def get_portfolio_summary(self, chat_id: int) -> Dict:
        """Get portfolio summary stats"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all open positions
            cursor.execute("""
                SELECT COUNT(*), SUM(total_value)
                FROM portfolio_positions
                WHERE chat_id = ? AND status = 'open'
            """, (chat_id,))

            row = cursor.fetchone()
            total_positions = row[0] or 0
            total_value = row[1] or 0

            # Calculate P/L for all positions
            cursor.execute("""
                SELECT entry_price, current_price, quantity, position_type
                FROM portfolio_positions
                WHERE chat_id = ? AND status = 'open'
            """, (chat_id,))

            rows = cursor.fetchall()
            total_pnl = 0.0
            total_pnl_percent = 0.0

            for row in rows:
                entry_price, current_price, quantity, pos_type = row
                if pos_type == 'LONG':
                    pnl = (current_price - entry_price) * quantity
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl = (entry_price - current_price) * quantity
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100

                total_pnl += pnl
                total_pnl_percent += pnl_percent

            conn.close()

            return {
                'total_positions': total_positions,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_pnl_percent': total_pnl_percent / total_positions if total_positions > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                'total_positions': 0,
                'total_value': 0,
                'total_pnl': 0,
                'total_pnl_percent': 0
            }

    def add_transaction(self, chat_id: int, symbol: str, transaction_type: str,
                       price: float, quantity: float, notes: str = None) -> Optional[int]:
        """Add transaction to history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            total_value = price * quantity

            cursor.execute("""
                INSERT INTO portfolio_transactions
                (chat_id, symbol, transaction_type, price, quantity, total_value, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (chat_id, symbol.upper(), transaction_type.upper(), price,
                  quantity, total_value, notes))

            conn.commit()
            transaction_id = cursor.lastrowid
            conn.close()

            logger.info(f"Transaction added: {transaction_id} - {transaction_type} {symbol}")
            return transaction_id
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return None


# Global database instance
db = TelegramDatabase()
