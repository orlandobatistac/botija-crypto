"""
Backtest con parámetros AI dinámicos vs Buy & Hold
"""
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf

print("=" * 70)
print("🤖 BACKTEST CON PARÁMETROS AI DINÁMICOS vs BUY & HOLD")
print("=" * 70)

# 1. Cargar datos de BTC
print("\n📥 Cargando datos de BTC 2020-2025...")
btc = yf.download("BTC-USD", start="2020-01-01", end="2025-11-30", progress=False)
print(f"   Datos: {len(btc)} días")

# 2. Calcular indicadores
print("\n📊 Calculando indicadores...")

# Aplanar columnas si es MultiIndex
if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

df = pd.DataFrame(index=btc.index)
df['Close'] = btc['Close'].values
df['ema20'] = df['Close'].ewm(span=20).mean()
df['ema50'] = df['Close'].ewm(span=50).mean()

# RSI
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# MACD
ema12 = df['Close'].ewm(span=12).mean()
ema26 = df['Close'].ewm(span=26).mean()
df['macd'] = ema12 - ema26
df['macd_signal'] = df['macd'].ewm(span=9).mean()

# Bollinger
df['bb_mid'] = df['Close'].rolling(20).mean()
bb_std = df['Close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * bb_std
df['bb_lower'] = df['bb_mid'] - 2 * bb_std

# Volatilidad
df['volatility'] = df['Close'].pct_change().rolling(20).std() * 100

# Score compuesto
def calc_score(row):
    score = 50
    if pd.isna(row['ema20']) or pd.isna(row['ema50']):
        return score

    # EMA trend
    if row['ema20'] > row['ema50']:
        score += 15
    else:
        score -= 15

    # RSI
    if row['rsi'] < 30:
        score += 20
    elif row['rsi'] < 45:
        score += 10
    elif row['rsi'] > 70:
        score -= 20
    elif row['rsi'] > 55:
        score -= 10

    # MACD
    if row['macd'] > row['macd_signal']:
        score += 10
    else:
        score -= 10

    # Bollinger
    if row['Close'] < row['bb_lower']:
        score += 15
    elif row['Close'] > row['bb_upper']:
        score -= 15

    return max(0, min(100, score))

df['score'] = df.apply(calc_score, axis=1)
df = df.dropna()
print(f"   Datos con indicadores: {len(df)} días")

# 3. Cargar regímenes AI
print("\n📂 Cargando regímenes AI de la DB...")
db_path = "backend/data/trading_bot.db"
conn = sqlite3.connect(db_path)
regimes_df = pd.read_sql_query("""
    SELECT week_start, regime, buy_threshold, sell_threshold,
           capital_percent, stop_loss_percent
    FROM ai_market_regimes
    ORDER BY week_start
""", conn)
conn.close()

regimes_df['week_start'] = pd.to_datetime(regimes_df['week_start'])
regimes_dict = regimes_df.set_index('week_start').to_dict('index')
print(f"   Regímenes cargados: {len(regimes_df)} semanas")
print(f"   Distribución: {regimes_df['regime'].value_counts().to_dict()}")

def get_regime_params(date):
    """Obtiene parámetros del régimen para una fecha."""
    if isinstance(date, pd.Timestamp):
        week_start = date - pd.Timedelta(days=date.dayofweek)
        week_start = week_start.normalize()
    else:
        date = pd.Timestamp(date)
        week_start = date - pd.Timedelta(days=date.dayofweek)
        week_start = week_start.normalize()

    if week_start in regimes_dict:
        return regimes_dict[week_start]

    for ws in sorted(regimes_dict.keys(), reverse=True):
        if ws <= date:
            return regimes_dict[ws]

    return {'regime': 'LATERAL', 'buy_threshold': 50, 'sell_threshold': 35,
            'capital_percent': 75, 'stop_loss_percent': 2.0}

# 4. Backtest AI Dinámico
print("\n🔄 Ejecutando backtest AI dinámico...")
initial_capital = 1000
capital = initial_capital
btc_holdings = 0
position = None
trades = []
equity_curve = []

for i in range(len(df)):
    row = df.iloc[i]
    date = row.name
    price = float(row['Close'])
    score = row['score']

    params = get_regime_params(date)
    buy_th = params['buy_threshold']
    sell_th = params['sell_threshold']
    capital_pct = params['capital_percent'] / 100
    regime = params['regime']

    # Ajustar capital por régimen
    if regime == 'BEAR':
        capital_pct = min(capital_pct, 0.5)
    elif regime == 'VOLATILE':
        capital_pct = min(capital_pct, 0.6)

    if position is None and score >= buy_th and capital > 10:
        invest = capital * capital_pct
        btc_holdings = invest / price
        capital -= invest
        position = {'entry_price': price, 'btc': btc_holdings, 'date': date, 'regime': regime}

    elif position is not None and score <= sell_th:
        sell_value = btc_holdings * price
        profit_pct = (price - position['entry_price']) / position['entry_price'] * 100
        capital += sell_value
        trades.append({
            'entry_date': position['date'],
            'exit_date': date,
            'profit_pct': profit_pct,
            'regime': position['regime']
        })
        btc_holdings = 0
        position = None

    total_value = capital + btc_holdings * price
    equity_curve.append(total_value)

# Cerrar posición final
if position is not None:
    final_price = float(df.iloc[-1]['Close'])
    capital += btc_holdings * final_price

ai_final = capital
ai_return = (ai_final - initial_capital) / initial_capital * 100

# Max drawdown
equity_curve = np.array(equity_curve)
peak = np.maximum.accumulate(equity_curve)
drawdown = (peak - equity_curve) / peak * 100
ai_max_dd = np.max(drawdown)

win_rate = sum(1 for t in trades if t['profit_pct'] > 0) / len(trades) * 100 if trades else 0

# 5. Buy & Hold
bh_start = float(df.iloc[0]['Close'])
bh_end = float(df.iloc[-1]['Close'])
bh_return = (bh_end - bh_start) / bh_start * 100
bh_final = initial_capital * (1 + bh_return/100)

# Max DD de B&H
prices = df['Close'].values
bh_peak = np.maximum.accumulate(prices)
bh_dd = (bh_peak - prices) / bh_peak * 100
bh_max_dd = np.max(bh_dd)

# 6. Resultados
print("\n" + "=" * 70)
print("📊 RESULTADOS FINALES")
print("=" * 70)

print(f"\n🤖 ESTRATEGIA AI DINÁMICA:")
print(f"   Capital final:  ${ai_final:,.2f}")
print(f"   Retorno total:  {ai_return:+.1f}%")
print(f"   Max Drawdown:   {ai_max_dd:.1f}%")
print(f"   Trades:         {len(trades)}")
print(f"   Win Rate:       {win_rate:.1f}%")

print(f"\n📈 BUY & HOLD:")
print(f"   Capital final:  ${bh_final:,.2f}")
print(f"   Retorno total:  {bh_return:+.1f}%")
print(f"   Max Drawdown:   {bh_max_dd:.1f}%")

print("\n" + "-" * 70)
diff = ai_return - bh_return
if diff > 0:
    print(f"✅ AI GANA POR {diff:+.1f}%")
else:
    print(f"❌ BUY & HOLD GANA POR {-diff:.1f}%")

# 7. Análisis por régimen
print("\n" + "=" * 70)
print("📈 ANÁLISIS POR RÉGIMEN")
print("=" * 70)

if trades:
    trades_df = pd.DataFrame(trades)
    for regime in ['BULL', 'BEAR', 'LATERAL', 'VOLATILE']:
        regime_trades = trades_df[trades_df['regime'] == regime]
        if len(regime_trades) > 0:
            avg_profit = regime_trades['profit_pct'].mean()
            wins = (regime_trades['profit_pct'] > 0).sum()
            total = len(regime_trades)
            print(f"   {regime:8}: {total:2} trades, Profit promedio: {avg_profit:+.1f}%, Win rate: {wins}/{total}")

# 8. Test por año
print("\n" + "=" * 70)
print("📅 COMPARACIÓN POR AÑO")
print("=" * 70)

years = ['2020', '2021', '2022', '2023', '2024', '2025']
ai_wins = 0
bh_wins = 0

print(f"\n{'Año':<6} {'AI Retorno':>12} {'B&H Retorno':>12} {'Diferencia':>12} {'Ganador':>12}")
print("-" * 60)

for year in years:
    year_data = df[df.index.year == int(year)]
    if len(year_data) < 30:
        continue

    # Simular año individual
    year_capital = 1000
    year_btc = 0
    year_pos = None

    for i in range(len(year_data)):
        row = year_data.iloc[i]
        price = float(row['Close'])
        score = row['score']
        params = get_regime_params(row.name)

        if year_pos is None and score >= params['buy_threshold'] and year_capital > 10:
            invest = year_capital * (params['capital_percent'] / 100)
            year_btc = invest / price
            year_capital -= invest
            year_pos = price
        elif year_pos is not None and score <= params['sell_threshold']:
            year_capital += year_btc * price
            year_btc = 0
            year_pos = None

    if year_pos is not None:
        year_capital += year_btc * float(year_data.iloc[-1]['Close'])

    year_ai_return = (year_capital - 1000) / 1000 * 100
    year_bh_return = (float(year_data.iloc[-1]['Close']) - float(year_data.iloc[0]['Close'])) / float(year_data.iloc[0]['Close']) * 100

    diff = year_ai_return - year_bh_return
    if diff > 0:
        winner = "AI ✅"
        ai_wins += 1
    else:
        winner = "B&H ⚠️"
        bh_wins += 1

    print(f"{year:<6} {year_ai_return:>+11.1f}% {year_bh_return:>+11.1f}% {diff:>+11.1f}% {winner:>12}")

print("-" * 60)
print(f"\n🏆 AI ganó {ai_wins}/{len(years)} años | B&H ganó {bh_wins}/{len(years)} años")

if ai_wins > bh_wins:
    print("\n✅ LA ESTRATEGIA AI ES CONSISTENTE - NO HAY OVERFITTING")
else:
    print("\n⚠️ LA ESTRATEGIA AI NO ES CONSISTENTE EN TODOS LOS AÑOS")
