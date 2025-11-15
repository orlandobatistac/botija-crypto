# Próximos Pasos - Botija Deployment

## 1. GitHub Actions - Probar Deployment Automático

### ✅ Cambios Completados
- Workflow actualizado: `deploy-vps.yml` ahora dispara en rama `main` (antes era `scaffold/init`)
- Script desplegará código automáticamente cuando hagas push a `main`

### 🚀 Cómo Probar

```bash
# 1. Hacer commit de cambios en rama local
git add .
git commit -m "Setup: GitHub Actions y SSL configuration"

# 2. Push a main
git push origin main

# 3. Ver deployment en GitHub
# Ve a: https://github.com/orlandobatistac/botija/actions
# Verás el workflow "Deploy to VPS" ejecutándose
```

**Verifica en VPS que el deployment fue exitoso:**
```bash
ssh root@74.208.146.203
systemctl status botija
journalctl -u botija -n 20
```

---

## 2. Scheduler - Activar Ciclos de Trading

### 📝 Configuración Actual
- **Modo**: Paper trading activo (sin credenciales Kraken)
- **Intervalo**: 3600 segundos (1 hora)
- **Cambio**: Scheduler ahora inicia con o sin credenciales Kraken

### 🔐 Activar Real Trading (Cuando tengas credenciales Kraken)

```bash
# SSH a VPS
ssh root@74.208.146.203

# Editar .env
nano /root/botija/.env

# Agregar credenciales:
KRAKEN_API_KEY=tu_api_key_aqui
KRAKEN_SECRET_KEY=tu_secret_aqui
```

**Luego reiniciar el bot:**
```bash
systemctl restart botija
journalctl -u botija -f  # Ver logs en vivo
```

### ✅ Verificar Scheduler Activo

```bash
curl http://74.208.146.203/api/v1/bot/dashboard
# Debe mostrar estado del scheduler

curl http://74.208.146.203/api/v1/paper/wallet
# Verificar que paper trading está funcionando
```

---

## 3. HTTPS/SSL con Let's Encrypt

### 📦 Script Automatizado Creado
- Archivo: `scripts/setup-ssl.sh`
- Instala certbot
- Configura Nginx con SSL
- Auto-renovación de certificados

### 🛠️ Instalación en VPS

**Prerequisito**: Tener un dominio apuntando a IP `74.208.146.203`

```bash
# SSH a VPS
ssh root@74.208.146.203

# Descargar el script
cd /root/botija
git pull origin main
chmod +x scripts/setup-ssl.sh

# Ejecutar setup (reemplaza "tu-dominio.com" con tu dominio real)
./scripts/setup-ssl.sh tu-dominio.com admin@tu-dominio.com
```

**Ejemplo:**
```bash
./scripts/setup-ssl.sh trading.example.com admin@example.com
```

### ✅ Después de Setup SSL

```bash
# Verificar certificados
certbot certificates

# Ver estado de auto-renovación
systemctl status certbot.timer

# Acceder a: https://tu-dominio.com
```

---

## 📋 Checklist Final

- [ ] Push a `main` → Verifica GitHub Actions workflow
- [ ] SSH a VPS → Confirma que código fue actualizado
- [ ] Verifica API: `curl http://74.208.146.203/api/v1/paper/wallet`
- [ ] Scheduler activo: Revisa `journalctl -u botija -f`
- [ ] (Opcional) SSL: Ejecuta `setup-ssl.sh` con tu dominio
- [ ] (Opcional) Kraken: Agrega credenciales cuando tengas API keys

---

## 🔗 Referencias de Comandos Útiles

```bash
# VPS SSH
ssh root@74.208.146.203

# Bot status
systemctl status botija
journalctl -u botija -f

# API health checks
curl http://74.208.146.203/health
curl http://74.208.146.203/api/v1/paper/wallet

# Nginx status
systemctl status nginx
tail -20 /var/log/nginx/error.log

# Ver variables de ambiente
grep -E "KRAKEN|TRADING" /root/botija/.env
```

---

## ⚠️ Notas Importantes

1. **Paper Trading**: Activo por defecto, no requiere credenciales
2. **Real Trading**: Requiere `KRAKEN_API_KEY` + `KRAKEN_SECRET_KEY` en `.env`
3. **Scheduler**: Se inicia automáticamente con el servicio botija
4. **SSL**: Completamente opcional, funciona con HTTP por ahora
5. **Auto-deploy**: Solo con push a rama `main`

---

## 🎯 Próximas Mejoras Futuras

- [ ] Monitoreo con Prometheus
- [ ] Alertas Telegram integritas
- [ ] Dashboard con gráficas en tiempo real
- [ ] WebSocket para live updates
- [ ] Rate limiting y autenticación API
