"""
Main trading bot orchestration
"""

import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime

from .kraken_client import KrakenClient
from .technical_indicators import TechnicalIndicators
from .ai_validator import AISignalValidator
from .telegram_alerts import TelegramAlerts
from .trailing_stop import TrailingStop
from .modes.factory import get_trading_engine

logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(
        self,
        kraken_api_key: str,
        kraken_secret: str,
        openai_api_key: str,
        telegram_token: str,
        telegram_chat_id: str,
        trade_amount: float = 0,  # 0 = use percentage
        trade_amount_percent: float = 10,  # 10% default
        min_balance: float = 0,  # 0 = use percentage
        min_balance_percent: float = 20,  # 20% default
        trailing_stop_pct: float = 0.99
    ):
        """Initialize trading bot"""
        # Only initialize KrakenClient if credentials are provided
        self.kraken = KrakenClient(kraken_api_key, kraken_secret) if kraken_api_key else None
        self.ai = AISignalValidator(openai_api_key) if openai_api_key else None
        self.telegram = TelegramAlerts(telegram_token, telegram_chat_id) if telegram_token else None
        
        self.trade_amount = trade_amount
        self.trade_amount_percent = trade_amount_percent
        self.min_balance = min_balance
        self.min_balance_percent = min_balance_percent
        self.trailing_stop_pct = trailing_stop_pct
        
        self.is_running = False
        self.active_trade: Optional[Dict] = None
        self.logger = logger
    
    def _calculate_trade_amount(self, usd_balance: float) -> float:
        """Calculate trade amount based on config (fixed or percentage)"""
        if self.trade_amount > 0:
            return self.trade_amount  # Use fixed amount
        return usd_balance * (self.trade_amount_percent / 100)  # Use percentage
    
    def _calculate_min_balance(self, usd_balance: float) -> float:
        """Calculate minimum balance based on config (fixed or percentage)"""
        if self.min_balance > 0:
            return self.min_balance  # Use fixed amount
        return usd_balance * (self.min_balance_percent / 100)  # Use percentage
    
    async def analyze_market(self) -> Dict:
        """Analyze current market conditions"""
        try:
            # Use trading engine factory
            engine = get_trading_engine()
            
            # Get price data
            balance = engine.get_balance()
            btc_balance = balance.get('btc', 0.0)
            usd_balance = balance.get('usd', 0.0)
            
            # Get current price
            current_price = engine.get_current_price()
            if not current_price:
                self.logger.warning("No price data available")
                return {}
            
            # Get OHLC data for indicators (use kraken or mock data)
            if self.kraken:
                ohlc_data = self.kraken.get_ohlc()
            else:
                # Mock OHLC for paper trading
                ohlc_data = [[0, 0, 0, 0, current_price] for _ in range(50)]
            
            if not ohlc_data:
                self.logger.warning("No OHLC data available")
                return {}
            
            # Extract closing prices
            closes = [float(candle[4]) for candle in ohlc_data]
            
            # Calculate technical indicators
            tech_signals = TechnicalIndicators.analyze_signals(closes)
            
            # Get AI signal (only if AI is available)
            if self.ai:
                ai_signal = self.ai.get_signal(
                    price=current_price,
                    ema20=tech_signals.get('ema20', 0),
                    ema50=tech_signals.get('ema50', 0),
                    rsi=tech_signals.get('rsi14', 0),
                    btc_balance=btc_balance,
                    usd_balance=usd_balance
                )
            else:
                # Mock AI signal for paper trading
                ai_signal = {'signal': 'HOLD', 'confidence': 0.5}
            
            # Calculate dynamic amounts
            trade_amount = self._calculate_trade_amount(usd_balance)
            min_balance_required = self._calculate_min_balance(usd_balance)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'btc_balance': btc_balance,
                'usd_balance': usd_balance,
                'tech_signals': tech_signals,
                'ai_signal': ai_signal,
                'trade_amount': trade_amount,
                'min_balance_required': min_balance_required,
                'should_buy': (
                    ai_signal['signal'] == 'BUY' and
                    usd_balance >= (min_balance_required + trade_amount) and
                    btc_balance == 0
                ),
                'should_sell': (
                    ai_signal['signal'] == 'SELL' and
                    btc_balance > 0
                )
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing market: {e}")
            if self.telegram:
                self.telegram.send_error_alert(str(e), 'HIGH')
            return {}
    
    async def execute_buy(self, analysis: Dict) -> bool:
        """Execute a buy order"""
        try:
            current_price = analysis['current_price']
            trade_amount = analysis.get('trade_amount', self.trade_amount)
            quantity = trade_amount / current_price
            
            self.logger.info(f"Executing BUY: {quantity:.8f} BTC at ${current_price:,.2f}")
            
            # Place limit order
            result = self.kraken.place_limit_order(
                pair='XBTUSDT',
                side='buy',
                price=current_price,
                volume=quantity
            )
            
            if result['success']:
                self.active_trade = {
                    'entry_price': current_price,
                    'quantity': quantity,
                    'order_id': result['order_id'],
                    'timestamp': datetime.now().isoformat(),
                    'trailing_stop': TrailingStop(current_price, self.trailing_stop_pct)
                }
                
                # Send alert
                self.telegram.send_buy_signal(
                    current_price,
                    quantity,
                    analysis['ai_signal']['confidence']
                )
                
                return True
            else:
                self.logger.error(f"Buy order failed: {result['error']}")
                self.telegram.send_error_alert(f"Buy order failed: {result['error']}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error executing buy: {e}")
            self.telegram.send_error_alert(str(e))
            return False
    
    async def execute_sell(self, analysis: Dict) -> bool:
        """Execute a sell order"""
        try:
            if not self.active_trade:
                self.logger.warning("No active trade to sell")
                return False
            
            quantity = self.active_trade['quantity']
            exit_price = analysis['current_price']
            entry_price = self.active_trade['entry_price']
            profit_loss = (exit_price - entry_price) * quantity
            
            self.logger.info(f"Executing SELL: {quantity:.8f} BTC at ${exit_price:,.2f}")
            
            # Place market sell order
            result = self.kraken.place_market_order(
                pair='XBTUSDT',
                side='sell',
                volume=quantity
            )
            
            if result['success']:
                # Send alert
                self.telegram.send_sell_signal(
                    entry_price,
                    exit_price,
                    profit_loss,
                    'TRAILING_STOP' if analysis['analysis_type'] == 'trailing' else 'AI_SIGNAL'
                )
                
                self.active_trade = None
                return True
            else:
                self.logger.error(f"Sell order failed: {result['error']}")
                self.telegram.send_error_alert(f"Sell order failed: {result['error']}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error executing sell: {e}")
            self.telegram.send_error_alert(str(e))
            return False
    
    async def run_cycle(self) -> Dict:
        """Execute one trading cycle"""
        try:
            logger.info("📊 Analizando mercado...")
            analysis = await self.analyze_market()
            
            if not analysis:
                logger.warning("⚠️  Análisis falló - sin datos")
                return {'success': False, 'reason': 'Analysis failed'}
            
            # Log market data
            logger.info(f"💰 Precio actual: ${analysis.get('current_price', 0):.2f}")
            logger.info(f"📈 BTC: {analysis.get('btc_balance', 0):.8f} | USD: ${analysis.get('usd_balance', 0):.2f}")
            
            tech = analysis.get('tech_signals', {})
            if tech:
                logger.info(f"📉 Indicadores - EMA20: {tech.get('ema20', 0):.2f} | EMA50: {tech.get('ema50', 0):.2f} | RSI: {tech.get('rsi14', 0):.2f}")
            
            ai_sig = analysis.get('ai_signal', {})
            if ai_sig:
                logger.info(f"🤖 Señal AI: {ai_sig.get('signal', 'N/A')} (confianza: {ai_sig.get('confidence', 0):.2f}%)")
            
            # Check trailing stop if position open
            if self.active_trade:
                ts = self.active_trade['trailing_stop']
                stop_info = ts.update(analysis['current_price'])
                
                logger.info(f"🎯 Trailing stop: ${stop_info['trailing_stop']:.2f} (distancia: {stop_info['distance_to_stop']:.2%})")
                
                if stop_info['should_sell']:
                    logger.info("🛑 Trailing stop triggered - ejecutando venta")
                    analysis['analysis_type'] = 'trailing'
                    await self.execute_sell(analysis)
                elif stop_info['distance_to_stop'] < stop_info['stop_percentage'] * 0.1:
                    # Update Telegram when getting close to stop
                    if self.telegram:
                        self.telegram.send_trailing_stop_update(
                            analysis['current_price'],
                            stop_info['trailing_stop']
                        )
            
            # Check for buy signal
            if analysis['should_buy']:
                logger.info("✅ Señal de COMPRA detectada")
                await self.execute_buy(analysis)
            
            # Check for sell signal
            elif analysis['should_sell']:
                logger.info("✅ Señal de VENTA detectada")
                analysis['analysis_type'] = 'signal'
                await self.execute_sell(analysis)
            else:
                logger.info("⏸️  Sin señales de trading - modo espera")
            
            return {'success': True, 'analysis': analysis}
        
        except Exception as e:
            logger.error(f"❌ Error en ciclo de trading: {e}")
            if self.telegram:
                self.telegram.send_error_alert(str(e), 'HIGH')
            return {'success': False, 'error': str(e)}
    
    async def start(self):
        """Start the trading bot"""
        self.is_running = True
        self.logger.info("Trading bot started")
        self.telegram.send_message("🟢 <b>Trading Bot Started</b> 🟢")
    
    async def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        self.logger.info("Trading bot stopped")
        self.telegram.send_message("🔴 <b>Trading Bot Stopped</b> 🔴")
