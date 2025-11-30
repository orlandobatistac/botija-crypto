"""
AI Regime Service - Gets market regime parameters from OpenAI in real-time
Caches results for 1 week to minimize API costs
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

    PROMPT_TEMPLATE = """
You are a professional BTC trader. Analyze the CURRENT market and provide trading parameters.

Current date: {current_date}

Based on:
- Recent BTC price trend
- Current crypto market news and events
- General market sentiment
- Current volatility

Respond ONLY with valid JSON:
{{
    "regime": "BULL|BEAR|LATERAL|VOLATILE",
    "buy_threshold": <number 40-70>,
    "sell_threshold": <number 25-45>,
    "capital_percent": <number 40-100>,
    "atr_multiplier": <number 1.0-2.5>,
    "stop_loss_percent": <number 1.5-4.0>,
    "confidence": <number 0.5-1.0>,
    "reasoning": "<brief analysis explanation>"
}}

Parameter guidelines:
- BULL: low buy_threshold (40-50), high capital (70-90%)
- BEAR: high buy_threshold (60-70), low capital (40-60%)
- LATERAL: medium buy_threshold (50-60), medium capital (50-70%)
- VOLATILE: high buy_threshold (55-65), low capital (50-60%)
"""

    @classmethod
    def _call_openai(cls) -> Optional[Dict]:
        """Call OpenAI API to get current market regime"""
        try:
            from openai import OpenAI

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, using defaults")
                return None

            client = OpenAI(api_key=api_key)

            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = cls.PROMPT_TEMPLATE.format(current_date=current_date)

            logger.info("Calling OpenAI for market regime analysis...")

            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            logger.info(f"OpenAI regime response: {data.get('regime')} - {data.get('reasoning', '')[:50]}")

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
