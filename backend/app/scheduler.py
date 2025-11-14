"""
Scheduler para ejecutar ciclos de trading automáticamente
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import asyncio
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
        kraken_client = KrakenClient()
        trading_bot = TradingBot(kraken_client)
        
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
        logger.error(f"❌ Error inicializando scheduler: {e}")

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
