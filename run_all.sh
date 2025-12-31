#!/bin/bash
# Crypto Trading Analyzer - Start All Services
# This script starts all trading system components

echo "=========================================="
echo "🚀 Crypto Trading Analyzer - Starting All Services"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Kill any existing processes
echo "🛑 Stopping existing processes..."
pkill -f "run_integrated_system.py" 2>/dev/null
pkill -f "run_trading_plans.py" 2>/dev/null
pkill -f "run_telegram_bot.py" 2>/dev/null
sleep 2

# Create logs directory
mkdir -p logs

echo ""
echo "📊 Starting Integrated Trading System (WebSocket + Scheduler)..."
nohup python run_integrated_system.py > logs/integrated_system.log 2>&1 &
INTEGRATED_PID=$!
echo "   - PID: $INTEGRATED_PID"
echo "   - Log: logs/integrated_system.log"

sleep 3

echo ""
echo "📈 Starting Trading Plan Scheduler..."
nohup python run_trading_plans.py --schedule > logs/scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "   - PID: $SCHEDULER_PID"
echo "   - Log: logs/scheduler.log"

sleep 3

echo ""
echo "🤖 Starting Telegram Bot..."
nohup python run_telegram_bot.py > logs/telegram_bot.log 2>&1 &
TELEGRAM_PID=$!
echo "   - PID: $TELEGRAM_PID"
echo "   - Log: logs/telegram_bot.log"

sleep 3

echo ""
echo "=========================================="
echo "✅ All Services Started!"
echo "=========================================="
echo ""
echo "Running Processes:"
ps aux | grep -E "run_integrated_system|run_trading_plans|run_telegram_bot" | grep -v grep
echo ""
echo "=========================================="
echo "📝 Monitor logs with:"
echo "   tail -f logs/integrated_system.log"
echo "   tail -f logs/scheduler.log"
echo "   tail -f logs/telegram_bot.log"
echo ""
echo "🛑 Stop all services:"
echo "   ./stop_all.sh"
echo "=========================================="

# Save PIDs for stop script
echo "$INTEGRATED_PID" > .integrated_pid
echo "$SCHEDULER_PID" > .scheduler_pid
echo "$TELEGRAM_PID" > .telegram_pid
