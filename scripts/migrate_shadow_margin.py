"""
Migration script: Add Shadow Margin columns to trades table
Run this once to update existing database schema
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "backend" / "data" / "trading_bot.db"

def migrate():
    print(f"📦 Migrating database: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get existing columns in trades table
    cursor.execute("PRAGMA table_info(trades)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"   Existing columns: {len(existing_columns)}")
    
    # New columns for Shadow Margin
    new_trade_columns = [
        ("ai_regime", "TEXT"),
        ("leverage_used", "REAL DEFAULT 1.0"),
        ("shadow_leverage", "REAL DEFAULT 1.0"),
        ("real_profit_usd", "REAL"),
        ("shadow_profit_usd", "REAL"),
    ]
    
    for col_name, col_type in new_trade_columns:
        if col_name not in existing_columns:
            sql = f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}"
            cursor.execute(sql)
            print(f"   ✅ Added trades.{col_name}")
        else:
            print(f"   ⏭️  trades.{col_name} already exists")
    
    # Get existing columns in trading_cycles table
    cursor.execute("PRAGMA table_info(trading_cycles)")
    existing_cycle_columns = {row[1] for row in cursor.fetchall()}
    
    # New columns for TradingCycle
    new_cycle_columns = [
        ("ai_regime", "TEXT"),
        ("leverage_multiplier", "REAL"),
        ("is_winter_mode", "INTEGER"),
        ("ema200", "REAL"),
    ]
    
    for col_name, col_type in new_cycle_columns:
        if col_name not in existing_cycle_columns:
            sql = f"ALTER TABLE trading_cycles ADD COLUMN {col_name} {col_type}"
            cursor.execute(sql)
            print(f"   ✅ Added trading_cycles.{col_name}")
        else:
            print(f"   ⏭️  trading_cycles.{col_name} already exists")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    migrate()
