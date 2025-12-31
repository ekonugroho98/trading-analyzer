"""
Paper Trading Manager
Manage paper trading positions without real money
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PositionType(Enum):
    """Position type"""
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(Enum):
    """Position status"""
    PENDING = "pending"  # Waiting for user confirmation
    OPEN = "open"        # Position opened
    CLOSED = "closed"    # Position closed


@dataclass
class PaperPosition:
    """Paper trading position"""
    id: Optional[int]
    chat_id: int
    symbol: str
    position_type: str  # LONG or SHORT
    entry_price: float
    quantity: float
    stop_loss: Optional[float]
    take_profits: List[Dict]  # [{"level": 100000, "percentage": 0.5, "filled": False}]
    status: str
    opened_at: datetime
    closed_at: Optional[datetime]
    pnl: Optional[float]
    pnl_percentage: Optional[float]
    notes: Optional[str]

    @property
    def total_value(self) -> float:
        """Calculate total position value"""
        return self.entry_price * self.quantity

    @property
    def current_value(self, current_price: float) -> float:
        """Calculate current value based on current price"""
        return current_price * self.quantity

    @property
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.position_type == PositionType.LONG.value:
            return (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - current_price) * self.quantity

    @property
    def unrealized_pnl_percentage(self, current_price: float) -> float:
        """Calculate unrealized P&L percentage"""
        if self.position_type == PositionType.LONG.value:
            return ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - current_price) / self.entry_price) * 100


class PaperTradingManager:
    """Manage paper trading positions"""

    def __init__(self, db):
        """Initialize paper trading manager"""
        self.db = db
        self.pending_confirmations: Dict[int, Dict] = {}  # chat_id -> pending_position

    def create_pending_position(
        self,
        chat_id: int,
        symbol: str,
        position_type: str,
        entry_price: float,
        quantity: float,
        stop_loss: float = None,
        take_profits: List[Dict] = None,
        notes: str = None
    ) -> PaperPosition:
        """Create pending position for confirmation"""
        position = PaperPosition(
            id=None,
            chat_id=chat_id,
            symbol=symbol,
            position_type=position_type,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profits=take_profits or [],
            status=PositionStatus.PENDING.value,
            opened_at=datetime.now(),
            closed_at=None,
            pnl=None,
            pnl_percentage=None,
            notes=notes
        )

        # Store in pending confirmations
        self.pending_confirmations[chat_id] = asdict(position)

        logger.info(f"Created pending paper position: {symbol} {position_type} @ {entry_price}")
        return position

    def confirm_position(self, chat_id: int) -> Optional[PaperPosition]:
        """Confirm and open pending position"""
        if chat_id not in self.pending_confirmations:
            logger.warning(f"No pending position for chat_id {chat_id}")
            return None

        pos_data = self.pending_confirmations[chat_id]

        # Insert into database
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO portfolio_positions (
                    chat_id, symbol, position_type, entry_price, quantity,
                    stop_loss, notes, status, opened_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_id,
                pos_data['symbol'],
                pos_data['position_type'],
                pos_data['entry_price'],
                pos_data['quantity'],
                pos_data['stop_loss'],
                pos_data['notes'],
                PositionStatus.OPEN.value,
                pos_data['opened_at']
            ))

            position_id = cursor.lastrowid
            conn.commit()

            # Store take profits separately
            if pos_data['take_profits']:
                for tp in pos_data['take_profits']:
                    cursor.execute("""
                        INSERT INTO position_take_profits (
                            position_id, level, percentage, status
                        ) VALUES (?, ?, ?, ?)
                    """, (position_id, tp['level'], tp.get('percentage', 1.0), 'pending'))

                conn.commit()

            # Create position object
            position = PaperPosition(
                id=position_id,
                **pos_data,
                status=PositionStatus.OPEN.value
            )

            # Remove from pending
            del self.pending_confirmations[chat_id]

            logger.info(f"Confirmed and opened paper position #{position_id}: {pos_data['symbol']}")
            return position

        except Exception as e:
            conn.rollback()
            logger.error(f"Error confirming position: {e}")
            return None
        finally:
            conn.close()

    def cancel_pending_position(self, chat_id: int) -> bool:
        """Cancel pending position"""
        if chat_id in self.pending_confirmations:
            del self.pending_confirmations[chat_id]
            logger.info(f"Cancelled pending position for chat_id {chat_id}")
            return True
        return False

    def get_open_positions(self, chat_id: int) -> List[PaperPosition]:
        """Get all open positions for user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, chat_id, symbol, position_type, entry_price, quantity,
                       stop_loss, notes, status, opened_at, closed_at
                FROM portfolio_positions
                WHERE chat_id = ? AND status = 'open'
                ORDER BY opened_at DESC
            """, (chat_id,))

            rows = cursor.fetchall()
            positions = []

            for row in rows:
                # Get take profits
                cursor.execute("""
                    SELECT level, percentage, status
                    FROM position_take_profits
                    WHERE position_id = ?
                    ORDER BY level ASC
                """, (row[0],))

                tp_rows = cursor.fetchall()
                take_profits = [
                    {"level": tp[0], "percentage": tp[1], "status": tp[2]}
                    for tp in tp_rows
                ]

                position = PaperPosition(
                    id=row[0],
                    chat_id=row[1],
                    symbol=row[2],
                    position_type=row[3],
                    entry_price=row[4],
                    quantity=row[5],
                    stop_loss=row[6],
                    take_profits=take_profits,
                    status=row[8],
                    opened_at=datetime.fromisoformat(row[9]),
                    closed_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    pnl=None,
                    pnl_percentage=None,
                    notes=row[7]
                )
                positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
        finally:
            conn.close()

    def close_position(self, position_id: int, close_price: float, chat_id: int) -> bool:
        """Close a position"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # Get position details
            cursor.execute("""
                SELECT position_type, entry_price, quantity
                FROM portfolio_positions
                WHERE id = ? AND chat_id = ?
            """, (position_id, chat_id))

            row = cursor.fetchone()
            if not row:
                logger.warning(f"Position {position_id} not found")
                return False

            position_type, entry_price, quantity = row

            # Calculate P&L
            if position_type == PositionType.LONG.value:
                pnl = (close_price - entry_price) * quantity
            else:  # SHORT
                pnl = (entry_price - close_price) * quantity

            pnl_percentage = (pnl / (entry_price * quantity)) * 100

            # Update position
            cursor.execute("""
                UPDATE portfolio_positions
                SET status = 'closed',
                    closed_at = ?,
                    pnl = ?,
                    pnl_percentage = ?
                WHERE id = ?
            """, (datetime.now(), pnl, pnl_percentage, position_id))

            conn.commit()
            logger.info(f"Closed position #{position_id} with P&L: ${pnl:.2f} ({pnl_percentage:.2f}%)")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error closing position: {e}")
            return False
        finally:
            conn.close()

    def get_portfolio_summary(self, chat_id: int) -> Dict[str, Any]:
        """Get portfolio summary for user"""
        positions = self.get_open_positions(chat_id)

        if not positions:
            return {
                'total_positions': 0,
                'total_value': 0,
                'total_pnl': 0,
                'positions': []
            }

        total_value = sum(pos.total_value for pos in positions)
        total_pnl = 0  # Need current prices for unrealized P&L

        return {
            'total_positions': len(positions),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'positions': positions
        }
