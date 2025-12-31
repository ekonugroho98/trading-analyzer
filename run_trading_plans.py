#!/usr/bin/env python3
"""
STANDALONE TRADING PLAN GENERATOR
Run manually untuk generate trading plans
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
from datetime import datetime
from scheduler import TradingScheduler
from deepseek_integration import TradingPlanGenerator, AnalysisRequest

def main():
    """Main function untuk run trading plans"""
    parser = argparse.ArgumentParser(description="Generate Trading Plans")
    parser.add_argument("--symbol", type=str, default="BTCUSDT",
                       help="Trading symbol (default: BTCUSDT)")
    parser.add_argument("--timeframe", type=str, default="4h",
                       help="Timeframe (default: 4h)")
    parser.add_argument("--all", action="store_true",
                       help="Generate for all major pairs")
    parser.add_argument("--schedule", action="store_true",
                       help="Start scheduler for automatic generation")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.schedule:
        # Start scheduler mode
        print("🚀 Starting Trading Plan Scheduler...")
        scheduler = TradingScheduler()
        scheduler.setup_trading_plan_tasks()
        scheduler.start(background=False)

    elif args.all:
        # Generate for all major pairs
        print("📊 Generating trading plans for all major pairs...")
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

        generator = TradingPlanGenerator()

        for symbol in symbols:
            try:
                print(f"\n🔍 Analyzing {symbol}...")
                request = AnalysisRequest(
                    symbol=symbol,
                    timeframe=args.timeframe,
                    data_points=100,
                    analysis_type="trading_plan"
                )

                plan = generator.generate_trading_plan(request)

                if plan:
                    print(f"✅ {symbol} Trading Plan Generated!")
                    print(f"   Trend: {plan.trend}")
                    print(f"   Signal: {plan.overall_signal.signal_type}")
                    print(f"   Confidence: {plan.overall_signal.confidence:.2%}")
                else:
                    print(f"❌ Failed to generate plan for {symbol}")

            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")

        print("\n✅ All trading plans generated!")

    else:
        # Generate for single symbol
        print(f"📊 Generating trading plan for {args.symbol}...")

        generator = TradingPlanGenerator()

        try:
            request = AnalysisRequest(
                symbol=args.symbol,
                timeframe=args.timeframe,
                data_points=100,
                analysis_type="trading_plan"
            )

            plan = generator.generate_trading_plan(request)

            if plan:
                print(f"\n✅ Trading Plan Generated for {args.symbol}!")
                print(f"{'='*60}")
                print(f"Trend: {plan.trend}")
                print(f"Signal: {plan.overall_signal.signal_type}")
                print(f"Confidence: {plan.overall_signal.confidence:.2%}")
                print(f"Reason: {plan.overall_signal.reason}")
                print(f"\nEntry Levels:")
                for entry in plan.entries:
                    print(f"  - ${entry.level:.2f} (weight: {entry.weight:.0%})")

                print(f"\nTake Profits:")
                for tp in plan.take_profits:
                    print(f"  - ${tp.level:.2f} (R:R {tp.reward_ratio:.1f}x)")

                print(f"\nStop Loss: ${plan.stop_loss:.2f}")
                print(f"Position Size: {plan.position_size}%")
                print(f"Risk/Reward: {plan.risk_reward_ratio:.2f}")
                print(f"{'='*60}")
            else:
                print(f"❌ Failed to generate trading plan")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
