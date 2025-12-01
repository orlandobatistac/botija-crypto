# Botija Crypto v3.1 - Smart Trend Follower

## 📌 Overview

Automated **BTC swing trading bot** using **CCXT + Kraken Spot API** with the **Smart Trend Follower (STF)** strategy.

**Backtest Results (2018-2025):**
- **SPOT (x1.0):** +1652% return
- **Shadow Margin (x1.5 BULL):** +2054% return
- **vs Buy & Hold:** +601%

**Robustness Tests:** 3/4 passed (EMA50 exit logic is robust even with random regimes)

**Core Features:**
- **CCXT Library** for Kraken API (portable to other exchanges)
- **EMA-based entries/exits** (regime-specific thresholds)
- **AI Regime Detection** (BULL/BEAR/LATERAL/VOLATILE via OpenAI GPT-5.1)
- **Shadow Margin Tracking** (x1.5 audit in BULL, spot execution)
- **Winter Protocol** (protective filter when price < EMA200)
- **Paper Trading Mode** ($1000 USD simulated wallet)
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

### Entry Conditions (Regime-Specific)
| Regime | Entry Threshold | Notes |
|--------|-----------------|-------|
| BULL 🟢 | Price > EMA20 + 1.5% | Aggressive entry |
| VOLATILE 🟠 | Price > EMA20 + 1.5% | Same as BULL |
| LATERAL 🟡 | Price > EMA50 + 1.5% | Conservative entry |
| BEAR 🔴 | **BLOCKED** | No entries allowed |

### Exit Conditions
- Price < **EMA50 - 1.5%** (dynamic exit based on EMA50)

### Shadow Margin (Audit Only)
| AI Regime | Shadow Leverage | Execution |
|-----------|-----------------|-----------|
| BULL 🟢 | x1.5 (tracked) | Spot |
| Others | x1.0 | Spot |

*Real trading is ALWAYS spot. Shadow margin tracks hypothetical leveraged returns.*

### Winter Protocol ❄️
When `Price < EMA200`:
- **BEAR/LATERAL/VOLATILE:** Entries blocked
- **BULL only:** Allowed if RSI > 65

## 📊 Technical Indicators

| Indicator | Usage |
|-----------|-------|
| EMA20 | Entry trigger (BULL/VOLATILE) |
| EMA50 | Entry (LATERAL) + Exit trigger |
| EMA200 | Winter Protocol filter |
| RSI14 | Winter momentum confirmation |

## 🤖 AI Regime Detection

OpenAI GPT-5.1 analyzes real-time market data:
- **BULL**: Strong uptrend → Shadow leverage x1.5
- **BEAR**: Downtrend → No entries
- **LATERAL**: Sideways → Conservative EMA50 entry
- **VOLATILE**: High volatility → EMA20 entry, spot only

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
│   │       ├── trading_bot.py   # Core bot (CCXT + Strategy)
│   │       ├── ai_regime.py     # OpenAI regime detection
│   │       └── telegram_alerts.py
│   ├── tests/
│   └── data/                    # SQLite database
├── frontend/
│   └── index.html               # Alpine.js dashboard
├── scripts/
│   ├── run_ai_backtest.py       # Backtest validation
│   └── test_overfitting.py      # Robustness tests
└── docs/
    └── STRATEGY.md              # Strategy documentation
```

## ⚙️ Configuration

### Environment Variables
```env
# Kraken API (leave empty for PAPER mode)
KRAKEN_API_KEY=
KRAKEN_SECRET_KEY=

# OpenAI
OPENAI_API_KEY=

# Telegram Alerts
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

# Trading
TRADING_INTERVAL_HOURS=4     # Cycle frequency
TRADE_AMOUNT_PERCENT=75      # % of balance per trade
```

## 📈 Dashboard Features

- **Bot Status**: Active/Inactive, PAPER/REAL mode
- **Paper Wallet**: $1000 USD starting balance
- **Balances**: BTC and USD (real or paper)
- **Next Cycle Countdown**: Real-time from scheduler
- **Trading Cycles History**: With STF strategy data
  - AI Regime (BULL/BEAR/LATERAL/VOLATILE)
  - Shadow Leverage (x1.5/x1.0)
  - Winter Mode status
  - EMAs and RSI values

## 🔧 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, APScheduler, CCXT
- **Frontend**: Alpine.js, TailwindCSS
- **Trading**: CCXT (Kraken), pandas, numpy
- **AI**: OpenAI GPT-5.1
- **Alerts**: python-telegram-bot
- **Database**: SQLite
- **Deploy**: VPS + Nginx + systemd + GitHub Actions

## 🛡️ Safety Features

- **No real leverage** (shadow tracking only)
- **Spot trading only** on Kraken
- **Paper trading mode** with $1000 simulated wallet
- **Winter Protocol** bear market filter
- **BEAR regime blocks** all entries
- **EMA50 dynamic exit** proven robust in Monte Carlo tests

## 📅 Trading Schedule

Cycles run every 4 hours at: **0:00, 4:00, 8:00, 12:00, 16:00, 20:00 ET**

## 🧪 Validation Tests

```bash
# Run strategy tests
cd backend && python -m pytest tests/test_strategy_logic.py -v

# Run backtest
python scripts/run_ai_backtest.py

# Run overfitting tests
python scripts/test_overfitting.py
```

## 🚀 Deployment

Automated via GitHub Actions on push to `main`:
1. SSH to VPS
2. Git pull
3. Install dependencies
4. Restart systemd service

## 💰 Capital Guide

Suggested starting capital for operating the bot:

| Level | Amount | Description |
|-------|--------|-------------|
| **Minimum** | $100-200 USD | Test bot in production, 1-2 small trades |
| **Recommended** | $500-1000 USD | Better trade sizing, lower fee impact |
| **Ideal** | $2000+ USD | Optimal for STF strategy swing trading |

**Tips:**
- Start small ($200-500) to validate everything works
- Scale up after 1-2 weeks of successful operation
- Kraken fees are ~0.26% per trade

## ⚠️ Disclaimer

**This bot is experimental software for educational purposes.**

- This is NOT financial advice
- Only invest what you can afford to lose
- Past backtest performance does not guarantee future results
- Cryptocurrency trading involves significant risk
- The authors are not responsible for any financial losses

---

**v3.1.0** - Smart Trend Follower + CCXT + GPT-5.1 | Built with ❤️ for BTC swing trading
