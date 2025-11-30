"""Quick stress test for November 2024 only."""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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

REGIME GUIDELINES:
- BULL: buy_threshold 40-50, capital 75-95%
- BEAR: buy_threshold 60-70, capital 30-50%
- LATERAL: buy_threshold 50-55, capital 50-70%
- VOLATILE: buy_threshold 55-65, capital 40-60%

Respond ONLY with valid JSON:
{{"regime": "BULL or BEAR or LATERAL or VOLATILE", "buy_threshold": 40-70, "sell_threshold": 25-45, "capital_percent": 30-100, "confidence": 0.5-1.0, "reasoning": "max 100 chars"}}
"""

print('='*70)
print('📊 STRESS TEST: US Elections + ATH (2024-11)')
print('   Trump victory, deregulation narrative, ATH breakout')
print('='*70)

# Get data
extended_start = '2024-09-01'
end_date = '2024-12-01'
btc = yf.download('BTC-USD', start=extended_start, end=end_date, interval='1d', progress=False)
if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

df = pd.DataFrame(index=btc.index)
df['close'] = btc['Close'].values
df['ema20'] = df['close'].ewm(span=20).mean()
df['ema50'] = df['close'].ewm(span=50).mean()
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))
df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
df['change_24h'] = df['close'].pct_change() * 100
df['change_7d'] = df['close'].pct_change(7) * 100
df = df[df.index >= '2024-11-01'].dropna()

print(f'\n📥 {len(df)} days loaded')
print('\n🤖 Calling OpenAI for daily regime analysis...')

context = 'US Presidential Election. Early results showing Republican lead. Market expecting crypto-friendly policies. SEC chair Gensler under pressure.'
results = []

for date, row in df.iterrows():
    ema20_pos = 'ABOVE' if row['close'] > row['ema20'] else 'BELOW'
    ema50_pos = 'ABOVE' if row['close'] > row['ema50'] else 'BELOW'
    ema_trend = 'ABOVE' if row['ema20'] > row['ema50'] else 'BELOW'

    prompt = PROMPT_4H.format(
        timestamp=date.strftime('%Y-%m-%d'),
        price=row['close'], change_24h=row['change_24h'], change_7d=row['change_7d'],
        rsi=row['rsi'], ema20=row['ema20'], ema50=row['ema50'],
        ema20_position=ema20_pos, ema50_position=ema50_pos, ema_trend=ema_trend,
        volatility=row['volatility'], context=context
    )

    try:
        response = client.chat.completions.create(
            model='gpt-5.1',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            response_format={'type': 'json_object'}
        )
        data = json.loads(response.choices[0].message.content)
        results.append({'date': date, 'price': row['close'], **data})
        regime = data.get('regime', 'N/A')
        buy_th = data.get('buy_threshold', 0)
        cap = data.get('capital_percent', 0)
        print(f"   {date.strftime('%Y-%m-%d')}: {regime:8s} | Buy>={buy_th:2d} | Cap:{cap:3d}% | ${row['close']:,.0f}")
    except Exception as e:
        print(f'   Error: {e}')

print(f'\n📈 Month Summary:')
regimes = [r['regime'] for r in results]
print(f'   BULL: {regimes.count("BULL")} days')
print(f'   BEAR: {regimes.count("BEAR")} days')
print(f'   LATERAL: {regimes.count("LATERAL")} days')
print(f'   VOLATILE: {regimes.count("VOLATILE")} days')

start_price = results[0]['price']
end_price = results[-1]['price']
ret = ((end_price - start_price) / start_price) * 100
print(f'\n   Price: ${start_price:,.0f} -> ${end_price:,.0f} ({ret:+.1f}%)')
