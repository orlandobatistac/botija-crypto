# Migración de Base de Datos - Agregar trading_mode

## Problema
La base de datos en producción no tiene la columna `trading_mode` en la tabla `bot_status`, causando errores 500.

## Solución

### Opción 1: SSH al servidor (recomendado)
```bash
# Conectar al servidor
ssh user@74.208.146.203

# Navegar al directorio del proyecto
cd /path/to/botija

# Ejecutar migración
python scripts/migrate_add_trading_mode.py backend/app.db

# Reiniciar servicio
sudo systemctl restart trading-bot
```

### Opción 2: Eliminar base de datos (datos se perderán)
```bash
ssh user@74.208.146.203
cd /path/to/botija/backend
rm app.db
# El servidor recreará la DB automáticamente con el schema correcto
sudo systemctl restart trading-bot
```

### Opción 3: Script remoto rápido
```bash
ssh user@74.208.146.203 "cd /path/to/botija && python -c \"
import sqlite3
conn = sqlite3.connect('backend/app.db')
conn.execute('ALTER TABLE bot_status ADD COLUMN trading_mode VARCHAR DEFAULT \\\"PAPER\\\"')
conn.execute('UPDATE bot_status SET trading_mode = \\\"PAPER\\\" WHERE trading_mode IS NULL')
conn.commit()
conn.close()
print('✅ Migración completada')
\""
```

## Verificación
Después de migrar, verifica en los logs que no aparezca más el error:
```
no such column: bot_status.trading_mode
```
