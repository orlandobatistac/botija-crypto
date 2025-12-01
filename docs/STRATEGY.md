# Smart Trend Follower Strategy - Technical Documentation

## Overview

The Smart Trend Follower (STF) is a swing trading strategy optimized for Bitcoin that achieved **+2990% return** in backtesting from 2018-2025. It combines EMA crossovers with AI regime detection and protective protocols.

## Strategy Components

### 1. Entry Signal

**Condition**: Price > EMA20 + 1.5%

```python
entry_threshold = ema20 * 1.015  # EMA20 + 1.5%
should_enter = current_price > entry_threshold
```

**Rationale**: Entering above EMA20 with a buffer confirms the trend has momentum, avoiding false breakouts.

### 2. Exit Signal

**Condition**: Price < EMA50 - 1.5%

```python
exit_threshold = ema50 * 0.985  # EMA50 - 1.5%
should_exit = current_price < exit_threshold
```

**Rationale**: Using EMA50 as exit (instead of EMA20) allows trades to breathe during pullbacks while protecting profits on trend reversals.

### 3. AI Regime Detection

The AI analyzes market conditions and classifies into 4 regimes:

| Regime | Description | Leverage |
|--------|-------------|----------|
| BULL 🟢 | Strong uptrend, momentum positive | x1.5 (shadow) |
| BEAR 🔴 | Downtrend, price falling | x1.0 (spot) |
| LATERAL 🟡 | Sideways consolidation | x1.0 (spot) |
| VOLATILE 🟠 | High volatility, unpredictable | x1.0 (spot) |

**Implementation**: OpenAI GPT-4 receives real-time market data (price, EMAs, RSI, recent candles) and returns regime classification.

### 4. Winter Protocol ❄️

**Condition**: Activated when `Price < EMA200`

When in Winter Mode:
- Extra caution for entries
- Only enters if RSI > 65 (strong momentum required)
- Protects against bear market false signals

```python
is_winter_mode = current_price < ema200
if is_winter_mode:
    can_enter = rsi > 65  # Require strong momentum
else:
    can_enter = True
```

### 5. Dynamic Leverage (Shadow)

Leverage is only applied in BULL regime:

```python
if ai_regime == "BULL":
    leverage = 1.5
else:
    leverage = 1.0
```

**Shadow Margin**: The system tracks what profits would be with leverage WITHOUT actually using margin. This allows auditing the leverage strategy's effectiveness.

- `real_profit_usd`: Actual spot profit
- `shadow_profit_usd`: Simulated leveraged profit

## Technical Indicators

### EMA (Exponential Moving Average)

```python
# Using pandas-ta library
ema20 = ta.ema(close_prices, length=20)
ema50 = ta.ema(close_prices, length=50)
ema200 = ta.ema(close_prices, length=200)
```

### RSI (Relative Strength Index)

```python
rsi14 = ta.rsi(close_prices, length=14)
```

## Trading Cycle Flow

```
Every 4 hours (1:00, 5:00, 9:00, 13:00, 17:00, 21:00 ET):

1. Fetch market data from Kraken
2. Calculate indicators (EMA20, EMA50, EMA200, RSI14)
3. Get AI regime classification
4. Check Winter Protocol status
5. Evaluate entry/exit conditions
6. Execute trade if conditions met
7. Update trailing stop if position open
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
| leverage_multiplier | Float | 1.0 or 1.5 |
| is_winter_mode | Boolean | Winter Protocol status |
| ai_signal | String | BUY/SELL/HOLD |
| action | String | BOUGHT/SOLD/HOLD |
| trading_mode | String | PAPER/REAL |

### Trade

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| trade_id | String | Unique identifier |
| order_type | String | BUY/SELL |
| entry_price | Float | Entry price |
| exit_price | Float | Exit price (if closed) |
| quantity | Float | BTC quantity |
| ai_regime | String | Regime at entry |
| leverage_used | Float | Leverage applied |
| real_profit_usd | Float | Actual profit |
| shadow_profit_usd | Float | Simulated leveraged profit |

## API Endpoints

### Bot Status
```
GET /api/v1/bot/dashboard
GET /api/v1/bot/scheduler/status
```

### Trading Cycles
```
GET /api/v1/cycles?limit=100
POST /api/v1/bot/cycle  (manual trigger)
```

### Paper Trading
```
GET /api/v1/paper/wallet
POST /api/v1/paper/reset
```

## Configuration

### Environment Variables

```env
# Trading Strategy
TRADING_INTERVAL_HOURS=4     # Cycle frequency
TRADE_AMOUNT_PERCENT=100     # % of balance per trade
TRAILING_STOP_PERCENTAGE=2   # Trailing stop distance

# STF Parameters (hardcoded for now)
ENTRY_BUFFER=0.015           # 1.5% above EMA20
EXIT_BUFFER=0.015            # 1.5% below EMA50
WINTER_RSI_THRESHOLD=65      # RSI required in Winter Mode
BULL_LEVERAGE=1.5            # Leverage in BULL regime
```

## Backtesting Results (2018-2025)

| Metric | Value |
|--------|-------|
| Total Return | +2990% |
| Win Rate | ~65% |
| Max Drawdown | ~35% |
| Avg Trade Duration | 2-3 weeks |
| Total Trades | ~120 |

## Files Reference

| File | Purpose |
|------|---------|
| `smart_trend_follower.py` | STF strategy logic |
| `ai_regime.py` | AI regime detection |
| `trading_bot.py` | Main orchestrator |
| `technical_indicators.py` | EMA, RSI calculations |
| `trailing_stop.py` | Trailing stop manager |
| `modes/paper.py` | Paper trading engine |
| `modes/real.py` | Real trading engine |

---

**Version**: 3.0.0 | **Strategy**: Smart Trend Follower
