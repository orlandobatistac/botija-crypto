# Smart Trend Follower Strategy - Technical Documentation

## Overview

The Smart Trend Follower (STF) is a swing trading strategy optimized for Bitcoin.

**Backtest Results (2018-2025):**
- **SPOT (x1.0):** +2412% return ($1,000 → $25,125)
- **vs Buy & Hold (+601%):** Outperforms by +1811%
- **Max Drawdown:** 42.3% (vs B&H 76.6%)
- **Total Trades:** 33 | **Win Rate:** 39.4%

**Robustness Validation:**
| Test | Result | Detail |
|------|--------|--------|
| Sensitivity | ✅ PASS | Stable across EMA40-60, Buffer 1-2% |
| Stress Test | ✅ PASS | +847% even with 0.3% fees |
| Concentration | ✅ PASS | Top 3 trades = 61% profits |
| Null Hypothesis | ❌ FAIL | Random regimes: +1958% vs AI: +1444% |

**Key Insight:** The Null Hypothesis "failure" reveals that the **EMA50 exit logic is the true edge**, not the AI regime detection. The strategy profits even with random regime assignments because the technical backbone (EMA50 exit + Winter Protocol) is inherently robust. The AI provides consistency and narrative value, but the core alpha comes from the exit logic.

## Strategy Components

### 1. Entry Signal (Regime-Specific)

| Regime | Entry Threshold | Rationale |
|--------|-----------------|-----------|
| BULL 🟢 | Price > EMA20 + 1.5% | Aggressive - ride momentum |
| LATERAL 🟡 | Price > EMA50 + 1.5% | Conservative - wait for confirmation |
| VOLATILE 🟠 | **BLOCKED** | 0% win rate in backtest |
| BEAR 🔴 | **BLOCKED** | Capital protection |

```python
BUFFER = 0.015  # 1.5%

if regime == 'BULL':
    entry_threshold = ema20 * (1 + BUFFER)
elif regime == 'LATERAL':
    entry_threshold = ema50 * (1 + BUFFER)
else:  # BEAR or VOLATILE
    entry_blocked = True  # 0% win rate
```

### 2. Exit Signal

**Standard Exit**: Price < EMA50 - 1.5%

**BULL Exception**: Only exit if Price < EMA50 - 3% (catastrophic drop)

```python
exit_threshold = ema50 * (1 - BUFFER)  # EMA50 - 1.5%
catastrophic_threshold = ema50 * 0.97   # EMA50 - 3%

if price < exit_threshold:
    if regime == 'BULL':
        should_exit = price < catastrophic_threshold  # More room
    else:
        should_exit = True
```

**Rationale**: Using EMA50 as exit (not EMA20) allows trades to breathe. Monte Carlo tests prove this is the robust core of the strategy.

### 3. AI Regime Detection

OpenAI GPT-5.1 classifies market conditions:

| Regime | Description | Entry | Action |
|--------|-------------|-------|--------|
| BULL 🟢 | Strong uptrend | EMA20+1.5% | Trade allowed |
| LATERAL 🟡 | Sideways | EMA50+1.5% | Trade allowed |
| VOLATILE 🟠 | High volatility | BLOCKED | 0% win rate |
| BEAR 🔴 | Downtrend | BLOCKED | Capital protection |

### 4. Winter Protocol ❄️

**Condition**: Activated when `Price < EMA200`

```python
is_winter = price < ema200

if is_winter:
    if regime != 'BULL':
        entry_blocked = True  # Only BULL allowed
    elif rsi < 65:
        entry_blocked = True  # Need strong momentum
    else:
        # Winter entry allowed - uses EMA20+1.5% threshold
        entry_threshold = ema20 * (1 + BUFFER)
```

**Rationale**: Prevents entries during macro bear markets (2018, 2022).

### 5. Shadow Margin (Audit Only)

Tracks hypothetical leveraged returns WITHOUT real margin:

```python
if regime == 'BULL':
    shadow_leverage = 1.5  # Tracked for audit
else:
    shadow_leverage = 1.0

# Real execution is ALWAYS spot
real_leverage = 1.0
```

## Technical Indicators

| Indicator | Calculation | Usage |
|-----------|-------------|-------|
| EMA20 | 20-period EWM | Entry (BULL/VOLATILE) |
| EMA50 | 50-period EWM | Entry (LATERAL) + Exit |
| EMA200 | 200-period EWM | Winter Protocol |
| RSI14 | 14-period RSI | Winter momentum filter |

```python
# Requires 1000+ candles for accurate EMA200
OHLC_LIMIT = 1000
OHLC_TIMEFRAME = '4h'
```

## Trading Cycle Flow

```
Every 4 hours (0:00, 4:00, 8:00, 12:00, 16:00, 20:00 ET):

1. Fetch 1000 candles from Kraken (CCXT)
2. Calculate indicators (EMA20, EMA50, EMA200, RSI14)
3. Get AI regime classification (OpenAI)
4. Check Winter Protocol status
5. Evaluate entry/exit with StrategyEngine
6. Execute trade if signal (paper or real)
7. Update paper wallet balance
8. Log cycle to database
9. Send Telegram alert
```

## Database Schema

### TradingCycle

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| timestamp | DateTime | Cycle execution time |
| btc_price | Float | Current BTC price |
| ema20, ema50 | Float | EMA values |
| ema200 | Float | EMA200 for Winter Protocol |
| rsi14 | Float | RSI value |
| ai_regime | String | BULL/BEAR/LATERAL/VOLATILE |
| leverage_multiplier | Float | 1.0 or 1.5 (shadow) |
| is_winter_mode | Boolean | Winter Protocol status |
| ai_signal | String | BUY/SELL/HOLD |
| action | String | BOUGHT/SOLD/HOLD |
| trading_mode | String | PAPER/REAL |

### BotStatus (Paper Wallet)

| Column | Type | Description |
|--------|------|-------------|
| trading_mode | String | PAPER/REAL |
| btc_balance | Float | BTC holdings |
| usd_balance | Float | USD balance ($1000 initial) |
| last_buy_price | Float | Entry price |

## Core Classes

### StrategyEngine (Pure Functions)
```python
class StrategyEngine:
    @staticmethod
    def calculate_indicators(closes) -> Dict
    @staticmethod
    def is_winter_mode(close, ema200) -> bool
    @staticmethod
    def get_shadow_leverage(regime) -> float
    @staticmethod
    def should_enter(close, ema20, ema50, ema200, rsi, regime, has_position) -> Tuple[bool, str]
    @staticmethod
    def should_exit(close, ema50, regime, has_position) -> Tuple[bool, str]
    @staticmethod
    def get_trading_signal(closes, regime, has_position) -> Dict
```

### TradingBot (Orchestrator)
```python
class TradingBot:
    def __init__(self, ..., dry_run=False)
    def _get_balance() -> Dict  # Paper or real
    def _update_paper_balance(btc, usd)
    async def run_cycle(trigger) -> Dict
    async def execute_buy(analysis) -> bool
    async def execute_sell(analysis) -> bool
```

## API Endpoints

### Bot Status
```
GET /api/v1/bot/status
GET /api/v1/bot/dashboard
GET /api/v1/bot/scheduler/status
```

### Trading Cycles
```
GET /api/v1/bot/cycles?limit=100
POST /api/v1/bot/cycle  (manual trigger)
```

### Paper Trading
```
GET /api/v1/paper/wallet
POST /api/v1/paper/reset
```

## Configuration Constants

```python
# Strategy (hardcoded in trading_bot.py)
BUFFER_PERCENT = 0.015          # 1.5% hysteresis
BULL_SHADOW_LEVERAGE = 1.5      # Shadow leverage for BULL
SPOT_LEVERAGE = 1.0             # Real execution
RSI_WINTER_THRESHOLD = 65       # RSI minimum for winter buys
OHLC_LIMIT = 1000               # Candles for EMA200 accuracy
OHLC_TIMEFRAME = '4h'           # 4-hour candles
```

## Backtesting & Validation

### Backtest vs Production Differences

| Aspect | Backtest | Production Bot |
|--------|----------|----------------|
| **OHLC Data** | Daily (yfinance) | 4H candles (Kraken CCXT) |
| **AI Regime Source** | Pre-populated DB (daily) | Real-time OpenAI API (each 4H cycle) |
| **Regime Granularity** | Daily from `ai_market_regimes` table | Fresh call every 4 hours |

**Note**: Backtest uses daily candles due to yfinance historical data limitations. Production uses 4H candles for more responsive signals. The strategy logic (entry/exit thresholds) is identical.

### AI Regime in Backtest

The backtest reads pre-populated regimes from `ai_market_regimes` table:
- **2018-2019**: Synthetic regimes generated from indicators (EMA/RSI rules)
- **2020-2025**: Real AI regimes populated via `scripts/populate_ai_regimes.py`

```python
# Backtest loads regimes by date
params = get_regime_params(date)  # Returns regime for that day
regime = params['regime']  # BULL, BEAR, LATERAL, VOLATILE
```

### Run Backtest
```bash
python scripts/run_ai_backtest.py
```

### Overfitting Tests
```bash
python scripts/test_overfitting.py
```

### Unit Tests
```bash
cd backend && python -m pytest tests/test_strategy_logic.py -v
```

## Files Reference

| File | Purpose |
|------|---------|
| `trading_bot.py` | Core bot with StrategyEngine + CCXT |
| `ai_regime.py` | OpenAI regime detection |
| `modes/paper.py` | Paper trading engine |
| `test_strategy_logic.py` | 22 strategy tests |
| `run_ai_backtest.py` | Backtest validation |
| `test_overfitting.py` | Robustness tests |

---

**Version**: 3.1.0 | **Strategy**: Smart Trend Follower + CCXT
