"""
Backtest con parámetros AI dinámicos vs Buy & Hold
VERSION AUDITADA - Smart Trend Following (IA + EMA50)

Correcciones aplicadas:
1. Timing: Señal en Close[T], ejecución en Close[T] con slippage 0.1%
2. Comisiones: 0.1% por operación (Binance estándar)
3. Lógica EMA50: Jerarquía correcta de decisiones
4. Debug: Prints detallados para semanas clave
"""
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf

# ============================================================
# CONFIGURACIÓN
# ============================================================
COMMISSION = 0.001      # 0.1% por operación
SLIPPAGE = 0.001        # 0.1% slippage simulado
BUFFER = 0.015          # 1.5% histéresis para evitar whipsaws
LEVERAGE = 1.5          # Apalancamiento x1.5
DAILY_INTEREST = 0.0004 # 0.04% diario por préstamo
DEBUG_MODE = True       # Mostrar decisiones detalladas
DEBUG_DATES = [         # Fechas clave para debug
    '2020-03-12',       # COVID crash
    '2021-05-17',       # China ban - antes
    '2021-05-18',       # China ban - antes
    '2021-05-19',       # China ban
    '2021-05-20',       # China ban - después
    '2021-11-10',       # ATH antes de caída
    '2022-06-13',       # Bear market profundo
    '2024-03-14',       # Bull run 2024
]

print("=" * 70)
print("🤖 BACKTEST AUDITADO: SMART TREND FOLLOWING (IA + EMA50)")
print("=" * 70)
print(f"   Comisión: {COMMISSION*100:.1f}% | Slippage: {SLIPPAGE*100:.1f}%")

# 1. Cargar datos de BTC
print("\n📥 Cargando datos de BTC 2018-2025...")
btc = yf.download("BTC-USD", start="2018-01-01", end="2025-11-30", progress=False)
print(f"   Datos: {len(btc)} días")

# 2. Calcular indicadores
print("\n📊 Calculando indicadores...")

if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

df = pd.DataFrame(index=btc.index)
df['Open'] = btc['Open'].values
df['Close'] = btc['Close'].values
df['ema20'] = df['Close'].ewm(span=20).mean()
df['ema50'] = df['Close'].ewm(span=50).mean()
df['ema200'] = df['Close'].ewm(span=200).mean()  # Protocolo de Invierno

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
print(f"   Regímenes AI cargados: {len(regimes_df)} semanas")
print(f"   Distribución: {regimes_df['regime'].value_counts().to_dict()}")

# Generar regímenes sintéticos para 2018-2019 (antes de tener IA)
print("\n📊 Generando regímenes sintéticos para 2018-2019...")
synthetic_count = 0
for date in df.index:
    if date < pd.Timestamp('2020-01-01'):
        week_start = date - pd.Timedelta(days=date.dayofweek)
        week_start = week_start.normalize()
        if week_start not in regimes_dict:
            row = df.loc[date]
            # Lógica simple basada en indicadores
            if row['Close'] > row['ema50'] and row['rsi'] > 55:
                regime = 'BULL'
            elif row['Close'] < row['ema50'] and row['rsi'] < 45:
                regime = 'BEAR'
            elif row['rsi'] > 60 or row['rsi'] < 40:
                regime = 'VOLATILE'
            else:
                regime = 'LATERAL'
            regimes_dict[week_start] = {
                'regime': regime, 'buy_threshold': 50, 'sell_threshold': 35,
                'capital_percent': 75, 'stop_loss_percent': 2.0
            }
            synthetic_count += 1
print(f"   Regímenes sintéticos creados: {synthetic_count}")

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

# ============================================================
# 4. BACKTEST AUDITADO
# ============================================================
print("\n🔄 Ejecutando backtest AUDITADO...")

initial_capital = 1000
capital = initial_capital
btc_holdings = 0
position = None
trades = []
equity_curve = []
total_commissions = 0
debug_logs = []

for i in range(len(df)):
    row = df.iloc[i]
    date = row.name
    date_str = date.strftime('%Y-%m-%d')
    close_price = float(row['Close'])
    ema20 = float(row['ema20'])
    ema50 = float(row['ema50'])

    params = get_regime_params(date)
    regime = params['regime']

    price_below_ema50 = close_price < ema50
    is_debug_date = date_str in DEBUG_DATES

    # ============================================================
    # LÓGICA DE TRADING: SMART TREND FOLLOWING + PROTOCOLO INVIERNO
    # ============================================================

    # --- SIN POSICIÓN: DECIDIR SI COMPRAR ---
    if position is None:
        should_buy = False
        buy_reason = ""

        ema20_upper = ema20 * (1 + BUFFER)  # EMA20 + 1.5% (Fast Entry)
        ema200 = float(row['ema200'])
        rsi = float(row['rsi'])

        # PROTOCOLO DE INVIERNO: Detectar Bear Market Macro
        is_crypto_winter = close_price < ema200

        if is_crypto_winter:
            # EN INVIERNO: Solo compramos si la IA dice BULL + RSI > 65 (momentum fuerte)
            # RSI 50-65 en invierno = rebote técnico falso, no comprar
            if regime == 'BULL' and rsi > 65:
                should_buy = True
                buy_reason = f"❄️ Invierno + BULL + RSI {rsi:.0f}>65 | Precio ${close_price:,.0f} < EMA200 ${ema200:,.0f}"
            else:
                should_buy = False  # CASH - IA dice Bull pero momentum insuficiente
                # No hay buy_reason porque no compramos
        else:
            # NO ES INVIERNO (Precio > EMA200): Lógica normal
            is_bullish_ai = (regime == 'BULL')
            is_technical_recovery = (regime != 'BEAR') and (close_price > ema20_upper)

            if is_bullish_ai:
                should_buy = True
                buy_reason = "Régimen BULL (Modo Euforia)"
            elif is_technical_recovery:
                should_buy = True
                buy_reason = f"Fast Entry: {regime} + Precio ${close_price:,.0f} > EMA20+1.5% ${ema20_upper:,.0f}"

        if should_buy and capital > 10:
            # DYNAMIC LEVERAGE: Solo apalancamiento en BULL
            if regime == 'BULL':
                current_leverage = LEVERAGE  # x1.5 en Euforia
            else:
                current_leverage = 1.0  # Spot en recuperación técnica

            exec_price = close_price * (1 + SLIPPAGE)
            buying_power = capital * current_leverage
            loan_amount = capital * (current_leverage - 1)  # 0 si spot
            commission = buying_power * COMMISSION
            invest = buying_power - commission
            btc_holdings = invest / exec_price
            total_commissions += commission
            capital = 0  # Todo el capital propio está invertido
            position = {
                'entry_price': exec_price,
                'entry_date': date,
                'regime': regime,
                'btc': btc_holdings,
                'loan_amount': loan_amount,
                'leverage_used': current_leverage
            }

            if is_debug_date:
                lev_str = f"x{current_leverage}" if current_leverage > 1 else "Spot"
                debug_logs.append(
                    f"🟢 {date_str}: COMPRA ({lev_str}) | Precio: ${exec_price:,.0f} | "
                    f"Régimen: {regime} | Razón: {buy_reason}"
                )

    # --- CON POSICIÓN: DECIDIR SI VENDER ---
    elif position is not None:
        should_sell = False
        sell_reason = ""

        # JERARQUÍA DE DECISIONES - LÓGICA SIMPLIFICADA FINAL
        # Evaluamos régimen ACTUAL (no el de entrada)

        # 1. ¿Qué dice la IA HOY?
        if regime == 'BULL':
            # MODO EUFORIA: HOLD siempre
            # Ignoramos si el precio rompe EMA momentáneamente (Bear Trap)
            should_sell = False
            sell_reason = f"HOLD - IA dice BULL (Modo Euforia)"

        # 2. Si la IA NO dice BULL (BEAR, VOLATILE o LATERAL):
        else:
            ema50_lower = ema50 * (1 - BUFFER)  # EMA50 - 1.5%
            # ¿Qué dice el Gráfico HOY? (con buffer de histéresis)
            if close_price < ema50_lower:
                # IA no es optimista Y perdimos soporte con fuerza = VENDER
                should_sell = True
                sell_reason = f"VENTA - {regime} + Precio ${close_price:,.0f} < EMA50-1.5% ${ema50_lower:,.0f}"
            else:
                # IA duda pero no rompimos soporte con fuerza = HOLD
                should_sell = False
                sell_reason = f"HOLD - {regime} pero Precio > EMA50-1.5% (buffer aguanta)"

        # Debug log para fechas clave
        if is_debug_date:
            action = "VENTA" if should_sell else "HOLD"
            debug_logs.append(
                f"{'🔴' if should_sell else '🟡'} {date_str}: {action} | "
                f"Precio: ${close_price:,.0f} | EMA50: ${ema50:,.0f} | "
                f"Régimen: {regime} | Razón: {sell_reason}"
            )

        if should_sell:
            # DYNAMIC LEVERAGE: Liquidación con devolución de préstamo (si existe)
            exec_price = close_price * (1 - SLIPPAGE)
            gross_value = btc_holdings * exec_price
            commission = gross_value * COMMISSION
            total_commissions += commission

            # Calcular intereses solo si hubo préstamo
            loan_amount = position['loan_amount']
            interest_cost = 0
            if loan_amount > 0:
                days_held = (date - position['entry_date']).days
                if days_held < 1:
                    days_held = 1  # Mínimo 1 día
                interest_cost = loan_amount * DAILY_INTEREST * days_held

            # Capital final = Valor bruto - préstamo - intereses - comisión
            net_value = gross_value - loan_amount - interest_cost - commission

            profit_pct = (exec_price - position['entry_price']) / position['entry_price'] * 100
            capital = max(0, net_value)  # Evitar capital negativo (liquidación)

            trades.append({
                'entry_date': position['entry_date'],
                'exit_date': date,
                'exit_price': exec_price,
                'entry_price': position['entry_price'],
                'profit_pct': profit_pct,
                'regime': position['regime'],
                'leverage': position.get('leverage_used', 1.0),
                'interest_paid': interest_cost
            })
            btc_holdings = 0
            position = None

    # Equity curve (considerando deuda si hay posición abierta)
    if position is not None:
        # Valor neto = valor BTC - préstamo pendiente - intereses acumulados
        loan_amount = position['loan_amount']
        accrued_interest = 0
        if loan_amount > 0:
            days_held = (date - position['entry_date']).days
            if days_held < 1:
                days_held = 1
            accrued_interest = loan_amount * DAILY_INTEREST * days_held
        net_equity = btc_holdings * close_price - loan_amount - accrued_interest
        total_value = max(0, net_equity)
    else:
        total_value = capital
    equity_curve.append(total_value)

# Cerrar posición final (si existe)
if position is not None:
    final_date = df.index[-1]
    final_price = float(df.iloc[-1]['Close']) * (1 - SLIPPAGE)
    gross_value = btc_holdings * final_price
    commission = gross_value * COMMISSION
    total_commissions += commission

    # Calcular intereses finales
    days_held = (final_date - position['entry_date']).days
    if days_held < 1:
        days_held = 1
    loan_amount = position['loan_amount']
    interest_cost = loan_amount * DAILY_INTEREST * days_held

    # Capital final = Valor bruto - préstamo - intereses - comisión
    capital = max(0, gross_value - loan_amount - interest_cost - commission)

    profit_pct = (final_price - position['entry_price']) / position['entry_price'] * 100
    trades.append({
        'entry_date': position['entry_date'],
        'exit_date': final_date,
        'entry_price': position['entry_price'],
        'exit_price': final_price,
        'profit_pct': profit_pct,
        'regime': position['regime'],
        'interest_paid': interest_cost
    })

ai_final = capital
ai_return = (ai_final - initial_capital) / initial_capital * 100

# Max drawdown
equity_curve = np.array(equity_curve)
peak = np.maximum.accumulate(equity_curve)
drawdown = (peak - equity_curve) / peak * 100
ai_max_dd = np.max(drawdown)

win_rate = sum(1 for t in trades if t['profit_pct'] > 0) / len(trades) * 100 if trades else 0

# ============================================================
# DETALLE DE TRADES
# ============================================================
print("\n" + "=" * 100)
print("📋 DETALLE DE TODOS LOS TRADES")
print("=" * 100)
print(f"{'#':<3} {'Entrada':<12} {'Salida':<12} {'Régimen':<10} {'Lever':<6} {'P.Entrada':>12} {'P.Salida':>12} {'Profit %':>10} {'Interés':>10}")
print("-" * 100)

running_capital = initial_capital
for i, t in enumerate(trades, 1):
    entry_date = t['entry_date'].strftime('%Y-%m-%d')
    exit_date = t['exit_date'].strftime('%Y-%m-%d')
    leverage = t.get('leverage', 1.0)
    interest = t.get('interest_paid', 0)
    profit_symbol = "✅" if t['profit_pct'] > 0 else "❌"
    print(f"{i:<3} {entry_date:<12} {exit_date:<12} {t['regime']:<10} x{leverage:<5.1f} ${t['entry_price']:>10,.0f} ${t['exit_price']:>10,.0f} {t['profit_pct']:>+9.1f}% ${interest:>9.2f} {profit_symbol}")

print("-" * 100)
print(f"{'TOTAL':>3} {'':<12} {'':<12} {'':<10} {'':<6} {'':<12} {'':<12} {'':<10} ${sum(t.get('interest_paid', 0) for t in trades):>9.2f}")

# Evolución del capital
print("\n" + "=" * 70)
print("📈 EVOLUCIÓN DEL CAPITAL")
print("=" * 70)
print(f"   Capital Inicial:     ${initial_capital:,.2f}")
print(f"   Capital Final:       ${ai_final:,.2f}")
print(f"   Ganancia Neta:       ${ai_final - initial_capital:,.2f}")
print(f"   Retorno Total:       {ai_return:+.1f}%")
print(f"   Total Comisiones:    ${total_commissions:.2f}")
print(f"   Total Intereses:     ${sum(t.get('interest_paid', 0) for t in trades):.2f}")

# ============================================================
# RETORNOS POR AÑO Y MES
# ============================================================
print("\n" + "=" * 70)
print("📅 RETORNOS POR AÑO")
print("=" * 70)

# Crear DataFrame de equity con fechas
equity_df = pd.DataFrame({
    'date': df.index,
    'equity': equity_curve
})
equity_df.set_index('date', inplace=True)
equity_df['year'] = equity_df.index.year
equity_df['month'] = equity_df.index.month
equity_df['year_month'] = equity_df.index.to_period('M')

# Retornos anuales
print(f"\n{'Año':<8} {'Inicio':>12} {'Fin':>12} {'Retorno':>12} {'Max DD':>10}")
print("-" * 56)
years = sorted(equity_df['year'].unique())
for year in years:
    year_data = equity_df[equity_df['year'] == year]['equity']
    if len(year_data) > 0:
        start_val = year_data.iloc[0]
        end_val = year_data.iloc[-1]
        year_return = (end_val - start_val) / start_val * 100
        # Max DD del año
        year_peak = np.maximum.accumulate(year_data.values)
        year_dd = (year_peak - year_data.values) / year_peak * 100
        year_max_dd = np.max(year_dd)
        symbol = "✅" if year_return > 0 else "❌"
        print(f"{year:<8} ${start_val:>10,.0f} ${end_val:>10,.0f} {year_return:>+11.1f}% {year_max_dd:>9.1f}% {symbol}")

# Retornos mensuales
print("\n" + "=" * 100)
print("📆 RETORNOS MENSUALES")
print("=" * 100)

# Calcular retorno mensual
monthly_returns = {}
for ym in equity_df['year_month'].unique():
    month_data = equity_df[equity_df['year_month'] == ym]['equity']
    if len(month_data) > 0:
        start_val = month_data.iloc[0]
        end_val = month_data.iloc[-1]
        ret = (end_val - start_val) / start_val * 100
        monthly_returns[ym] = ret

# Crear tabla pivote año x mes
print(f"\n{'Año':<6}", end="")
for m in range(1, 13):
    print(f"{'Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic'.split()[m-1]:>8}", end="")
print(f"{'TOTAL':>10}")
print("-" * 112)

for year in years:
    print(f"{year:<6}", end="")
    year_total = 0
    for month in range(1, 13):
        ym = pd.Period(f"{year}-{month:02d}", freq='M')
        if ym in monthly_returns:
            ret = monthly_returns[ym]
            year_total += ret
            if ret > 5:
                print(f"{ret:>+7.1f}%", end="")
            elif ret < -5:
                print(f"{ret:>+7.1f}%", end="")
            else:
                print(f"{ret:>+7.1f}%", end="")
        else:
            print(f"{'--':>8}", end="")
    print(f"{year_total:>+9.1f}%")

# Estadísticas mensuales
positive_months = sum(1 for r in monthly_returns.values() if r > 0)
negative_months = sum(1 for r in monthly_returns.values() if r < 0)
avg_positive = np.mean([r for r in monthly_returns.values() if r > 0]) if positive_months > 0 else 0
avg_negative = np.mean([r for r in monthly_returns.values() if r < 0]) if negative_months > 0 else 0

print("-" * 112)
print(f"\n📊 Estadísticas Mensuales:")
print(f"   Meses positivos: {positive_months} ({positive_months/len(monthly_returns)*100:.1f}%)")
print(f"   Meses negativos: {negative_months} ({negative_months/len(monthly_returns)*100:.1f}%)")
print(f"   Retorno promedio mes positivo: {avg_positive:+.1f}%")
print(f"   Retorno promedio mes negativo: {avg_negative:+.1f}%")

# ============================================================
# 5. BUY & HOLD (con comisiones para comparación justa)
# ============================================================
bh_start = float(df.iloc[0]['Close'])
bh_end = float(df.iloc[-1]['Close'])

# B&H también paga comisión de entrada y salida
bh_invested = initial_capital - (initial_capital * COMMISSION)
bh_btc = bh_invested / (bh_start * (1 + SLIPPAGE))
bh_final_gross = bh_btc * bh_end * (1 - SLIPPAGE)
bh_final = bh_final_gross - (bh_final_gross * COMMISSION)

bh_return = (bh_final - initial_capital) / initial_capital * 100

# Max DD de B&H
prices = df['Close'].values
bh_peak = np.maximum.accumulate(prices)
bh_dd = (bh_peak - prices) / bh_peak * 100
bh_max_dd = np.max(bh_dd)

# ============================================================
# 6. DEBUG LOGS
# ============================================================
if DEBUG_MODE and debug_logs:
    print("\n" + "=" * 70)
    print("🔍 DEBUG: DECISIONES EN FECHAS CLAVE")
    print("=" * 70)
    for log in debug_logs:
        print(f"   {log}")

# ============================================================
# 7. RESULTADOS FINALES
# ============================================================
print("\n" + "=" * 70)
print("📊 RESULTADOS FINALES (CON COMISIONES)")
print("=" * 70)

print(f"\n🤖 ESTRATEGIA AI (Smart Trend Following):")
print(f"   Capital final:   ${ai_final:,.2f}")
print(f"   Retorno total:   {ai_return:+.1f}%")
print(f"   Max Drawdown:    {ai_max_dd:.1f}%")
print(f"   Trades:          {len(trades)}")
print(f"   Win Rate:        {win_rate:.1f}%")
print(f"   Comisiones:      ${total_commissions:.2f}")

print(f"\n📈 BUY & HOLD:")
print(f"   Capital final:   ${bh_final:,.2f}")
print(f"   Retorno total:   {bh_return:+.1f}%")
print(f"   Max Drawdown:    {bh_max_dd:.1f}%")

print("\n" + "=" * 70)
print("📋 TABLA COMPARATIVA FINAL")
print("=" * 70)
print(f"\n{'Métrica':<20} {'AI Bot':>15} {'Buy & Hold':>15} {'Diferencia':>15}")
print("-" * 65)
print(f"{'Retorno Total':<20} {ai_return:>+14.1f}% {bh_return:>+14.1f}% {ai_return - bh_return:>+14.1f}%")
print(f"{'Max Drawdown':<20} {ai_max_dd:>14.1f}% {bh_max_dd:>14.1f}% {bh_max_dd - ai_max_dd:>+14.1f}%")
print(f"{'Trades':<20} {len(trades):>15} {'1':>15} {len(trades)-1:>+15}")
print(f"{'Capital Final':<20} ${ai_final:>13,.0f} ${bh_final:>13,.0f} ${ai_final-bh_final:>+13,.0f}")

print("\n" + "-" * 65)
diff = ai_return - bh_return
if diff > 0:
    print(f"✅ AI GANA POR {diff:+.1f}% con {bh_max_dd - ai_max_dd:.1f}% MENOS RIESGO")
elif ai_max_dd < bh_max_dd * 0.7:  # Si DD es 30% menor, considerar victoria
    print(f"🟡 B&H gana en retorno ({-diff:.1f}%) pero AI tiene {bh_max_dd - ai_max_dd:.1f}% MENOS DRAWDOWN")
else:
    print(f"❌ BUY & HOLD GANA POR {-diff:.1f}%")

# ============================================================
# 8. ANÁLISIS POR RÉGIMEN
# ============================================================
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

# ============================================================
# 9. VEREDICTO FINAL
# ============================================================
print("\n" + "=" * 70)
print("⚖️ VEREDICTO FINAL")
print("=" * 70)

if ai_return > bh_return:
    print("\n🏆 LA ESTRATEGIA AI SUPERA A BUY & HOLD")
    print("   ✅ APROBADO para considerar Live Trading")
elif ai_return > bh_return * 0.9 and ai_max_dd < bh_max_dd * 0.7:
    print("\n🥈 LA ESTRATEGIA AI tiene mejor perfil RIESGO/RETORNO")
    print("   🟡 Considerar si se valora más la protección del capital")
else:
    print("\n❌ BUY & HOLD sigue siendo superior")
    print("   ⚠️ NO RECOMENDADO para Live Trading hasta mejorar estrategia")
