"""
Migration script to add new indicator columns to trading_cycles table
Run with: python scripts/migrate_add_new_indicators.py
"""

import sqlite3
import os

def migrate():
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'trading_bot.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # New columns to add
    new_columns = [
        ("macd", "REAL"),
        ("macd_signal", "REAL"),
        ("macd_hist", "REAL"),
        ("bb_upper", "REAL"),
        ("bb_lower", "REAL"),
        ("bb_position", "REAL"),
        ("tech_score", "INTEGER"),
    ]

    # Check existing columns
    cursor.execute("PRAGMA table_info(trading_cycles)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # Add missing columns
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE trading_cycles ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Column {col_name} might already exist: {e}")
        else:
            print(f"⏭️ Column {col_name} already exists")

    conn.commit()
    conn.close()
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    migrate()
