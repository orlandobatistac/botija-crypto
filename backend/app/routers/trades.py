"""
Trade router for Kraken AI Trading Bot
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/trades",
    tags=["trades"]
)

@router.get("/", response_model=list[schemas.Trade])
async def get_trades(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get all trades with pagination"""
    trades = db.query(models.Trade).offset(skip).limit(limit).all()
    return trades

@router.get("/{trade_id}", response_model=schemas.Trade)
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get a specific trade by ID"""
    trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not trade:
        return {"error": "Trade not found"}
    return trade

@router.post("/", response_model=schemas.Trade)
async def create_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    """Create a new trade record"""
    db_trade = models.Trade(**trade.dict())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade
