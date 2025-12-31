#!/usr/bin/env python3
"""
Get All Binance Futures Symbols
Fetch all available trading pairs from Binance Futures
"""

import requests
import json
from datetime import datetime

def get_binance_futures_symbols():
    """Get all USDT-M futures symbols from Binance"""

    # Binance Futures API endpoint
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"

    try:
        print("=" * 60)
        print("📡 Fetching Binance Futures Symbols...")
        print("=" * 60)

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Filter USDT-M futures pairs
        usdt_pairs = []
        for symbol_info in data['symbols']:
            if (
                symbol_info['quoteAsset'] == 'USDT' and
                symbol_info['status'] == 'TRADING' and
                symbol_info['contractType'] == 'PERPETUAL'
            ):
                usdt_pairs.append({
                    'symbol': symbol_info['symbol'],
                    'baseAsset': symbol_info['baseAsset'],
                    'status': symbol_info['status'],
                    'contractType': symbol_info['contractType']
                })

        # Sort by symbol
        usdt_pairs.sort(key=lambda x: x['symbol'])

        print(f"\n✅ Found {len(usdt_pairs)} USDT-M perpetual futures pairs\n")

        # Group by first letter for easier reading
        grouped = {}
        for pair in usdt_pairs:
            first_letter = pair['symbol'][0]
            if first_letter not in grouped:
                grouped[first_letter] = []
            grouped[first_letter].append(pair['symbol'])

        # Print grouped results
        print("=" * 60)
        print("📋 Available Binance Futures USDT-M Pairs:")
        print("=" * 60)

        for letter in sorted(grouped.keys()):
            symbols_str = ', '.join(grouped[letter])
            print(f"\n[{letter}] {symbols_str}")

        # Save to file
        output_file = 'data/binance_futures_symbols.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_pairs': len(usdt_pairs),
                'symbols': [p['symbol'] for p in usdt_pairs],
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        print(f"\n✅ Saved to {output_file}")

        # Create Python list for easy copying
        symbols_list = ', '.join([f'"{s}"' for s in [p['symbol'] for p in usdt_pairs]])

        print("\n" + "=" * 60)
        print("📋 Python List (ready to copy):")
        print("=" * 60)
        print(f"\nsymbols = [{symbols_list}]\n")

        # Top 20 by market cap (manual selection for now)
        top_coins = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
            "LINKUSDT", "ATOMUSDT", "LTCUSDT", "UNIUSDT", "NEARUSDT",
            "APTUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT", "SEIUSDT"
        ]

        print("=" * 60)
        print("🔥 Top 20 Coins (Recommended for Trading):")
        print("=" * 60)
        print(f"\n{', '.join(top_coins)}\n")

        return usdt_pairs

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []


def get_top_volume_symbols(limit=20):
    """Get top symbols by 24h volume from Binance Futures"""

    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"

    try:
        print("=" * 60)
        print(f"📊 Fetching Top {limit} by Volume (24h)...")
        print("=" * 60)

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Filter USDT pairs and sort by volume
        usdt_tickers = [
            {
                'symbol': t['symbol'],
                'volume': float(t['quoteVolume']),
                'change': float(t['priceChangePercent'])
            }
            for t in data
            if t['symbol'].endswith('USDT')
        ]

        # Sort by volume (descending)
        usdt_tickers.sort(key=lambda x: x['volume'], reverse=True)

        # Get top N
        top_tickers = usdt_tickers[:limit]

        print(f"\n✅ Top {limit} USDT-M Futures by 24h Volume:\n")
        print(f"{'Rank':<5} {'Symbol':<12} {'Volume (USDT)':<20} {'24h Change'}")
        print("-" * 60)

        for i, ticker in enumerate(top_tickers, 1):
            volume_str = f"${ticker['volume']:,.0f}"
            change_str = f"{ticker['change']:+.2f}%"
            emoji = "🟢" if ticker['change'] >= 0 else "🔴"
            print(f"{i:<5} {ticker['symbol']:<12} {volume_str:<20} {emoji} {change_str}")

        # Return as list
        return [t['symbol'] for t in top_tickers]

    except Exception as e:
        print(f"❌ Error: {e}")
        return []


if __name__ == "__main__":
    import os

    # Create data directory
    os.makedirs("data", exist_ok=True)

    # Get all symbols
    all_pairs = get_binance_futures_symbols()

    print("\n" + "=" * 60)
    print("\n")

    # Get top by volume
    top_symbols = get_top_volume_symbols(20)

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)
