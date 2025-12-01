"""
Dry Run Script - Execute single cycle with live Kraken data
"""
import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.trading_bot import TradingBot, StrategyEngine, CCXTKrakenClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def run_dry_cycle():
    """Execute a dry run cycle with live market data"""
    logger.info("=" * 70)
    logger.info("🚀 SMART TREND FOLLOWER - DRY RUN")
    logger.info("=" * 70)

    # Initialize CCXT client (public API only)
    client = CCXTKrakenClient()

    # Fetch live data
    logger.info("📡 Fetching live data from Kraken...")

    # Get ticker
    ticker = client.get_ticker("BTC/USD")
    if not ticker:
        logger.error("Failed to fetch ticker")
        return

    current_price = ticker['last']
    logger.info(f"💰 Current BTC/USD: ${current_price:,.2f}")

    # Get OHLCV (1000 candles for EMA200 accuracy)
    ohlcv = client.get_ohlcv("BTC/USD", "4h", limit=1000)
    if not ohlcv:
        logger.error("Failed to fetch OHLCV data")
        return

    logger.info(f"📊 Fetched {len(ohlcv)} 4H candles")

    # Extract closes
    closes = [candle[4] for candle in ohlcv]

    # Simulate AI regime (would come from database in production)
    # For dry run, we'll determine based on trend
    import pandas as pd
    series = pd.Series(closes)
    ema20 = series.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = series.ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = series.ewm(span=200, adjust=False).mean().iloc[-1]

    # Simple regime detection for demo
    if current_price > ema200 and ema20 > ema50:
        regime = "BULL"
    elif current_price < ema200:
        regime = "BEAR"
    elif abs(ema20 - ema50) / ema50 < 0.01:  # Less than 1% difference
        regime = "LATERAL"
    else:
        regime = "VOLATILE"

    logger.info(f"🎯 Detected Regime: {regime}")

    # Get trading signal (simulating no position)
    signal = StrategyEngine.get_trading_signal(
        closes=closes,
        regime=regime,
        has_position=False,  # Simulating no position
        current_price=current_price
    )

    # Log the decision
    logger.info("-" * 70)
    winter_emoji = "❄️" if signal['is_winter_mode'] else "☀️"
    logger.info(
        f"[INFO] Winter Mode: {winter_emoji} {'ON' if signal['is_winter_mode'] else 'OFF'} | "
        f"Regime: {signal['regime']} | "
        f"RSI: {signal['rsi']:.0f} | "
        f"DECISION: {signal['signal']}"
    )
    logger.info(f"📝 Reason: {signal['reason']}")
    logger.info("-" * 70)

    # Log indicators
    logger.info("📈 INDICATORS:")
    logger.info(f"   Price:  ${signal['price']:,.2f}")
    logger.info(f"   EMA20:  ${signal['ema20']:,.2f}")
    logger.info(f"   EMA50:  ${signal['ema50']:,.2f}")
    logger.info(f"   EMA200: ${signal['ema200']:,.2f}")
    logger.info(f"   RSI14:  {signal['rsi']:.1f}")

    # Log thresholds
    logger.info("🎯 THRESHOLDS:")
    logger.info(f"   Entry (BULL/VOL): ${signal['entry_threshold_bull']:,.2f} (EMA20 + 1.5%)")
    logger.info(f"   Entry (LATERAL):  ${signal['entry_threshold_lateral']:,.2f} (EMA50 + 1.5%)")
    logger.info(f"   Exit:             ${signal['exit_threshold']:,.2f} (EMA50 - 1.5%)")

    # Shadow Margin info
    logger.info(f"💼 Shadow Leverage: x{signal['shadow_leverage']}")

    logger.info("=" * 70)
    logger.info("✅ DRY RUN COMPLETE")
    logger.info("=" * 70)

    return signal


if __name__ == "__main__":
    asyncio.run(run_dry_cycle())
