#!/usr/bin/env python3
"""Test /plan BEATUSDT command"""

import asyncio
from deepseek_integration import TradingPlanGenerator, AnalysisRequest
from collector import CryptoDataCollector

async def test_plan_command():
    """Test plan command for BEATUSDT"""

    symbol = "BEATUSDT"
    timeframe = "4h"

    print(f"📊 Testing /plan {symbol} {timeframe}")
    print("=" * 60)

    # Initialize collector
    collector = CryptoDataCollector()

    # Pre-fetch data using auto-detect
    print(f"1. Fetching data for {symbol}...")
    df_test = collector.get_binance_klines_auto(symbol, timeframe, limit=100)

    if df_test is None or len(df_test) < 50:
        print(f"❌ Insufficient data for {symbol}")
        return

    print(f"✅ Got {len(df_test)} candles")

    # Generate trading plan
    print(f"\n2. Generating AI trading plan...")
    generator = TradingPlanGenerator()

    request = AnalysisRequest(
        symbol=symbol,
        timeframe=timeframe,
        data_points=100,
        analysis_type="trading_plan"
    )

    # Run in executor
    loop = asyncio.get_event_loop()
    plan = await loop.run_in_executor(None, generator.generate_trading_plan, request)

    if plan:
        print("\n" + "=" * 60)
        print("🤖 AI TRADING PLAN")
        print("=" * 60)
        print(plan)
        print("=" * 60)
    else:
        print(f"❌ Failed to generate trading plan for {symbol}")

if __name__ == "__main__":
    asyncio.run(test_plan_command())
