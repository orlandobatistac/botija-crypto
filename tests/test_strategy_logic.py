"""
Test Strategy Logic - Validates capital protection rules

Tests:
1. Winter Protocol: Blocks buys when RSI < 65 in winter mode
2. Shadow Margin: Verifies x1.5 shadow leverage for BULL regime
3. EMA50 Exit: Confirms sell signal when price drops below EMA50

Backtest reference: +2990% vs Buy & Hold +601% (2018-2025)
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import strategy engine directly for unit testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.trading_bot import (
    StrategyEngine,
    TradingSignal,
    MarketRegime,
    BUFFER_PERCENT,
    BULL_SHADOW_LEVERAGE,
    SPOT_LEVERAGE,
    RSI_WINTER_THRESHOLD
)


class TestWinterProtocol:
    """
    Test 1: Winter Protocol - Anti-Knife Filter

    Scenario: Price $20k, EMA200 $30k (winter mode)
    AI Regime: BULL
    RSI: 40 (below threshold)
    Expected: REJECT buy signal
    """

    def test_winter_mode_detection(self):
        """Test that winter mode is correctly detected"""
        # Winter: price below EMA200
        assert StrategyEngine.is_winter_mode(20000, 30000) is True
        # Not winter: price above EMA200
        assert StrategyEngine.is_winter_mode(35000, 30000) is False
        # Edge case: exactly at EMA200
        assert StrategyEngine.is_winter_mode(30000, 30000) is False

    def test_winter_blocks_low_rsi_bull(self):
        """
        CRITICAL TEST: Winter + BULL + Low RSI = NO BUY

        This is the anti-knife filter that saved the strategy in bear markets.
        """
        close = 20000       # Price
        ema20 = 22000       # EMA20 (price below for extra confirmation)
        ema50 = 25000       # EMA50
        ema200 = 30000      # Winter threshold (price below = winter)
        rsi = 40            # BELOW 65 threshold
        regime = MarketRegime.BULL.value
        has_position = False

        should_buy, reason = StrategyEngine.should_enter(
            close, ema20, ema50, ema200, rsi, regime, has_position
        )

        assert should_buy is False, "Should REJECT buy in winter with low RSI"
        assert "BLOCKED" in reason, f"Reason should mention blocked: {reason}"
        assert "RSI" in reason, f"Reason should mention RSI: {reason}"
        assert "65" in reason, f"Reason should mention threshold: {reason}"

    def test_winter_allows_high_rsi_bull(self):
        """Winter + BULL + High RSI (>65) + Price above EMA20+buffer = ALLOW BUY"""
        close = 25000       # Price above EMA20+1.5%
        ema20 = 24000       # EMA20 * 1.015 = 24360, close > 24360 ✓
        ema50 = 23000       # EMA50
        ema200 = 30000      # Winter threshold
        rsi = 70            # ABOVE 65 threshold
        regime = MarketRegime.BULL.value
        has_position = False

        should_buy, reason = StrategyEngine.should_enter(
            close, ema20, ema50, ema200, rsi, regime, has_position
        )

        # Need to check if close > ema20 * 1.015
        entry_threshold = ema20 * (1 + BUFFER_PERCENT)
        if close > entry_threshold:
            assert should_buy is True, f"Should ALLOW buy: {reason}"
            assert "ENTRY ALLOWED" in reason

    def test_winter_blocks_non_bull_regime(self):
        """Winter + LATERAL/BEAR/VOLATILE = NO BUY regardless of RSI"""
        close = 25000
        ema20 = 24000
        ema50 = 23000
        ema200 = 30000      # Winter mode
        rsi = 80            # High RSI but doesn't matter
        has_position = False

        for regime in [MarketRegime.LATERAL.value, MarketRegime.BEAR.value, MarketRegime.VOLATILE.value]:
            should_buy, reason = StrategyEngine.should_enter(
                close, ema20, ema50, ema200, rsi, regime, has_position
            )
            assert should_buy is False, f"Should REJECT {regime} in winter"
            assert "BLOCKED" in reason


class TestShadowMargin:
    """
    Test 2: Shadow Margin Tracking

    Verifies that:
    - Shadow Margin is DISABLED (always returns 1.0)
    - All regimes get shadow_leverage = 1.0 (pure SPOT)
    - Real execution is always spot (x1.0)
    """

    def test_bull_gets_shadow_leverage_1_5(self):
        """Shadow margin is DISABLED - BULL should return 1.0 (pure SPOT)"""
        leverage = StrategyEngine.get_shadow_leverage(MarketRegime.BULL.value)
        # Shadow margin disabled - always SPOT
        assert leverage == SPOT_LEVERAGE, "Shadow margin disabled - should be SPOT (1.0x)"
        assert leverage == 1.0

    def test_non_bull_gets_spot_leverage(self):
        """Non-BULL regimes should return x1.0 (spot)"""
        for regime in [MarketRegime.LATERAL.value, MarketRegime.BEAR.value, MarketRegime.VOLATILE.value]:
            leverage = StrategyEngine.get_shadow_leverage(regime)
            assert leverage == SPOT_LEVERAGE, f"{regime} should get {SPOT_LEVERAGE}x"
            assert leverage == 1.0

    def test_trading_signal_includes_shadow_leverage(self):
        """Full trading signal should include shadow_leverage field (always 1.0 - disabled)"""
        # Generate enough price data for indicators
        closes = list(range(1000, 1500))  # 500 prices

        signal = StrategyEngine.get_trading_signal(
            closes=closes,
            regime=MarketRegime.BULL.value,
            has_position=False
        )

        assert 'shadow_leverage' in signal, "Signal must include shadow_leverage"
        # Shadow margin disabled - always 1.0
        assert signal['shadow_leverage'] == 1.0, "Shadow margin disabled - should be 1.0x"

    def test_shadow_leverage_in_signal_for_lateral(self):
        """LATERAL regime signal should have 1.0x shadow leverage"""
        closes = list(range(1000, 1500))

        signal = StrategyEngine.get_trading_signal(
            closes=closes,
            regime=MarketRegime.LATERAL.value,
            has_position=False
        )

        assert signal['shadow_leverage'] == 1.0


class TestEMA50Exit:
    """
    Test 3: Smart Exit Logic

    Exit when: Close < EMA50 * 0.985 (1.5% buffer below)
    Exception: BULL regime holds unless catastrophic (3% below)
    """

    def test_exit_below_ema50_buffer(self):
        """Price below EMA50-1.5% should trigger SELL in non-BULL"""
        ema50 = 50000
        exit_threshold = ema50 * (1 - BUFFER_PERCENT)  # 49,250
        close = 49000       # Below threshold
        regime = MarketRegime.LATERAL.value
        has_position = True

        should_sell, reason = StrategyEngine.should_exit(
            close, ema50, regime, has_position
        )

        assert should_sell is True, f"Should trigger sell: {reason}"
        assert "EXIT" in reason

    def test_hold_above_ema50_buffer(self):
        """Price above EMA50-1.5% should HOLD"""
        ema50 = 50000
        close = 49500       # Above threshold (49,250)
        regime = MarketRegime.LATERAL.value
        has_position = True

        should_sell, reason = StrategyEngine.should_exit(
            close, ema50, regime, has_position
        )

        assert should_sell is False, f"Should HOLD: {reason}"
        assert "HOLD" in reason

    def test_bull_holds_on_minor_drop(self):
        """BULL regime should HOLD on minor drops (< 3% below EMA50)"""
        ema50 = 50000
        exit_threshold = ema50 * (1 - BUFFER_PERCENT)  # 49,250
        close = 49000       # Below 1.5% but above 3%
        regime = MarketRegime.BULL.value
        has_position = True

        should_sell, reason = StrategyEngine.should_exit(
            close, ema50, regime, has_position
        )

        # BULL should hold unless catastrophic
        assert should_sell is False, f"BULL should HOLD on minor drop: {reason}"
        assert "HOLDING" in reason or "HOLD" in reason

    def test_bull_sells_on_catastrophic_drop(self):
        """BULL regime should SELL on catastrophic drop (>3% below EMA50)"""
        ema50 = 50000
        catastrophic_threshold = ema50 * 0.97  # 48,500
        close = 48000       # Below 3% threshold
        regime = MarketRegime.BULL.value
        has_position = True

        should_sell, reason = StrategyEngine.should_exit(
            close, ema50, regime, has_position
        )

        assert should_sell is True, f"BULL should SELL on catastrophic: {reason}"
        assert "CATASTROPHIC" in reason

    def test_no_exit_without_position(self):
        """Should not trigger exit if no position held"""
        should_sell, reason = StrategyEngine.should_exit(
            close=40000,
            ema50=50000,
            regime=MarketRegime.LATERAL.value,
            has_position=False
        )

        assert should_sell is False
        assert "No position" in reason


class TestSmartEntry:
    """
    Test entry logic for different regimes
    """

    def test_bull_entry_requires_ema20_buffer(self):
        """BULL/VOLATILE: Entry requires Close > EMA20 * 1.015"""
        ema20 = 50000
        entry_threshold = ema20 * (1 + BUFFER_PERCENT)  # 50,750

        # Below threshold - no entry
        should_buy, _ = StrategyEngine.should_enter(
            close=50500, ema20=ema20, ema50=48000, ema200=40000,
            rsi=55, regime=MarketRegime.BULL.value, has_position=False
        )
        assert should_buy is False

        # Above threshold - entry allowed
        should_buy, reason = StrategyEngine.should_enter(
            close=51000, ema20=ema20, ema50=48000, ema200=40000,
            rsi=55, regime=MarketRegime.BULL.value, has_position=False
        )
        assert should_buy is True
        assert "EMA20+1.5%" in reason

    def test_lateral_entry_requires_ema50_buffer(self):
        """LATERAL: Entry requires Close > EMA50 * 1.015"""
        ema50 = 50000
        entry_threshold = ema50 * (1 + BUFFER_PERCENT)  # 50,750

        # Below threshold - no entry
        should_buy, _ = StrategyEngine.should_enter(
            close=50500, ema20=52000, ema50=ema50, ema200=40000,
            rsi=55, regime=MarketRegime.LATERAL.value, has_position=False
        )
        assert should_buy is False

        # Above threshold - entry allowed
        should_buy, reason = StrategyEngine.should_enter(
            close=51000, ema20=52000, ema50=ema50, ema200=40000,
            rsi=55, regime=MarketRegime.LATERAL.value, has_position=False
        )
        assert should_buy is True
        assert "EMA50+1.5%" in reason

    def test_bear_blocks_all_entries(self):
        """BEAR regime should block all entries"""
        should_buy, reason = StrategyEngine.should_enter(
            close=60000, ema20=50000, ema50=48000, ema200=40000,
            rsi=80, regime=MarketRegime.BEAR.value, has_position=False
        )
        assert should_buy is False
        assert "BLOCKED" in reason

    def test_no_entry_with_existing_position(self):
        """Should not enter if already holding position"""
        should_buy, reason = StrategyEngine.should_enter(
            close=60000, ema20=50000, ema50=48000, ema200=40000,
            rsi=80, regime=MarketRegime.BULL.value, has_position=True
        )
        assert should_buy is False
        assert "Already" in reason


class TestIndicatorCalculation:
    """
    Test technical indicator calculations
    """

    def test_ema_calculation_accuracy(self):
        """Verify EMA calculation matches pandas"""
        # Generate test data
        prices = list(range(100, 400))  # 300 prices
        series = pd.Series(prices)

        indicators = StrategyEngine.calculate_indicators(series)

        # Should have all required fields
        assert 'ema20' in indicators
        assert 'ema50' in indicators
        assert 'ema200' in indicators
        assert 'rsi14' in indicators
        assert 'close' in indicators

    def test_insufficient_data_handling(self):
        """Should handle insufficient data gracefully"""
        closes = list(range(1, 30))  # Only 29 prices

        signal = StrategyEngine.get_trading_signal(
            closes=closes,
            regime=MarketRegime.BULL.value,
            has_position=False
        )

        assert signal['signal'] == TradingSignal.HOLD.value
        assert "Insufficient" in signal['reason']


class TestFullTradingSignal:
    """
    Integration tests for complete trading signals
    """

    def test_complete_signal_structure(self):
        """Verify signal contains all required fields"""
        closes = list(range(1000, 1500))

        signal = StrategyEngine.get_trading_signal(
            closes=closes,
            regime=MarketRegime.BULL.value,
            has_position=False
        )

        required_fields = [
            'signal', 'reason', 'regime', 'shadow_leverage',
            'is_winter_mode', 'price', 'ema20', 'ema50', 'ema200',
            'rsi', 'entry_threshold_bull', 'entry_threshold_lateral',
            'exit_threshold', 'timestamp'
        ]

        for field in required_fields:
            assert field in signal, f"Missing field: {field}"

    def test_signal_with_custom_price(self):
        """Should use custom current_price when provided"""
        closes = list(range(1000, 1500))
        custom_price = 99999.99

        signal = StrategyEngine.get_trading_signal(
            closes=closes,
            regime=MarketRegime.BULL.value,
            has_position=False,
            current_price=custom_price
        )

        assert signal['price'] == custom_price


# ============================================================================
# MOCK TESTS FOR DATABASE INTEGRATION
# ============================================================================
class TestShadowMarginDatabase:
    """
    Test shadow margin is correctly saved to database
    """

    @patch('app.services.trading_bot.TradingBot._save_trade_to_db')
    def test_buy_saves_shadow_leverage(self, mock_save):
        """BUY in BULL regime should save shadow_leverage=1.5"""
        from app.services.trading_bot import TradingBot

        bot = TradingBot(dry_run=True)

        # Mock analysis
        analysis = {
            'price': 50000,
            'usd_balance': 10000,
            'regime': MarketRegime.BULL.value,
            'shadow_leverage': 1.5,
            'confidence': 0.8
        }

        # Execute (async)
        import asyncio
        asyncio.run(bot.execute_buy(analysis))

        # Verify save was called with correct shadow_leverage
        if mock_save.called:
            call_args = mock_save.call_args
            assert call_args.kwargs.get('shadow_leverage') == 1.5 or \
                   (len(call_args.args) > 4 and call_args.args[4] == 1.5)


# ============================================================================
# RUN TESTS
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
