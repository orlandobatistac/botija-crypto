"""
AI Regime Service - Gets market regime parameters from OpenAI in real-time
Uses real market data injection (same as backtest) for honest analysis
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache for current regime (refreshes weekly)
_regime_cache: Dict = {}
_cache_expiry: Optional[datetime] = None


class AIRegimeService:
    """Service to get AI-generated market regime parameters in real-time"""

    # Default parameters when API fails
    DEFAULT_PARAMS = {
        'regime': 'LATERAL',
        'buy_threshold': 50,
        'sell_threshold': 35,
        'capital_percent': 75,
        'atr_multiplier': 1.5,
        'stop_loss_percent': 2.0,
        'confidence': 0.5,
        'reasoning': 'Default parameters - API unavailable',
        'source': 'default'
    }

    # Prompt with real data injection (same as backtest)
    PROMPT_TEMPLATE = """You are an AGGRESSIVE BTC swing trader analyzing this week.
Date: {current_date}

=== REAL MARKET DATA (no simulation) ===
Current Price: ${price:,.0f}
7-day Change: {change_7d:+.1f}%
30-day Change: {change_30d:+.1f}%
RSI (14): {rsi:.1f}
EMA20 vs EMA50: {ema_signal}
Weekly Volatility: {volatility:.1f}%
Volume vs 20-week avg: {volume_ratio:.1f}x
Price vs 52-week High: {vs_52w_high:.1f}%
Price vs 52-week Low: {vs_52w_low:+.1f}%

=== REGIME GUIDELINES ===
BULL (strong uptrend): buy_threshold 40-50, capital 80-95%
  - RSI < 70, price above EMAs, positive momentum
BEAR (strong downtrend): buy_threshold 60-70, capital 30-50%
  - RSI > 30 (oversold = opportunity), price below EMAs
LATERAL (consolidation): buy_threshold 50-55, capital 50-70%
  - RSI 40-60, price between EMAs, low volatility
VOLATILE (high uncertainty): buy_threshold 55-65, capital 40-60%
  - Wide price swings, news-driven, elevated volatility

=== IMPORTANT ===
- Be AGGRESSIVE in clear trends (BULL/BEAR)
- Only use VOLATILE when volatility is extreme (>5% weekly)
- LATERAL is for genuine consolidation, not uncertainty
- Lower buy_threshold = more trades = better for swing trading

Respond ONLY with this JSON format:
{{
  "regime": "BULL|BEAR|LATERAL|VOLATILE",
  "buy_threshold": 45,
  "sell_threshold": 35,
  "capital_percent": 85,
  "atr_multiplier": 1.5,
  "stop_loss_percent": 2.5,
  "confidence": 0.8,
  "reasoning": "Brief explanation (max 80 chars)"
}}
"""

    @classmethod
    def _fetch_market_data(cls) -> Optional[Dict]:
        """Fetch real market data from Kraken for AI analysis"""
        try:
            from .kraken_client import KrakenClient
            import pandas as pd
            
            # Use public API (no auth needed)
            client = KrakenClient(api_key="", api_secret="")
            
            # Get OHLC data (daily candles, 720 = 720 days)
            ohlc = client.get_ohlc(interval=1440)  # Daily candles
            if not ohlc or len(ohlc) < 50:
                logger.warning("Insufficient OHLC data for regime analysis")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlc, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Current price
            price = df['close'].iloc[-1]
            
            # Price changes
            if len(df) >= 7:
                price_7d = df['close'].iloc[-7]
                change_7d = ((price - price_7d) / price_7d) * 100
            else:
                change_7d = 0
                
            if len(df) >= 30:
                price_30d = df['close'].iloc[-30]
                change_30d = ((price - price_30d) / price_30d) * 100
            else:
                change_30d = 0
            
            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            
            # Calculate EMAs
            ema20 = df['close'].ewm(span=20).mean().iloc[-1]
            ema50 = df['close'].ewm(span=50).mean().iloc[-1]
            ema_signal = "BULLISH" if ema20 > ema50 else "BEARISH"
            
            # Volatility (7-day)
            returns = df['close'].pct_change()
            volatility = returns.tail(7).std() * 100
            
            # Volume ratio
            vol_ma20 = df['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = df['volume'].iloc[-1] / vol_ma20 if vol_ma20 > 0 else 1.0
            
            # 52-week high/low
            high_52w = df['close'].tail(252).max() if len(df) >= 252 else df['close'].max()
            low_52w = df['close'].tail(252).min() if len(df) >= 252 else df['close'].min()
            vs_52w_high = ((price - high_52w) / high_52w) * 100
            vs_52w_low = ((price - low_52w) / low_52w) * 100
            
            return {
                'price': price,
                'change_7d': change_7d,
                'change_30d': change_30d,
                'rsi': current_rsi,
                'ema_signal': ema_signal,
                'volatility': volatility if not pd.isna(volatility) else 2.0,
                'volume_ratio': volume_ratio if not pd.isna(volume_ratio) else 1.0,
                'vs_52w_high': vs_52w_high,
                'vs_52w_low': vs_52w_low
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None

    @classmethod
    def _call_openai(cls) -> Optional[Dict]:
        """Call OpenAI API with real market data for regime analysis"""
        try:
            from openai import OpenAI

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, using defaults")
                return None

            # Fetch real market data
            market_data = cls._fetch_market_data()
            if not market_data:
                logger.warning("Could not fetch market data, using fallback")
                return None

            client = OpenAI(api_key=api_key)

            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = cls.PROMPT_TEMPLATE.format(
                current_date=current_date,
                **market_data
            )

            logger.info(f"Calling OpenAI for regime analysis (BTC=${market_data['price']:,.0f}, RSI={market_data['rsi']:.0f})")

            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            logger.info(f"OpenAI regime: {data.get('regime')} - {data.get('reasoning', '')[:50]}")

            return data

        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return None

    @classmethod
    def _get_recent_regimes(cls, n_weeks: int = 4) -> list:
        """Get the last N weeks of regimes from DB for momentum calculation"""
        try:
            from ..database import SessionLocal
            from ..models import AIMarketRegime

            db = SessionLocal()

            regimes = db.query(AIMarketRegime).order_by(
                AIMarketRegime.week_start.desc()
            ).limit(n_weeks).all()

            db.close()

            return [r.regime for r in regimes]
        except Exception as e:
            logger.error(f"Error getting recent regimes: {e}")
            return []

    @classmethod
    def _apply_momentum_multiplier(cls, regime_data: Dict) -> Dict:
        """
        Apply momentum multiplier for prolonged BULL/BEAR markets.
        If 3+ consecutive weeks of same regime, adjust thresholds.
        """
        recent_regimes = cls._get_recent_regimes(4)
        current_regime = regime_data.get('regime', 'LATERAL')

        if len(recent_regimes) < 3:
            return regime_data

        # Count consecutive same-regime weeks
        streak = 0
        for r in recent_regimes:
            if r == current_regime:
                streak += 1
            else:
                break

        # Apply momentum adjustment if 3+ weeks streak
        if streak >= 3:
            if current_regime == 'BULL':
                # More aggressive in prolonged bull: lower buy threshold, higher capital
                original_buy = regime_data.get('buy_threshold', 50)
                original_capital = regime_data.get('capital_percent', 75)

                regime_data['buy_threshold'] = max(40, original_buy - 10)
                regime_data['capital_percent'] = min(95, original_capital + 10)
                regime_data['momentum_applied'] = True
                regime_data['momentum_streak'] = streak

                logger.info(f"Momentum multiplier applied: {streak} weeks BULL streak. "
                           f"Buy threshold: {original_buy} -> {regime_data['buy_threshold']}, "
                           f"Capital: {original_capital}% -> {regime_data['capital_percent']}%")

            elif current_regime == 'BEAR':
                # More defensive in prolonged bear: higher buy threshold, lower capital
                original_buy = regime_data.get('buy_threshold', 50)
                original_capital = regime_data.get('capital_percent', 75)

                regime_data['buy_threshold'] = min(70, original_buy + 10)
                regime_data['capital_percent'] = max(30, original_capital - 15)
                regime_data['momentum_applied'] = True
                regime_data['momentum_streak'] = streak

                logger.info(f"Momentum multiplier applied: {streak} weeks BEAR streak. "
                           f"Buy threshold: {original_buy} -> {regime_data['buy_threshold']}, "
                           f"Capital: {original_capital}% -> {regime_data['capital_percent']}%")

        return regime_data

    @classmethod
    def get_current_regime(cls) -> Dict:
        """
        Get AI regime parameters for the current cycle.
        Calls OpenAI API every cycle (every 4 hours) for real-time market analysis.
        Applies momentum multiplier for prolonged trends.
        """
        # No cache - call OpenAI every cycle for real-time analysis
        regime_data = cls._call_openai()

        if regime_data:
            result = {
                'regime': regime_data.get('regime', 'LATERAL'),
                'buy_threshold': regime_data.get('buy_threshold', 50),
                'sell_threshold': regime_data.get('sell_threshold', 35),
                'capital_percent': regime_data.get('capital_percent', 75),
                'atr_multiplier': regime_data.get('atr_multiplier', 1.5),
                'stop_loss_percent': regime_data.get('stop_loss_percent', 2.0),
                'confidence': regime_data.get('confidence', 0.7),
                'reasoning': regime_data.get('reasoning', ''),
                'source': 'openai',
                'analyzed_at': datetime.now().isoformat()
            }

            # Apply momentum multiplier for prolonged trends
            result = cls._apply_momentum_multiplier(result)

            # Save to DB for history
            cls._save_to_db(result)

            logger.info(f"AI Regime: {result['regime']} (real-time analysis)")
            return result

        # Try to get from DB as fallback
        db_regime = cls._get_from_db()
        if db_regime:
            logger.info(f"Using DB cached regime: {db_regime['regime']}")
            return db_regime

        logger.warning("No AI regime available, using defaults")
        return cls.DEFAULT_PARAMS

    @classmethod
    def _save_to_db(cls, regime_data: Dict) -> None:
        """Save regime to database for history"""
        try:
            from ..database import SessionLocal
            from ..models import AIMarketRegime

            db = SessionLocal()

            # Calculate week start (Monday)
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            # Check if already exists for this week
            existing = db.query(AIMarketRegime).filter(
                AIMarketRegime.week_start == week_start
            ).first()

            if existing:
                # Update existing
                existing.regime = regime_data['regime']
                existing.buy_threshold = regime_data['buy_threshold']
                existing.sell_threshold = regime_data['sell_threshold']
                existing.capital_percent = regime_data['capital_percent']
                existing.atr_multiplier = regime_data['atr_multiplier']
                existing.stop_loss_percent = regime_data['stop_loss_percent']
                existing.confidence = regime_data['confidence']
                existing.reasoning = regime_data['reasoning']
            else:
                # Create new
                new_regime = AIMarketRegime(
                    week_start=week_start,
                    week_end=week_start + timedelta(days=6),
                    regime=regime_data['regime'],
                    buy_threshold=regime_data['buy_threshold'],
                    sell_threshold=regime_data['sell_threshold'],
                    capital_percent=regime_data['capital_percent'],
                    atr_multiplier=regime_data['atr_multiplier'],
                    stop_loss_percent=regime_data['stop_loss_percent'],
                    confidence=regime_data['confidence'],
                    reasoning=regime_data['reasoning']
                )
                db.add(new_regime)

            db.commit()
            db.close()
            logger.debug("Regime saved to DB")

        except Exception as e:
            logger.error(f"Error saving regime to DB: {e}")

    @classmethod
    def _get_from_db(cls) -> Optional[Dict]:
        """Get most recent regime from database as fallback"""
        try:
            from ..database import SessionLocal
            from ..models import AIMarketRegime

            db = SessionLocal()

            regime = db.query(AIMarketRegime).order_by(
                AIMarketRegime.week_start.desc()
            ).first()

            db.close()

            if regime:
                return {
                    'regime': regime.regime,
                    'buy_threshold': regime.buy_threshold,
                    'sell_threshold': regime.sell_threshold,
                    'capital_percent': regime.capital_percent,
                    'atr_multiplier': regime.atr_multiplier,
                    'stop_loss_percent': regime.stop_loss_percent,
                    'confidence': regime.confidence,
                    'reasoning': regime.reasoning,
                    'source': 'database',
                    'week_start': regime.week_start.isoformat() if regime.week_start else None
                }

            return None

        except Exception as e:
            logger.error(f"Error getting regime from DB: {e}")
            return None

    @classmethod
    def force_refresh(cls) -> Dict:
        """Force a fresh call to OpenAI, ignoring cache"""
        global _regime_cache, _cache_expiry
        _regime_cache = {}
        _cache_expiry = None
        return cls.get_current_regime()

    @classmethod
    def get_regime_for_date(cls, target_date: datetime) -> Dict:
        """
        Get AI regime parameters for a specific date.
        Used for backtesting - reads from pre-populated DB.
        """
        try:
            from ..database import SessionLocal
            from ..models import AIMarketRegime

            db = SessionLocal()

            regime = db.query(AIMarketRegime).filter(
                AIMarketRegime.week_start <= target_date
            ).order_by(AIMarketRegime.week_start.desc()).first()

            db.close()

            if regime:
                return {
                    'regime': regime.regime,
                    'buy_threshold': regime.buy_threshold,
                    'sell_threshold': regime.sell_threshold,
                    'capital_percent': regime.capital_percent,
                    'atr_multiplier': regime.atr_multiplier,
                    'stop_loss_percent': regime.stop_loss_percent,
                    'confidence': regime.confidence,
                    'reasoning': regime.reasoning
                }

            return cls.DEFAULT_PARAMS

        except Exception as e:
            logger.error(f"Error getting AI regime for {target_date}: {e}")
            return cls.DEFAULT_PARAMS
        except Exception as e:
            logger.error(f"Error checking AI regime availability: {e}")
            return False
