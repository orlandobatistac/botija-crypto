"""
Bot router for Kraken AI Trading Bot
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/bot",
    tags=["bot"]
)

@router.get("/status", response_model=schemas.BotStatus)
async def get_bot_status(db: Session = Depends(get_db)):
    """Get current bot status"""
    status = db.query(models.BotStatus).order_by(models.BotStatus.id.desc()).first()
    if not status:
        return {"error": "No status found"}
    return status

@router.post("/status", response_model=schemas.BotStatus)
async def update_bot_status(status: schemas.BotStatusCreate, db: Session = Depends(get_db)):
    """Update bot status"""
    db_status = models.BotStatus(**status.dict())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.get("/signals", response_model=list[schemas.Signal])
async def get_recent_signals(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent trading signals"""
    signals = db.query(models.Signal).order_by(models.Signal.timestamp.desc()).limit(limit).all()
    return signals
