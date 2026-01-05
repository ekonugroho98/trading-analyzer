"""
Signal History Tracker
Track all AI trading signals and their outcomes
"""

import logging
import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)


class SignalTracker:
    """Track trading signals and their outcomes"""

    def __init__(self, db_path: str = None):
        """Initialize signal tracker database

        Args:
            db_path: Path to database file
        """
        if db_path is None:
            # Use same path as telegram_users.db
            db_path = config.DATA_DIR / "telegram_users.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()
        logger.info(f"Signal tracker initialized: {self.db_path}")

    def _init_database(self):
        """Create signal_history table if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Signal history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                timeframe TEXT,
                signal_type TEXT,
                confidence REAL,
                entries TEXT,
                take_profits TEXT,
                stop_loss REAL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                outcome TEXT DEFAULT 'pending',
                actual_outcome REAL,
                outcome_at TIMESTAMP,
                plan_id TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_history_user_id ON signal_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_history_symbol ON signal_history(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_history_outcome ON signal_history(outcome)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_history_generated_at ON signal_history(generated_at)")

        conn.commit()
        conn.close()

    def save_signal(
        self,
        user_id: int,
        symbol: str,
        timeframe: str,
        signal_type: str,
        confidence: float,
        entries: List[float],
        take_profits: List[Dict],
        stop_loss: float,
        plan_id: str = None
    ) -> Optional[int]:
        """Save trading signal to database

        Args:
            user_id: User chat_id
            symbol: Trading pair symbol
            timeframe: Timeframe (1h, 4h, 1d, etc)
            signal_type: Signal type (BUY/SELL/HOLD)
            confidence: Confidence score (0-1)
            entries: List of entry prices
            take_profits: List of take profit dicts with level and reward_ratio
            stop_loss: Stop loss price
            plan_id: Optional plan reference ID

        Returns:
            Signal ID or None if failed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert lists to JSON
            entries_json = json.dumps(entries)
            take_profits_json = json.dumps(take_profits)

            cursor.execute("""
                INSERT INTO signal_history
                (user_id, symbol, timeframe, signal_type, confidence, entries,
                 take_profits, stop_loss, plan_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, symbol.upper(), timeframe, signal_type.upper(),
                  confidence, entries_json, take_profits_json,
                  stop_loss, plan_id))

            conn.commit()
            signal_id = cursor.lastrowid
            conn.close()

            logger.info(f"Signal saved: {signal_id} - {symbol} {signal_type} @{timeframe}")
            return signal_id

        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return None

    def update_signal_outcome(
        self,
        signal_id: int,
        outcome: str,
        actual_outcome: float = None
    ) -> bool:
        """Update signal outcome

        Args:
            signal_id: Signal ID
            outcome: Outcome ('won', 'lost', 'breakeven')
            actual_outcome: Actual P&L in USD or percentage

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if actual_outcome is not None:
                cursor.execute("""
                    UPDATE signal_history
                    SET outcome = ?, actual_outcome = ?, outcome_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (outcome, actual_outcome, signal_id))
            else:
                cursor.execute("""
                    UPDATE signal_history
                    SET outcome = ?, outcome_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (outcome, signal_id))

            conn.commit()
            conn.close()

            logger.info(f"Signal outcome updated: {signal_id} -> {outcome}")
            return True

        except Exception as e:
            logger.error(f"Error updating signal outcome: {e}")
            return False

    def get_signal_history(
        self,
        user_id: int = None,
        symbol: str = None,
        timeframe: str = None,
        outcome: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get signal history with filters

        Args:
            user_id: Filter by user ID
            symbol: Filter by symbol
            timeframe: Filter by timeframe
            outcome: Filter by outcome ('pending', 'won', 'lost', 'breakeven')
            limit: Maximum number of records

        Returns:
            List of signal dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT id, user_id, symbol, timeframe, signal_type, confidence,
                       entries, take_profits, stop_loss, generated_at,
                       outcome, actual_outcome, outcome_at, plan_id
                FROM signal_history
                WHERE 1=1
            """
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            if outcome:
                query += " AND outcome = ?"
                params.append(outcome)

            query += " ORDER BY generated_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Parse results
            signals = []
            for row in rows:
                try:
                    entries = json.loads(row[6]) if row[6] else []
                    take_profits = json.loads(row[7]) if row[7] else []
                except:
                    entries = []
                    take_profits = []

                signals.append({
                    'id': row[0],
                    'user_id': row[1],
                    'symbol': row[2],
                    'timeframe': row[3],
                    'signal_type': row[4],
                    'confidence': row[5],
                    'entries': entries,
                    'take_profits': take_profits,
                    'stop_loss': row[8],
                    'generated_at': row[9],
                    'outcome': row[10],
                    'actual_outcome': row[11],
                    'outcome_at': row[12],
                    'plan_id': row[13]
                })

            return signals

        except Exception as e:
            logger.error(f"Error getting signal history: {e}")
            return []

    def get_signal_stats(
        self,
        user_id: int = None,
        symbol: str = None,
        timeframe: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate signal statistics

        Args:
            user_id: Filter by user ID
            symbol: Filter by symbol
            timeframe: Filter by timeframe
            days: Lookback period in days

        Returns:
            Statistics dict
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate start time
            start_time = datetime.now() - timedelta(days=days)

            # Build query
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome = 'breakeven' THEN 1 ELSE 0 END) as breakeven,
                    SUM(CASE WHEN outcome = 'pending' THEN 1 ELSE 0 END) as pending,
                    AVG(confidence) as avg_confidence,
                    AVG(CASE WHEN outcome = 'won' THEN confidence ELSE NULL END) as avg_win_confidence,
                    AVG(CASE WHEN outcome = 'lost' THEN confidence ELSE NULL END) as avg_loss_confidence
                FROM signal_history
                WHERE generated_at >= ?
            """
            params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()

            total = row[0] or 0
            wins = row[1] or 0
            losses = row[2] or 0
            breakeven = row[3] or 0
            pending = row[4] or 0
            avg_confidence = row[5] or 0
            avg_win_confidence = row[6] or 0
            avg_loss_confidence = row[7] or 0

            # Calculate win rate
            completed = wins + losses + breakeven
            win_rate = (wins / completed * 100) if completed > 0 else 0

            return {
                'total_signals': total,
                'wins': wins,
                'losses': losses,
                'breakeven': breakeven,
                'pending': pending,
                'win_rate': win_rate,
                'avg_confidence': avg_confidence,
                'avg_win_confidence': avg_win_confidence,
                'avg_loss_confidence': avg_loss_confidence,
                'period_days': days
            }

        except Exception as e:
            logger.error(f"Error calculating signal stats: {e}")
            return {
                'total_signals': 0,
                'wins': 0,
                'losses': 0,
                'breakeven': 0,
                'pending': 0,
                'win_rate': 0,
                'avg_confidence': 0,
                'avg_win_confidence': 0,
                'avg_loss_confidence': 0,
                'period_days': days
            }

    def get_best_signals(
        self,
        user_id: int = None,
        limit: int = 10,
        sort_by: str = 'confidence'
    ) -> List[Dict]:
        """Get best performing signals

        Args:
            user_id: Filter by user ID
            limit: Maximum number of records
            sort_by: Sort field ('confidence', 'profit')

        Returns:
            List of signal dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT id, user_id, symbol, timeframe, signal_type, confidence,
                       entries, take_profits, stop_loss, generated_at,
                       outcome, actual_outcome, outcome_at, plan_id
                FROM signal_history
                WHERE outcome != 'pending'
            """
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if sort_by == 'profit':
                query += " ORDER BY actual_outcome DESC"
            else:  # confidence
                query += " ORDER BY confidence DESC"

            query += " LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Parse results
            signals = []
            for row in rows:
                try:
                    entries = json.loads(row[6]) if row[6] else []
                    take_profits = json.loads(row[7]) if row[7] else []
                except:
                    entries = []
                    take_profits = []

                signals.append({
                    'id': row[0],
                    'user_id': row[1],
                    'symbol': row[2],
                    'timeframe': row[3],
                    'signal_type': row[4],
                    'confidence': row[5],
                    'entries': entries,
                    'take_profits': take_profits,
                    'stop_loss': row[8],
                    'generated_at': row[9],
                    'outcome': row[10],
                    'actual_outcome': row[11],
                    'outcome_at': row[12],
                    'plan_id': row[13]
                })

            return signals

        except Exception as e:
            logger.error(f"Error getting best signals: {e}")
            return []

    def get_worst_signals(
        self,
        user_id: int = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get worst performing signals

        Args:
            user_id: Filter by user ID
            limit: Maximum number of records

        Returns:
            List of signal dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT id, user_id, symbol, timeframe, signal_type, confidence,
                       entries, take_profits, stop_loss, generated_at,
                       outcome, actual_outcome, outcome_at, plan_id
                FROM signal_history
                WHERE outcome = 'lost'
            """
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " ORDER BY actual_outcome ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Parse results
            signals = []
            for row in rows:
                try:
                    entries = json.loads(row[6]) if row[6] else []
                    take_profits = json.loads(row[7]) if row[7] else []
                except:
                    entries = []
                    take_profits = []

                signals.append({
                    'id': row[0],
                    'user_id': row[1],
                    'symbol': row[2],
                    'timeframe': row[3],
                    'signal_type': row[4],
                    'confidence': row[5],
                    'entries': entries,
                    'take_profits': take_profits,
                    'stop_loss': row[8],
                    'generated_at': row[9],
                    'outcome': row[10],
                    'actual_outcome': row[11],
                    'outcome_at': row[12],
                    'plan_id': row[13]
                })

            return signals

        except Exception as e:
            logger.error(f"Error getting worst signals: {e}")
            return []

    def get_performance_by_symbol(self, user_id: int = None, days: int = 30) -> List[Dict]:
        """Get performance breakdown by symbol

        Args:
            user_id: Filter by user ID
            days: Lookback period in days

        Returns:
            List of performance dicts by symbol
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            start_time = datetime.now() - timedelta(days=days)

            query = """
                SELECT
                    symbol,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'lost' THEN 1 ELSE 0 END) as losses,
                    AVG(confidence) as avg_confidence
                FROM signal_history
                WHERE generated_at >= ?
            """
            params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " GROUP BY symbol ORDER BY wins DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            performance = []
            for row in rows:
                total = row[1] or 0
                wins = row[2] or 0
                losses = row[3] or 0
                completed = wins + losses
                win_rate = (wins / completed * 100) if completed > 0 else 0

                performance.append({
                    'symbol': row[0],
                    'total_signals': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'avg_confidence': row[4] or 0
                })

            return performance

        except Exception as e:
            logger.error(f"Error getting performance by symbol: {e}")
            return []

    def get_performance_by_timeframe(self, user_id: int = None, days: int = 30) -> List[Dict]:
        """Get performance breakdown by timeframe

        Args:
            user_id: Filter by user ID
            days: Lookback period in days

        Returns:
            List of performance dicts by timeframe
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            start_time = datetime.now() - timedelta(days=days)

            query = """
                SELECT
                    timeframe,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'lost' THEN 1 ELSE 0 END) as losses,
                    AVG(confidence) as avg_confidence
                FROM signal_history
                WHERE generated_at >= ?
            """
            params = [start_time.strftime('%Y-%m-%d %H:%M:%S')]

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " GROUP BY timeframe ORDER BY wins DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            performance = []
            for row in rows:
                total = row[1] or 0
                wins = row[2] or 0
                losses = row[3] or 0
                completed = wins + losses
                win_rate = (wins / completed * 100) if completed > 0 else 0

                performance.append({
                    'timeframe': row[0],
                    'total_signals': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'avg_confidence': row[4] or 0
                })

            return performance

        except Exception as e:
            logger.error(f"Error getting performance by timeframe: {e}")
            return []


# Global signal tracker instance
_signal_tracker_instance = None


def get_signal_tracker() -> SignalTracker:
    """Get global signal tracker instance"""
    global _signal_tracker_instance
    if _signal_tracker_instance is None:
        _signal_tracker_instance = SignalTracker()
    return _signal_tracker_instance
