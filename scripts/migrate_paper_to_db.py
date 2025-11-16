#!/usr/bin/env python3
"""
Migrate paper trading data from CSV/JSON to SQLite database
Run this once to preserve historical paper trading data
"""

import sys
import json
import csv
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal, engine
from app.models import Base, Trade, BotStatus
import uuid

def migrate_wallet():
    """Migrate paper wallet from JSON to BotStatus table"""
    wallet_path = backend_path / 'data' / 'paper_wallet.json'
    
    if not wallet_path.exists():
        print(f"⚠️  No wallet file found at {wallet_path}")
        return
    
    try:
        with open(wallet_path, 'r') as f:
            wallet = json.load(f)
        
        db = SessionLocal()
        try:
            # Check if PAPER status already exists
            status = db.query(BotStatus).filter(BotStatus.trading_mode == "PAPER").first()
            
            if status:
                print("⚠️  PAPER BotStatus already exists, skipping wallet migration")
            else:
                status = BotStatus(
                    is_running=True,
                    trading_mode="PAPER",
                    btc_balance=wallet.get('btc_balance', 0.0),
                    usd_balance=wallet.get('usd_balance', 1000.0),
                    last_buy_price=wallet.get('last_buy_price'),
                    trailing_stop_price=wallet.get('trailing_stop')
                )
                db.add(status)
                db.commit()
                print(f"✅ Wallet migrated: ${status.usd_balance:.2f} USD, {status.btc_balance:.8f} BTC")
        finally:
            db.close()
    
    except Exception as e:
        print(f"❌ Error migrating wallet: {e}")

def migrate_trades():
    """Migrate paper trades from CSV to Trade table"""
    trades_path = backend_path / 'data' / 'paper_trades.csv'
    
    if not trades_path.exists():
        print(f"⚠️  No trades file found at {trades_path}")
        return
    
    try:
        db = SessionLocal()
        migrated = 0
        
        with open(trades_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Skip if trade already exists (by timestamp and type)
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    
                    trade = Trade(
                        trade_id=f"PAPER-{uuid.uuid4().hex[:8]}",
                        order_type=row['type'].upper(),
                        symbol="BTCUSD",
                        entry_price=float(row['price']),
                        quantity=float(row['volume']),
                        status="CLOSED",
                        trading_mode="PAPER",
                        created_at=timestamp
                    )
                    
                    db.add(trade)
                    migrated += 1
                
                except Exception as e:
                    print(f"⚠️  Skipped row: {e}")
                    continue
        
        db.commit()
        print(f"✅ Migrated {migrated} trades from CSV to database")
        db.close()
    
    except Exception as e:
        print(f"❌ Error migrating trades: {e}")

def main():
    print("🔄 Starting Paper Trading data migration...")
    print()
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Migrate wallet
    print("📊 Migrating wallet...")
    migrate_wallet()
    print()
    
    # Migrate trades
    print("📈 Migrating trades...")
    migrate_trades()
    print()
    
    print("✅ Migration complete!")
    print()
    print("💡 Old CSV/JSON files are still in backend/data/ - you can delete them manually if migration was successful")

if __name__ == "__main__":
    main()
