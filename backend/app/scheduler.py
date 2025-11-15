"""
Scheduler para ejecutar ciclos de trading automáticamente
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import asyncio
import os
from .services.trading_bot import TradingBot
from .services.kraken_client import KrakenClient
from .config import Config

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
trading_bot = None

def init_scheduler():
    """Inicializa el scheduler con el bot de trading"""
    global trading_bot
    
    try:
        config = Config()
        
        # Obtener credenciales Kraken
        kraken_key = os.getenv('KRAKEN_API_KEY', '')
        kraken_secret = os.getenv('KRAKEN_SECRET_KEY', '')
        
        # Inicializar bot (con o sin credenciales)
        if kraken_key and kraken_secret:
            kraken_client = KrakenClient(kraken_key, kraken_secret)
            trading_bot = TradingBot(kraken_client)
            logger.info("✅ Bot inicializado con credenciales Kraken (REAL TRADING)")
        else:
            # Paper trading mode (sin credenciales)
            trading_bot = TradingBot(None)
            logger.info("✅ Bot inicializado en modo PAPER TRADING (sin credenciales Kraken)")
        
        # Agregar job para ejecutar ciclo cada hora (3600 segundos por defecto)
        scheduler.add_job(
            run_trading_cycle,
            IntervalTrigger(seconds=config.TRADING_INTERVAL),
            id='trading_cycle',
            name='Ejecutar ciclo de trading',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(f"✅ Scheduler iniciado - Ciclo de trading cada {config.TRADING_INTERVAL}s")
        
    except Exception as e:
        logger.warning(f"⚠️  Scheduler deshabilitado: {e}")

def run_trading_cycle():
    """Ejecuta un ciclo completo de trading"""
    try:
        # Ejecutar en loop asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(trading_bot.run_cycle())
        logger.info("✅ Ciclo de trading completado")
    except Exception as e:
        logger.error(f"❌ Error en ciclo de trading: {e}")

def shutdown_scheduler():
    """Apaga el scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler detenido")
