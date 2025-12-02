"""
Script to populate database with AI-analyzed market regimes.
Generates optimal trading parameters per week based on REAL historical data.
Uses yfinance to inject actual price/indicator data into prompts.
"""

import os
import sys
import json
import time
from datetime import date, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI
import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Prompt template with REAL data injection
PROMPT_TEMPLATE = """You are an AGGRESSIVE BTC swing trader analyzing this week.
Date: {week_start}

=== REAL MARKET DATA (no simulation) ===
Current Price: ${price:,.0f}
7-day Change: {change_7d:+.1f}%
30-day Change: {change_30d:+.1f}%
RSI (14): {rsi:.1f}
EMA20 vs EMA50: {ema_signal}
Weekly Volatility: {volatility:.1f}%
Volume vs 20-week avg: {volume_ratio:.1f}x
Price vs 52-week High: {vs_52w_high:.1f}%
Price vs 52-week Low: {vs_52w_low:+.1f}%

=== REGIME GUIDELINES ===
BULL (strong uptrend): buy_threshold 40-50, capital 80-95%
  - RSI < 70, price above EMAs, positive momentum
BEAR (strong downtrend): buy_threshold 60-70, capital 30-50%
  - RSI > 30 (oversold = opportunity), price below EMAs
LATERAL (consolidation): buy_threshold 50-55, capital 50-70%
  - RSI 40-60, price between EMAs, low volatility
VOLATILE (high uncertainty): buy_threshold 55-65, capital 40-60%
  - Wide price swings, news-driven, elevated volatility

=== IMPORTANT ===
- Be AGGRESSIVE in clear trends (BULL/BEAR)
- Only use VOLATILE when volatility is extreme (>5% weekly)
- LATERAL is for genuine consolidation, not uncertainty
- Lower buy_threshold = more trades = better for swing trading

Respond ONLY with this JSON format:
{{
  "regime": "BULL|BEAR|LATERAL|VOLATILE",
  "buy_threshold": 45,
  "sell_threshold": 35,
  "capital_percent": 85,
  "atr_multiplier": 1.5,
  "stop_loss_percent": 2.5,
  "confidence": 0.8,
  "reasoning": "Brief explanation (max 80 chars)"
}}
"""


def fetch_btc_data(start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch BTC historical data from yfinance."""
    # Add buffer for indicator calculations
    buffer_start = start_date - timedelta(days=60)

    btc = yf.Ticker("BTC-USD")
    df = btc.history(start=buffer_start.isoformat(), end=(end_date + timedelta(days=7)).isoformat())

    if df.empty:
        raise ValueError("Could not fetch BTC data from yfinance")

    # Calculate indicators
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Volatility (weekly returns std)
    df['Returns'] = df['Close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=7).std() * 100

    # Volume moving average
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()

    # 52-week high/low
    df['High_52w'] = df['Close'].rolling(window=252, min_periods=1).max()
    df['Low_52w'] = df['Close'].rolling(window=252, min_periods=1).min()

    return df


def get_week_data(df: pd.DataFrame, week_start: date) -> dict:
    """Extract market data for a specific week."""
    # Make timezone-aware to match yfinance data
    week_start_ts = pd.Timestamp(week_start, tz='UTC')

    # Find the closest trading day
    mask = df.index >= week_start_ts
    if not mask.any():
        return None

    idx = df.index[mask][0]
    row = df.loc[idx]

    # Get historical prices for change calculations
    price = row['Close']

    # 7-day change
    past_7d = df.index[df.index <= idx][-8:-1] if len(df.index[df.index <= idx]) > 7 else df.index[:1]
    if len(past_7d) > 0:
        price_7d_ago = df.loc[past_7d[0], 'Close']
        change_7d = ((price - price_7d_ago) / price_7d_ago) * 100
    else:
        change_7d = 0

    # 30-day change
    past_30d = df.index[df.index <= idx]
    if len(past_30d) > 30:
        price_30d_ago = df.loc[past_30d[-31], 'Close']
        change_30d = ((price - price_30d_ago) / price_30d_ago) * 100
    else:
        change_30d = 0

    # EMA signal
    ema_signal = "ABOVE (bullish)" if row['EMA20'] > row['EMA50'] else "BELOW (bearish)"

    # Volume ratio
    volume_ratio = row['Volume'] / row['Volume_MA20'] if row['Volume_MA20'] > 0 else 1.0

    # 52-week comparisons
    vs_52w_high = ((price - row['High_52w']) / row['High_52w']) * 100
    vs_52w_low = ((price - row['Low_52w']) / row['Low_52w']) * 100

    return {
        'price': price,
        'change_7d': change_7d,
        'change_30d': change_30d,
        'rsi': row['RSI'] if not pd.isna(row['RSI']) else 50,
        'ema_signal': ema_signal,
        'volatility': row['Volatility'] if not pd.isna(row['Volatility']) else 2.0,
        'volume_ratio': volume_ratio,
        'vs_52w_high': vs_52w_high,
        'vs_52w_low': vs_52w_low
    }


def get_weeks(start: date, end: date) -> list[date]:
    """Generate list of week start dates (Mondays)."""
    weeks = []
    current = start - timedelta(days=start.weekday())  # Adjust to Monday
    while current <= end:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks


def get_days(start: date, end: date) -> list[date]:
    """Generate list of all dates."""
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def fetch_regime_single(week_start: date, market_data: dict) -> dict:
    """Call OpenAI for a single week with real market data."""

    prompt = PROMPT_TEMPLATE.format(
        week_start=week_start.isoformat(),
        **market_data
    )

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    tokens = response.usage.total_tokens

    data = json.loads(content)
    data['week_start'] = week_start.isoformat()

    return data, tokens


def init_database(db_path: str):
    """Create table if not exists."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing table to repopulate
    cursor.execute("DROP TABLE IF EXISTS ai_market_regimes")

    cursor.execute("""
        CREATE TABLE ai_market_regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL UNIQUE,
            week_end DATE NOT NULL,
            regime TEXT NOT NULL,
            buy_threshold INTEGER DEFAULT 50,
            sell_threshold INTEGER DEFAULT 35,
            capital_percent INTEGER DEFAULT 75,
            atr_multiplier REAL DEFAULT 1.5,
            stop_loss_percent REAL DEFAULT 2.0,
            confidence REAL DEFAULT 0.7,
            reasoning TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_week_start ON ai_market_regimes(week_start)")

    conn.commit()
    conn.close()
    print("✅ Table ai_market_regimes created (daily granularity)")


def save_regime(db_path: str, regime: dict) -> bool:
    """Save a single regime to database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        week_start = regime.get("week_start")
        if not week_start:
            return False

        week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO ai_market_regimes
            (week_start, week_end, regime, buy_threshold, sell_threshold,
             capital_percent, atr_multiplier, stop_loss_percent, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            week_start,
            week_end,
            regime.get("regime", "LATERAL"),
            regime.get("buy_threshold", 50),
            regime.get("sell_threshold", 35),
            regime.get("capital_percent", 75),
            regime.get("atr_multiplier", 1.5),
            regime.get("stop_loss_percent", 2.0),
            regime.get("confidence", 0.7),
            regime.get("reasoning", "")
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"   ⚠️ Error saving {regime}: {e}")
        conn.close()
        return False


def populate_database():
    """Populate DB with AI regimes using REAL market data (DAILY granularity)."""
    start = date(2018, 1, 1)
    end = date(2025, 11, 30)

    db_path = Path(__file__).parent.parent / "backend" / "data" / "trading_bot.db"

    print("=" * 60)
    print("🤖 POPULATING DATABASE WITH AI REGIMES (DAILY - gpt-5-nano)")
    print("=" * 60)
    print(f"📅 Period: {start} to {end}")

    # Fetch all BTC data first
    print("\n📊 Fetching BTC historical data from yfinance...")
    try:
        btc_data = fetch_btc_data(start, end)
        print(f"   ✅ Got {len(btc_data)} days of data")
    except Exception as e:
        print(f"   ❌ Error fetching data: {e}")
        return

    # Generate days (not weeks)
    all_days = get_days(start, end)
    print(f"📆 Total days: {len(all_days)}")

    # Initialize DB
    init_database(str(db_path))

    # Process each day individually with real data
    all_regimes = []
    total_tokens = 0
    regime_counts = {"BULL": 0, "BEAR": 0, "LATERAL": 0, "VOLATILE": 0}

    for i, day in enumerate(all_days):
        # Progress every 50 days
        if i % 50 == 0:
            print(f"\n📅 Progress: {i}/{len(all_days)} days ({i*100//len(all_days)}%)")

        try:
            # Get real market data for this day
            market_data = get_week_data(btc_data, day)

            if market_data is None:
                continue

            # Call OpenAI with real data
            regime, tokens = fetch_regime_single(day, market_data)
            total_tokens += tokens

            # Save to DB (reusing week_start field for date)
            regime['week_start'] = day.isoformat()
            if save_regime(str(db_path), regime):
                all_regimes.append(regime)
                r = regime.get("regime", "UNKNOWN")
                regime_counts[r] = regime_counts.get(r, 0) + 1

            # Print every 100 days
            if i % 100 == 0:
                print(f"   {day}: {r} (${market_data['price']:,.0f}) [{tokens} tok]")

        except Exception as e:
            if i % 100 == 0:
                print(f"   {day}: ❌ {e}")

        # Rate limiting - minimal delay for nano model
        if i < len(all_days) - 1:
            time.sleep(0.1)

    # Calculate cost (gpt-5-nano: $0.025/1M input, $0.20/1M output)
    estimated_cost = (total_tokens / 1_000_000) * 0.15  # Average ~$0.15/1M

    print("\n" + "=" * 60)
    print(f"✅ COMPLETED: {len(all_regimes)} days processed")
    print(f"💰 Total tokens: {total_tokens:,} (~${estimated_cost:.2f})")
    print(f"📁 Database: {db_path}")
    print("=" * 60)

    # Show summary
    print("\n📊 Regime distribution:")
    for regime, count in sorted(regime_counts.items()):
        pct = (count / len(all_regimes) * 100) if all_regimes else 0
        print(f"   {regime}: {count} days ({pct:.1f}%)")


if __name__ == "__main__":
    populate_database()
