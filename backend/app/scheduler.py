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
        
        # Obtener credenciales y parámetros
        kraken_key = os.getenv('KRAKEN_API_KEY', '')
        kraken_secret = os.getenv('KRAKEN_SECRET_KEY', '')
        openai_key = os.getenv('OPENAI_API_KEY', '')
        telegram_token = os.getenv('TELEGRAM_TOKEN', '')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Inicializar bot con todos los parámetros
        trading_bot = TradingBot(
            kraken_api_key=kraken_key,
            kraken_secret=kraken_secret,
            openai_api_key=openai_key,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            trade_amount=config.TRADE_AMOUNT_USD,
            min_balance=config.MIN_BALANCE_USD,
            trailing_stop_pct=config.TRAILING_STOP_PERCENTAGE
        )
        
        mode = "REAL TRADING" if (kraken_key and kraken_secret) else "PAPER TRADING"
        logger.info(f"✅ Bot inicializado en modo {mode}")
        
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

def get_scheduler_status():
    """Retorna el estado actual del scheduler"""
    from datetime import datetime, timedelta
    
    status = {
        "running": scheduler.running,
        "jobs": len(scheduler.get_jobs()) if scheduler.running else 0
    }
    
    if scheduler.running:
        jobs = scheduler.get_jobs()
        if jobs:
            job = jobs[0]
            next_run = job.next_run_time
            if next_run:
                now = datetime.now(next_run.tzinfo) if next_run.tzinfo else datetime.now()
                time_until = next_run - now
                seconds = int(time_until.total_seconds())
                
                minutes = seconds // 60
                secs = seconds % 60
                
                status["next_cycle"] = f"{minutes}m {secs}s"
                status["next_run_time"] = next_run.isoformat()
                status["last_result"] = "pending"
            else:
                status["next_cycle"] = "unknown"
    
    return status

