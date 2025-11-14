"""
Tests para paper trading
"""

import pytest
import json
import csv
from pathlib import Path
from app.services.modes.paper import PaperTradingEngine
from app.services.modes.factory import get_trading_engine
from app.services.trading_mode import MODE

@pytest.fixture
def paper_engine():
    """Fixture para crear instancia de PaperTradingEngine"""
    engine = PaperTradingEngine()
    engine.reset_wallet(1000.0)
    return engine

def test_paper_engine_initialization(paper_engine):
    """Test que paper engine se inicializa correctamente"""
    wallet = paper_engine.get_wallet_summary()
    
    assert wallet['usd_balance'] == 1000.0
    assert wallet['btc_balance'] == 0.0
    assert wallet['trailing_stop'] is None

def test_paper_engine_buy(paper_engine):
    """Test compra en modo paper"""
    price = 50000.0
    usd_amount = 200.0
    
    success, message = paper_engine.buy(price, usd_amount)
    
    assert success is True
    assert "paper buy" in message.lower()
    
    wallet = paper_engine.get_wallet_summary()
    expected_btc = usd_amount / price
    
    assert wallet['usd_balance'] == 1000.0 - usd_amount
    assert wallet['btc_balance'] == pytest.approx(expected_btc, rel=1e-5)
    assert wallet['trailing_stop'] == pytest.approx(price * 0.99, rel=1e-5)

def test_paper_engine_buy_insufficient_balance(paper_engine):
    """Test compra sin fondos suficientes"""
    price = 50000.0
    usd_amount = 2000.0  # Más que balance inicial
    
    success, message = paper_engine.buy(price, usd_amount)
    
    assert success is False
    assert "insufficient" in message.lower()

def test_paper_engine_sell(paper_engine):
    """Test venta en modo paper"""
    # Primero comprar
    paper_engine.buy(50000.0, 200.0)
    wallet = paper_engine.get_wallet_summary()
    initial_btc = wallet['btc_balance']
    
    # Vender
    sell_price = 51000.0
    success, message = paper_engine.sell(sell_price, initial_btc)
    
    assert success is True
    assert "paper sell" in message.lower()
    
    wallet = paper_engine.get_wallet_summary()
    assert wallet['btc_balance'] == 0.0
    assert wallet['trailing_stop'] is None

def test_paper_engine_sell_no_position(paper_engine):
    """Test venta sin posición abierta"""
    success, message = paper_engine.sell(50000.0, 0.1)
    
    assert success is False
    assert "insufficient" in message.lower()

def test_paper_engine_trailing_stop(paper_engine):
    """Test actualización de trailing stop"""
    # Comprar
    entry_price = 50000.0
    paper_engine.buy(entry_price, 200.0)
    
    # Precio sube
    new_price = 51000.0
    result = paper_engine.update_trailing_stop(new_price)
    
    assert result['should_sell'] is False
    expected_stop = max(entry_price * 0.99, new_price * 0.99)
    assert result['trailing_stop'] == pytest.approx(expected_stop, rel=1e-5)

def test_paper_engine_trailing_stop_triggers_sell(paper_engine):
    """Test que trailing stop trigger venta"""
    # Comprar
    entry_price = 50000.0
    paper_engine.buy(entry_price, 200.0)
    
    # Precio cae debajo del trailing stop
    low_price = entry_price * 0.98  # Por debajo de 0.99 stop
    result = paper_engine.update_trailing_stop(low_price)
    
    assert result['should_sell'] is True

def test_paper_engine_reset_wallet(paper_engine):
    """Test reset de wallet"""
    # Hacer operaciones
    paper_engine.buy(50000.0, 500.0)
    
    # Reset
    paper_engine.reset_wallet(2000.0)
    
    wallet = paper_engine.get_wallet_summary()
    assert wallet['usd_balance'] == 2000.0
    assert wallet['btc_balance'] == 0.0

def test_paper_engine_wallet_persistence(paper_engine):
    """Test que wallet se persiste en JSON"""
    # Hacer operación
    paper_engine.buy(50000.0, 300.0)
    wallet_before = paper_engine.get_wallet_summary()
    
    # Crear nueva instancia
    new_engine = PaperTradingEngine()
    wallet_after = new_engine.get_wallet_summary()
    
    # Verificar que se recuperó el estado
    assert wallet_before['usd_balance'] == pytest.approx(
        wallet_after['usd_balance'], rel=1e-5
    )
    assert wallet_before['btc_balance'] == pytest.approx(
        wallet_after['btc_balance'], rel=1e-5
    )

def test_paper_engine_trade_logging(paper_engine):
    """Test que trades se registran en CSV"""
    # Hacer compra
    paper_engine.buy(50000.0, 200.0)
    
    # Verificar CSV
    trades_path = Path(__file__).parent.parent / 'data' / 'paper_trades.csv'
    assert trades_path.exists()
    
    with open(trades_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) > 0
        assert rows[-1]['type'] == 'BUY'
        assert float(rows[-1]['price']) == 50000.0

def test_factory_pattern_paper_mode(monkeypatch):
    """Test que factory retorna PaperTradingEngine en modo PAPER"""
    monkeypatch.setenv('TRADING_MODE', 'PAPER')
    
    # Recargar módulo para aplicar cambio de env
    import importlib
    from app.services import trading_mode
    importlib.reload(trading_mode)
    from app.services.trading_mode import MODE
    
    # Factory debería retornar PaperTradingEngine
    if MODE == "PAPER":
        engine = get_trading_engine()
        assert isinstance(engine, PaperTradingEngine)

def test_get_open_position_none(paper_engine):
    """Test que no hay posición abierta sin compra"""
    position = paper_engine.get_open_position()
    assert position == {} or position is None

def test_get_open_position_after_buy(paper_engine):
    """Test posición abierta después de compra"""
    paper_engine.buy(50000.0, 200.0)
    position = paper_engine.get_open_position()
    
    assert position is not None
    assert position != {}
    assert position.get('entry_price') == 50000.0
    assert position.get('btc_balance') > 0

def test_close_position(paper_engine):
    """Test cierre de posición"""
    paper_engine.buy(50000.0, 200.0)
    success = paper_engine.close_position()
    
    assert success is True
    position = paper_engine.get_open_position()
    assert position == {} or position is None

def test_load_balances(paper_engine):
    """Test carga de balances"""
    balances = paper_engine.load_balances()
    
    assert 'btc' in balances
    assert 'usd' in balances
    assert isinstance(balances['btc'], float)
    assert isinstance(balances['usd'], float)
