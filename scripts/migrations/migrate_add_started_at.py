#!/usr/bin/env python3
"""
Migration: Add started_at column to bot_status table
Run: python scripts/migrate_add_started_at.py
"""

import sqlite3
import os
from datetime import datetime, timezone

def get_db_path():
    """Get database path from environment or default"""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///backend/botija-crypto.db')
    if db_url.startswith('sqlite:///'):
        return db_url.replace('sqlite:///', '')
    return 'backend/botija-crypto.db'

def migrate():
    db_path = get_db_path()
    print(f"📦 Migrating database: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(bot_status)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'started_at' in columns:
            print("✅ Column 'started_at' already exists")
        else:
            # Add column
            cursor.execute("ALTER TABLE bot_status ADD COLUMN started_at DATETIME")
            print("✅ Added column 'started_at' to bot_status")

            # Set initial value to now for existing rows
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE bot_status SET started_at = ?", (now,))
            print(f"✅ Set started_at to {now} for existing rows")

        conn.commit()
        print("✅ Migration completed successfully")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
