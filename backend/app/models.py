"""
Database models for Kraken AI Trading Bot
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .database import Base

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String, unique=True, index=True)
    order_type = Column(String)  # BUY, SELL
    symbol = Column(String, default="BTCUSD")
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float)
    profit_loss = Column(Float, nullable=True)
    status = Column(String)  # OPEN, CLOSED, CANCELLED
    trailing_stop = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

class BotStatus(Base):
    __tablename__ = "bot_status"
    
    id = Column(Integer, primary_key=True, index=True)
    is_running = Column(Boolean, default=False)
    btc_balance = Column(Float, default=0.0)
    usd_balance = Column(Float, default=0.0)
    last_check = Column(DateTime(timezone=True), server_default=func.now())
    last_trade_id = Column(String, nullable=True)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ema20 = Column(Float)
    ema50 = Column(Float)
    rsi14 = Column(Float)
    ai_signal = Column(String)  # BUY, SELL, HOLD
    confidence = Column(Float)
    action_taken = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
