"""
Smart Trend Follower Trading Bot - Production Implementation
Backtest results: +2990% vs Buy & Hold +601% (2018-2025)

Strategy Rules (Hardcoded):
- Entry: Price > EMA20 * 1.015 (BULL/VOLATILE) or EMA50 * 1.015 (LATERAL)
- Exit: Price < EMA50 * 0.985 (Dynamic, NO trailing stop)
- Winter Protocol: If Close < EMA200, only BUY if AI_Regime == 'BULL' AND RSI > 65
- Shadow Margin: Track x1.5 leverage for BULL regime (Spot execution only)

Uses CCXT for Kraken API (portability).
"""

import logging
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime
from enum import Enum

import ccxt
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# STRATEGY CONSTANTS (Hardcoded from winning backtest)
# ============================================================================
BUFFER_PERCENT = 0.015          # 1.5% hysteresis buffer
BULL_SHADOW_LEVERAGE = 1.5      # Shadow leverage for BULL regime audit
SPOT_LEVERAGE = 1.0             # Real execution is always spot
RSI_WINTER_THRESHOLD = 65       # RSI minimum for winter buys
OHLC_LIMIT = 1000               # Candles to fetch (ensures EMA200 accuracy)
OHLC_TIMEFRAME = '4h'           # 4-hour candles


class TradingSignal(str, Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketRegime(str, Enum):
    """AI Market regime classification"""
    BULL = "BULL"
    BEAR = "BEAR"
    LATERAL = "LATERAL"
    VOLATILE = "VOLATILE"


# ============================================================================
# CORE STRATEGY ENGINE
# ============================================================================
class StrategyEngine:
    """
    Core strategy logic - Pure functions for testability.
    All business rules are encapsulated here.
    """

    @staticmethod
    def calculate_indicators(closes: pd.Series) -> Dict[str, float]:
        """
        Calculate all required technical indicators.

        Args:
            closes: Series of closing prices (need 200+ for EMA200)

        Returns:
            Dict with ema20, ema50, ema200, rsi14
        """
        if len(closes) < 200:
            logger.warning(f"Insufficient data for EMA200: {len(closes)} candles")

        ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = closes.ewm(span=200, adjust=False).mean().iloc[-1] if len(closes) >= 200 else closes.mean()

        # RSI calculation
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi14 = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50.0

        return {
            'ema20': float(ema20),
            'ema50': float(ema50),
            'ema200': float(ema200),
            'rsi14': float(rsi14),
            'close': float(closes.iloc[-1])
        }

    @staticmethod
    def is_winter_mode(close: float, ema200: float) -> bool:
        """
        Winter Protocol: Check if market is in "winter" (bearish macro).

        Rule: Winter = Close < EMA200
        """
        return close < ema200

    @staticmethod
    def get_shadow_leverage(regime: str) -> float:
        """
        Get shadow leverage for margin performance audit.
        Real trading is ALWAYS spot (x1.0).

        Rule: BULL regime gets x1.5 shadow leverage for tracking.
        """
        if regime == MarketRegime.BULL.value:
            return BULL_SHADOW_LEVERAGE
        return SPOT_LEVERAGE

    @staticmethod
    def should_enter(
        close: float,
        ema20: float,
        ema50: float,
        ema200: float,
        rsi: float,
        regime: str,
        has_position: bool
    ) -> Tuple[bool, str]:
        """
        Smart Entry Logic.

        Rules:
        1. Must NOT have existing position
        2. Winter Protocol: If Close < EMA200, only enter if regime == BULL AND RSI > 65
        3. If NOT winter:
           - BULL/VOLATILE: Enter if Close > EMA20 * 1.015
           - LATERAL: Enter if Close > EMA50 * 1.015

        Returns:
            (should_enter, reason_string)
        """
        if has_position:
            return False, "Already holding position"

        is_winter = StrategyEngine.is_winter_mode(close, ema200)

        # Winter Protocol
        if is_winter:
            if regime != MarketRegime.BULL.value:
                return False, f"Winter Mode ON | Regime: {regime} | BLOCKED (Only BULL allowed)"
            if rsi < RSI_WINTER_THRESHOLD:
                return False, f"Winter Mode ON | Regime: BULL | RSI: {rsi:.0f} | BLOCKED (RSI < {RSI_WINTER_THRESHOLD})"
            # Winter entry allowed
            entry_threshold = ema20 * (1 + BUFFER_PERCENT)
            if close > entry_threshold:
                return True, f"Winter Mode ON | Regime: BULL | RSI: {rsi:.0f} >= {RSI_WINTER_THRESHOLD} | ENTRY ALLOWED"
            return False, f"Winter Mode ON | Price ${close:,.0f} < Entry ${entry_threshold:,.0f}"

        # Normal market (not winter)
        if regime in [MarketRegime.BULL.value, MarketRegime.VOLATILE.value]:
            entry_threshold = ema20 * (1 + BUFFER_PERCENT)
            if close > entry_threshold:
                return True, f"Normal Mode | Regime: {regime} | Price ${close:,.0f} > EMA20+1.5% ${entry_threshold:,.0f}"
            return False, f"Normal Mode | Regime: {regime} | Price ${close:,.0f} < EMA20+1.5% ${entry_threshold:,.0f}"

        elif regime == MarketRegime.LATERAL.value:
            entry_threshold = ema50 * (1 + BUFFER_PERCENT)
            if close > entry_threshold:
                return True, f"Normal Mode | Regime: LATERAL | Price ${close:,.0f} > EMA50+1.5% ${entry_threshold:,.0f}"
            return False, f"Normal Mode | Regime: LATERAL | Price ${close:,.0f} < EMA50+1.5% ${entry_threshold:,.0f}"

        else:  # BEAR or unknown
            return False, f"Normal Mode | Regime: {regime} | BLOCKED (No entries in BEAR)"

    @staticmethod
    def should_exit(
        close: float,
        ema50: float,
        regime: str,
        has_position: bool
    ) -> Tuple[bool, str]:
        """
        Smart Exit Logic.

        Rules:
        1. Must have position
        2. Exit if Close < EMA50 * 0.985 (1.5% buffer below)
        3. Exception: In BULL regime, give more room (HOLD unless catastrophic)

        Returns:
            (should_exit, reason_string)
        """
        if not has_position:
            return False, "No position to exit"

        exit_threshold = ema50 * (1 - BUFFER_PERCENT)

        if close < exit_threshold:
            # In BULL, we might want to hold tighter, but still exit on break
            if regime == MarketRegime.BULL.value:
                # Give a bit more room in BULL - check if drop is significant
                catastrophic_threshold = ema50 * 0.97  # 3% below EMA50
                if close < catastrophic_threshold:
                    return True, f"BULL Regime | CATASTROPHIC DROP | Price ${close:,.0f} < EMA50-3% ${catastrophic_threshold:,.0f}"
                return False, f"BULL Regime | Price ${close:,.0f} < EMA50-1.5% but HOLDING (not catastrophic)"

            return True, f"EXIT Signal | Price ${close:,.0f} < EMA50-1.5% ${exit_threshold:,.0f}"

        return False, f"HOLD | Price ${close:,.0f} >= EMA50-1.5% ${exit_threshold:,.0f}"

    @staticmethod
    def get_trading_signal(
        closes: list,
        regime: str,
        has_position: bool,
        current_price: Optional[float] = None
    ) -> Dict:
        """
        Main decision function - returns complete trading signal.

        Args:
            closes: List of closing prices (need 1000+ for accurate EMA200)
            regime: Current AI regime (BULL, BEAR, LATERAL, VOLATILE)
            has_position: Whether we currently hold BTC
            current_price: Override price (uses last close if not provided)

        Returns:
            Dict with signal, reason, indicators, shadow_leverage, etc.
        """
        if len(closes) < 50:
            return {
                'signal': TradingSignal.HOLD.value,
                'reason': f"Insufficient data: {len(closes)} candles (need 50+)",
                'shadow_leverage': SPOT_LEVERAGE,
                'is_winter_mode': False
            }

        series = pd.Series(closes)
        indicators = StrategyEngine.calculate_indicators(series)

        close = current_price if current_price else indicators['close']
        ema20 = indicators['ema20']
        ema50 = indicators['ema50']
        ema200 = indicators['ema200']
        rsi = indicators['rsi14']

        is_winter = StrategyEngine.is_winter_mode(close, ema200)
        shadow_leverage = StrategyEngine.get_shadow_leverage(regime)

        # Determine signal
        if has_position:
            should_sell, reason = StrategyEngine.should_exit(close, ema50, regime, has_position)
            signal = TradingSignal.SELL.value if should_sell else TradingSignal.HOLD.value
        else:
            should_buy, reason = StrategyEngine.should_enter(
                close, ema20, ema50, ema200, rsi, regime, has_position
            )
            signal = TradingSignal.BUY.value if should_buy else TradingSignal.HOLD.value

        return {
            'signal': signal,
            'reason': reason,
            'regime': regime,
            'shadow_leverage': shadow_leverage,
            'is_winter_mode': is_winter,
            'price': close,
            'ema20': ema20,
            'ema50': ema50,
            'ema200': ema200,
            'rsi': rsi,
            'entry_threshold_bull': ema20 * (1 + BUFFER_PERCENT),
            'entry_threshold_lateral': ema50 * (1 + BUFFER_PERCENT),
            'exit_threshold': ema50 * (1 - BUFFER_PERCENT),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# CCXT KRAKEN CLIENT
# ============================================================================
class CCXTKrakenClient:
    """
    CCXT-based Kraken client for portability.
    Supports both public and authenticated API calls.
    """

    def __init__(self, api_key: str = "", api_secret: str = ""):
        """Initialize CCXT Kraken client"""
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        self.logger = logger

    def get_ticker(self, symbol: str = "BTC/USD") -> Dict:
        """Get current ticker data"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return {}

    def get_ohlcv(
        self,
        symbol: str = "BTC/USD",
        timeframe: str = OHLC_TIMEFRAME,
        limit: int = OHLC_LIMIT
    ) -> list:
        """
        Get OHLCV data with sufficient history for EMA200.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe (4h recommended)
            limit: Number of candles (1000 for accurate EMA200)

        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            self.logger.info(f"Fetched {len(ohlcv)} candles for {symbol} ({timeframe})")
            return ohlcv
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV: {e}")
            return []

    def get_balance(self) -> Dict[str, float]:
        """Get account balances (requires authentication)"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'btc': float(balance.get('BTC', {}).get('free', 0)),
                'usd': float(balance.get('USD', {}).get('free', 0)),
                'total_btc': float(balance.get('BTC', {}).get('total', 0)),
                'total_usd': float(balance.get('USD', {}).get('total', 0))
            }
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return {'btc': 0, 'usd': 0, 'total_btc': 0, 'total_usd': 0}

    def create_market_order(self, symbol: str, side: str, amount: float) -> Dict:
        """
        Create a market order (real execution).

        Args:
            symbol: Trading pair (BTC/USD)
            side: 'buy' or 'sell'
            amount: Amount in base currency (BTC)

        Returns:
            Order result dict
        """
        try:
            order = self.exchange.create_market_order(symbol, side, amount)
            self.logger.info(f"Market order executed: {side.upper()} {amount} {symbol}")
            return {
                'success': True,
                'order_id': order['id'],
                'side': side,
                'amount': amount,
                'price': order.get('average', order.get('price')),
                'status': order['status']
            }
        except Exception as e:
            self.logger.error(f"Order execution failed: {e}")
            return {'success': False, 'error': str(e)}


# ============================================================================
# TRADING BOT ORCHESTRATOR
# ============================================================================
class TradingBot:
    """
    Main trading bot orchestrator.
    Executes strategy, manages positions, tracks shadow margin.
    """

    def __init__(
        self,
        kraken_api_key: str = "",
        kraken_secret: str = "",
        openai_api_key: str = "",
        telegram_token: str = "",
        telegram_chat_id: str = "",
        trade_amount: float = 100.0,  # Legacy param (ignored)
        trade_amount_percent: float = 75.0,
        min_balance: float = 50.0,  # Legacy param (ignored)
        min_balance_percent: float = 20.0,
        trailing_stop_pct: float = 0.0,  # Legacy param (ignored, we use EMA50)
        dry_run: bool = False
    ):
        """
        Initialize trading bot.

        Args:
            kraken_api_key: Kraken API key
            kraken_secret: Kraken API secret
            openai_api_key: OpenAI API key for regime detection
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID for alerts
            trade_amount: (Legacy) Fixed USD amount - ignored
            trade_amount_percent: % of capital per trade
            min_balance: (Legacy) Fixed USD reserve - ignored
            min_balance_percent: % of capital to keep as reserve
            trailing_stop_pct: (Legacy) Trailing stop % - ignored, uses EMA50
            dry_run: If True, simulate orders without execution
        """
        self.client = CCXTKrakenClient(kraken_api_key, kraken_secret)
        self.openai_api_key = openai_api_key
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.trade_amount_percent = trade_amount_percent
        self.min_balance_percent = min_balance_percent
        self.dry_run = dry_run

        self.is_running = False
        self.active_position: Optional[Dict] = None
        self.logger = logger

        # Initialize Telegram if configured
        self.telegram = None
        if telegram_token and telegram_chat_id:
            try:
                from .telegram_alerts import TelegramAlerts
                self.telegram = TelegramAlerts(telegram_token, telegram_chat_id)
            except Exception as e:
                self.logger.warning(f"Telegram init failed: {e}")

        # Initialize paper wallet if dry_run
        if self.dry_run:
            self._init_paper_wallet()

    def _init_paper_wallet(self):
        """Initialize paper wallet in database if not exists"""
        try:
            from ..database import SessionLocal
            from ..models import BotStatus
            db = SessionLocal()
            status = db.query(BotStatus).filter(BotStatus.trading_mode == "PAPER").first()
            if not status:
                status = BotStatus(
                    is_running=True,
                    trading_mode="PAPER",
                    btc_balance=0.0,
                    usd_balance=1000.0,
                    last_buy_price=None,
                    trailing_stop_price=None
                )
                db.add(status)
                db.commit()
                self.logger.info("Created PAPER wallet with $1000 USD")
            db.close()
        except Exception as e:
            self.logger.warning(f"Paper wallet init failed: {e}")

    def _get_paper_balance(self) -> Dict[str, float]:
        """Get balance from paper wallet in database"""
        try:
            from ..database import SessionLocal
            from ..models import BotStatus
            db = SessionLocal()
            status = db.query(BotStatus).filter(BotStatus.trading_mode == "PAPER").first()
            db.close()
            if status:
                return {'btc': status.btc_balance or 0, 'usd': status.usd_balance or 0}
            return {'btc': 0, 'usd': 1000}
        except Exception as e:
            self.logger.warning(f"Paper balance fetch failed: {e}")
            return {'btc': 0, 'usd': 1000}

    def _update_paper_balance(self, btc: float = None, usd: float = None):
        """Update paper wallet balance in database"""
        try:
            from ..database import SessionLocal
            from ..models import BotStatus
            db = SessionLocal()
            status = db.query(BotStatus).filter(BotStatus.trading_mode == "PAPER").first()
            if status:
                if btc is not None:
                    status.btc_balance = btc
                if usd is not None:
                    status.usd_balance = usd
                db.commit()
            db.close()
        except Exception as e:
            self.logger.warning(f"Paper balance update failed: {e}")

    def _get_balance(self) -> Dict[str, float]:
        """Get balance - paper wallet if dry_run, else real Kraken"""
        if self.dry_run:
            return self._get_paper_balance()
        return self.client.get_balance()

    def _get_ai_regime(self) -> Dict:
        """Get current AI regime from database or service"""
        try:
            from .ai_regime import AIRegimeService
            return AIRegimeService.get_current_regime()
        except Exception as e:
            self.logger.warning(f"AI regime fetch failed: {e}")
            return {
                'regime': MarketRegime.LATERAL.value,
                'confidence': 0.5,
                'reasoning': 'Default - AI unavailable'
            }

    def _has_position(self) -> bool:
        """Check if we have an open BTC position"""
        try:
            balance = self._get_balance()
            btc_balance = balance.get('btc', 0)
            return btc_balance > 0.0001  # More than dust
        except Exception:
            return self.active_position is not None

    def _save_trade_to_db(
        self,
        order_type: str,
        price: float,
        quantity: float,
        regime: str,
        shadow_leverage: float,
        trade_id: str = None
    ) -> None:
        """
        Save trade to database with shadow margin tracking.

        Args:
            order_type: 'BUY' or 'SELL'
            price: Execution price
            quantity: BTC quantity
            regime: AI regime at trade time
            shadow_leverage: Shadow leverage (1.0 or 1.5)
            trade_id: Exchange order ID
        """
        try:
            from ..database import SessionLocal
            from ..models import Trade
            import uuid

            db = SessionLocal()

            trade = Trade(
                trade_id=trade_id or str(uuid.uuid4()),
                order_type=order_type,
                symbol="BTCUSD",
                entry_price=price if order_type == "BUY" else None,
                exit_price=price if order_type == "SELL" else None,
                quantity=quantity,
                status="OPEN" if order_type == "BUY" else "CLOSED",
                trading_mode="PAPER" if self.dry_run else "REAL",
                ai_regime=regime,
                leverage_used=SPOT_LEVERAGE,  # Always spot
                shadow_leverage=shadow_leverage,  # Audit field
                created_at=datetime.now()
            )

            db.add(trade)
            db.commit()
            db.close()

            self.logger.info(
                f"💾 Trade saved: {order_type} | Regime: {regime} | "
                f"Shadow Leverage: x{shadow_leverage}"
            )
        except Exception as e:
            self.logger.error(f"Error saving trade to DB: {e}")

    def _save_cycle_to_db(self, cycle_data: Dict, execution_time_ms: int, trigger: str) -> None:
        """Save trading cycle to database"""
        try:
            from ..database import SessionLocal
            from ..models import TradingCycle

            db = SessionLocal()
            cycle = TradingCycle(
                btc_price=cycle_data.get('price', 0),
                ema20=cycle_data.get('ema20', 0),
                ema50=cycle_data.get('ema50', 0),
                rsi14=cycle_data.get('rsi', 0),
                ema200=cycle_data.get('ema200', 0),
                btc_balance=cycle_data.get('btc_balance', 0),
                usd_balance=cycle_data.get('usd_balance', 0),
                ai_signal=cycle_data.get('signal', 'HOLD'),
                ai_confidence=cycle_data.get('confidence', 0),
                ai_reason=cycle_data.get('reason', ''),
                ai_regime=cycle_data.get('regime', 'LATERAL'),
                leverage_multiplier=cycle_data.get('shadow_leverage', 1.0),
                is_winter_mode=cycle_data.get('is_winter_mode', False),
                action=cycle_data.get('action', 'HOLD'),
                trade_id=cycle_data.get('trade_id'),
                execution_time_ms=execution_time_ms,
                trading_mode="PAPER" if self.dry_run else "REAL",
                trigger=trigger,
                error_message=cycle_data.get('error')
            )
            db.add(cycle)
            db.commit()
            db.close()

        except Exception as e:
            self.logger.error(f"Error saving cycle to DB: {e}")

    async def analyze_market(self) -> Dict:
        """
        Analyze current market conditions.

        Returns:
            Complete market analysis with trading signal
        """
        try:
            # Fetch OHLCV data (1000 candles for EMA200 accuracy)
            ohlcv = self.client.get_ohlcv(limit=OHLC_LIMIT)
            if not ohlcv or len(ohlcv) < 50:
                return {'error': 'Insufficient OHLCV data'}

            closes = [candle[4] for candle in ohlcv]  # Close prices

            # Get current ticker
            ticker = self.client.get_ticker()
            current_price = ticker.get('last', closes[-1])

            # Get AI regime
            ai_regime_data = self._get_ai_regime()
            regime = ai_regime_data.get('regime', MarketRegime.LATERAL.value)

            # Check position status
            has_position = self._has_position()

            # Get trading signal from strategy engine
            signal = StrategyEngine.get_trading_signal(
                closes=closes,
                regime=regime,
                has_position=has_position,
                current_price=current_price
            )

            # Get balances
            balance = self._get_balance()

            # Add balance and regime info to signal
            signal.update({
                'btc_balance': balance.get('btc', 0),
                'usd_balance': balance.get('usd', 0),
                'has_position': has_position,
                'confidence': ai_regime_data.get('confidence', 0.5),
                'regime_reasoning': ai_regime_data.get('reasoning', '')
            })

            return signal

        except Exception as e:
            self.logger.error(f"Market analysis error: {e}")
            return {'error': str(e)}

        except Exception as e:
            self.logger.error(f"Error analyzing market: {e}")
            if self.telegram:
                self.telegram.send_error_alert(str(e), 'HIGH')
            return {}

    async def execute_buy(self, analysis: Dict) -> bool:
        """Execute a buy order"""
        try:
            usd_balance = analysis.get('usd_balance', 0)
            current_price = analysis.get('price', 0)

            if usd_balance <= 0 or current_price <= 0:
                self.logger.warning("Insufficient balance or invalid price")
                return False

            # Calculate trade amount
            trade_amount_usd = usd_balance * (self.trade_amount_percent / 100)
            min_balance = usd_balance * (self.min_balance_percent / 100)

            if trade_amount_usd + min_balance > usd_balance:
                trade_amount_usd = usd_balance - min_balance

            if trade_amount_usd < 10:  # Minimum order size
                self.logger.warning(f"Trade amount too small: ${trade_amount_usd:.2f}")
                return False

            btc_quantity = trade_amount_usd / current_price
            regime = analysis.get('regime', MarketRegime.LATERAL.value)
            shadow_leverage = analysis.get('shadow_leverage', SPOT_LEVERAGE)

            self.logger.info(
                f"🟢 EXECUTING BUY: {btc_quantity:.6f} BTC @ ${current_price:,.2f} | "
                f"Regime: {regime} | Shadow: x{shadow_leverage}"
            )

            if self.dry_run:
                order_id = f"DRY_RUN_{datetime.now().timestamp()}"
                success = True
                # Update paper wallet
                new_usd = usd_balance - trade_amount_usd
                new_btc = self._get_balance().get('btc', 0) + btc_quantity
                self._update_paper_balance(btc=new_btc, usd=new_usd)
                self.logger.info(f"📝 Paper wallet updated: ${new_usd:.2f} USD, {new_btc:.6f} BTC")
            else:
                result = self.client.create_market_order("BTC/USD", "buy", btc_quantity)
                success = result.get('success', False)
                order_id = result.get('order_id', '')

            if success:
                self.active_position = {
                    'entry_price': current_price,
                    'quantity': btc_quantity,
                    'order_id': order_id,
                    'regime': regime,
                    'shadow_leverage': shadow_leverage,
                    'timestamp': datetime.now().isoformat()
                }

                # Save to database
                self._save_trade_to_db(
                    order_type="BUY",
                    price=current_price,
                    quantity=btc_quantity,
                    regime=regime,
                    shadow_leverage=shadow_leverage,
                    trade_id=order_id
                )

                # Telegram alert
                if self.telegram:
                    self.telegram.send_buy_signal(
                        current_price, btc_quantity,
                        analysis.get('confidence', 0.7)
                    )

                return True

            return False

        except Exception as e:
            self.logger.error(f"Buy execution error: {e}")
            return False

    async def execute_sell(self, analysis: Dict) -> bool:
        """Execute a sell order"""
        try:
            if not self.active_position:
                # Check actual balance
                balance = self._get_balance()
                btc_balance = balance.get('btc', 0)
                if btc_balance <= 0.0001:
                    self.logger.warning("No position to sell")
                    return False
                quantity = btc_balance
                entry_price = analysis.get('price', 0)  # Use current as fallback
                regime = analysis.get('regime', MarketRegime.LATERAL.value)
                shadow_leverage = SPOT_LEVERAGE
            else:
                quantity = self.active_position['quantity']
                entry_price = self.active_position['entry_price']
                regime = self.active_position.get('regime', MarketRegime.LATERAL.value)
                shadow_leverage = self.active_position.get('shadow_leverage', SPOT_LEVERAGE)

            current_price = analysis.get('price', 0)
            profit_loss = (current_price - entry_price) * quantity
            profit_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0

            self.logger.info(
                f"🔴 EXECUTING SELL: {quantity:.6f} BTC @ ${current_price:,.2f} | "
                f"P/L: ${profit_loss:,.2f} ({profit_pct:+.2f}%)"
            )

            if self.dry_run:
                order_id = f"DRY_RUN_{datetime.now().timestamp()}"
                success = True
                # Update paper wallet
                sell_value = quantity * current_price
                new_usd = self._get_balance().get('usd', 0) + sell_value
                self._update_paper_balance(btc=0, usd=new_usd)
                self.logger.info(f"📝 Paper wallet updated: ${new_usd:.2f} USD, 0 BTC")
            else:
                result = self.client.create_market_order("BTC/USD", "sell", quantity)
                success = result.get('success', False)
                order_id = result.get('order_id', '')

            if success:
                # Calculate shadow profit
                shadow_profit = profit_loss * shadow_leverage

                # Save to database
                self._save_trade_to_db(
                    order_type="SELL",
                    price=current_price,
                    quantity=quantity,
                    regime=regime,
                    shadow_leverage=shadow_leverage,
                    trade_id=order_id
                )

                # Telegram alert
                if self.telegram:
                    self.telegram.send_sell_signal(
                        entry_price, current_price, profit_loss, 'STRATEGY_EXIT'
                    )

                self.active_position = None
                return True

            return False

        except Exception as e:
            self.logger.error(f"Sell execution error: {e}")
            return False

    async def run_cycle(self, trigger: str = "scheduled") -> Dict:
        """
        Execute one complete trading cycle.

        Args:
            trigger: What triggered this cycle ('scheduled', 'manual', 'api')

        Returns:
            Cycle result dict
        """
        import time
        start_time = time.time()

        self.logger.info("=" * 60)
        self.logger.info("📊 STARTING TRADING CYCLE")
        self.logger.info("=" * 60)

        try:
            # Analyze market
            analysis = await self.analyze_market()

            if 'error' in analysis:
                self.logger.error(f"Analysis failed: {analysis['error']}")
                return {'success': False, 'error': analysis['error']}

            # Log decision
            winter_status = "❄️ ON" if analysis.get('is_winter_mode') else "☀️ OFF"
            self.logger.info(
                f"[INFO] Winter Mode: {winter_status} | "
                f"Regime: {analysis.get('regime')} | "
                f"RSI: {analysis.get('rsi', 0):.0f} | "
                f"DECISION: {analysis.get('signal')} ({analysis.get('reason')})"
            )
            self.logger.info(
                f"📈 Price: ${analysis.get('price', 0):,.2f} | "
                f"EMA20: ${analysis.get('ema20', 0):,.2f} | "
                f"EMA50: ${analysis.get('ema50', 0):,.2f} | "
                f"EMA200: ${analysis.get('ema200', 0):,.2f}"
            )

            action = 'HOLD'
            trade_id = None

            signal = analysis.get('signal', TradingSignal.HOLD.value)

            if signal == TradingSignal.BUY.value:
                self.logger.info("✅ BUY SIGNAL TRIGGERED")
                success = await self.execute_buy(analysis)
                action = 'BOUGHT' if success else 'BUY_FAILED'
                if success and self.active_position:
                    trade_id = self.active_position.get('order_id')

            elif signal == TradingSignal.SELL.value:
                self.logger.info("✅ SELL SIGNAL TRIGGERED")
                success = await self.execute_sell(analysis)
                action = 'SOLD' if success else 'SELL_FAILED'
            else:
                self.logger.info("⏸️ HOLDING - No action required")

            # Save cycle to database
            execution_time_ms = int((time.time() - start_time) * 1000)
            analysis['action'] = action
            analysis['trade_id'] = trade_id
            self._save_cycle_to_db(analysis, execution_time_ms, trigger)

            self.logger.info(f"💾 Cycle completed in {execution_time_ms}ms")
            self.logger.info("=" * 60)

            return {
                'success': True,
                'signal': signal,
                'action': action,
                'analysis': analysis
            }

        except Exception as e:
            self.logger.error(f"❌ Cycle error: {e}")
            return {'success': False, 'error': str(e)}

    async def start(self):
        """Start the trading bot daemon"""
        self.is_running = True
        self.logger.info("🟢 Trading Bot Started")
        if self.telegram:
            self.telegram.send_message("🟢 <b>Trading Bot Started</b> 🟢")

    async def stop(self):
        """Stop the trading bot daemon"""
        self.is_running = False
        self.logger.info("🔴 Trading Bot Stopped")
        if self.telegram:
            self.telegram.send_message("🔴 <b>Trading Bot Stopped</b> 🔴")


# ============================================================================
# DRY RUN / SIMULATION MODE
# ============================================================================
async def run_dry_cycle():
    """
    Execute a single dry-run cycle for testing/validation.
    Uses public API only (no auth required).
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    bot = TradingBot(dry_run=True)
    result = await bot.run_cycle(trigger="dry_run")
    return result


if __name__ == "__main__":
    # Quick test
    asyncio.run(run_dry_cycle())
