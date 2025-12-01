# Kraken AI Trading Bot v3.0 - Smart Trend Follower

## 📌 Overview

Automated **BTC swing trading bot** using **Kraken Spot API** with the **Smart Trend Follower (STF)** strategy. Achieved **+2990% return** in backtesting (2018-2025).

**Core Features:**
- **EMA-based entries/exits** (EMA20+1.5% entry, EMA50-1.5% exit)
- **AI Regime Detection** (BULL/BEAR/LATERAL/VOLATILE)
- **Dynamic Leverage** (x1.5 in BULL, x1.0 spot otherwise)
- **Winter Protocol** (protective filter when price < EMA200)
- **Shadow Margin Tracking** (audit leverage without real margin)
- **Telegram Alerts** for all trading events

## 🚀 Quick Start

```bash
# Start API
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Access
# Dashboard: http://localhost:8001/
# API Docs: http://localhost:8001/docs
```

## 🧠 Smart Trend Follower Strategy

### Entry Conditions
- Price crosses **above EMA20 + 1.5%**
- AI Regime is favorable (BULL preferred)
- Winter Protocol check passes (if price < EMA200, requires RSI > 65)

### Exit Conditions
- Price crosses **below EMA50 - 1.5%**
- Or trailing stop triggered

### Dynamic Leverage
| AI Regime | Leverage | Mode |
|-----------|----------|------|
| BULL 🟢 | x1.5 | Margin (shadow) |
| BEAR 🔴 | x1.0 | Spot |
| LATERAL 🟡 | x1.0 | Spot |
| VOLATILE 🟠 | x1.0 | Spot |

### Winter Protocol ❄️
When `Price < EMA200`:
- Extra caution mode activated
- Only enters if RSI > 65 (strong momentum)
- Protects against bear market entries

## 📊 Technical Indicators

| Indicator | Usage |
|-----------|-------|
| EMA20 | Entry trigger (price > EMA20+1.5%) |
| EMA50 | Exit trigger (price < EMA50-1.5%) |
| EMA200 | Winter Protocol filter |
| RSI14 | Momentum confirmation |

## 🤖 AI Regime Detection

OpenAI analyzes real-time market data to classify:
- **BULL**: Strong uptrend, use leverage
- **BEAR**: Downtrend, stay in spot
- **LATERAL**: Sideways, stay in spot
- **VOLATILE**: High volatility, stay in spot

## 📁 Project Structure

```
botija-crypto/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── scheduler.py         # Trading cycles (every 4h)
│   │   ├── models.py            # DB models
│   │   ├── routers/             # API endpoints
│   │   └── services/
│   │       ├── trading_bot.py   # Main bot logic
│   │       ├── smart_trend_follower.py  # STF strategy
│   │       ├── ai_regime.py     # AI regime detection
│   │       ├── kraken_client.py # Kraken API
│   │       ├── technical_indicators.py
│   │       ├── trailing_stop.py
│   │       ├── telegram_alerts.py
│   │       └── modes/
│   │           ├── paper.py     # Paper trading
│   │           └── real.py      # Real trading
│   └── tests/
├── frontend/
│   ├── index.html               # Dashboard
│   └── stores/                  # Alpine.js state
├── scripts/                     # Deploy & migrations
└── docs/                        # Documentation
```

## ⚙️ Configuration

### Environment Variables
```env
# Kraken API
KRAKEN_API_KEY=
KRAKEN_SECRET_KEY=

# OpenAI
OPENAI_API_KEY=

# Telegram Alerts
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

# Trading
TRADING_MODE=PAPER           # PAPER or REAL
TRADING_INTERVAL_HOURS=4     # Cycle frequency
TRADE_AMOUNT_PERCENT=100     # % of balance per trade
```

## 📈 Dashboard Features

- **Bot Status**: Active/Inactive, PAPER/REAL mode
- **Balances**: BTC and USD
- **Next Cycle Countdown**: Real-time from scheduler
- **Trading Cycles History**: With STF strategy data
  - AI Regime (BULL/BEAR/LATERAL/VOLATILE)
  - Leverage used (x1.5/x1.0)
  - Winter Mode status
  - EMAs and RSI values

## 🔧 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, APScheduler
- **Frontend**: Alpine.js, TailwindCSS
- **Trading**: krakenex, pandas, ta
- **AI**: OpenAI GPT-4
- **Alerts**: python-telegram-bot
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Deploy**: VPS + Nginx + systemd + GitHub Actions

## 📊 Shadow Margin Tracking

Tracks hypothetical leverage performance without real margin:
- `real_profit_usd`: Actual spot profit
- `shadow_profit_usd`: Simulated x1.5 profit in BULL regime

Allows auditing if leverage would have improved returns.

## 🛡️ Safety Features

- **No real leverage** (shadow tracking only)
- **Spot trading only** on Kraken
- **Paper trading mode** for testing
- **Trailing stop** protection
- **Winter Protocol** bear market filter
- **AI validation** before entries

## 📅 Trading Schedule

Cycles run every 4 hours at: **1:00, 5:00, 9:00, 13:00, 17:00, 21:00 ET**

## 🚀 Deployment

Automated via GitHub Actions on push to `main`:
1. SSH to VPS
2. Git pull
3. Install dependencies
4. Restart systemd service

---

**v3.0.0** - Smart Trend Follower | Built with ❤️ for BTC swing trading
