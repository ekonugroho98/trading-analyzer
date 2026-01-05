"""
Whale Transaction Monitor
Track large on-chain transactions using Whale Alert API
"""

import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WhaleTransaction:
    """Whale transaction data"""
    transaction_id: str
    symbol: str
    transaction_type: str  # 'deposit', 'withdrawal', 'transfer'
    amount: float
    amount_usd: float
    from_address: str
    to_address: str
    from_owner: str  # 'exchange', 'wallet', 'unknown'
    to_owner: str
    timestamp: datetime
    tx_hash: str


class WhaleMonitor:
    """Monitor whale transactions using Whale Alert API"""

    def __init__(self, api_key: str = None):
        """Initialize whale monitor

        Args:
            api_key: Whale Alert API key (free tier available at whale-alert.io)
        """
        self.api_key = api_key
        self.base_url = "https://api.whale-alert.io/v1"
        self.min_value_usd = 500000  # Minimum $500k transactions

        # Symbol mapping untuk Whale Alert
        self.symbol_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'binancecoin': 'BNB',
            'usd-coin': 'USDC',
            'tether': 'USDT',
            'ripple': 'XRP',
            'cardano': 'ADA',
            'solana': 'SOL',
            'dogecoin': 'DOGE',
            'polkadot': 'DOT',
            'avalanche-2': 'AVAX',
            'chainlink': 'LINK',
            'matic-network': 'MATIC',
            'litecoin': 'LTC',
        }

    async def get_transactions(
        self,
        symbol: str = None,
        limit: int = 20,
        minutes: int = 60
    ) -> List[WhaleTransaction]:
        """Get recent whale transactions

        Args:
            symbol: Filter by symbol (e.g., 'BTC', 'ETH')
            limit: Maximum number of transactions
            minutes: Lookback period in minutes

        Returns:
            List of WhaleTransaction objects
        """
        if not self.api_key:
            logger.warning("Whale Alert API key not configured, returning mock data")
            return self._get_mock_transactions(symbol, limit)

        try:
            # Calculate start time
            start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp())

            # Build URL
            url = f"{self.base_url}/transactions"
            params = {
                'api_key': self.api_key,
                'min_value': self.min_value_usd,
                'limit': limit,
                'start': start_time
            }

            if symbol:
                # Map symbol to Whale Alert format
                whale_symbol = self._symbol_to_whale_format(symbol)
                if whale_symbol:
                    params['symbol'] = whale_symbol

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Whale Alert API error: {response.status}")
                        return []

                    data = await response.json()

                    # Parse transactions
                    transactions = []
                    for tx in data.get('transactions', []):
                        transaction = self._parse_transaction(tx)
                        if transaction:
                            transactions.append(transaction)

                    logger.info(f"Retrieved {len(transactions)} whale transactions")
                    return transactions

        except Exception as e:
            logger.error(f"Error fetching whale transactions: {e}")
            return []

    def _parse_transaction(self, tx: Dict) -> Optional[WhaleTransaction]:
        """Parse transaction from API response

        Args:
            tx: Transaction dict from API

        Returns:
            WhaleTransaction object or None
        """
        try:
            # Extract symbol
            symbol = tx.get('symbol', '')

            # Map to our symbol format
            if symbol in self.symbol_map.values():
                mapped_symbol = symbol
            else:
                mapped_symbol = self._whale_symbol_to_standard(symbol)

            # Determine transaction type
            tx_type = tx.get('transaction_type', 'transfer')

            # Determine owners
            from_owner = tx.get('from_owner', 'unknown').lower()
            to_owner = tx.get('to_owner', 'unknown').lower()

            # Map owner types
            if 'exchange' in from_owner:
                from_owner = 'exchange'
            elif 'wallet' in from_owner or 'unknown' not in from_owner:
                from_owner = 'wallet'
            else:
                from_owner = 'unknown'

            if 'exchange' in to_owner:
                to_owner = 'exchange'
            elif 'wallet' in to_owner or 'unknown' not in to_owner:
                to_owner = 'wallet'
            else:
                to_owner = 'unknown'

            return WhaleTransaction(
                transaction_id=str(tx.get('id', '')),
                symbol=mapped_symbol,
                transaction_type=tx_type,
                amount=float(tx.get('amount', 0)),
                amount_usd=float(tx.get('amount_usd', 0)),
                from_address=tx.get('from', '')[:10] + '...',  # Truncate address
                to_address=tx.get('to', '')[:10] + '...',
                from_owner=from_owner,
                to_owner=to_owner,
                timestamp=datetime.fromtimestamp(tx.get('timestamp', 0)),
                tx_hash=tx.get('hash', '')
            )

        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None

    def _symbol_to_whale_format(self, symbol: str) -> Optional[str]:
        """Convert symbol to Whale Alert format

        Args:
            symbol: Symbol in our format (e.g., 'BTCUSDT')

        Returns:
            Symbol in Whale Alert format or None
        """
        # Remove USDT suffix
        base = symbol.replace('USDT', '').replace('USD', '')

        # Map to Whale Alert format
        for whale_key, whale_value in self.symbol_map.items():
            if base == whale_value:
                return whale_key

        return None

    def _whale_symbol_to_standard(self, whale_symbol: str) -> str:
        """Convert Whale Alert symbol to our format

        Args:
            whale_symbol: Symbol in Whale Alert format

        Returns:
            Symbol in our format
        """
        # Direct mapping
        if whale_symbol in self.symbol_map.values():
            return whale_symbol

        # Try to map from Whale Alert format
        for whale_key, whale_value in self.symbol_map.items():
            if whale_key.lower() in whale_symbol.lower():
                return whale_value

        return whale_symbol.upper()

    def _get_mock_transactions(
        self,
        symbol: str = None,
        limit: int = 20
    ) -> List[WhaleTransaction]:
        """Generate mock whale transactions for testing

        Args:
            symbol: Filter by symbol
            limit: Maximum number of transactions

        Returns:
            List of mock WhaleTransaction objects
        """
        logger.info("Generating mock whale transactions")

        import random

        # Mock symbols
        symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE']
        if symbol:
            symbols = [symbol.replace('USDT', '')]

        # Mock owners
        owners = ['exchange', 'wallet', 'unknown']

        # Mock transaction types
        tx_types = ['deposit', 'withdrawal', 'transfer']

        transactions = []
        now = datetime.now()

        for i in range(min(limit, 10)):
            sym = random.choice(symbols)

            # Mock amount based on symbol
            if sym == 'BTC':
                amount = random.uniform(100, 1000)
                amount_usd = amount * random.uniform(90000, 95000)
            elif sym == 'ETH':
                amount = random.uniform(1000, 10000)
                amount_usd = amount * random.uniform(3000, 4000)
            elif sym == 'BNB':
                amount = random.uniform(5000, 50000)
                amount_usd = amount * random.uniform(500, 700)
            else:
                amount = random.uniform(100000, 10000000)
                amount_usd = amount * random.uniform(0.5, 2)

            # Only include if above min_value
            if amount_usd < self.min_value_usd:
                continue

            tx = WhaleTransaction(
                transaction_id=f"mock_{i}",
                symbol=sym,
                transaction_type=random.choice(tx_types),
                amount=round(amount, 4),
                amount_usd=round(amount_usd, 2),
                from_address=f"0x{''.join(random.choice('0123456789abcdef') for _ in range(8))}...",
                to_address=f"0x{''.join(random.choice('0123456789abcdef') for _ in range(8))}...",
                from_owner=random.choice(owners),
                to_owner=random.choice(owners),
                timestamp=now - timedelta(minutes=random.randint(1, 60)),
                tx_hash=f"0x{''.join(random.choice('0123456789abcdef') for _ in range(64))}"
            )

            transactions.append(tx)

        logger.info(f"Generated {len(transactions)} mock transactions")
        return transactions

    def analyze_transaction(self, tx: WhaleTransaction) -> Dict[str, Any]:
        """Analyze whale transaction untuk market impact

        Args:
            tx: WhaleTransaction to analyze

        Returns:
            Analysis dict with impact assessment
        """
        impact = {
            'direction': 'NEUTRAL',
            'significance': 'LOW',
            'reason': ''
        }

        # Exchange inflow (potentially bearish)
        if tx.to_owner == 'exchange' and tx.from_owner == 'wallet':
            impact['direction'] = 'BEARISH'
            impact['reason'] = 'Large deposit to exchange - potential sell pressure'
            if tx.amount_usd > 10000000:  # $10M+
                impact['significance'] = 'HIGH'
            elif tx.amount_usd > 5000000:  # $5M+
                impact['significance'] = 'MEDIUM'

        # Exchange outflow (potentially bullish)
        elif tx.from_owner == 'exchange' and tx.to_owner == 'wallet':
            impact['direction'] = 'BULLISH'
            impact['reason'] = 'Large withdrawal from exchange - potential accumulation'
            if tx.amount_usd > 10000000:
                impact['significance'] = 'HIGH'
            elif tx.amount_usd > 5000000:
                impact['significance'] = 'MEDIUM'

        # Wallet to wallet (neutral, accumulation)
        elif tx.from_owner == 'wallet' and tx.to_owner == 'wallet':
            impact['direction'] = 'NEUTRAL'
            impact['reason'] = 'Wallet-to-wallet transfer - accumulation or distribution'

        # Exchange to exchange (arbitrage)
        elif tx.from_owner == 'exchange' and tx.to_owner == 'exchange':
            impact['direction'] = 'NEUTRAL'
            impact['reason'] = 'Exchange-to-exchange transfer - likely arbitrage'

        return impact


# Global whale monitor instance
_whale_monitor_instance = None


def get_whale_monitor() -> WhaleMonitor:
    """Get global whale monitor instance"""
    global _whale_monitor_instance
    if _whale_monitor_instance is None:
        from config import config
        api_key = getattr(config, 'WHALE_ALERT_API_KEY', None)
        _whale_monitor_instance = WhaleMonitor(api_key=api_key)
    return _whale_monitor_instance
