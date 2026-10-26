import os
import sys
import shutil
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Anchored to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BACKEND_DIR / "outreachiq.db"
BACKUP_DIR = BACKEND_DIR / "backups"


def backup_database():
    """Performs an online, zero-downtime, transaction-consistent SQLite backup."""
    if not DB_FILE.exists():
        print(f"Error: Database file {DB_FILE} does not exist.", file=sys.stderr)
        return False

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"outreachiq_backup_{timestamp}.db"

    print(f"Initiating SQLite consistent backup to {backup_file}...")
    source_con = sqlite3.connect(DB_FILE)
    dest_con = sqlite3.connect(backup_file)

    try:
        with dest_con:
            source_con.backup(dest_con, pages=50)
        dest_con.close()
        source_con.close()

        # Run integrity check on backup copy
        verify_con = sqlite3.connect(backup_file)
        result = verify_con.execute("PRAGMA integrity_check").fetchone()
        verify_con.close()

        if result and result[0] == "ok":
            print(f"Backup completed and verified successfully: {backup_file} ({backup_file.stat().st_size} bytes)")
            return backup_file
        else:
            print(f"Integrity check failed on backup: {result}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Backup failed: {e}", file=sys.stderr)
        return False


def restore_database(backup_path: Path):
    """Restores database from a verified backup file after safety check."""
    if not backup_path.exists():
        print(f"Error: Backup file {backup_path} not found.", file=sys.stderr)
        return False

    # Verify backup integrity first
    verify_con = sqlite3.connect(backup_path)
    result = verify_con.execute("PRAGMA integrity_check").fetchone()
    verify_con.close()
    if not result or result[0] != "ok":
        print(f"Aborting restore: Backup file {backup_path} is corrupted ({result}).", file=sys.stderr)
        return False

    # Create safety snapshot of current db if it exists
    if DB_FILE.exists():
        safety_path = BACKUP_DIR / f"pre_restore_safety_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB_FILE, safety_path)
        print(f"Created pre-restore safety snapshot at {safety_path}")

    shutil.copy2(backup_path, DB_FILE)
    print(f"Successfully restored database from {backup_path} to {DB_FILE}!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OutReachIQ Database Backup and Restore Utility")
    parser.add_argument("--backup", action="store_true", help="Perform online database backup")
    parser.add_argument("--restore", type=str, help="Restore database from specified backup file path")

    args = parser.parse_args()
    if args.backup:
        backup_database()
    elif args.restore:
        restore_database(Path(args.restore))
    else:
        parser.print_help()
