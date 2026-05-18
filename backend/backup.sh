#!/bin/bash
# SQLite 数据库备份脚本
# 用法: ./backup.sh [KEEP_DAYS]
# KEEP_DAYS: 保留天数，默认 7

set -e

BACKUP_DIR="/data/backups"
DB_FILE="/data/project_manager.db"
KEEP_DAYS="${1:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 一致性备份
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/pm_$TIMESTAMP.db'"

# 压缩
gzip "$BACKUP_DIR/pm_$TIMESTAMP.db"

# 清理旧备份
find "$BACKUP_DIR" -name "pm_*.db.gz" -mtime +$KEEP_DAYS -delete

echo "[$(date)] Backup completed: pm_$TIMESTAMP.db.gz (auto-clean >${KEEP_DAYS}d)"
