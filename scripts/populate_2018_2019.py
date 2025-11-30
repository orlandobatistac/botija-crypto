"""
Populate AI regimes for 2018-2019 using same prompt/API as 2020+
"""

import os
import sys
import json
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI
import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    buffer_start = start_date - timedelta(days=60)
    btc = yf.Ticker("BTC-USD")
    df = btc.history(start=buffer_start.isoformat(), end=(end_date + timedelta(days=7)).isoformat())

    if df.empty:
        raise ValueError("Could not fetch BTC data")

    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Returns'] = df['Close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=7).std() * 100
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['High_52w'] = df['Close'].rolling(window=252, min_periods=1).max()
    df['Low_52w'] = df['Close'].rolling(window=252, min_periods=1).min()

    return df


def get_week_data(df: pd.DataFrame, week_start: date) -> dict:
    """Extract market data for a specific week."""
    week_start_ts = pd.Timestamp(week_start, tz='UTC')
    mask = df.index >= week_start_ts
    if not mask.any():
        return None

    idx = df.index[mask][0]
    row = df.loc[idx]

    price = row['Close']

    # 7-day change
    idx_7d = df.index.get_indexer([idx - pd.Timedelta(days=7)], method='nearest')[0]
    price_7d = df.iloc[idx_7d]['Close'] if idx_7d >= 0 else price
    change_7d = ((price - price_7d) / price_7d * 100) if price_7d > 0 else 0

    # 30-day change
    idx_30d = df.index.get_indexer([idx - pd.Timedelta(days=30)], method='nearest')[0]
    price_30d = df.iloc[idx_30d]['Close'] if idx_30d >= 0 else price
    change_30d = ((price - price_30d) / price_30d * 100) if price_30d > 0 else 0

    ema_signal = "BULLISH" if row['EMA20'] > row['EMA50'] else "BEARISH"
    volume_ratio = row['Volume'] / row['Volume_MA20'] if row['Volume_MA20'] > 0 else 1.0
    vs_52w_high = ((price - row['High_52w']) / row['High_52w'] * 100) if row['High_52w'] > 0 else 0
    vs_52w_low = ((price - row['Low_52w']) / row['Low_52w'] * 100) if row['Low_52w'] > 0 else 0

    return {
        'price': price,
        'change_7d': change_7d,
        'change_30d': change_30d,
        'rsi': row['RSI'] if pd.notna(row['RSI']) else 50,
        'ema_signal': ema_signal,
        'volatility': row['Volatility'] if pd.notna(row['Volatility']) else 2.0,
        'volume_ratio': volume_ratio if pd.notna(volume_ratio) else 1.0,
        'vs_52w_high': vs_52w_high,
        'vs_52w_low': vs_52w_low
    }


def get_weeks(start: date, end: date) -> list:
    """Generate list of Monday dates."""
    weeks = []
    current = start - timedelta(days=start.weekday())
    while current <= end:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks


def fetch_regime_single(week_start: date, market_data: dict) -> tuple:
    """Fetch regime from OpenAI for a single week."""
    prompt = PROMPT_TEMPLATE.format(
        week_start=week_start.isoformat(),
        **market_data
    )

    response = client.chat.completions.create(
        model="gpt-4.1",  # Usar modelo disponible
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    tokens = response.usage.total_tokens
    data = json.loads(content)
    data['week_start'] = week_start.isoformat()

    return data, tokens


def save_regime(db_path: str, regime: dict) -> bool:
    """Save regime to database."""
    try:
        week_start_str = regime.get("week_start")
        week_start_date = date.fromisoformat(week_start_str)
        week_end_date = week_start_date + timedelta(days=6)

        conn = sqlite3.connect(db_path)
        conn.execute("""
            INSERT OR REPLACE INTO ai_market_regimes
            (week_start, week_end, regime, buy_threshold, sell_threshold,
             capital_percent, atr_multiplier, stop_loss_percent,
             confidence, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            week_start_str,
            week_end_date.isoformat(),
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
        print(f"   ⚠️ Error saving: {e}")
        return False


def main():
    """Populate 2018-2019 regimes."""
    start = date(2018, 1, 1)
    end = date(2019, 12, 31)

    db_path = Path(__file__).parent.parent / "backend" / "data" / "trading_bot.db"

    print("=" * 60)
    print("🤖 POPULATING 2018-2019 WITH AI REGIMES")
    print("=" * 60)
    print(f"📅 Period: {start} to {end}")

    print("\n📊 Fetching BTC historical data...")
    try:
        btc_data = fetch_btc_data(start, end)
        print(f"   ✅ Got {len(btc_data)} days of data")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    all_weeks = get_weeks(start, end)
    print(f"📆 Total weeks to process: {len(all_weeks)}")

    # Check existing
    conn = sqlite3.connect(str(db_path))
    existing = conn.execute(
        "SELECT week_start FROM ai_market_regimes WHERE week_start < '2020-01-01'"
    ).fetchall()
    conn.close()
    existing_dates = set(r[0] for r in existing)
    print(f"   Already have: {len(existing_dates)} weeks")

    # Filter weeks to process
    weeks_to_process = [w for w in all_weeks if w.isoformat() not in existing_dates]
    print(f"   Need to process: {len(weeks_to_process)} weeks")

    if not weeks_to_process:
        print("\n✅ All weeks already populated!")
        return

    input(f"\n⚠️ This will make {len(weeks_to_process)} API calls. Press Enter to continue...")

    total_tokens = 0
    regime_counts = {"BULL": 0, "BEAR": 0, "LATERAL": 0, "VOLATILE": 0}

    for i, week_start in enumerate(weeks_to_process):
        print(f"\n🔄 Week {i+1}/{len(weeks_to_process)}: {week_start}", end=" ")

        try:
            market_data = get_week_data(btc_data, week_start)
            if market_data is None:
                print("⚠️ No data")
                continue

            regime, tokens = fetch_regime_single(week_start, market_data)
            total_tokens += tokens

            if save_regime(str(db_path), regime):
                r = regime.get("regime", "UNKNOWN")
                regime_counts[r] = regime_counts.get(r, 0) + 1
                print(f"→ {r} (${market_data['price']:,.0f}, RSI:{market_data['rsi']:.0f}) [{tokens} tokens]")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(0.5)

    estimated_cost = (total_tokens / 1_000_000) * 5

    print("\n" + "=" * 60)
    print(f"✅ COMPLETED: {sum(regime_counts.values())} weeks")
    print(f"💰 Tokens: {total_tokens:,} (~${estimated_cost:.2f})")
    print("=" * 60)

    print("\n📊 Regime distribution (2018-2019):")
    for regime, count in sorted(regime_counts.items()):
        pct = (count / sum(regime_counts.values()) * 100) if sum(regime_counts.values()) > 0 else 0
        print(f"   {regime}: {count} weeks ({pct:.1f}%)")


if __name__ == "__main__":
    main()
