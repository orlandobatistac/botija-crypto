"""
Batch API script to populate AI regimes efficiently.
Uses OpenAI Batch API for 50% cost savings and no rate limiting.

Commands:
    python scripts/populate_batch.py submit    - Create and submit batch job
    python scripts/populate_batch.py status    - Check batch status
    python scripts/populate_batch.py download  - Download results and populate DB
"""

import os
import sys
import json
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

# Paths
SCRIPT_DIR = Path(__file__).parent
BATCH_FILE = SCRIPT_DIR / "batch_requests.jsonl"
BATCH_ID_FILE = SCRIPT_DIR / "batch_id.txt"
DB_PATH = SCRIPT_DIR.parent / "backend" / "data" / "trading_bot.db"

# Prompt template (IDENTICAL to production ai_regime.py)
PROMPT_TEMPLATE = """You are an AGGRESSIVE BTC swing trader analyzing this day.
Date: {date}

=== REAL MARKET DATA (no simulation) ===
Current Price: ${price:,.0f}
7-day Change: {change_7d:+.1f}%
30-day Change: {change_30d:+.1f}%
RSI (14): {rsi:.1f}
EMA20 vs EMA50: {ema_signal}
Weekly Volatility: {volatility:.1f}%
Volume vs 20-day avg: {volume_ratio:.1f}x
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

    # Calculate indicators
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Volatility
    df['Returns'] = df['Close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=7).std() * 100

    # Volume moving average
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()

    # 52-week high/low
    df['High_52w'] = df['Close'].rolling(window=252, min_periods=1).max()
    df['Low_52w'] = df['Close'].rolling(window=252, min_periods=1).min()

    return df


def get_day_data(df: pd.DataFrame, target_date: date) -> dict:
    """Extract market data for a specific day."""
    target_ts = pd.Timestamp(target_date, tz='UTC')

    mask = df.index >= target_ts
    if not mask.any():
        return None

    idx = df.index[mask][0]
    row = df.loc[idx]
    price = row['Close']

    # 7-day change
    past_idx = df.index[df.index <= idx]
    if len(past_idx) > 7:
        price_7d = df.loc[past_idx[-8], 'Close']
        change_7d = ((price - price_7d) / price_7d) * 100
    else:
        change_7d = 0

    # 30-day change
    if len(past_idx) > 30:
        price_30d = df.loc[past_idx[-31], 'Close']
        change_30d = ((price - price_30d) / price_30d) * 100
    else:
        change_30d = 0

    ema_signal = "BULLISH" if row['EMA20'] > row['EMA50'] else "BEARISH"
    vs_52w_high = ((price - row['High_52w']) / row['High_52w']) * 100
    vs_52w_low = ((price - row['Low_52w']) / row['Low_52w']) * 100

    # Volume ratio
    volume_ratio = row['Volume'] / row['Volume_MA20'] if row['Volume_MA20'] > 0 else 1.0

    return {
        'price': price,
        'change_7d': change_7d,
        'change_30d': change_30d,
        'rsi': row['RSI'] if not pd.isna(row['RSI']) else 50,
        'ema_signal': ema_signal,
        'volatility': row['Volatility'] if not pd.isna(row['Volatility']) else 2.0,
        'volume_ratio': volume_ratio if not pd.isna(volume_ratio) else 1.0,
        'vs_52w_high': vs_52w_high,
        'vs_52w_low': vs_52w_low
    }


def create_batch_file():
    """Create JSONL file with all batch requests."""
    start = date(2018, 1, 1)
    end = date(2025, 11, 30)

    print("=" * 60)
    print("📦 CREATING BATCH REQUEST FILE")
    print("=" * 60)

    # Fetch BTC data
    print("\n📊 Fetching BTC historical data...")
    btc_data = fetch_btc_data(start, end)
    print(f"   ✅ Got {len(btc_data)} days of data")

    # Generate all days
    all_days = []
    current = start
    while current <= end:
        all_days.append(current)
        current += timedelta(days=1)
    print(f"📆 Total days to process: {len(all_days)}")

    # Create JSONL file
    print(f"\n📝 Writing batch requests to {BATCH_FILE}...")
    requests_written = 0

    with open(BATCH_FILE, 'w') as f:
        for day in all_days:
            market_data = get_day_data(btc_data, day)
            if market_data is None:
                continue

            prompt = PROMPT_TEMPLATE.format(date=day.isoformat(), **market_data)

            request = {
                "custom_id": day.isoformat(),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-5",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
            }

            f.write(json.dumps(request) + "\n")
            requests_written += 1

    print(f"   ✅ Written {requests_written} requests")
    return requests_written


def submit_batch():
    """Submit batch job to OpenAI."""
    if not BATCH_FILE.exists():
        print("❌ Batch file not found. Creating it first...")
        create_batch_file()

    print("\n📤 Uploading batch file to OpenAI...")
    with open(BATCH_FILE, 'rb') as f:
        batch_file = client.files.create(file=f, purpose="batch")
    print(f"   ✅ File uploaded: {batch_file.id}")

    print("\n🚀 Creating batch job...")
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    # Save batch ID
    with open(BATCH_ID_FILE, 'w') as f:
        f.write(batch.id)

    print(f"   ✅ Batch created: {batch.id}")
    print(f"\n📋 Status: {batch.status}")
    print(f"💾 Batch ID saved to {BATCH_ID_FILE}")
    print("\n⏳ Run 'python scripts/populate_batch.py status' to check progress")


def check_status():
    """Check batch job status."""
    if not BATCH_ID_FILE.exists():
        print("❌ No batch ID found. Run 'submit' first.")
        return None

    batch_id = BATCH_ID_FILE.read_text().strip()
    batch = client.batches.retrieve(batch_id)

    print("=" * 60)
    print(f"📋 BATCH STATUS: {batch.id}")
    print("=" * 60)
    print(f"   Status: {batch.status}")
    print(f"   Completed: {batch.request_counts.completed}/{batch.request_counts.total}")
    print(f"   Failed: {batch.request_counts.failed}")

    if batch.status == "completed":
        print("\n✅ BATCH COMPLETED!")
        print("   Run 'python scripts/populate_batch.py download' to get results")
    elif batch.status == "failed":
        print(f"\n❌ BATCH FAILED")
        if batch.errors:
            for error in batch.errors.data:
                print(f"   Error: {error.message}")
    elif batch.status == "in_progress":
        pct = (batch.request_counts.completed / batch.request_counts.total) * 100
        print(f"\n⏳ Progress: {pct:.1f}%")

    return batch


def download_results():
    """Download batch results and populate database."""
    if not BATCH_ID_FILE.exists():
        print("❌ No batch ID found. Run 'submit' first.")
        return

    batch_id = BATCH_ID_FILE.read_text().strip()
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        print(f"❌ Batch not completed yet. Status: {batch.status}")
        return

    print("=" * 60)
    print("📥 DOWNLOADING BATCH RESULTS")
    print("=" * 60)

    # Download results
    print("\n📥 Downloading results file...")
    result_file = client.files.content(batch.output_file_id)
    results_text = result_file.text

    # Parse results
    results = [json.loads(line) for line in results_text.strip().split('\n')]
    print(f"   ✅ Got {len(results)} results")

    # Initialize database
    print("\n💾 Populating database...")
    init_database()

    # Process results
    regime_counts = {"BULL": 0, "BEAR": 0, "LATERAL": 0, "VOLATILE": 0}
    saved = 0
    errors = 0

    for result in results:
        try:
            day = result['custom_id']
            response = result['response']

            if response['status_code'] != 200:
                errors += 1
                continue

            content = response['body']['choices'][0]['message']['content']
            data = json.loads(content)
            data['week_start'] = day

            if save_regime(data):
                saved += 1
                regime = data.get('regime', 'UNKNOWN')
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
        except Exception as e:
            errors += 1

    print(f"   ✅ Saved: {saved}")
    print(f"   ❌ Errors: {errors}")

    print("\n📊 Regime distribution:")
    for regime, count in sorted(regime_counts.items()):
        pct = (count / saved * 100) if saved > 0 else 0
        print(f"   {regime}: {count} days ({pct:.1f}%)")

    # Cleanup
    print("\n🧹 Cleaning up...")
    BATCH_FILE.unlink(missing_ok=True)
    BATCH_ID_FILE.unlink(missing_ok=True)
    print("   ✅ Done!")


def init_database():
    """Create table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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


def save_regime(regime: dict) -> bool:
    """Save a single regime to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        day = regime.get("week_start")
        if not day:
            return False

        cursor.execute("""
            INSERT OR REPLACE INTO ai_market_regimes
            (week_start, week_end, regime, buy_threshold, sell_threshold,
             capital_percent, atr_multiplier, stop_loss_percent, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            day,
            day,  # week_end = same day for daily granularity
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
        conn.close()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/populate_batch.py submit   - Create and submit batch")
        print("  python scripts/populate_batch.py status   - Check batch status")
        print("  python scripts/populate_batch.py download - Download results to DB")
        return

    command = sys.argv[1].lower()

    if command == "submit":
        create_batch_file()
        submit_batch()
    elif command == "status":
        check_status()
    elif command == "download":
        download_results()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
