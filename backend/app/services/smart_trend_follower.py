"""
Smart Trend Follower - Production implementation of winning backtest strategy
Backtest results: +2990% vs Buy & Hold +601% (2018-2025)

Strategy:
- Entry: Price > EMA20 + 1.5% buffer (fast entry)
- Exit: Price < EMA50 - 1.5% buffer (slow exit)
- Dynamic Leverage: x1.5 for BULL, x1.0 for others
- Winter Protocol: If Price < EMA200, only enter if RSI > 65
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Strategy constants from winning backtest
BUFFER_PERCENT = 0.015  # 1.5% hysteresis buffer
BULL_LEVERAGE = 1.5     # Leverage multiplier for BULL regime
SPOT_LEVERAGE = 1.0     # Spot trading for non-BULL regimes
RSI_WINTER_THRESHOLD = 65  # RSI threshold for winter protocol


class SmartTrendFollower:
    """
    Production implementation of the winning backtest strategy.
    Uses EMA20/EMA50 crossover with buffer + AI regime + winter protocol.
    """

    @staticmethod
    def calculate_ema200(prices: list) -> float:
        """Calculate EMA200 for winter protocol detection"""
        if len(prices) < 200:
            return prices[-1] if prices else 0

        import pandas as pd
        series = pd.Series(prices)
        ema200 = series.ewm(span=200, adjust=False).mean()
        return float(ema200.iloc[-1])

    @staticmethod
    def is_winter_mode(price: float, ema200: float) -> bool:
        """Check if we're in winter mode (price below EMA200)"""
        return price < ema200

    @staticmethod
    def get_leverage_multiplier(regime: str) -> float:
        """
        Get leverage multiplier based on AI regime.
        BULL = x1.5, others = x1.0 (spot)
        """
        if regime == 'BULL':
            return BULL_LEVERAGE
        return SPOT_LEVERAGE

    @staticmethod
    def should_enter(
        price: float,
        ema20: float,
        ema50: float,
        ema200: float,
        rsi: float,
        regime: str,
        has_position: bool
    ) -> Tuple[bool, str]:
        """
        Determine if we should enter a position.

        Rules:
        1. Must not have existing position
        2. Price must be above EMA20 + 1.5% buffer
        3. EMA20 must be above EMA50 (trend confirmation)
        4. Winter protocol: If price < EMA200, RSI must be > 65

        Returns: (should_enter, reason)
        """
        if has_position:
            return False, "Already has position"

        entry_threshold = ema20 * (1 + BUFFER_PERCENT)

        # Check basic entry condition
        if price < entry_threshold:
            return False, f"Price ${price:,.0f} < EMA20+1.5% ${entry_threshold:,.0f}"

        # Check trend confirmation
        if ema20 < ema50:
            return False, f"EMA20 ${ema20:,.0f} < EMA50 ${ema50:,.0f} (no uptrend)"

        # Winter protocol check
        if SmartTrendFollower.is_winter_mode(price, ema200):
            if rsi < RSI_WINTER_THRESHOLD:
                return False, f"Winter mode + RSI {rsi:.0f} < {RSI_WINTER_THRESHOLD} (blocked)"
            logger.info(f"🥶 Winter mode but RSI {rsi:.0f} >= {RSI_WINTER_THRESHOLD} - entry allowed")

        leverage = SmartTrendFollower.get_leverage_multiplier(regime)
        return True, f"BUY signal: Price ${price:,.0f} > EMA20+1.5% ${entry_threshold:,.0f}, Regime: {regime}, Leverage: x{leverage}"

    @staticmethod
    def should_exit(
        price: float,
        ema50: float,
        regime: str,
        has_position: bool
    ) -> Tuple[bool, str]:
        """
        Determine if we should exit a position.

        Rules:
        1. Must have existing position
        2. Price must be below EMA50 - 1.5% buffer

        Returns: (should_exit, reason)
        """
        if not has_position:
            return False, "No position to exit"

        exit_threshold = ema50 * (1 - BUFFER_PERCENT)

        if price < exit_threshold:
            return True, f"SELL signal: Price ${price:,.0f} < EMA50-1.5% ${exit_threshold:,.0f}"

        return False, f"HOLD: Price ${price:,.0f} >= EMA50-1.5% ${exit_threshold:,.0f}"

    @staticmethod
    def get_trading_signal(
        prices: list,
        regime: str,
        has_position: bool,
        current_price: Optional[float] = None
    ) -> Dict:
        """
        Get complete trading signal with all parameters.

        Args:
            prices: Historical price data (need 200+ for EMA200)
            regime: Current AI regime (BULL, BEAR, LATERAL, VOLATILE)
            has_position: Whether we currently have a BTC position
            current_price: Override for current price (uses last price if not provided)

        Returns:
            Dict with signal, reason, leverage, thresholds, etc.
        """
        if len(prices) < 50:
            return {
                'signal': 'HOLD',
                'reason': 'Insufficient price data',
                'leverage': 1.0,
                'regime': regime
            }

        import pandas as pd
        series = pd.Series(prices)

        # Calculate EMAs
        ema20 = float(series.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(series.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = SmartTrendFollower.calculate_ema200(prices)

        # Calculate RSI
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50

        price = current_price if current_price else prices[-1]
        leverage = SmartTrendFollower.get_leverage_multiplier(regime)
        is_winter = SmartTrendFollower.is_winter_mode(price, ema200)

        # Determine signal
        if has_position:
            should_sell, reason = SmartTrendFollower.should_exit(
                price, ema50, regime, has_position
            )
            signal = 'SELL' if should_sell else 'HOLD'
        else:
            should_buy, reason = SmartTrendFollower.should_enter(
                price, ema20, ema50, ema200, rsi, regime, has_position
            )
            signal = 'BUY' if should_buy else 'HOLD'

        return {
            'signal': signal,
            'reason': reason,
            'leverage': leverage,
            'regime': regime,
            'price': price,
            'ema20': ema20,
            'ema50': ema50,
            'ema200': ema200,
            'rsi': rsi,
            'entry_threshold': ema20 * (1 + BUFFER_PERCENT),
            'exit_threshold': ema50 * (1 - BUFFER_PERCENT),
            'is_winter_mode': is_winter,
            'winter_rsi_ok': rsi >= RSI_WINTER_THRESHOLD if is_winter else True,
            'buffer_percent': BUFFER_PERCENT * 100,
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def calculate_position_size(
        usd_balance: float,
        capital_percent: float,
        leverage: float,
        price: float
    ) -> Tuple[float, float]:
        """
        Calculate position size considering leverage.

        Returns: (btc_quantity, effective_exposure)
        """
        # Base investment
        base_investment = usd_balance * (capital_percent / 100)

        # Apply leverage
        effective_exposure = base_investment * leverage

        # Calculate BTC quantity
        btc_quantity = effective_exposure / price

        return btc_quantity, effective_exposure
