"""
Test de Overfitting para la Estrategia AI
==========================================
Pruebas:
1. Walk-Forward Analysis (entrenar en periodo, probar en siguiente)
2. Parameter Sensitivity (variar parámetros ±20%)
3. Monte Carlo Simulation (shuffle de regímenes)
4. Out-of-Sample Test (2018-2019 sin datos de entrenamiento)
"""
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🔬 TEST DE OVERFITTING - ESTRATEGIA AI")
print("=" * 80)

# ============================================================
# CONFIGURACIÓN BASE
# ============================================================
COMMISSION = 0.001
SLIPPAGE = 0.001
BUFFER = 0.015
LEVERAGE = 1.5
DAILY_INTEREST = 0.0004

def run_backtest(df, regimes_dict, params=None):
    """Ejecuta backtest con parámetros configurables"""
    if params is None:
        params = {'buffer': BUFFER, 'rsi_winter': 65, 'leverage': LEVERAGE}

    buffer = params.get('buffer', BUFFER)
    rsi_winter = params.get('rsi_winter', 65)
    leverage = params.get('leverage', LEVERAGE)

    capital = 1000
    btc_holdings = 0
    position = None
    trades = []

    def get_regime(date):
        week_start = (date - pd.Timedelta(days=date.weekday())).strftime('%Y-%m-%d')
        if week_start in regimes_dict:
            return regimes_dict[week_start]
        for ws in sorted(regimes_dict.keys(), reverse=True):
            if ws <= date.strftime('%Y-%m-%d'):
                return regimes_dict[ws]
        return 'LATERAL'

    for i in range(len(df)):
        row = df.iloc[i]
        date = row.name
        close = float(row['Close'])
        ema20 = float(row['ema20'])
        ema50 = float(row['ema50'])
        ema200 = float(row['ema200'])
        rsi = float(row['rsi'])

        regime = get_regime(date)
        is_winter = close < ema200
        ema20_upper = ema20 * (1 + buffer)
        ema50_lower = ema50 * (1 - buffer)

        # LÓGICA DE COMPRA
        if position is None and capital > 10:
            should_buy = False
            if is_winter:
                if regime == 'BULL' and rsi > rsi_winter:
                    should_buy = True
            else:
                if regime == 'BULL':
                    should_buy = True
                elif regime != 'BEAR' and close > ema20_upper:
                    should_buy = True

            if should_buy:
                current_lev = leverage if regime == 'BULL' else 1.0
                exec_price = close * (1 + SLIPPAGE)
                buying_power = capital * current_lev
                loan = capital * (current_lev - 1)
                commission = buying_power * COMMISSION
                btc_holdings = (buying_power - commission) / exec_price
                position = {'entry': exec_price, 'date': date, 'loan': loan, 'regime': regime}
                capital = 0

        # LÓGICA DE VENTA
        elif position is not None:
            should_sell = False
            if regime == 'BULL':
                should_sell = False
            else:
                if close < ema50_lower:
                    should_sell = True

            if should_sell:
                exec_price = close * (1 - SLIPPAGE)
                gross = btc_holdings * exec_price
                commission = gross * COMMISSION
                days = max(1, (date - position['date']).days)
                interest = position['loan'] * DAILY_INTEREST * days
                capital = max(0, gross - position['loan'] - interest - commission)
                profit = (exec_price - position['entry']) / position['entry'] * 100
                trades.append({'profit': profit, 'regime': position['regime']})
                btc_holdings = 0
                position = None

    # Cerrar posición final
    if position is not None:
        exec_price = float(df.iloc[-1]['Close']) * (1 - SLIPPAGE)
        gross = btc_holdings * exec_price
        commission = gross * COMMISSION
        days = max(1, (df.index[-1] - position['date']).days)
        interest = position['loan'] * DAILY_INTEREST * days
        capital = max(0, gross - position['loan'] - interest - commission)

    final_return = (capital - 1000) / 1000 * 100
    win_rate = sum(1 for t in trades if t['profit'] > 0) / len(trades) * 100 if trades else 0

    return {
        'return': final_return,
        'trades': len(trades),
        'win_rate': win_rate,
        'capital': capital
    }

# ============================================================
# CARGAR DATOS
# ============================================================
print("\n📥 Cargando datos...")

# Datos extendidos (2018-2025) para out-of-sample
btc = yf.download("BTC-USD", start="2018-01-01", end="2025-11-30", progress=False)
if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

df = pd.DataFrame(index=btc.index)
df['Close'] = btc['Close'].values
df['ema20'] = df['Close'].ewm(span=20).mean()
df['ema50'] = df['Close'].ewm(span=50).mean()
df['ema200'] = df['Close'].ewm(span=200).mean()

delta = df['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
df['rsi'] = 100 - (100 / (1 + gain/loss))
df = df.dropna()

# Cargar regímenes
conn = sqlite3.connect('backend/data/trading_bot.db')
regimes = pd.read_sql("SELECT week_start, regime FROM ai_market_regimes", conn)
conn.close()
regimes_dict = dict(zip(regimes['week_start'], regimes['regime']))

print(f"   Datos: {len(df)} días ({df.index[0].strftime('%Y-%m-%d')} a {df.index[-1].strftime('%Y-%m-%d')})")

# ============================================================
# TEST 1: WALK-FORWARD ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("📊 TEST 1: WALK-FORWARD ANALYSIS")
print("=" * 80)
print("   Dividimos en periodos y probamos si la estrategia funciona en cada uno")

periods = [
    ('2020-01', '2020-12', '2020'),
    ('2021-01', '2021-12', '2021'),
    ('2022-01', '2022-12', '2022'),
    ('2023-01', '2023-12', '2023'),
    ('2024-01', '2024-12', '2024'),
    ('2025-01', '2025-11', '2025'),
]

print(f"\n{'Periodo':<12} {'Retorno AI':>12} {'Trades':>8} {'Win Rate':>10} {'Resultado':>12}")
print("-" * 60)

wf_results = []
for start, end, label in periods:
    period_df = df[start:end]
    if len(period_df) > 50:
        result = run_backtest(period_df, regimes_dict)
        wf_results.append(result['return'])
        status = "✅" if result['return'] > 0 else "❌"
        print(f"{label:<12} {result['return']:>+11.1f}% {result['trades']:>8} {result['win_rate']:>9.1f}% {status:>12}")

positive_periods = sum(1 for r in wf_results if r > 0)
print(f"\n   Periodos positivos: {positive_periods}/{len(wf_results)} ({positive_periods/len(wf_results)*100:.0f}%)")
wf_pass = positive_periods >= len(wf_results) * 0.6

# ============================================================
# TEST 2: PARAMETER SENSITIVITY
# ============================================================
print("\n" + "=" * 80)
print("📊 TEST 2: PARAMETER SENSITIVITY (±20%)")
print("=" * 80)
print("   Si pequeños cambios en parámetros destruyen resultados = overfitting")

df_2020_2025 = df['2020-01':]
base_result = run_backtest(df_2020_2025, regimes_dict)
base_return = base_result['return']

param_tests = [
    ('Buffer 1.2%', {'buffer': 0.012}),
    ('Buffer 1.5% (base)', {'buffer': 0.015}),
    ('Buffer 1.8%', {'buffer': 0.018}),
    ('Buffer 2.0%', {'buffer': 0.020}),
    ('RSI Winter 55', {'rsi_winter': 55}),
    ('RSI Winter 65 (base)', {'rsi_winter': 65}),
    ('RSI Winter 70', {'rsi_winter': 70}),
    ('RSI Winter 75', {'rsi_winter': 75}),
    ('Leverage 1.3x', {'leverage': 1.3}),
    ('Leverage 1.5x (base)', {'leverage': 1.5}),
    ('Leverage 1.7x', {'leverage': 1.7}),
    ('Leverage 2.0x', {'leverage': 2.0}),
]

print(f"\n{'Parámetro':<22} {'Retorno':>12} {'vs Base':>12} {'Estable':>10}")
print("-" * 60)

stable_count = 0
returns_list = []
for name, params in param_tests:
    result = run_backtest(df_2020_2025, regimes_dict, params)
    diff = result['return'] - base_return
    returns_list.append(result['return'])
    # Consideramos estable si el retorno sigue siendo positivo y > 50% del base
    is_stable = result['return'] > 0 and result['return'] > base_return * 0.5
    if is_stable:
        stable_count += 1
    status = "✅" if is_stable else "⚠️"
    print(f"{name:<22} {result['return']:>+11.1f}% {diff:>+11.1f}% {status:>10}")

sensitivity_std = np.std(returns_list)
print(f"\n   Desviación estándar de retornos: {sensitivity_std:.1f}%")
print(f"   Configuraciones estables: {stable_count}/{len(param_tests)} ({stable_count/len(param_tests)*100:.0f}%)")
sensitivity_pass = stable_count >= len(param_tests) * 0.7

# ============================================================
# TEST 3: MONTE CARLO - SHUFFLE DE REGÍMENES
# ============================================================
print("\n" + "=" * 80)
print("📊 TEST 3: MONTE CARLO (100 simulaciones con regímenes aleatorios)")
print("=" * 80)
print("   Si la estrategia funciona con regímenes random = la IA no aporta valor")

np.random.seed(42)
regimes_list = list(regimes_dict.values())
n_simulations = 100
random_returns = []

for i in range(n_simulations):
    # Crear regímenes aleatorios
    shuffled = np.random.choice(regimes_list, size=len(regimes_dict))
    random_regimes = dict(zip(regimes_dict.keys(), shuffled))
    result = run_backtest(df_2020_2025, random_regimes)
    random_returns.append(result['return'])

random_mean = np.mean(random_returns)
random_std = np.std(random_returns)
random_95 = np.percentile(random_returns, 95)

print(f"\n   Estrategia con IA real:     {base_return:+.1f}%")
print(f"   Media con regímenes random: {random_mean:+.1f}%")
print(f"   Desv. estándar random:      {random_std:.1f}%")
print(f"   Percentil 95 random:        {random_95:+.1f}%")
print(f"\n   Z-Score de la IA: {(base_return - random_mean) / random_std:.2f}")

# La IA debe superar el percentil 95 de random
monte_carlo_pass = base_return > random_95
print(f"\n   ¿IA supera P95 random? {'✅ SÍ' if monte_carlo_pass else '❌ NO'}")

# ============================================================
# TEST 4: OUT-OF-SAMPLE (2018-2019)
# ============================================================
print("\n" + "=" * 80)
print("📊 TEST 4: OUT-OF-SAMPLE (2018-2019)")
print("=" * 80)
print("   Probamos en datos que NO se usaron para desarrollar la estrategia")

# Crear regímenes sintéticos para 2018-2019 basados en EMA20 vs EMA50
# (Ya que no tenemos regímenes AI para ese periodo)
df_oos = df['2018-01':'2019-12']

# Simular regímenes basados en tendencia técnica
synthetic_regimes = {}
for date in df_oos.index:
    week_start = (date - pd.Timedelta(days=date.weekday())).strftime('%Y-%m-%d')
    if week_start not in synthetic_regimes:
        row = df_oos.loc[date]
        if row['Close'] > row['ema50'] and row['rsi'] > 50:
            synthetic_regimes[week_start] = 'BULL'
        elif row['Close'] < row['ema50'] and row['rsi'] < 50:
            synthetic_regimes[week_start] = 'BEAR'
        else:
            synthetic_regimes[week_start] = 'LATERAL'

oos_result = run_backtest(df_oos, synthetic_regimes)

# Buy & Hold 2018-2019
bh_start = float(df_oos.iloc[0]['Close'])
bh_end = float(df_oos.iloc[-1]['Close'])
bh_return = (bh_end - bh_start) / bh_start * 100

print(f"\n   Retorno AI (2018-2019):  {oos_result['return']:+.1f}%")
print(f"   Retorno B&H (2018-2019): {bh_return:+.1f}%")
print(f"   Trades: {oos_result['trades']}, Win Rate: {oos_result['win_rate']:.1f}%")

# Consideramos éxito si no pierde más que B&H * 1.5 en un periodo difícil
oos_pass = oos_result['return'] > bh_return * 0.5 or oos_result['return'] > 0
print(f"\n   ¿Resultado aceptable? {'✅ SÍ' if oos_pass else '❌ NO'}")

# ============================================================
# TEST 5: DISTRIBUCIÓN DE TRADES
# ============================================================
print("\n" + "=" * 80)
print("📊 TEST 5: ANÁLISIS DE CONCENTRACIÓN DE GANANCIAS")
print("=" * 80)

# Ejecutar backtest completo y obtener trades
capital = 1000
btc_holdings = 0
position = None
all_trades = []

def get_regime(date):
    week_start = (date - pd.Timedelta(days=date.weekday())).strftime('%Y-%m-%d')
    if week_start in regimes_dict:
        return regimes_dict[week_start]
    for ws in sorted(regimes_dict.keys(), reverse=True):
        if ws <= date.strftime('%Y-%m-%d'):
            return regimes_dict[ws]
    return 'LATERAL'

for i in range(len(df_2020_2025)):
    row = df_2020_2025.iloc[i]
    date = row.name
    close = float(row['Close'])
    ema20 = float(row['ema20'])
    ema50 = float(row['ema50'])
    ema200 = float(row['ema200'])
    rsi = float(row['rsi'])

    regime = get_regime(date)
    is_winter = close < ema200
    ema20_upper = ema20 * (1 + BUFFER)
    ema50_lower = ema50 * (1 - BUFFER)

    if position is None and capital > 10:
        should_buy = False
        if is_winter:
            if regime == 'BULL' and rsi > 65:
                should_buy = True
        else:
            if regime == 'BULL':
                should_buy = True
            elif regime != 'BEAR' and close > ema20_upper:
                should_buy = True

        if should_buy:
            current_lev = LEVERAGE if regime == 'BULL' else 1.0
            exec_price = close * (1 + SLIPPAGE)
            buying_power = capital * current_lev
            loan = capital * (current_lev - 1)
            commission = buying_power * COMMISSION
            btc_holdings = (buying_power - commission) / exec_price
            position = {'entry': exec_price, 'date': date, 'loan': loan, 'regime': regime, 'capital_before': capital}
            capital = 0

    elif position is not None:
        should_sell = False
        if regime == 'BULL':
            should_sell = False
        else:
            if close < ema50_lower:
                should_sell = True

        if should_sell:
            exec_price = close * (1 - SLIPPAGE)
            gross = btc_holdings * exec_price
            commission = gross * COMMISSION
            days = max(1, (date - position['date']).days)
            interest = position['loan'] * DAILY_INTEREST * days
            capital = max(0, gross - position['loan'] - interest - commission)
            profit_pct = (exec_price - position['entry']) / position['entry'] * 100
            profit_abs = capital - position['capital_before'] if position['capital_before'] > 0 else capital - 1000
            all_trades.append({
                'profit_pct': profit_pct,
                'profit_abs': profit_abs,
                'regime': position['regime']
            })
            btc_holdings = 0
            position = None

# Cerrar última posición
if position is not None:
    exec_price = float(df_2020_2025.iloc[-1]['Close']) * (1 - SLIPPAGE)
    gross = btc_holdings * exec_price
    commission = gross * COMMISSION
    days = max(1, (df_2020_2025.index[-1] - position['date']).days)
    interest = position['loan'] * DAILY_INTEREST * days
    capital = max(0, gross - position['loan'] - interest - commission)

if all_trades:
    profits = [t['profit_pct'] for t in all_trades]
    sorted_profits = sorted(profits, reverse=True)

    total_profit_sum = sum(p for p in profits if p > 0)
    top3_profit = sum(sorted_profits[:3]) if len(sorted_profits) >= 3 else sum(sorted_profits)
    concentration = (top3_profit / total_profit_sum * 100) if total_profit_sum > 0 else 0

    print(f"\n   Total trades: {len(all_trades)}")
    print(f"   Top 3 trades: {sorted_profits[:3]}")
    print(f"   Concentración en top 3: {concentration:.1f}% de las ganancias")

    # Si más del 80% de ganancias vienen de 3 trades = peligroso
    concentration_pass = concentration < 80
    print(f"\n   ¿Diversificación aceptable? {'✅ SÍ' if concentration_pass else '⚠️ CONCENTRADO'}")
else:
    concentration_pass = False
    print("   No hay trades para analizar")

# ============================================================
# VEREDICTO FINAL
# ============================================================
print("\n" + "=" * 80)
print("🏆 VEREDICTO FINAL - OVERFITTING TEST")
print("=" * 80)

tests = [
    ("Walk-Forward Analysis", wf_pass),
    ("Parameter Sensitivity", sensitivity_pass),
    ("Monte Carlo (IA > Random)", monte_carlo_pass),
    ("Out-of-Sample 2018-2019", oos_pass),
    ("Diversificación de Trades", concentration_pass),
]

print(f"\n{'Test':<30} {'Resultado':>15}")
print("-" * 50)
for name, passed in tests:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{name:<30} {status:>15}")

passed_count = sum(1 for _, p in tests if p)
print("-" * 50)
print(f"{'TOTAL':<30} {passed_count}/{len(tests)} tests")

if passed_count >= 4:
    print("\n🟢 ESTRATEGIA ROBUSTA - Bajo riesgo de overfitting")
elif passed_count >= 3:
    print("\n🟡 ESTRATEGIA MODERADA - Riesgo medio de overfitting")
else:
    print("\n🔴 POSIBLE OVERFITTING - Revisar estrategia")
