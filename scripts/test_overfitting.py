"""
🔬 TEST DE ROBUSTEZ Y OVERFITTING
Validación estadística de la estrategia Smart Trend Following

Tests:
1. Sensibilidad de Parámetros (EMA_EXIT, BUFFER)
2. Null Hypothesis (IA vs Random)
3. Stress Test (Comisiones altas)
4. Concentración de Profits (Top 3 trades)
"""
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Tuple
import random

# ============================================================
# CONFIGURACIÓN BASE
# ============================================================
COMMISSION_BASE = 0.001
SLIPPAGE_BASE = 0.001
BUFFER_BASE = 0.015
LEVERAGE = 1.5
DAILY_INTEREST = 0.0004
EMA_EXIT_BASE = 50

# ============================================================
# CARGA DE DATOS (una sola vez)
# ============================================================
print("=" * 70)
print("🔬 TEST DE ROBUSTEZ Y OVERFITTING")
print("=" * 70)

print("\n📥 Cargando datos BTC 2018-2025...")
btc = yf.download("BTC-USD", start="2018-01-01", end="2025-11-30", progress=False)

if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

df_base = pd.DataFrame(index=btc.index)
df_base['Open'] = btc['Open'].values
df_base['Close'] = btc['Close'].values
df_base['ema20'] = df_base['Close'].ewm(span=20).mean()
df_base['ema200'] = df_base['Close'].ewm(span=200).mean()

# RSI
delta = df_base['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df_base['rsi'] = 100 - (100 / (1 + rs))

# Cargar regímenes AI
db_path = "backend/data/trading_bot.db"
conn = sqlite3.connect(db_path)
regimes_df = pd.read_sql_query("""
    SELECT week_start, regime FROM ai_market_regimes ORDER BY week_start
""", conn)
conn.close()
regimes_df['week_start'] = pd.to_datetime(regimes_df['week_start'])
regimes_dict = regimes_df.set_index('week_start')['regime'].to_dict()

# Generar sintéticos 2018-2019
for date in df_base.index:
    if date < pd.Timestamp('2020-01-01'):
        week_start = (date - pd.Timedelta(days=date.dayofweek)).normalize()
        if week_start not in regimes_dict:
            row = df_base.loc[date]
            if row['Close'] > row['ema20'] * 1.02 and row['rsi'] > 55:
                regimes_dict[week_start] = 'BULL'
            elif row['Close'] < row['ema20'] * 0.98 and row['rsi'] < 45:
                regimes_dict[week_start] = 'BEAR'
            elif row['rsi'] > 60 or row['rsi'] < 40:
                regimes_dict[week_start] = 'VOLATILE'
            else:
                regimes_dict[week_start] = 'LATERAL'

print(f"   Datos: {len(df_base)} días | Regímenes: {len(regimes_dict)} semanas")


def get_regime(date: pd.Timestamp, random_mode: bool = False) -> str:
    """Obtiene régimen para una fecha."""
    if random_mode:
        return random.choice(['BULL', 'BEAR', 'VOLATILE', 'LATERAL'])

    week_start = (date - pd.Timedelta(days=date.dayofweek)).normalize()
    if week_start in regimes_dict:
        return regimes_dict[week_start]

    for ws in sorted(regimes_dict.keys(), reverse=True):
        if ws <= date:
            return regimes_dict[ws]
    return 'LATERAL'


def run_backtest(
    ema_exit: int = 50,
    buffer: float = 0.015,
    commission: float = 0.001,
    slippage: float = 0.001,
    random_regimes: bool = False,
    seed: int = None
) -> Dict:
    """
    Ejecuta backtest con parámetros configurables.
    Retorna métricas clave.
    """
    if seed is not None:
        random.seed(seed)

    # Calcular EMA de salida dinámica
    df = df_base.copy()
    df[f'ema{ema_exit}'] = df['Close'].ewm(span=ema_exit).mean()
    df = df.dropna()

    capital = 1000.0
    btc_holdings = 0.0
    position = None
    trades = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]
        date = row.name
        close = float(row['Close'])
        ema20 = float(row['ema20'])
        ema_exit_val = float(row[f'ema{ema_exit}'])
        ema200 = float(row['ema200'])
        rsi = float(row['rsi'])

        regime = get_regime(date, random_mode=random_regimes)

        # Entry logic
        if position is None and capital > 10:
            should_buy = False
            ema20_entry = ema20 * (1 + buffer)
            ema_exit_entry = ema_exit_val * (1 + buffer)
            is_winter = close < ema200

            if is_winter:
                if regime == 'BULL' and rsi > 65 and close > ema20_entry:
                    should_buy = True
            else:
                if regime == 'BULL' and close > ema20_entry:
                    should_buy = True
                elif regime == 'VOLATILE' and close > ema20_entry:
                    should_buy = True
                elif regime == 'LATERAL' and close > ema_exit_entry:
                    should_buy = True
                # BEAR: no entries

            if should_buy:
                lev = LEVERAGE if regime == 'BULL' else 1.0
                exec_price = close * (1 + slippage)
                buying_power = capital * lev
                loan = capital * (lev - 1)
                comm = buying_power * commission
                invest = buying_power - comm
                btc_holdings = invest / exec_price
                capital = 0
                position = {
                    'entry_price': exec_price,
                    'entry_date': date,
                    'regime': regime,
                    'loan': loan,
                    'leverage': lev
                }

        # Exit logic
        elif position is not None:
            ema_exit_threshold = ema_exit_val * (1 - buffer)
            catastrophic = ema_exit_val * 0.97

            should_sell = False
            if close < ema_exit_threshold:
                if regime == 'BULL':
                    if close < catastrophic:
                        should_sell = True
                else:
                    should_sell = True

            if should_sell:
                exec_price = close * (1 - slippage)
                gross = btc_holdings * exec_price
                comm = gross * commission
                days = max(1, (date - position['entry_date']).days)
                interest = position['loan'] * DAILY_INTEREST * days
                net = gross - position['loan'] - interest - comm
                profit_pct = (exec_price - position['entry_price']) / position['entry_price'] * 100
                capital = max(0, net)
                trades.append({
                    'profit_pct': profit_pct,
                    'profit_abs': net - 1000 * (1 if len(trades) == 0 else 0),
                    'regime': position['regime']
                })
                btc_holdings = 0
                position = None

        # Track equity
        if position is not None:
            days = max(1, (date - position['entry_date']).days)
            interest = position['loan'] * DAILY_INTEREST * days
            equity = btc_holdings * close - position['loan'] - interest
            equity_curve.append(max(0, equity))
        else:
            equity_curve.append(capital)

    # Close final position
    if position is not None:
        final_price = float(df.iloc[-1]['Close']) * (1 - slippage)
        gross = btc_holdings * final_price
        comm = gross * commission
        days = max(1, (df.index[-1] - position['entry_date']).days)
        interest = position['loan'] * DAILY_INTEREST * days
        capital = max(0, gross - position['loan'] - interest - comm)
        profit_pct = (final_price - position['entry_price']) / position['entry_price'] * 100
        trades.append({
            'profit_pct': profit_pct,
            'profit_abs': capital - 1000,
            'regime': position['regime']
        })

    # Metrics
    equity_arr = np.array(equity_curve) if equity_curve else np.array([1000])
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (peak - equity_arr) / np.maximum(peak, 1) * 100
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    final_capital = capital
    total_return = (final_capital - 1000) / 1000 * 100

    return {
        'final_capital': final_capital,
        'total_return': total_return,
        'max_drawdown': max_dd,
        'trades': len(trades),
        'trades_detail': trades
    }


# ============================================================
# 1. TEST DE SENSIBILIDAD DE PARÁMETROS
# ============================================================
print("\n" + "=" * 70)
print("🔬 TEST 1: SENSIBILIDAD DE PARÁMETROS")
print("=" * 70)

ema_values = [40, 45, 50, 55, 60]
buffer_values = [0.010, 0.015, 0.020]

print("\n📊 Variando EMA de Salida (Buffer fijo 1.5%):")
print("-" * 50)
ema_results = []
for ema in ema_values:
    result = run_backtest(ema_exit=ema, buffer=BUFFER_BASE)
    ema_results.append(result['total_return'])
    print(f"   EMA{ema}: {result['total_return']:+.1f}% | DD: {result['max_drawdown']:.1f}%")

ema_std = np.std(ema_results)
ema_mean = np.mean(ema_results)
ema_range = max(ema_results) - min(ema_results)
ema_pass = ema_range < 500  # Si varía menos de 500% es estable

print(f"\n   Rango: {ema_range:.0f}% | Desv.Est: {ema_std:.0f}%")
print(f"   {'✅ PASS' if ema_pass else '❌ FAIL'}: {'Estable' if ema_pass else 'Inestable'}")

print("\n📊 Variando Buffer (EMA50 fija):")
print("-" * 50)
buffer_results = []
for buf in buffer_values:
    result = run_backtest(ema_exit=EMA_EXIT_BASE, buffer=buf)
    buffer_results.append(result['total_return'])
    print(f"   Buffer {buf*100:.1f}%: {result['total_return']:+.1f}% | DD: {result['max_drawdown']:.1f}%")

buffer_std = np.std(buffer_results)
buffer_range = max(buffer_results) - min(buffer_results)
buffer_pass = buffer_range < 500

print(f"\n   Rango: {buffer_range:.0f}% | Desv.Est: {buffer_std:.0f}%")
print(f"   {'✅ PASS' if buffer_pass else '❌ FAIL'}: {'Estable' if buffer_pass else 'Inestable'}")

sensitivity_pass = ema_pass and buffer_pass


# ============================================================
# 2. TEST NULL HYPOTHESIS (IA vs Random)
# ============================================================
print("\n" + "=" * 70)
print("🎲 TEST 2: NULL HYPOTHESIS (IA vs RANDOM)")
print("=" * 70)

# Retorno real con IA
real_result = run_backtest()
real_return = real_result['total_return']
print(f"\n📈 Retorno REAL (IA): {real_return:+.1f}%")

# 10 simulaciones random
print("\n🎰 Simulaciones con regímenes ALEATORIOS:")
random_returns = []
for i in range(10):
    result = run_backtest(random_regimes=True, seed=42 + i)
    random_returns.append(result['total_return'])
    print(f"   Sim {i+1}: {result['total_return']:+.1f}%")

random_mean = np.mean(random_returns)
random_std = np.std(random_returns)
threshold = random_mean + 2 * random_std

print(f"\n📊 Estadísticas Random:")
print(f"   Media: {random_mean:+.1f}%")
print(f"   Desv.Est: {random_std:.1f}%")
print(f"   Umbral (μ + 2σ): {threshold:+.1f}%")

null_pass = real_return > threshold
print(f"\n   IA ({real_return:+.1f}%) > Umbral ({threshold:+.1f}%)?")
print(f"   {'✅ PASS' if null_pass else '❌ FAIL'}: IA {'supera' if null_pass else 'NO supera'} random + 2σ")


# ============================================================
# 3. TEST DE ESTRÉS (Comisiones altas)
# ============================================================
print("\n" + "=" * 70)
print("📉 TEST 3: ESTRÉS DE EJECUCIÓN")
print("=" * 70)

# Escenario pesimista
stress_result = run_backtest(commission=0.003, slippage=0.005)
stress_return = stress_result['total_return']

# Buy & Hold
bh_start = float(df_base.iloc[0]['Close'])
bh_end = float(df_base.iloc[-1]['Close'])
bh_return = (bh_end - bh_start) / bh_start * 100

print(f"\n⚡ Escenario Pesimista (0.3% com + 0.5% slip):")
print(f"   Retorno Estrategia: {stress_return:+.1f}%")
print(f"   Retorno Buy&Hold:   {bh_return:+.1f}%")

stress_pass = stress_return > bh_return
print(f"\n   {'✅ PASS' if stress_pass else '❌ FAIL'}: "
      f"{'Supera' if stress_pass else 'NO supera'} Buy & Hold en stress test")


# ============================================================
# 4. ANÁLISIS DE CONCENTRACIÓN
# ============================================================
print("\n" + "=" * 70)
print("📊 TEST 4: CONCENTRACIÓN DE PROFITS")
print("=" * 70)

# Recalcular trades con profits absolutos
result = run_backtest()
trades_detail = result['trades_detail']

# Calcular profit absoluto por trade
profits = []
running_capital = 1000
for t in trades_detail:
    profit_pct = t['profit_pct']
    profit_abs = running_capital * (profit_pct / 100)
    profits.append(profit_abs)
    running_capital = running_capital * (1 + profit_pct / 100)

# Top 3 trades
sorted_profits = sorted(profits, reverse=True)
top3 = sorted_profits[:3] if len(sorted_profits) >= 3 else sorted_profits
total_profit = sum(p for p in profits if p > 0)
top3_sum = sum(top3)
top3_pct = (top3_sum / total_profit * 100) if total_profit > 0 else 0

print(f"\n💰 Análisis de Trades Ganadores:")
print(f"   Total trades: {len(profits)}")
print(f"   Total profit positivo: ${total_profit:,.0f}")
print(f"\n   Top 3 trades:")
for i, p in enumerate(top3, 1):
    print(f"   #{i}: ${p:+,.0f}")
print(f"\n   Top 3 representan: {top3_pct:.1f}% del profit total")

concentration_warning = top3_pct > 90
print(f"\n   {'⚠️ WARNING: FRAGILE' if concentration_warning else '✅ OK'}: "
      f"{'Alta' if concentration_warning else 'Baja'} concentración de ganancias")


# ============================================================
# REPORTE FINAL
# ============================================================
print("\n" + "=" * 70)
print("📋 REPORTE DE ROBUSTEZ FINAL")
print("=" * 70)

tests = [
    ("Sensibilidad de Parámetros", sensitivity_pass),
    ("Null Hypothesis (IA > Random)", null_pass),
    ("Stress Test (Comisiones Altas)", stress_pass),
    ("Concentración de Profits", not concentration_warning),
]

print("\n   Test                              Resultado")
print("   " + "-" * 50)
passed = 0
for name, result in tests:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"   {name:<35} {status}")
    if result:
        passed += 1

print("   " + "-" * 50)
print(f"   Total: {passed}/{len(tests)} tests pasados")

# Veredicto final
all_passed = passed == len(tests)
critical_passed = null_pass and stress_pass  # Los más importantes

print("\n" + "=" * 70)
if all_passed:
    print("🏆 VEREDICTO: ✅ ROBUSTO")
    print("   La estrategia pasa todos los tests de validación.")
elif critical_passed:
    print("🔶 VEREDICTO: ⚠️ ACEPTABLE CON PRECAUCIÓN")
    print("   Supera random y stress test, pero tiene algunas debilidades.")
else:
    print("❌ VEREDICTO: ⚠️ SOBREAJUSTADO")
    print("   La estrategia NO pasa los tests críticos.")
print("=" * 70)
