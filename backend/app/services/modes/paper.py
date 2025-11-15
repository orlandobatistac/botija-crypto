"""
Paper trading mode - simulates trades with real market data
"""

import logging
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from .base import TradingEngine

logger = logging.getLogger(__name__)

# Path to paper wallet file
PAPER_WALLET_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'paper_wallet.json'
PAPER_TRADES_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'paper_trades.csv'

class PaperTradingEngine(TradingEngine):
    """Paper trading engine - simulates trades locally"""
    
    def __init__(self):
        """Initialize paper trading engine"""
        self.logger = logger
        self.wallet = self._load_wallet()
        self._ensure_trade_log_exists()
    
    def _load_wallet(self) -> Dict:
        """Load paper wallet from file"""
        try:
            PAPER_WALLET_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            if PAPER_WALLET_PATH.exists():
                with open(PAPER_WALLET_PATH, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading wallet: {e}")
        
        # Default wallet
        return {
            'usd_balance': 1000.0,
            'btc_balance': 0.0,
            'last_buy_price': None,
            'trailing_stop': None,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_wallet(self):
        """Save paper wallet to file"""
        try:
            PAPER_WALLET_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.wallet['last_updated'] = datetime.now().isoformat()
            
            with open(PAPER_WALLET_PATH, 'w') as f:
                json.dump(self.wallet, f, indent=2)
            
            self.logger.info("Paper wallet saved")
        except Exception as e:
            self.logger.error(f"Error saving wallet: {e}")
    
    def _ensure_trade_log_exists(self):
        """Create trade log file if it doesn't exist"""
        try:
            PAPER_TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            if not PAPER_TRADES_PATH.exists():
                with open(PAPER_TRADES_PATH, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'type', 'price', 'volume', 'balance_usd', 'balance_btc'])
        except Exception as e:
            self.logger.error(f"Error creating trade log: {e}")
    
    def _log_trade(self, trade_type: str, price: float, volume: float):
        """Log trade to CSV file"""
        try:
            with open(PAPER_TRADES_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    trade_type,
                    f'{price:.2f}',
                    f'{volume:.8f}',
                    f'{self.wallet["usd_balance"]:.2f}',
                    f'{self.wallet["btc_balance"]:.8f}'
                ])
            self.logger.info(f"Trade logged: {trade_type} {volume:.8f} BTC at ${price:.2f}")
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
    
    def load_balances(self) -> Dict[str, float]:
        """Load simulated balances"""
        return {
            'btc': self.wallet['btc_balance'],
            'usd': self.wallet['usd_balance']
        }
    
    def buy(self, price: float, usd_amount: float) -> Tuple[bool, str]:
        """Simulate a buy operation"""
        try:
            if self.wallet['usd_balance'] < usd_amount:
                msg = f"Insufficient USD balance: ${self.wallet['usd_balance']:.2f} < ${usd_amount:.2f}"
                self.logger.warning(msg)
                return False, msg
            
            # Calculate volume
            volume = usd_amount / price
            
            # Update balances
            self.wallet['usd_balance'] -= usd_amount
            self.wallet['btc_balance'] += volume
            self.wallet['last_buy_price'] = price
            
            # Initialize trailing stop at 99% of entry price
            self.wallet['trailing_stop'] = price * 0.99
            
            # Save and log
            self._save_wallet()
            self._log_trade('BUY', price, volume)
            
            msg = f"PAPER BUY: {volume:.8f} BTC at ${price:,.2f} | USD: ${self.wallet['usd_balance']:.2f} | BTC: {self.wallet['btc_balance']:.8f}"
            self.logger.info(msg)
            
            return True, msg
        
        except Exception as e:
            self.logger.error(f"Error in paper buy: {e}")
            return False, f"Paper buy error: {str(e)}"
    
    def sell(self, price: float, btc_amount: float) -> Tuple[bool, str]:
        """Simulate a sell operation"""
        try:
            if self.wallet['btc_balance'] < btc_amount:
                msg = f"Insufficient BTC balance: {self.wallet['btc_balance']:.8f} < {btc_amount:.8f}"
                self.logger.warning(msg)
                return False, msg
            
            # Calculate USD gained
            usd_gained = btc_amount * price
            
            # Calculate P/L
            if self.wallet['last_buy_price']:
                pnl = (price - self.wallet['last_buy_price']) * btc_amount
            else:
                pnl = 0.0
            
            # Update balances
            self.wallet['usd_balance'] += usd_gained
            self.wallet['btc_balance'] -= btc_amount
            self.wallet['last_buy_price'] = None
            self.wallet['trailing_stop'] = None
            
            # Save and log
            self._save_wallet()
            self._log_trade('SELL', price, btc_amount)
            
            msg = f"PAPER SELL: {btc_amount:.8f} BTC at ${price:,.2f} | P/L: ${pnl:+,.2f} | USD: ${self.wallet['usd_balance']:.2f} | BTC: {self.wallet['btc_balance']:.8f}"
            self.logger.info(msg)
            
            return True, msg
        
        except Exception as e:
            self.logger.error(f"Error in paper sell: {e}")
            return False, f"Paper sell error: {str(e)}"
    
    def update_trailing_stop(self, price: float) -> Dict:
        """Update trailing stop simulation"""
        try:
            if self.wallet['btc_balance'] > 0 and self.wallet['trailing_stop']:
                # Move stop up if price went higher
                new_stop = max(self.wallet['trailing_stop'], price * 0.99)
                
                if new_stop > self.wallet['trailing_stop']:
                    self.wallet['trailing_stop'] = new_stop
                    self._save_wallet()
                    self.logger.info(f"Trailing stop updated to ${new_stop:,.2f}")
                
                # Check if should sell
                should_sell = price <= self.wallet['trailing_stop']
                
                return {
                    'engine': 'paper',
                    'current_price': price,
                    'trailing_stop': self.wallet['trailing_stop'],
                    'btc_balance': self.wallet['btc_balance'],
                    'should_sell': should_sell,
                    'distance_to_stop': price - self.wallet['trailing_stop']
                }
            
            return {
                'engine': 'paper',
                'current_price': price,
                'trailing_stop': None,
                'btc_balance': self.wallet['btc_balance'],
                'should_sell': False
            }
        
        except Exception as e:
            self.logger.error(f"Error updating trailing stop: {e}")
            return {}
    
    def get_open_position(self) -> Dict:
        """Get simulated open position"""
        if self.wallet['btc_balance'] > 0:
            return {
                'btc_balance': self.wallet['btc_balance'],
                'entry_price': self.wallet['last_buy_price'],
                'trailing_stop': self.wallet['trailing_stop'],
                'mode': 'paper'
            }
        return {}
    
    def close_position(self) -> bool:
        """Close simulated position"""
        try:
            if self.wallet['btc_balance'] > 0:
                # Use last known price (would need to pass current price in real scenario)
                # For now, just clear the position
                self.wallet['btc_balance'] = 0.0
                self.wallet['last_buy_price'] = None
                self.wallet['trailing_stop'] = None
                self._save_wallet()
                return True
            return True
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
    
    def reset_wallet(self, initial_usd: float = 1000.0):
        """Reset wallet to initial state"""
        self.wallet = {
            'usd_balance': initial_usd,
            'btc_balance': 0.0,
            'last_buy_price': None,
            'trailing_stop': None,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        self._save_wallet()
        self.logger.info(f"Wallet reset with ${initial_usd:.2f} USD")
    
    def get_wallet_summary(self) -> Dict:
        """Get complete wallet summary"""
        return {
            'mode': 'paper',
            'usd_balance': self.wallet['usd_balance'],
            'btc_balance': self.wallet['btc_balance'],
            'last_buy_price': self.wallet['last_buy_price'],
            'trailing_stop': self.wallet['trailing_stop'],
            'created_at': self.wallet['created_at'],
            'last_updated': self.wallet['last_updated']
        }
