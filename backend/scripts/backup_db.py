#!/usr/bin/env python3
"""
Project Manager System - Database Backup Script

Usage:
    python scripts/backup_db.py                    # backup to ./backups/
    python scripts/backup_db.py --output /path/to/save  # custom output dir
    python scripts/backup_db.py --db ./project_manager.db  # custom db path

Scheduled via cron / Task Scheduler:
    # Daily backup at 3 AM:
    0 3 * * * cd /app && python scripts/backup_db.py
"""
import argparse
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_default_db_path() -> Path:
    """Try to determine DB path from common locations."""
    candidates = [
        Path("./project_manager.db"),
        Path("./data/project_manager.db"),
        Path("../data/project_manager.db"),
        Path("/data/project_manager.db"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return Path("./project_manager.db")


def clean_old_backups(backup_dir: Path, keep_days: int = 30):
    """Remove backups older than keep_days."""
    now = datetime.now()
    cutoff = now - timedelta(days=keep_days)
    for f in backup_dir.glob("project_manager_*.db.gz"):
        if f.stat().st_mtime < cutoff.timestamp():
            f.unlink()
            print(f"  [cleanup] removed old backup: {f.name}")


def backup_database(db_path: Path, output_dir: Path, compress: bool = True):
    """Create a database backup."""
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"project_manager_{timestamp}.db"
    backup_path = output_dir / backup_name

    print(f"Backing up: {db_path}")
    print(f"       to: {backup_path}")

    shutil.copy2(db_path, backup_path)
    file_size = backup_path.stat().st_size

    if compress:
        import gzip
        gz_path = output_dir / f"{backup_name}.gz"
        with open(backup_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                f_out.writelines(f_in)
        backup_path.unlink()
        gz_size = gz_path.stat().st_size
        print(f"Compressed: {gz_path} ({gz_size:,} bytes)")
    else:
        print(f"Done: {backup_path} ({file_size:,} bytes)")

    # Clean old backups
    clean_old_backups(output_dir)
    print("Backup completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Backup Project Manager database")
    parser.add_argument(
        "--db",
        type=Path,
        help="Path to SQLite database file (auto-detected if not specified)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./backups"),
        help="Output directory for backups (default: ./backups)",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Skip gzip compression",
    )
    args = parser.parse_args()

    db_path = args.db or get_default_db_path()
    backup_database(db_path.resolve(), args.output.resolve(), compress=not args.no_compress)


if __name__ == "__main__":
    main()
