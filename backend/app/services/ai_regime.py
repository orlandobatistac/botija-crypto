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
Eres un trader profesional de BTC. Analiza el mercado ACTUAL y proporciona parámetros de trading.

Fecha actual: {current_date}

Basándote en:
- Tendencia reciente del precio de BTC
- Noticias y eventos actuales del mercado crypto
- Sentimiento general del mercado
- Volatilidad actual

Responde SOLO con JSON válido:
{{
    "regime": "BULL|BEAR|LATERAL|VOLATILE",
    "buy_threshold": <número 40-70>,
    "sell_threshold": <número 25-45>,
    "capital_percent": <número 40-100>,
    "atr_multiplier": <número 1.0-2.5>,
    "stop_loss_percent": <número 1.5-4.0>,
    "confidence": <número 0.5-1.0>,
    "reasoning": "<explicación breve del análisis>"
}}

Guía de parámetros:
- BULL: buy_threshold bajo (40-50), capital alto (70-90%)
- BEAR: buy_threshold alto (60-70), capital bajo (40-60%)
- LATERAL: buy_threshold medio (50-60), capital medio (50-70%)
- VOLATILE: buy_threshold alto (55-65), capital bajo (50-60%)
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
                model="gpt-4o-mini",
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
    def get_current_regime(cls) -> Dict:
        """
        Get AI regime parameters for the current week.
        Calls OpenAI API and caches result for 1 week.
        """
        global _regime_cache, _cache_expiry

        now = datetime.now()

        # Check cache validity
        if _cache_expiry and now < _cache_expiry and _regime_cache:
            logger.debug(f"Using cached regime: {_regime_cache.get('regime')}")
            return _regime_cache

        # Call OpenAI for fresh analysis
        regime_data = cls._call_openai()

        if regime_data:
            # Cache for 1 week (until next Monday)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            _cache_expiry = now + timedelta(days=days_until_monday)
            _cache_expiry = _cache_expiry.replace(hour=0, minute=0, second=0, microsecond=0)

            _regime_cache = {
                'regime': regime_data.get('regime', 'LATERAL'),
                'buy_threshold': regime_data.get('buy_threshold', 50),
                'sell_threshold': regime_data.get('sell_threshold', 35),
                'capital_percent': regime_data.get('capital_percent', 75),
                'atr_multiplier': regime_data.get('atr_multiplier', 1.5),
                'stop_loss_percent': regime_data.get('stop_loss_percent', 2.0),
                'confidence': regime_data.get('confidence', 0.7),
                'reasoning': regime_data.get('reasoning', ''),
                'source': 'openai',
                'cached_until': _cache_expiry.isoformat()
            }

            # Save to DB for history/backup
            cls._save_to_db(_regime_cache)

            logger.info(f"AI Regime updated: {_regime_cache['regime']} (cached until {_cache_expiry})")
            return _regime_cache

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
