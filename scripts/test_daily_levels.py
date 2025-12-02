#!/usr/bin/env python3
"""
Test script for Daily Levels / 4H Execution architecture.
Verifies that we can fetch enough daily candles for EMA200.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.trading_bot import CCXTKrakenClient, OHLC_LIMIT, EMA_SLOW, OHLC_TIMEFRAME
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_daily_data():
    """Test that we can fetch enough daily candles for indicators"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Daily Levels / 4H Execution Architecture")
    print("="*60)
    
    # Initialize client (public API, no auth needed)
    client = CCXTKrakenClient()
    
    # Test 1: Fetch daily candles
    print(f"\n📊 Test 1: Fetch DAILY candles ({OHLC_LIMIT} requested)")
    print("-" * 40)
    print(f"   Timeframe: {OHLC_TIMEFRAME}")
    ohlcv = client.get_ohlcv(limit=OHLC_LIMIT)
    print(f"   Requested: {OHLC_LIMIT}")
    print(f"   Received:  {len(ohlcv)}")
    
    # Check if we have enough for EMA200
    if len(ohlcv) >= EMA_SLOW:
        print(f"   ✅ Sufficient for EMA{EMA_SLOW}: {len(ohlcv)} >= {EMA_SLOW}")
    else:
        print(f"   ❌ INSUFFICIENT: {len(ohlcv)} < {EMA_SLOW}")
        return False
    
    # Test 2: Data integrity
    print("\n📊 Test 2: Data integrity check")
    print("-" * 40)
    
    timestamps = [c[0] for c in ohlcv]
    is_sorted = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
    print(f"   Timestamps sorted: {'✅ Yes' if is_sorted else '❌ No'}")
    
    unique_timestamps = len(set(timestamps))
    has_duplicates = unique_timestamps != len(timestamps)
    print(f"   No duplicates: {'✅ Yes' if not has_duplicates else '❌ No'}")
    
    # Test 3: Price data
    print("\n📊 Test 3: Price data analysis")
    print("-" * 40)
    
    closes = [c[4] for c in ohlcv]
    min_price = min(closes)
    max_price = max(closes)
    latest_price = closes[-1]
    print(f"   Price range: ${min_price:,.0f} - ${max_price:,.0f}")
    print(f"   Latest daily close: ${latest_price:,.0f}")
    
    # Test 4: Time coverage
    print("\n📊 Test 4: Time coverage")
    print("-" * 40)
    from datetime import datetime
    first_date = datetime.fromtimestamp(timestamps[0] / 1000)
    last_date = datetime.fromtimestamp(timestamps[-1] / 1000)
    days_covered = (last_date - first_date).days
    print(f"   First candle: {first_date.strftime('%Y-%m-%d')}")
    print(f"   Last candle:  {last_date.strftime('%Y-%m-%d')}")
    print(f"   Days covered: {days_covered}")
    
    # Test 5: Calculate EMAs to verify
    print("\n📊 Test 5: EMA calculation verification")
    print("-" * 40)
    import pandas as pd
    closes_series = pd.Series(closes)
    
    ema20 = closes_series.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = closes_series.ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = closes_series.ewm(span=200, adjust=False).mean().iloc[-1]
    
    print(f"   EMA20:  ${ema20:,.0f}")
    print(f"   EMA50:  ${ema50:,.0f}")
    print(f"   EMA200: ${ema200:,.0f}")
    print(f"   Latest: ${latest_price:,.0f}")
    
    # Market state
    if latest_price > ema200:
        print(f"   📈 Market above EMA200 (SUMMER mode)")
    else:
        print(f"   📉 Market below EMA200 (WINTER mode)")
    
    # Final summary
    print("\n" + "="*60)
    print("📋 SUMMARY - Daily Levels Architecture")
    print("="*60)
    print(f"   Total candles: {len(ohlcv)} DAILY")
    print(f"   History:       {days_covered} days (~{days_covered/365:.1f} years)")
    print(f"   EMA200 ready:  {'✅ Yes' if len(ohlcv) >= 200 else '❌ No'}")
    
    if len(ohlcv) >= EMA_SLOW and is_sorted and not has_duplicates:
        print("\n   🎉 ALL TESTS PASSED!")
        print("   ✅ Architecture: Daily Levels / 4H Execution is READY")
        return True
    else:
        print("\n   ❌ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = test_daily_data()
    sys.exit(0 if success else 1)
