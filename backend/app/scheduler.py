"""
Scheduler para ejecutar ciclos de trading automáticamente
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio
import os
from datetime import datetime
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
            trade_amount_percent=config.TRADE_AMOUNT_PERCENT,
            min_balance=config.MIN_BALANCE_USD,
            min_balance_percent=config.MIN_BALANCE_PERCENT,
            trailing_stop_pct=config.TRAILING_STOP_PERCENTAGE
        )
        
        mode = "REAL TRADING" if (kraken_key and kraken_secret) else "PAPER TRADING"
        logger.info(f"✅ Bot inicializado en modo {mode}")
        
        # Ejecutar ciclo cada hora en punto en hora de Charlotte, NC (Eastern Time)
        scheduler.add_job(
            run_trading_cycle,
            CronTrigger(minute=0, timezone='America/New_York'),  # Charlotte, NC timezone
            id='trading_cycle',
            name='Trading cycle - hourly on the hour (ET)',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(f"✅ Scheduler iniciado - Ciclo de trading cada hora en punto (XX:00 ET - Charlotte, NC)")
        
    except Exception as e:
        logger.warning(f"⚠️  Scheduler deshabilitado: {e}")


def run_trading_cycle():
    """Ejecuta un ciclo completo de trading"""
    try:
        now = datetime.now()
        logger.info(f"🔄 Iniciando ciclo de trading - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ejecutar en loop asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(trading_bot.run_cycle())
        
        logger.info(f"✅ Ciclo de trading completado - {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ Error en ciclo de trading: {e}")

def shutdown_scheduler():
    """Apaga el scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler detenido")

def get_scheduler_status():
    """Retorna el estado actual del scheduler con countdown preciso"""
    from datetime import datetime
    import pytz
    
    status = {
        "running": scheduler.running,
        "jobs": len(scheduler.get_jobs()) if scheduler.running else 0,
        "next_run_time": None,
        "seconds_until_next": 0,
        "last_result": "pending"
    }
    
    if not scheduler.running:
        return status
    
    try:
        jobs = scheduler.get_jobs()
        if not jobs:
            return status
        
        job = jobs[0]
        if not job.next_run_time:
            return status
        
        next_run = job.next_run_time
        
        # Obtener tiempo actual con timezone awareness
        if next_run.tzinfo:
            now = datetime.now(next_run.tzinfo)
        else:
            now = datetime.now()
        
        # Calcular diferencia en segundos
        time_diff = next_run - now
        seconds = int(time_diff.total_seconds())
        
        status["next_run_time"] = next_run.isoformat()
        status["seconds_until_next"] = max(0, seconds)
        
        logger.debug(f"Scheduler status: next_run={next_run}, now={now}, seconds={seconds}")
        
    except Exception as e:
        logger.error(f"Error calculating scheduler status: {e}")
        status["error"] = str(e)
    
    return status

