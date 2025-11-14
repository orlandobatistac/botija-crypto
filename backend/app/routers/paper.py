"""
Paper trading routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..services.modes.paper import PaperTradingEngine

router = APIRouter(
    prefix="/api/v1/paper",
    tags=["paper trading"]
)

# Initialize paper engine
paper_engine = PaperTradingEngine()

@router.get("/wallet")
async def get_wallet():
    """Get current paper wallet status"""
    return paper_engine.get_wallet_summary()

@router.get("/trades")
async def get_paper_trades(limit: int = 20):
    """Get recent simulated trades"""
    try:
        trades = []
        import csv
        from pathlib import Path
        
        trades_path = Path(__file__).parent.parent.parent / 'data' / 'paper_trades.csv'
        
        if trades_path.exists():
            with open(trades_path, 'r') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= limit:
                        break
                    trades.append(row)
            
            # Reverse to show most recent first
            trades.reverse()
        
        return {"trades": trades, "total": len(trades)}
    except Exception as e:
        return {"error": str(e)}

@router.post("/reset")
async def reset_wallet(initial_usd: float = 1000.0):
    """Reset paper wallet to initial state"""
    try:
        paper_engine.reset_wallet(initial_usd)
        return {
            "message": f"Paper wallet reset to ${initial_usd:.2f}",
            "wallet": paper_engine.get_wallet_summary()
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/simulate-buy")
async def simulate_buy(price: float, usd_amount: float):
    """Manually simulate a buy order"""
    try:
        success, message = paper_engine.buy(price, usd_amount)
        return {
            "success": success,
            "message": message,
            "wallet": paper_engine.get_wallet_summary() if success else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/simulate-sell")
async def simulate_sell(price: float, btc_amount: float):
    """Manually simulate a sell order"""
    try:
        success, message = paper_engine.sell(price, btc_amount)
        return {
            "success": success,
            "message": message,
            "wallet": paper_engine.get_wallet_summary() if success else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/stats")
async def get_paper_stats():
    """Get paper trading statistics"""
    try:
        wallet = paper_engine.get_wallet_summary()
        
        # Calculate stats
        total_trades = 0
        buy_trades = 0
        sell_trades = 0
        
        import csv
        from pathlib import Path
        
        trades_path = Path(__file__).parent.parent.parent / 'data' / 'paper_trades.csv'
        
        if trades_path.exists():
            with open(trades_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_trades += 1
                    if row.get('type') == 'BUY':
                        buy_trades += 1
                    elif row.get('type') == 'SELL':
                        sell_trades += 1
        
        return {
            "wallet": wallet,
            "stats": {
                "total_trades": total_trades,
                "buy_trades": buy_trades,
                "sell_trades": sell_trades,
                "position_open": wallet['btc_balance'] > 0
            }
        }
    except Exception as e:
        return {"error": str(e)}
