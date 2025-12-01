"""
Trading mode configuration - DEPRECATED
Use Config.TRADING_MODE from app.config instead
"""
import os

# PAPER: Simulated trading with real market data
# REAL: Actual trades on Kraken Spot API
MODE = os.getenv('TRADING_MODE', 'PAPER').upper()
