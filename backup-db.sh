#!/bin/bash

# ============================================
# Database Backup Script
# Crypto Trading Analyzer
# ============================================

# Configuration
USERNAME=$(whoami)
DB_DIR="/var/lib/crypto-trading-analyzer"
BACKUP_DIR="/home/$USERNAME/backups"
RETENTION_DAYS=7

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Generate timestamp
DATE=$(date +%Y%m%d_%H%M%S)

# Database file
DB_FILE="$DB_DIR/trading_bot.db"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file not found at $DB_FILE"
    echo "Checking alternative location..."
    DB_FILE="/opt/crypto-trading-analyzer/data/trading_bot.db"
    if [ ! -f "$DB_FILE" ]; then
        echo "Error: Database file not found!"
        exit 1
    fi
fi

# Backup filename
BACKUP_FILE="$BACKUP_DIR/trading_bot_$DATE.db"

# Copy database
echo "Starting backup at $(date)"
cp $DB_FILE $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE
BACKUP_FILE="$BACKUP_FILE.gz"

# Get file size
SIZE=$(du -h $BACKUP_FILE | cut -f1)

echo "Backup completed: $BACKUP_FILE ($SIZE)"

# Remove old backups (older than RETENTION_DAYS)
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "trading_bot_*.db.gz" -mtime +$RETENTION_DAYS -delete

# List current backups
echo ""
echo "Current backups:"
ls -lh $BACKUP_DIR/trading_bot_*.db.gz 2>/dev/null | awk '{print $9, $5}'

echo ""
echo "Backup process completed at $(date)"
