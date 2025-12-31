#!/bin/bash
# Crypto Trading Analyzer - Stop All Services
# This script stops all running trading system components

echo "=========================================="
echo "🛑 Crypto Trading Analyzer - Stopping All Services"
echo "=========================================="

# Kill by process name
echo "Stopping Integrated Trading System..."
pkill -f "run_integrated_system.py" 2>/dev/null

echo "Stopping Trading Plan Scheduler..."
pkill -f "run_trading_plans.py" 2>/dev/null

echo "Stopping Telegram Bot..."
pkill -f "run_telegram_bot.py" 2>/dev/null

# Also kill by saved PIDs if available
if [ -f .integrated_pid ]; then
    PID=$(cat .integrated_pid)
    kill $PID 2>/dev/null
    rm .integrated_pid
fi

if [ -f .scheduler_pid ]; then
    PID=$(cat .scheduler_pid)
    kill $PID 2>/dev/null
    rm .scheduler_pid
fi

if [ -f .telegram_pid ]; then
    PID=$(cat .telegram_pid)
    kill $PID 2>/dev/null
    rm .telegram_pid
fi

sleep 2

echo ""
echo "=========================================="
echo "✅ All Services Stopped!"
echo "=========================================="
echo ""

# Check if any processes are still running
REMAINING=$(ps aux | grep -E "run_integrated_system|run_trading_plans|run_telegram_bot" | grep -v grep)
if [ -n "$REMAINING" ]; then
    echo "⚠️  Some processes are still running:"
    echo "$REMAINING"
    echo ""
    echo "Force kill with: pkill -9 -f 'python run_*.py'"
else
    echo "All processes stopped successfully."
fi
