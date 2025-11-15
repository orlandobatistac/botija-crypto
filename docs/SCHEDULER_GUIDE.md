# Scheduler Activation Guide - Botija Trading Bot

## Current Status

✅ **Scheduler Logic**: Enhanced to support both paper trading and real trading modes
✅ **Paper Trading**: Active by default (no Kraken credentials required)
⏳ **Real Trading**: Ready to activate (requires Kraken API credentials)

---

## How the Scheduler Works

### Architecture

```
FastAPI App Startup
    ↓
init_scheduler() called
    ↓
Check Kraken credentials
    ├─ If present: Initialize TradingBot with KrakenClient
    │             → Real trading enabled
    └─ If absent: Initialize TradingBot without KrakenClient
                  → Paper trading enabled
    ↓
APScheduler starts background job
    ↓
Every TRADING_INTERVAL seconds (default 3600s / 1 hour)
    ↓
run_trading_cycle() executes
    ├─ Fetch BTC price
    ├─ Calculate indicators (EMA20, EMA50, RSI14)
    ├─ Get AI validation signal
    ├─ Execute buy/sell orders
    └─ Update wallet balance
```

### Current Configuration (from `.env`)

```env
TRADING_MODE=PAPER           # Operating mode
TRADING_INTERVAL=3600        # 1 hour between cycles
TRADE_AMOUNT_USD=100         # Amount per trade
MIN_BALANCE_USD=65           # Minimum required balance
TRAILING_STOP_PERCENTAGE=0.99
```

---

## Paper Trading Mode (Currently Active)

### How It Works

1. **Simulated Execution**: All trades happen in memory/database
2. **Fake Wallet**: Starts with $1,004 USD (from `backend/data/paper_wallet.json`)
3. **Real Data**: Uses actual Kraken price feeds
4. **No Real Money**: Zero financial risk

### Current Paper Trading Status

```
Wallet: $1,004.00 USD
BTC Holdings: 0.0 BTC
Last Trade: Nov 15, 2025
Win Rate: ~50% (testing purposes)
```

### Active Paper Trading Endpoints

```bash
# Check wallet
curl http://74.208.146.203/api/v1/paper/wallet

# Get trade history
curl http://74.208.146.203/api/v1/paper/trades

# Full dashboard
curl http://74.208.146.203/api/v1/bot/dashboard
```

---

## Activating Real Trading (When Ready)

### Prerequisites

1. **Kraken Account**: Created and verified
2. **API Keys**: Generated in Kraken account settings
3. **Fund Account**: Deposit real BTC to Kraken spot wallet
4. **VPS Access**: SSH credentials to `root@74.208.146.203`

### Step 1: Get Kraken API Keys

1. Log in to Kraken (https://www.kraken.com/)
2. Go to Settings → API
3. Create new API key with permissions:
   - Query Funds
   - Query Orders
   - Create Orders
   - Cancel Orders
4. Save the API Key and Secret Key

### Step 2: Add Credentials to VPS

```bash
# SSH to VPS
ssh root@74.208.146.203

# Edit environment variables
nano /root/botija/.env

# Find or add these lines:
KRAKEN_API_KEY=your_api_key_here
KRAKEN_SECRET_KEY=your_secret_key_here

# Save (Ctrl+O, Enter, Ctrl+X)
```

**Example:**
```env
KRAKEN_API_KEY=abc123def456ghi789jkl012mno345pqr
KRAKEN_SECRET_KEY=xyz789abc456def123ghi012jkl345mno
```

### Step 3: Restart the Bot

```bash
# Restart the service
systemctl restart botija

# View startup logs
journalctl -u botija -f

# You should see:
# ✅ Bot inicializado con credenciales Kraken (REAL TRADING)
# ✅ Scheduler iniciado - Ciclo de trading cada 3600s
```

### Step 4: Verify Real Trading is Active

```bash
# Check scheduler status
curl http://74.208.146.203/api/v1/bot/status

# Monitor live trading logs
journalctl -u botija -f

# Watch for:
# - "Ciclo de trading completado"
# - Trade signals and executions
# - Error messages (if any)
```

---

## Trading Bot Behavior

### Buy Signal Logic

The bot buys BTC when:
- ✅ EMA20 > EMA50 (uptrend)
- ✅ RSI14 between 45-60 (momentum)
- ✅ AI validator confirms signal (OpenAI API)
- ✅ Wallet balance > MIN_BALANCE_USD ($65)

### Sell Signal Logic

The bot sells BTC when:
- ✅ Price drops below trailing stop (99% of entry price)
- ✅ OR EMA20 < EMA50 (downtrend reversal)
- ✅ AI validator confirms sell signal

### Risk Management

- **Trade Amount**: Fixed $100 USD per buy order
- **Minimum Balance**: Must have $65 USD before buying
- **Trailing Stop**: Sells automatically if price drops 1% from entry
- **Max Leverage**: None (spot trading only)

---

## Monitoring the Scheduler

### Check if Scheduler is Running

```bash
# SSH to VPS
ssh root@74.208.146.203

# View real-time logs
journalctl -u botija -f

# Look for these lines:
# ✅ Scheduler iniciado
# ✅ Ciclo de trading completado
# ❌ Any error messages
```

### Retrieve Trading History

```bash
# Paper trading trades
curl http://74.208.146.203/api/v1/paper/trades | jq

# All trades (with timestamps)
curl http://74.208.146.203/api/v1/trades | jq

# Recent 10 trades
curl "http://74.208.146.203/api/v1/trades?limit=10" | jq
```

### Dashboard Statistics

```bash
curl http://74.208.146.203/api/v1/bot/dashboard | jq
```

Response includes:
- Current BTC position
- Wallet balance
- Last trade details
- Trading mode (PAPER or REAL)
- Scheduler status

---

## Pausing/Resuming the Scheduler

### Pause Trading (Emergency)

```bash
ssh root@74.208.146.203

# Edit config
nano /root/botija/.env

# Change this:
TRADING_ENABLED=false

# Save and restart
systemctl restart botija
```

### Resume Trading

```bash
# Set back to true
TRADING_ENABLED=true

# Restart
systemctl restart botija
```

---

## Troubleshooting

### Issue: Scheduler Not Starting

```bash
journalctl -u botija -n 50
# Look for error messages
```

Common causes:
- Missing requirements: `pip install apscheduler`
- Invalid .env syntax
- Permission issues on `/root/botija`

**Fix:**
```bash
cd /root/botija
source venv_botija/bin/activate
pip install -r backend/requirements.txt
systemctl restart botija
```

### Issue: Trades Not Executing

```bash
# Check if bot has balance
curl http://74.208.146.203/api/v1/paper/wallet

# Check for signals (live logs)
journalctl -u botija -f
```

Common causes:
- Balance below MIN_BALANCE_USD ($65)
- No buy signals from AI validator
- Kraken API error (if real trading)

### Issue: High Error Rate

```bash
# Restart fresh
systemctl restart botija
systemctl status botija

# Clear any stuck jobs
systemctl stop botija
sleep 5
systemctl start botija
```

---

## Key Configuration Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRADING_ENABLED` | `true` | Enable/disable trading |
| `TRADING_MODE` | `PAPER` | PAPER or REAL mode |
| `TRADING_INTERVAL` | `3600` | Seconds between cycles (1 hour) |
| `TRADE_AMOUNT_USD` | `100` | USD per buy order |
| `MIN_BALANCE_USD` | `65` | Minimum balance required |
| `TRAILING_STOP_PERCENTAGE` | `0.99` | Sell if price < entry * 0.99 |

---

## Next Steps

1. **Monitor Paper Trading**: Watch logs for 1-2 days
   ```bash
   journalctl -u botija -f --grep="Ciclo de trading"
   ```

2. **Review Trade History**: Check performance metrics
   ```bash
   curl http://74.208.146.203/api/v1/paper/trades
   ```

3. **When Ready for Real Trading**:
   - Get Kraken API keys
   - Add to `.env` on VPS
   - Start with small balance (~$500)
   - Monitor closely for first week

4. **Optional Enhancements**:
   - Setup Telegram alerts
   - Configure email notifications
   - Add Discord webhooks
   - Monitor with Prometheus

---

## Support Commands

```bash
# Full scheduler status
systemctl status botija

# Live logs (last 100 lines)
journalctl -u botija -n 100

# Restart bot
systemctl restart botija

# Stop bot
systemctl stop botija

# Start bot
systemctl start botija

# Check Python version
python3 --version

# Check required packages
pip list | grep apscheduler

# Test API connectivity
curl http://74.208.146.203/health
```

---

**Last Updated**: November 15, 2025
**Scheduler Status**: ✅ Active in Paper Trading Mode
**Next Activation**: Add Kraken API keys to `/root/botija/.env`
