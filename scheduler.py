"""
SCHEDULER MODULE - Automated Task Scheduling
"""

import schedule
import time
import threading
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Optional
import logging
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from config import config, Timeframe
from collector import CryptoDataCollector

logger = logging.getLogger(__name__)

# ============ DATA STRUCTURES ============
@dataclass
class ScheduledTask:
    """Task configuration"""
    name: str
    function: Callable
    interval: str  # 'hourly', 'daily', '5m', '1h', etc.
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    retry_count: int = 0
    max_retries: int = 3

class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

# ============ MAIN SCHEDULER CLASS ============
class TradingScheduler:
    """
    Advanced task scheduler for crypto trading system
    """
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_queue = []
        self.running = False
        self.scheduler_thread = None
        self.collector = CryptoDataCollector()
        
        # Trading plan generator (lazy initialization)
        self.trading_plan_generator = None
        self._trading_plan_generator_class = None
        self._analysis_request_class = None
        
        # Task history
        self.task_history = []
        self.max_history = 1000
        
        # Statistics
        self.tasks_executed = 0
        self.tasks_failed = 0
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        logger.info("Trading Scheduler initialized")
    
    # ============ TASK MANAGEMENT ============
    def register_task(self, name: str, function: Callable, 
                     interval: str, priority: TaskPriority = TaskPriority.MEDIUM,
                     *args, **kwargs) -> str:
        """
        Register a new scheduled task
        
        Args:
            name: Unique task name
            function: Function to execute
            interval: Execution interval
            priority: Task priority
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            Task ID
        """
        with self.lock:
            if name in self.tasks:
                logger.warning(f"Task '{name}' already exists. Updating...")
            
            task = ScheduledTask(
                name=name,
                function=function,
                interval=interval,
                args=args,
                kwargs=kwargs
            )
            
            self.tasks[name] = task
            
            # Schedule the task
            self._schedule_task(task)
            
            logger.info(f"Registered task: {name} (interval: {interval})")
            return name
    
    def remove_task(self, name: str):
        """Remove a scheduled task"""
        with self.lock:
            if name in self.tasks:
                del self.tasks[name]
                logger.info(f"Removed task: {name}")
    
    def enable_task(self, name: str, enabled: bool = True):
        """Enable or disable a task"""
        with self.lock:
            if name in self.tasks:
                self.tasks[name].enabled = enabled
                status = "enabled" if enabled else "disabled"
                logger.info(f"Task '{name}' {status}")
    
    def _schedule_task(self, task: ScheduledTask):
        """Schedule task based on interval"""
        interval = task.interval.lower()
        
        # Clear existing schedule for this task
        schedule.clear(task.name)
        
        if interval == 'minutely':
            schedule.every().minute.do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == '5m':
            schedule.every(5).minutes.do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == '15m':
            schedule.every(15).minutes.do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == 'hourly':
            schedule.every().hour.do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == '4h':
            schedule.every(4).hours.do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == 'daily':
            schedule.every().day.at("00:00").do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval == 'weekly':
            schedule.every().monday.at("00:00").do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
            
        elif interval.startswith('every_'):
            # Custom interval like 'every_30_minutes'
            parts = interval.split('_')
            if len(parts) == 3:
                value = int(parts[1])
                unit = parts[2]
                
                if unit.startswith('minute'):
                    schedule.every(value).minutes.do(
                        self._execute_task_wrapper, task.name
                    ).tag(task.name)
                elif unit.startswith('hour'):
                    schedule.every(value).hours.do(
                        self._execute_task_wrapper, task.name
                    ).tag(task.name)
        
        elif interval == 'market_open':
            # Special: Run at market open times (00:00 UTC)
            schedule.every().day.at("00:00").do(
                self._execute_task_wrapper, task.name
            ).tag(task.name)
        
        else:
            logger.warning(f"Unknown interval: {interval}. Task not scheduled.")
    
    # ============ TASK EXECUTION ============
    def _execute_task_wrapper(self, task_name: str):
        """Wrapper for task execution with error handling"""
        with self.lock:
            if task_name not in self.tasks:
                logger.error(f"Task '{task_name}' not found")
                return
            
            task = self.tasks[task_name]
            
            if not task.enabled:
                logger.debug(f"Task '{task_name}' is disabled, skipping")
                return
            
            task.last_run = datetime.now()
            
            # Execute task
            task_status = self._execute_task(task)
            
            # Update task history
            self._add_to_history(task_name, task_status)
            
            # Update statistics
            if task_status == TaskStatus.COMPLETED:
                self.tasks_executed += 1
            elif task_status == TaskStatus.FAILED:
                self.tasks_failed += 1
    
    def _execute_task(self, task: ScheduledTask) -> TaskStatus:
        """Execute a single task with retry logic"""
        logger.info(f"Executing task: {task.name}")
        
        for attempt in range(task.max_retries + 1):
            try:
                # Execute the task
                task.function(*task.args, **task.kwargs)
                
                # Update task info
                task.retry_count = 0
                task.next_run = self._calculate_next_run(task)
                
                logger.info(f"Task '{task.name}' completed successfully")
                return TaskStatus.COMPLETED
                
            except Exception as e:
                task.retry_count += 1
                
                if attempt < task.max_retries:
                    logger.warning(
                        f"Task '{task.name}' failed (attempt {attempt + 1}/{task.max_retries}): {e}"
                    )
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Task '{task.name}' failed after {task.max_retries} attempts: {e}")
                    task.next_run = datetime.now() + timedelta(minutes=5)  # Retry in 5 min
                    return TaskStatus.FAILED
        
        return TaskStatus.FAILED
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculate next run time for task"""
        interval = task.interval.lower()
        now = datetime.now()
        
        if interval == '5m':
            return now + timedelta(minutes=5)
        elif interval == '15m':
            return now + timedelta(minutes=15)
        elif interval == 'hourly':
            return now + timedelta(hours=1)
        elif interval == '4h':
            return now + timedelta(hours=4)
        elif interval == 'daily':
            return now + timedelta(days=1)
        elif interval == 'weekly':
            return now + timedelta(weeks=1)
        else:
            return now + timedelta(minutes=5)  # Default
    
    def _add_to_history(self, task_name: str, status: TaskStatus):
        """Add task execution to history"""
        history_entry = {
            'task_name': task_name,
            'timestamp': datetime.now(),
            'status': status.value,
            'retry_count': self.tasks[task_name].retry_count
        }
        
        self.task_history.append(history_entry)
        
        # Limit history size
        if len(self.task_history) > self.max_history:
            self.task_history = self.task_history[-self.max_history:]
    
    # ============ SCHEDULER CONTROL ============
    def start(self, background: bool = True):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        if background:
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                name="TradingScheduler",
                daemon=True
            )
            self.scheduler_thread.start()
            logger.info("Scheduler started in background thread")
        else:
            logger.info("Scheduler started in foreground")
            self._run_scheduler()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                # Run pending tasks
                schedule.run_pending()
                
                # Sleep for 1 second
                time.sleep(1)
                
                # Print status every minute
                if int(time.time()) % 60 == 0:
                    self._print_status()
                    
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info("Scheduler loop ended")
    
    def run_once(self, task_name: str):
        """Run a task immediately once"""
        if task_name in self.tasks:
            logger.info(f"Running task '{task_name}' once")
            self._execute_task_wrapper(task_name)
        else:
            logger.error(f"Task '{task_name}' not found")
    
    def run_all_now(self):
        """Run all enabled tasks once"""
        logger.info("Running all tasks now")
        with self.lock:
            for task_name in self.tasks:
                if self.tasks[task_name].enabled:
                    self.run_once(task_name)
    
    # ============ STATISTICS & MONITORING ============
    def _print_status(self):
        """Print scheduler status"""
        pending = len(schedule.get_jobs())
        with self.lock:
            enabled_tasks = sum(1 for t in self.tasks.values() if t.enabled)
            
            logger.info(
                f"Scheduler Status - "
                f"Tasks: {len(self.tasks)} total, {enabled_tasks} enabled, "
                f"{pending} pending, "
                f"Executed: {self.tasks_executed}, Failed: {self.tasks_failed}"
            )
    
    def get_status(self) -> Dict:
        """Get detailed scheduler status"""
        with self.lock:
            tasks_info = []
            for name, task in self.tasks.items():
                tasks_info.append({
                    'name': name,
                    'enabled': task.enabled,
                    'interval': task.interval,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'retry_count': task.retry_count
                })
            
            return {
                'running': self.running,
                'total_tasks': len(self.tasks),
                'enabled_tasks': sum(1 for t in self.tasks.values() if t.enabled),
                'tasks_executed': self.tasks_executed,
                'tasks_failed': self.tasks_failed,
                'tasks': tasks_info,
                'pending_jobs': len(schedule.get_jobs())
            }
    
    def get_task_history(self, task_name: str = None, limit: int = 50) -> List:
        """Get task execution history"""
        if task_name:
            history = [h for h in self.task_history if h['task_name'] == task_name]
        else:
            history = self.task_history
        
        return history[-limit:]
    
    # ============ PRESET TASKS ============
    def setup_default_tasks(self):
        """Setup default trading tasks"""
        logger.info("Setting up default trading tasks")
        
        # 1. Data Collection Tasks
        self.register_task(
            name="collect_btc_eth_1h",
            function=self._collect_major_pairs,
            interval="hourly",
            priority=TaskPriority.HIGH,
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            interval_str="1h",
            limit=500
        )
        
        self.register_task(
            name="collect_all_majors_4h",
            function=self._collect_major_pairs,
            interval="4h",
            priority=TaskPriority.MEDIUM,
            symbols=config.TRADING.default_symbols,
            interval_str="4h",
            limit=200
        )
        
        # 2. Market Analysis Tasks
        self.register_task(
            name="analyze_market_daily",
            function=self._analyze_market,
            interval="daily",
            priority=TaskPriority.HIGH
        )
        
        self.register_task(
            name="update_technical_indicators",
            function=self._update_indicators,
            interval="15m",
            priority=TaskPriority.MEDIUM
        )
        
        # 3. Risk Management Tasks
        self.register_task(
            name="check_risk_exposure",
            function=self._check_risk,
            interval="5m",
            priority=TaskPriority.CRITICAL
        )
        
        self.register_task(
            name="generate_daily_report",
            function=self._generate_report,
            interval="daily",
            priority=TaskPriority.MEDIUM
        )
        
        # 4. Maintenance Tasks
        self.register_task(
            name="cleanup_old_data",
            function=self._cleanup_data,
            interval="daily",
            priority=TaskPriority.LOW
        )
        
        self.register_task(
            name="backup_database",
            function=self._backup_database,
            interval="weekly",
            priority=TaskPriority.MEDIUM
        )
        
        logger.info(f"Registered {len(self.tasks)} default tasks")
    
    # ============ TASK FUNCTIONS ============
    def _collect_major_pairs(self, symbols: List[str], interval_str: str, limit: int):
        """Task: Collect data for major pairs"""
        logger.info(f"Collecting {len(symbols)} pairs ({interval_str})")
        
        for exchange_name in ["binance", "bybit"]:
            for symbol in symbols:
                try:
                    if exchange_name == "binance":
                        data = self.collector.get_binance_klines(
                            symbol=symbol,
                            interval=interval_str,
                            limit=limit
                        )
                    else:
                        data = self.collector.get_bybit_klines(
                            symbol=symbol,
                            interval=interval_str,
                            limit=limit
                        )
                    
                    if data is not None:
                        logger.debug(f"Collected {symbol} from {exchange_name}: {len(data)} candles")
                        
                except Exception as e:
                    logger.error(f"Error collecting {symbol} from {exchange_name}: {e}")
                
                time.sleep(0.5)  # Rate limiting
        
        logger.info("Major pairs collection completed")
    
    def _analyze_market(self):
        """Task: Perform market analysis"""
        logger.info("Performing market analysis...")
        
        # Collect latest data
        btc_data = self.collector.get_binance_klines("BTCUSDT", "1d", 30)
        
        if btc_data is not None:
            # Calculate metrics
            latest_price = btc_data.iloc[-1]['close']
            price_change = btc_data['close'].pct_change().iloc[-1] * 100
            
            logger.info(f"BTC Analysis - Price: ${latest_price:.2f}, Change: {price_change:.2f}%")
            
            # Check for significant movements
            if abs(price_change) > 5:
                logger.warning(f"Significant BTC movement: {price_change:.2f}%")
                # Trigger alert
                self._send_alert(f"BTC moved {price_change:.2f}%")
        
        logger.info("Market analysis completed")
    
    def _update_indicators(self):
        """Task: Update technical indicators"""
        logger.debug("Updating technical indicators...")
        # Implementation for indicator updates
    
    def _check_risk(self):
        """Task: Check risk exposure"""
        logger.debug("Checking risk exposure...")
        # Implementation for risk checks
    
    def _generate_report(self):
        """Task: Generate daily report"""
        logger.info("Generating daily report...")
        
        report = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'tasks_executed': self.tasks_executed,
            'tasks_failed': self.tasks_failed,
            'status': self.get_status()
        }
        
        # Save report
        report_file = config.DATA_DIR / f"reports/daily_{datetime.now().strftime('%Y%m%d')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Daily report saved to {report_file}")
    
    def _cleanup_data(self):
        """Task: Cleanup old data"""
        logger.info("Cleaning up old data...")
        
        data_dir = config.DATA_DIR
        cutoff_time = datetime.now() - timedelta(days=30)
        
        for file in data_dir.rglob("*.csv"):
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            if file_time < cutoff_time:
                file.unlink()
                logger.debug(f"Removed old file: {file}")
        
        logger.info("Data cleanup completed")
    
    def _backup_database(self):
        """Task: Backup database"""
        logger.info("Backing up database...")
        # Implementation for database backup
    
    def _send_alert(self, message: str):
        """Send alert notification"""
        logger.warning(f"ALERT: {message}")
        # Implement alert sending (Slack, Telegram, Email, etc.)
    
    # ============ TRADING PLAN GENERATOR INITIALIZATION ============
    def _init_trading_plan_generator(self):
        """Initialize trading plan generator lazily"""
        if self.trading_plan_generator is None:
            try:
                from deepseek_integration import TradingPlanGenerator, AnalysisRequest
                self._trading_plan_generator_class = TradingPlanGenerator
                self._analysis_request_class = AnalysisRequest
                self.trading_plan_generator = TradingPlanGenerator()
                logger.debug("Trading plan generator initialized")
            except ImportError as e:
                logger.error(f"Failed to import trading plan generator: {e}")
                raise
    
    # ============ TRADING PLAN TASKS SETUP ============
    def setup_trading_plan_tasks(self):
        """Setup automatic trading plan generation tasks"""
        logger.info("Setting up trading plan generation tasks...")
        
        # 1. Daily Trading Plans (4h timeframe)
        self.register_task(
            name="generate_daily_trading_plans_4h",
            function=self._generate_daily_trading_plans,
            interval="daily",
            priority=TaskPriority.HIGH,
            timeframe="4h",
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        )
        
        # 2. Intraday Trading Plans (1h timeframe)
        self.register_task(
            name="generate_intraday_trading_plans_1h",
            function=self._generate_intraday_trading_plans,
            interval="4h",  # Every 4 hours
            priority=TaskPriority.MEDIUM,
            timeframe="1h",
            symbols=["BTCUSDT", "ETHUSDT"]
        )
        
        # 3. Weekly Analysis (1d timeframe)
        self.register_task(
            name="generate_weekly_analysis",
            function=self._generate_weekly_analysis,
            interval="weekly",
            priority=TaskPriority.MEDIUM,
            timeframe="1d"
        )
        
        # 4. Market Open Plans (00:00 UTC)
        self.register_task(
            name="generate_market_open_plans",
            function=self._generate_market_open_plans,
            interval="market_open",
            priority=TaskPriority.HIGH
        )
        
        logger.info("Trading plan tasks registered")
    
    # ============ TRADING PLAN GENERATION FUNCTIONS ============
    def _generate_daily_trading_plans(self, timeframe="4h", symbols=None):
        """Generate daily trading plans for major pairs"""
        self._init_trading_plan_generator()
        
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        
        logger.info(f"Generating daily trading plans for {len(symbols)} symbols...")
        
        successful_plans = 0
        failed_plans = []
        
        for symbol in symbols:
            try:
                request = self._analysis_request_class(
                    symbol=symbol,
                    timeframe=timeframe,
                    data_points=200,
                    analysis_type="trading_plan",
                    risk_profile="moderate"
                )
                
                plan = self.trading_plan_generator.generate_trading_plan(request)
                
                if plan.entries:  # Only save if we have valid entries
                    # Save plan
                    self.trading_plan_generator.save_trading_plan(plan)
                    
                    # Also export to CSV
                    self.trading_plan_generator.export_to_csv(plan)
                    
                    # Print summary
                    logger.info(f"  ✅ {symbol}: {plan.overall_signal.signal_type} "
                              f"(Confidence: {plan.overall_signal.confidence:.1%})")
                    
                    successful_plans += 1
                    
                    # Send alert for high confidence signals
                    if plan.overall_signal.confidence > 0.7:
                        self._alert_high_confidence_signal(plan)
                        
                else:
                    logger.warning(f"  ⚠ {symbol}: No valid entries generated")
                    failed_plans.append(symbol)
                    
            except Exception as e:
                logger.error(f"  ❌ {symbol}: Failed to generate plan - {e}")
                failed_plans.append(symbol)
            
            # Rate limiting between symbols
            time.sleep(2)
        
        # Log summary
        logger.info(f"Daily trading plans generated: {successful_plans} successful, "
                   f"{len(failed_plans)} failed")
        
        # Save summary report
        self._save_generation_report(successful_plans, failed_plans, timeframe)
        
        return successful_plans
    
    def _generate_intraday_trading_plans(self, timeframe="1h", symbols=None):
        """Generate intraday trading plans"""
        self._init_trading_plan_generator()
        
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT"]
        
        logger.info(f"Generating intraday trading plans ({timeframe})...")
        
        plans = []
        for symbol in symbols:
            try:
                request = self._analysis_request_class(
                    symbol=symbol,
                    timeframe=timeframe,
                    data_points=100,
                    analysis_type="trading_plan",
                    risk_profile="aggressive"  # More aggressive for intraday
                )
                
                plan = self.trading_plan_generator.generate_trading_plan(request)
                plans.append(plan)
                
                # Save with intraday prefix
                filename = f"intraday_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                self.trading_plan_generator.save_trading_plan(plan, filename)
                
                logger.info(f"  ✅ {symbol}: {plan.overall_signal.signal_type}")
                
            except Exception as e:
                logger.error(f"  ❌ {symbol}: Failed - {e}")
        
        return plans
    
    def _generate_weekly_analysis(self, timeframe="1d"):
        """Generate weekly swing trading analysis"""
        self._init_trading_plan_generator()
        
        logger.info("Generating weekly swing trading analysis...")
        
        # Analyze top 10 coins
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
                  "XRPUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT"]
        
        weekly_report = {
            "generated_at": datetime.now().isoformat(),
            "timeframe": timeframe,
            "analysis": []
        }
        
        for symbol in symbols:
            try:
                request = self._analysis_request_class(
                    symbol=symbol,
                    timeframe=timeframe,
                    data_points=50,  # 50 days for weekly analysis
                    analysis_type="trading_plan",
                    risk_profile="conservative"  # Conservative for swing trading
                )
                
                plan = self.trading_plan_generator.generate_trading_plan(request)
                
                weekly_report["analysis"].append({
                    "symbol": symbol,
                    "signal": plan.overall_signal.signal_type,
                    "confidence": plan.overall_signal.confidence,
                    "trend": plan.trend,
                    "risk_reward": plan.risk_reward_ratio
                })
                
                logger.info(f"  📊 {symbol}: {plan.trend} - {plan.overall_signal.signal_type}")
                
            except Exception as e:
                logger.error(f"  ❌ {symbol}: Failed - {e}")
                weekly_report["analysis"].append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        # Save weekly report
        report_file = config.DATA_DIR / f"reports/weekly_{datetime.now().strftime('%Y%m%d')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(weekly_report, f, indent=2)
        
        logger.info(f"Weekly report saved to {report_file}")
        return weekly_report
    
    def _generate_market_open_plans(self):
        """Generate trading plans at market open (00:00 UTC)"""
        self._init_trading_plan_generator()
        
        logger.info("Generating market open trading plans...")
        
        # Focus on majors for market open
        symbols = ["BTCUSDT", "ETHUSDT"]
        
        for symbol in symbols:
            try:
                # Generate multiple timeframe analysis
                timeframes = ["15m", "1h", "4h"]
                
                for tf in timeframes:
                    request = self.AnalysisRequest(
                        symbol=symbol,
                        timeframe=tf,
                        data_points=100,
                        analysis_type="trading_plan",
                        risk_profile="moderate"
                    )
                    
                    plan = self.trading_plan_generator.generate_trading_plan(request)
                    
                    # Save with market open prefix
                    filename = f"market_open_{symbol}_{tf}_{datetime.now().strftime('%Y%m%d')}.json"
                    self.trading_plan_generator.save_trading_plan(plan, filename)
                    
                    logger.info(f"  ✅ {symbol} ({tf}): {plan.overall_signal.signal_type}")
            
            except Exception as e:
                logger.error(f"  ❌ {symbol}: Failed - {e}")
    
    # ============ TRADING PLAN HELPER FUNCTIONS ============
    def _alert_high_confidence_signal(self, plan):
        """Send alert for high confidence signals"""
        try:
            if plan.overall_signal.confidence > 0.7:
                alert_message = (
                    f"🚨 HIGH CONFIDENCE SIGNAL\n"
                    f"Symbol: {plan.symbol}\n"
                    f"Timeframe: {plan.timeframe}\n"
                    f"Signal: {plan.overall_signal.signal_type}\n"
                    f"Confidence: {plan.overall_signal.confidence:.1%}\n"
                    f"Trend: {plan.trend}\n"
                    f"Risk/Reward: 1:{plan.risk_reward_ratio:.1f}"
                )
                
                logger.info(f"High confidence signal detected: {plan.symbol}")
                
                # Send to alert system (Slack/Telegram/Email)
                if hasattr(config, 'ALERTS') and config.ALERTS.enable_slack:
                    self._send_slack_alert(alert_message)
                
                if hasattr(config, 'ALERTS') and config.ALERTS.enable_telegram:
                    self._send_telegram_alert(alert_message)
        except Exception as e:
            logger.error(f"Error sending high confidence alert: {e}")
    
    def _save_generation_report(self, successful: int, failed: List[str], timeframe: str):
        """Save generation report"""
        report = {
            "date": datetime.now().isoformat(),
            "timeframe": timeframe,
            "successful": successful,
            "failed": failed,
            "failed_count": len(failed)
        }
        
        report_file = config.DATA_DIR / f"reports/generation_{datetime.now().strftime('%Y%m%d')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _send_slack_alert(self, message: str):
        """Send alert to Slack"""
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
            response = client.chat_postMessage(
                channel=os.getenv("SLACK_CHANNEL", "#trading-alerts"),
                text=message
            )
            logger.debug(f"Slack alert sent: {response}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_telegram_alert(self, message: str):
        """Send alert to Telegram"""
        try:
            import telebot
            
            bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            
            bot.send_message(chat_id, message)
            logger.debug("Telegram alert sent")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

# ============ ADVANCED SCHEDULER WITH APScheduler ============
class AdvancedTradingScheduler:
    """
    Advanced scheduler using APScheduler for more features
    """
    
    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.trigger.interval import IntervalTrigger
        
        self.scheduler = BackgroundScheduler(
            jobstores={
                'default': {
                    'type': 'sqlalchemy',
                    'url': f"sqlite:///{config.DATA_DIR}/jobs.sqlite"
                }
            },
            executors={
                'default': {
                    'type': 'threadpool',
                    'max_workers': 20
                }
            },
            job_defaults={
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 60
            }
        )
        
        self.jobs = {}
        logger.info("Advanced Scheduler initialized")
    
    def add_cron_job(self, name: str, function: Callable, 
                    cron_expression: str, *args, **kwargs):
        """Add a cron job"""
        trigger = CronTrigger.from_crontab(cron_expression)
        
        job = self.scheduler.add_job(
            func=function,
            trigger=trigger,
            name=name,
            args=args,
            kwargs=kwargs,
            id=name,
            replace_existing=True
        )
        
        self.jobs[name] = job
        logger.info(f"Added cron job: {name} ({cron_expression})")
    
    def add_interval_job(self, name: str, function: Callable,
                        minutes: int = None, hours: int = None,
                        *args, **kwargs):
        """Add an interval job"""
        if minutes:
            trigger = IntervalTrigger(minutes=minutes)
        elif hours:
            trigger = IntervalTrigger(hours=hours)
        else:
            raise ValueError("Must specify minutes or hours")
        
        job = self.scheduler.add_job(
            func=function,
            trigger=trigger,
            name=name,
            args=args,
            kwargs=kwargs,
            id=name,
            replace_existing=True
        )
        
        self.jobs[name] = job
        logger.info(f"Added interval job: {name} (every {minutes or hours} {'minutes' if minutes else 'hours'})")
    
    def start(self):
        """Start the advanced scheduler"""
        self.scheduler.start()
        logger.info("Advanced scheduler started")
    
    def stop(self):
        """Stop the advanced scheduler"""
        self.scheduler.shutdown()
        logger.info("Advanced scheduler stopped")

# ============ EXAMPLE USAGE ============
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("TRADING PLAN SCHEDULER")
    print("=" * 60)
    
    # Create scheduler
    scheduler = TradingScheduler()
    
    # Setup ALL tasks
    print("\n1. Setting up all tasks...")
    scheduler.setup_default_tasks()           # Data collection tasks
    scheduler.setup_trading_plan_tasks()      # Trading plan generation tasks
    
    # Print status
    status = scheduler.get_status()
    print(f"\n📋 Task Status:")
    print(f"  Total Tasks: {status['total_tasks']}")
    print(f"  Trading Plan Tasks: {sum(1 for t in status['tasks'] if 'plan' in t['name'])}")
    
    # Run one trading plan generation immediately for demo
    print("\n2. Generating sample trading plan...")
    scheduler.run_once("generate_daily_trading_plans_4h")
    
    # Start scheduler
    print("\n3. Starting scheduler in background...")
    scheduler.start(background=True)
    
    try:
        print("\n⏰ Scheduler running with trading plan generation!")
        print("\nAutomatic schedules:")
        print("  • Daily Plans (4h): 00:00 UTC")
        print("  • Intraday Plans (1h): Every 4 hours")
        print("  • Weekly Analysis: Monday 00:00 UTC")
        print("  • Market Open Plans: 00:00 UTC daily")
        print("\nCheck 'data/trading_plans/' folder for generated plans")
        
        # Keep running
        while True:
            time.sleep(60)
            
            # Print status every 5 minutes
            if int(time.time()) % 300 == 0:
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] Scheduler active...")
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping scheduler...")
        scheduler.stop()
        print("✅ Scheduler stopped")
    
    print("\n" + "=" * 60)