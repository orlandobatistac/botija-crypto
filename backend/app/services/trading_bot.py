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
from .ai_regime import AIRegimeService
from .smart_trend_follower import SmartTrendFollower

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

    def _get_risk_profile(self) -> Dict:
        """Get current risk profile from database, enhanced with AI regime"""
        try:
            from ..database import SessionLocal
            from ..models import RiskProfile

            db = SessionLocal()
            profile = db.query(RiskProfile).first()
            db.close()

            # Get AI regime for current week
            ai_regime = AIRegimeService.get_current_regime()

            if profile:
                # Merge profile with AI regime (AI regime takes priority for thresholds)
                return {
                    'profile': profile.profile,
                    'buy_score_threshold': ai_regime['buy_threshold'],  # AI regime
                    'sell_score_threshold': ai_regime['sell_threshold'],  # AI regime
                    'trade_amount_percent': ai_regime['capital_percent'],  # AI regime
                    'trailing_stop_percent': ai_regime['stop_loss_percent'],  # AI regime
                    'ai_regime': ai_regime['regime'],
                    'ai_confidence': ai_regime['confidence'],
                    'ai_reasoning': ai_regime['reasoning']
                }
        except Exception as e:
            self.logger.warning(f"Could not load risk profile: {e}")

        # Default moderate profile with AI regime fallback
        ai_regime = AIRegimeService.get_current_regime()
        return {
            'profile': 'ai_dynamic',
            'buy_score_threshold': ai_regime['buy_threshold'],
            'sell_score_threshold': ai_regime['sell_threshold'],
            'trade_amount_percent': ai_regime['capital_percent'],
            'trailing_stop_percent': ai_regime['stop_loss_percent'],
            'ai_regime': ai_regime['regime'],
            'ai_confidence': ai_regime['confidence'],
            'ai_reasoning': ai_regime['reasoning']
        }

    async def analyze_market(self) -> Dict:
        """Analyze current market conditions using Smart Trend Follower strategy"""
        try:
            # Get risk profile with AI regime
            risk_profile = self._get_risk_profile()
            ai_regime = risk_profile.get('ai_regime', 'LATERAL')

            # Use trading engine factory
            engine = get_trading_engine()

            # Get balances
            balance = engine.get_balance()
            btc_balance = balance.get('btc', 0.0)
            usd_balance = balance.get('usd', 0.0)
            has_position = btc_balance > 0.0001  # More than dust

            # Get current price
            current_price = engine.get_current_price()
            if not current_price:
                self.logger.warning("No price data available")
                return {}

            # Get OHLC data for indicators (need 200+ candles for EMA200)
            from ..config import Config
            if self.kraken:
                ohlc_data = self.kraken.get_ohlc(interval=Config.KRAKEN_OHLC_INTERVAL)
            else:
                public_client = KrakenClient(api_key="", api_secret="")
                ohlc_data = public_client.get_ohlc(interval=Config.KRAKEN_OHLC_INTERVAL)

            if not ohlc_data:
                self.logger.warning("No OHLC data available")
                return {}

            # Extract closing prices
            closes = [float(candle[4]) for candle in ohlc_data]

            # Get Smart Trend Follower signal (winning backtest strategy)
            stf_signal = SmartTrendFollower.get_trading_signal(
                prices=closes,
                regime=ai_regime,
                has_position=has_position,
                current_price=current_price
            )

            # Also get technical indicators for logging/display
            tech_signals = TechnicalIndicators.analyze_signals(closes)

            # Log the smart trend follower decision
            self.logger.info(
                f"🎯 Smart Trend Follower: {stf_signal['signal']} | "
                f"Regime: {ai_regime} | Leverage: x{stf_signal['leverage']} | "
                f"Winter: {'❄️' if stf_signal.get('is_winter_mode') else '☀️'}"
            )
            self.logger.info(f"   Reason: {stf_signal['reason']}")

            # Calculate position size with leverage
            leverage = stf_signal['leverage']
            capital_percent = risk_profile['trade_amount_percent']
            btc_qty, effective_exposure = SmartTrendFollower.calculate_position_size(
                usd_balance=usd_balance,
                capital_percent=capital_percent,
                leverage=leverage,
                price=current_price
            )

            # Build AI signal format for compatibility
            ai_signal = {
                'signal': stf_signal['signal'],
                'confidence': risk_profile.get('ai_confidence', 0.7),
                'reason': stf_signal['reason']
            }

            return {
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'btc_balance': btc_balance,
                'usd_balance': usd_balance,
                'tech_signals': tech_signals,
                'ai_signal': ai_signal,
                'stf_signal': stf_signal,  # Full Smart Trend Follower signal
                'trade_amount': effective_exposure / leverage,  # Base amount before leverage
                'effective_exposure': effective_exposure,
                'leverage': leverage,
                'min_balance_required': self._calculate_min_balance(usd_balance),
                'risk_profile': risk_profile,
                'should_buy': (
                    stf_signal['signal'] == 'BUY' and
                    usd_balance >= (self._calculate_min_balance(usd_balance) + effective_exposure / leverage)
                ),
                'should_sell': (
                    stf_signal['signal'] == 'SELL' and
                    has_position
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
            
            # Get AI regime for shadow margin tracking
            stf = analysis.get('stf_signal', {})
            ai_regime = stf.get('regime', 'LATERAL')

            self.logger.info(f"Executing BUY: {quantity:.8f} BTC at ${current_price:,.2f} | Regime: {ai_regime}")

            # Use trading engine factory
            engine = get_trading_engine(self.kraken)
            success, message = engine.buy(current_price, trade_amount, ai_regime=ai_regime)

            if success:
                self.active_trade = {
                    'entry_price': current_price,
                    'quantity': quantity,
                    'order_id': message,
                    'timestamp': datetime.now().isoformat(),
                    'trailing_stop': TrailingStop(current_price, self.trailing_stop_pct),
                    'ai_regime': ai_regime  # Store for sell
                }

                # Send alert
                if self.telegram:
                    self.telegram.send_buy_signal(
                        current_price,
                        quantity,
                        analysis['ai_signal']['confidence']
                    )

                return True
            else:
                self.logger.error(f"Buy order failed: {message}")
                if self.telegram:
                    self.telegram.send_error_alert(f"Buy order failed: {message}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing buy: {e}")
            if self.telegram:
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
            
            # Get AI regime from when we entered the trade
            ai_regime = self.active_trade.get('ai_regime', 'LATERAL')

            self.logger.info(f"Executing SELL: {quantity:.8f} BTC at ${exit_price:,.2f} | Regime: {ai_regime}")

            # Use trading engine factory
            engine = get_trading_engine(self.kraken)
            success, message = engine.sell(exit_price, quantity, ai_regime=ai_regime)

            if success:
                # Send alert
                if self.telegram:
                    self.telegram.send_sell_signal(
                        entry_price,
                        exit_price,
                        profit_loss,
                        'TRAILING_STOP' if analysis.get('analysis_type') == 'trailing' else 'AI_SIGNAL'
                    )

                self.active_trade = None
                return True
            else:
                self.logger.error(f"Sell order failed: {message}")
                if self.telegram:
                    self.telegram.send_error_alert(f"Sell order failed: {message}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing sell: {e}")
            if self.telegram:
                self.telegram.send_error_alert(str(e))
            return False

    async def run_cycle(self, trigger: str = "scheduled") -> Dict:
        """Execute one trading cycle"""
        import time
        from ..models import TradingCycle
        from ..database import SessionLocal

        start_time = time.time()
        cycle_data = {
            'btc_price': 0,
            'ema20': 0,
            'ema50': 0,
            'rsi14': 0,
            'btc_balance': 0,
            'usd_balance': 0,
            'ai_signal': 'HOLD',
            'ai_confidence': 0,
            'ai_reason': None,
            'action': 'ERROR',
            'trade_id': None,
            'trading_mode': 'PAPER' if not self.kraken else 'REAL',
            'error_message': None,
            # Shadow Margin tracking
            'ai_regime': None,
            'leverage_multiplier': 1.0,
            'is_winter_mode': False,
            'ema200': None
        }

        try:
            logger.info("📊 Analizando mercado...")
            analysis = await self.analyze_market()

            if not analysis:
                logger.warning("⚠️  Análisis falló - sin datos")
                cycle_data['error_message'] = 'Analysis failed - no data'
                cycle_data['action'] = 'ERROR'
                self._save_cycle(cycle_data, int((time.time() - start_time) * 1000), trigger)
                return {'success': False, 'reason': 'Analysis failed'}

            # Update cycle data from analysis
            cycle_data['btc_price'] = analysis.get('current_price', 0)
            cycle_data['btc_balance'] = analysis.get('btc_balance', 0)
            cycle_data['usd_balance'] = analysis.get('usd_balance', 0)

            tech = analysis.get('tech_signals', {})
            if tech:
                cycle_data['ema20'] = tech.get('ema20', 0)
                cycle_data['ema50'] = tech.get('ema50', 0)
                cycle_data['rsi14'] = tech.get('rsi14', 0)
                # New indicators
                cycle_data['macd'] = tech.get('macd')
                cycle_data['macd_signal'] = tech.get('macd_signal')
                cycle_data['macd_hist'] = tech.get('macd_hist')
                cycle_data['bb_upper'] = tech.get('bb_upper')
                cycle_data['bb_lower'] = tech.get('bb_lower')
                cycle_data['bb_position'] = tech.get('bb_position')
                cycle_data['tech_score'] = tech.get('score')

            ai_sig = analysis.get('ai_signal', {})
            if ai_sig:
                cycle_data['ai_signal'] = ai_sig.get('signal', 'HOLD')
                cycle_data['ai_confidence'] = ai_sig.get('confidence', 0)
                cycle_data['ai_reason'] = ai_sig.get('reason', None)

            # Smart Trend Follower data for Shadow Margin
            stf = analysis.get('stf_signal', {})
            if stf:
                cycle_data['ai_regime'] = stf.get('regime')
                cycle_data['leverage_multiplier'] = stf.get('leverage', 1.0)
                cycle_data['is_winter_mode'] = stf.get('is_winter_mode', False)
                cycle_data['ema200'] = stf.get('ema200')

            # Log market data
            logger.info(f"💰 Precio actual: ${analysis.get('current_price', 0):.2f}")
            logger.info(f"📈 BTC: {analysis.get('btc_balance', 0):.8f} | USD: ${analysis.get('usd_balance', 0):.2f}")

            if tech:
                score = tech.get('score', 'N/A')
                logger.info(f"📉 Indicadores - EMA20: {tech.get('ema20', 0):.2f} | EMA50: {tech.get('ema50', 0):.2f} | RSI: {tech.get('rsi14', 0):.2f} | Score: {score}")

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
                result = await self.execute_buy(analysis)
                cycle_data['action'] = 'BOUGHT' if result else 'BUY_FAILED'
                if result and self.active_trade:
                    cycle_data['trade_id'] = self.active_trade.get('trade_id')

            # Check for sell signal
            elif analysis['should_sell']:
                logger.info("✅ Señal de VENTA detectada")
                analysis['analysis_type'] = 'signal'
                result = await self.execute_sell(analysis)
                cycle_data['action'] = 'SOLD' if result else 'SELL_FAILED'
            else:
                logger.info("⏸️  Sin señales de trading - modo espera")
                cycle_data['action'] = 'HOLD'

            # Save cycle to database
            execution_time = int((time.time() - start_time) * 1000)
            self._save_cycle(cycle_data, execution_time, trigger)

            return {'success': True, 'analysis': analysis}

        except Exception as e:
            logger.error(f"❌ Error en ciclo de trading: {e}")
            cycle_data['error_message'] = str(e)
            cycle_data['action'] = 'ERROR'
            self._save_cycle(cycle_data, int((time.time() - start_time) * 1000), trigger)

            if self.telegram:
                self.telegram.send_error_alert(str(e), 'HIGH')
            return {'success': False, 'error': str(e)}

    def _save_cycle(self, cycle_data: Dict, execution_time_ms: int, trigger: str = "scheduled"):
        """Save trading cycle to database"""
        try:
            from ..models import TradingCycle
            from ..database import SessionLocal

            db = SessionLocal()
            cycle = TradingCycle(
                btc_price=cycle_data['btc_price'],
                ema20=cycle_data['ema20'],
                ema50=cycle_data['ema50'],
                rsi14=cycle_data['rsi14'],
                macd=cycle_data.get('macd'),
                macd_signal=cycle_data.get('macd_signal'),
                macd_hist=cycle_data.get('macd_hist'),
                bb_upper=cycle_data.get('bb_upper'),
                bb_lower=cycle_data.get('bb_lower'),
                bb_position=cycle_data.get('bb_position'),
                tech_score=cycle_data.get('tech_score'),
                btc_balance=cycle_data['btc_balance'],
                usd_balance=cycle_data['usd_balance'],
                ai_signal=cycle_data['ai_signal'],
                ai_confidence=cycle_data['ai_confidence'],
                ai_reason=cycle_data['ai_reason'],
                action=cycle_data['action'],
                trade_id=cycle_data['trade_id'],
                execution_time_ms=execution_time_ms,
                trading_mode=cycle_data['trading_mode'],
                trigger=trigger,
                error_message=cycle_data['error_message'],
                # Shadow Margin tracking
                ai_regime=cycle_data.get('ai_regime'),
                leverage_multiplier=cycle_data.get('leverage_multiplier'),
                is_winter_mode=cycle_data.get('is_winter_mode'),
                ema200=cycle_data.get('ema200')
            )
            db.add(cycle)
            db.commit()
            db.close()
            logger.info(f"💾 Ciclo guardado en DB ({execution_time_ms}ms, trigger={trigger}, regime={cycle_data.get('ai_regime')})")
        except Exception as e:
            logger.error(f"Error guardando ciclo en DB: {e}")

    async def start(self):
        """Start the trading bot"""
        self.is_running = True
        self.logger.info("Trading bot started")
        if self.telegram:
            self.telegram.send_message("🟢 <b>Trading Bot Started</b> 🟢")

    async def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        self.logger.info("Trading bot stopped")
        if self.telegram:
            self.telegram.send_message("🔴 <b>Trading Bot Stopped</b> 🔴")
