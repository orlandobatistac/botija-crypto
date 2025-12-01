"""
Pydantic schemas for Botija Crypto API
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TradeBase(BaseModel):
    order_type: str
    symbol: str = "BTCUSD"
    entry_price: float
    quantity: float
    status: str
    trading_mode: str = "REAL"

class TradeCreate(TradeBase):
    pass

class Trade(TradeBase):
    id: int
    trade_id: Optional[str] = None
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    trailing_stop: Optional[float] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%SZ') if v else None
        }

class BotStatusBase(BaseModel):
    is_running: bool
    trading_mode: str = "PAPER"
    btc_balance: float
    usd_balance: float

class BotStatusCreate(BotStatusBase):
    pass

class BotStatus(BotStatusBase):
    id: int
    last_buy_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    last_check: datetime
    last_trade_id: Optional[str] = None
    error_count: int
    updated_at: datetime

    class Config:
        from_attributes = True

class SignalBase(BaseModel):
    ema20: float
    ema50: float
    rsi14: float
    ai_signal: str
    confidence: float

class SignalCreate(SignalBase):
    pass

class Signal(SignalBase):
    id: int
    timestamp: datetime
    action_taken: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%SZ') if v else None
        }

class TradingCycleBase(BaseModel):
    btc_price: float
    ema20: float
    ema50: float
    rsi14: float
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_position: Optional[float] = None
    tech_score: Optional[int] = None
    btc_balance: float
    usd_balance: float
    ai_signal: str
    ai_confidence: float
    action: str
    trading_mode: str
    # Smart Trend Follower fields
    ai_regime: Optional[str] = None
    leverage_multiplier: Optional[float] = None
    is_winter_mode: Optional[bool] = None
    ema200: Optional[float] = None

class TradingCycleCreate(TradingCycleBase):
    ai_reason: Optional[str] = None
    trade_id: Optional[str] = None
    execution_time_ms: Optional[int] = None
    trigger: Optional[str] = None
    error_message: Optional[str] = None

class TradingCycle(TradingCycleBase):
    id: int
    timestamp: datetime
    ai_reason: Optional[str] = None
    trade_id: Optional[str] = None
    execution_time_ms: Optional[int] = None
    trigger: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%SZ') if v else None
        }


# Risk Profile Schemas
class RiskProfileBase(BaseModel):
    profile: str = "moderate"  # conservative, moderate, aggressive
    buy_score_threshold: int = 65
    sell_score_threshold: int = 35
    trade_amount_percent: float = 10.0
    max_trades_per_day: int = 3
    trailing_stop_percent: float = 2.0

class RiskProfileUpdate(BaseModel):
    profile: Optional[str] = None
    buy_score_threshold: Optional[int] = None
    sell_score_threshold: Optional[int] = None
    trade_amount_percent: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    trailing_stop_percent: Optional[float] = None

class RiskProfile(RiskProfileBase):
    id: int
    updated_at: datetime
    # Calculated projections
    projected_monthly_return_min: Optional[float] = None
    projected_monthly_return_max: Optional[float] = None

    class Config:
        from_attributes = True

# Risk profile presets (basado en backtest 2020-2025 con datos reales de BTC)
# Optimizado para superar Buy & Hold: threshold de compra bajo = entrar rápido
RISK_PRESETS = {
    "conservative": {
        "buy_score_threshold": 55,  # Entrar más fácil
        "sell_score_threshold": 30,
        "trade_amount_percent": 50.0,
        "max_trades_per_day": 2,
        "trailing_stop_percent": 1.5,
        # Backtest: +850% en 5 años, max drawdown -46%
        "projected_monthly_return_min": 2.5,
        "projected_monthly_return_max": 5.0,
    },
    "moderate": {
        "buy_score_threshold": 50,  # Threshold óptimo del backtest
        "sell_score_threshold": 35,
        "trade_amount_percent": 75.0,
        "max_trades_per_day": 3,
        "trailing_stop_percent": 2.0,
        # Backtest: +1019% en 5 años (supera B&H +950%), max drawdown -43%
        "projected_monthly_return_min": 3.5,
        "projected_monthly_return_max": 7.0,
    },
    "aggressive": {
        "buy_score_threshold": 50,  # Mismo threshold óptimo
        "sell_score_threshold": 40,  # Salir más tarde = más tiempo en mercado
        "trade_amount_percent": 100.0,
        "max_trades_per_day": 5,
        "trailing_stop_percent": 3.0,
        # Backtest: +996% en 5 años, max drawdown -44%
        "projected_monthly_return_min": 3.5,
        "projected_monthly_return_max": 7.0,
    }
}
