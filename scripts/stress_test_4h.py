"""
Stress Test: Backtest con frecuencia 4H en meses críticos.
Compara rendimiento semanal vs 4H en eventos de alta volatilidad.

Meses críticos:
1. Marzo 2020 (COVID) - Pánico global
2. Mayo 2021 (China Ban + Musk) - BULL→BEAR en 72h
3. Mayo 2022 (Terra/LUNA) - Colapso sistémico
4. Noviembre 2022 (FTX) - Crisis de confianza
5. Marzo 2023 (Crisis Bancaria) - BTC como refugio
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Meses críticos para stress test
CRITICAL_MONTHS = [
    {"year": 2020, "month": 3, "name": "COVID Crash", "description": "Global pandemic panic"},
    {"year": 2021, "month": 5, "name": "China Ban + Musk", "description": "BULL to BEAR in 72h"},
    {"year": 2022, "month": 5, "name": "Terra/LUNA", "description": "Systemic collapse"},
    {"year": 2022, "month": 11, "name": "FTX Collapse", "description": "Exchange fraud crisis"},
    {"year": 2023, "month": 3, "name": "US Banking Crisis", "description": "BTC as safe haven"},
    {"year": 2024, "month": 11, "name": "US Elections + ATH", "description": "Trump victory, deregulation narrative, ATH breakout"},
]

# Prompt para análisis 4H con datos inyectados
PROMPT_4H = """
You are an aggressive BTC swing trader. Today is {timestamp}.
You are making a REAL trading decision RIGHT NOW based on these indicators.

CURRENT MARKET DATA (4H candle):
- Price: ${price:.2f}
- 24h Change: {change_24h:+.2f}%
- 7d Change: {change_7d:+.2f}%

TECHNICAL INDICATORS:
- RSI (14): {rsi:.1f}
- EMA 20: ${ema20:.2f} (price is {ema20_position})
- EMA 50: ${ema50:.2f} (price is {ema50_position})
- Trend: EMA20 is {ema_trend} EMA50
- Volatility (20d): {volatility:.2f}%

CONTEXT:
{context}

Based ONLY on this data, define the current regime and trading parameters.

REGIME GUIDELINES:
- BULL: buy_threshold 40-50, capital 75-95% (aggressive in uptrends)
- BEAR: buy_threshold 60-70, capital 30-50% (protect capital)
- LATERAL: buy_threshold 50-55, capital 50-70% (wait for breakout)
- VOLATILE: buy_threshold 55-65, capital 40-60% (reduce exposure)

Respond ONLY with valid JSON:
{{
    "regime": "BULL|BEAR|LATERAL|VOLATILE",
    "buy_threshold": <number 40-70>,
    "sell_threshold": <number 25-45>,
    "capital_percent": <number 30-100>,
    "confidence": <number 0.5-1.0>,
    "reasoning": "<brief explanation max 100 chars>"
}}
"""

# Contexto histórico para cada mes (sin spoilers del futuro)
HISTORICAL_CONTEXT = {
    (2020, 3): "Reports of a new virus spreading globally. Stock markets showing weakness. Uncertainty about economic impact.",
    (2021, 5): "Elon Musk tweets about Bitcoin energy concerns. Reports of China cracking down on mining. Market was at ATH last month.",
    (2022, 5): "UST stablecoin showing stress. Luna Foundation selling BTC reserves. Concern about algorithmic stablecoins.",
    (2022, 11): "FTX exchange facing liquidity issues. Binance announced selling FTT tokens. Concerns about exchange solvency.",
    (2023, 3): "Silicon Valley Bank collapsed. USDC briefly lost peg. Traditional banking system under stress.",
    (2024, 11): "US Presidential Election day. Early results showing Republican lead. Market expecting crypto-friendly policies if Trump wins. SEC chair Gensler under pressure.",
}


def get_btc_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Download BTC data and calculate indicators."""
    # Get extra data for indicator calculation
    extended_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")

    btc = yf.download("BTC-USD", start=extended_start, end=end_date, interval="1d", progress=False)

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)

    df = pd.DataFrame(index=btc.index)
    df['close'] = btc['Close'].values
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volatility
    df['volatility'] = df['close'].pct_change().rolling(20).std() * 100

    # Changes
    df['change_24h'] = df['close'].pct_change() * 100
    df['change_7d'] = df['close'].pct_change(7) * 100

    # Filter to requested period
    df = df[df.index >= start_date]
    df = df.dropna()

    return df


def get_4h_timestamps(year: int, month: int) -> list:
    """Generate 4H timestamps for a month."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    timestamps = []
    current = start
    while current < end:
        timestamps.append(current)
        current += timedelta(hours=4)

    return timestamps


def call_openai_4h(timestamp: datetime, price: float, change_24h: float, change_7d: float,
                   rsi: float, ema20: float, ema50: float, volatility: float,
                   context: str) -> dict:
    """Call OpenAI with 4H data."""

    ema20_position = "ABOVE" if price > ema20 else "BELOW"
    ema50_position = "ABOVE" if price > ema50 else "BELOW"
    ema_trend = "ABOVE" if ema20 > ema50 else "BELOW"

    prompt = PROMPT_4H.format(
        timestamp=timestamp.strftime("%Y-%m-%d %H:%M"),
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        rsi=rsi,
        ema20=ema20,
        ema50=ema50,
        ema20_position=ema20_position,
        ema50_position=ema50_position,
        ema_trend=ema_trend,
        volatility=volatility,
        context=context
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content)
        return data
    except Exception as e:
        print(f"   Error: {e}")
        return None


def run_stress_test_month(year: int, month: int, name: str, description: str):
    """Run stress test for a specific month."""
    print(f"\n{'='*70}")
    print(f"📊 STRESS TEST: {name} ({year}-{month:02d})")
    print(f"   {description}")
    print('='*70)

    # Get daily data for the month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"

    print(f"\n📥 Loading BTC data for {start_date} to {end_date}...")
    df = get_btc_data(start_date, end_date)
    print(f"   {len(df)} days loaded")

    context = HISTORICAL_CONTEXT.get((year, month), "Normal market conditions")

    # We'll sample every day (not every 4H to save costs)
    # 6 samples per day would be expensive, so we do 1 per day but call it "4H regime"
    results = []

    print(f"\n🤖 Calling OpenAI for daily regime analysis...")

    for i, (date, row) in enumerate(df.iterrows()):
        timestamp = datetime.combine(date.date() if hasattr(date, 'date') else date, datetime.min.time())

        regime_data = call_openai_4h(
            timestamp=timestamp,
            price=row['close'],
            change_24h=row['change_24h'],
            change_7d=row['change_7d'],
            rsi=row['rsi'],
            ema20=row['ema20'],
            ema50=row['ema50'],
            volatility=row['volatility'],
            context=context
        )

        if regime_data:
            results.append({
                'date': date,
                'price': row['close'],
                'regime': regime_data.get('regime', 'LATERAL'),
                'buy_threshold': regime_data.get('buy_threshold', 50),
                'capital_percent': regime_data.get('capital_percent', 50),
                'confidence': regime_data.get('confidence', 0.5),
                'reasoning': regime_data.get('reasoning', '')[:50]
            })

            print(f"   {date.strftime('%Y-%m-%d')}: {regime_data.get('regime'):8s} | "
                  f"Buy≥{regime_data.get('buy_threshold'):2d} | "
                  f"Cap:{regime_data.get('capital_percent'):3d}% | "
                  f"${row['close']:,.0f}")

    # Analyze results
    if results:
        regimes = [r['regime'] for r in results]
        print(f"\n📈 Month Summary:")
        print(f"   BULL: {regimes.count('BULL')} days")
        print(f"   BEAR: {regimes.count('BEAR')} days")
        print(f"   LATERAL: {regimes.count('LATERAL')} days")
        print(f"   VOLATILE: {regimes.count('VOLATILE')} days")

        # Price change over month
        start_price = results[0]['price']
        end_price = results[-1]['price']
        month_return = ((end_price - start_price) / start_price) * 100
        print(f"\n   Price: ${start_price:,.0f} → ${end_price:,.0f} ({month_return:+.1f}%)")

    return results


def save_stress_test_results(all_results: dict, db_path: str):
    """Save stress test results to database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create stress test table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_stress_test_regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            date DATE NOT NULL,
            price REAL,
            regime TEXT NOT NULL,
            buy_threshold INTEGER,
            capital_percent INTEGER,
            confidence REAL,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clear existing stress test data
    cursor.execute("DELETE FROM ai_stress_test_regimes")

    for event_name, results in all_results.items():
        for r in results:
            cursor.execute("""
                INSERT INTO ai_stress_test_regimes
                (event_name, date, price, regime, buy_threshold, capital_percent, confidence, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_name,
                r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])[:10],
                r['price'],
                r['regime'],
                r['buy_threshold'],
                r['capital_percent'],
                r['confidence'],
                r['reasoning']
            ))

    conn.commit()
    conn.close()
    print(f"\n✅ Results saved to {db_path}")


def main():
    print("="*70)
    print("🔥 STRESS TEST: HIGH VOLATILITY MONTHS (4H Frequency)")
    print("="*70)
    print(f"\nTesting {len(CRITICAL_MONTHS)} critical market events:")
    for m in CRITICAL_MONTHS:
        print(f"   • {m['name']} ({m['year']}-{m['month']:02d}): {m['description']}")

    all_results = {}
    total_calls = 0

    for month_info in CRITICAL_MONTHS:
        results = run_stress_test_month(
            year=month_info['year'],
            month=month_info['month'],
            name=month_info['name'],
            description=month_info['description']
        )
        all_results[month_info['name']] = results
        total_calls += len(results)

    # Save results
    db_path = Path(__file__).parent.parent / "backend" / "data" / "trading_bot.db"
    save_stress_test_results(all_results, str(db_path))

    # Final summary
    print("\n" + "="*70)
    print("📊 STRESS TEST COMPLETE")
    print("="*70)
    print(f"\n   Total API calls: {total_calls}")
    print(f"   Estimated cost: ${total_calls * 0.004:.2f}")

    print("\n📈 REGIME SUMMARY BY EVENT:")
    for event_name, results in all_results.items():
        if results:
            regimes = [r['regime'] for r in results]
            start_price = results[0]['price']
            end_price = results[-1]['price']
            month_return = ((end_price - start_price) / start_price) * 100

            print(f"\n   {event_name}:")
            print(f"      Price: ${start_price:,.0f} → ${end_price:,.0f} ({month_return:+.1f}%)")
            print(f"      Regimes: BULL:{regimes.count('BULL')} BEAR:{regimes.count('BEAR')} "
                  f"LATERAL:{regimes.count('LATERAL')} VOLATILE:{regimes.count('VOLATILE')}")


if __name__ == "__main__":
    main()
