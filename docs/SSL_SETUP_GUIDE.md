# HTTPS/SSL Configuration Guide - Botija

## Overview

Your VPS is currently running on **HTTP only**. This guide shows how to enable **HTTPS with SSL/TLS** using Let's Encrypt (free certificates with auto-renewal).

---

## Prerequisites

1. **Domain Name**: You must own or control a domain
   - Example: `trading.example.com`
   - OR: `botija.yourcompany.com`

2. **DNS Configuration**: Domain must point to VPS IP
   ```
   botija.example.com  A  74.208.146.203
   ```

3. **SSH Access**: You have `root@74.208.146.203`

---

## Option A: Automated Setup (Recommended)

### Step 1: Use the Provided Script

A fully automated script is included in the repo:

```bash
# SSH to VPS
ssh root@74.208.146.203

# Download latest code
cd /root/botija && git pull origin main

# Make script executable
chmod +x scripts/setup-ssl.sh

# Run the setup
./scripts/setup-ssl.sh trading.example.com admin@example.com
```

**What it does:**
1. ✅ Installs certbot (Let's Encrypt client)
2. ✅ Generates SSL certificate
3. ✅ Configures Nginx with HTTPS
4. ✅ Sets up HTTP → HTTPS redirect
5. ✅ Enables auto-renewal (systemd timer)

### Step 2: Verify SSL is Working

```bash
# Test certificate
certbot certificates

# Expected output:
# Certificate Name: trading.example.com
# Expiry Date: 2025-02-15
# Auto-renewal: ENABLED
```

### Step 3: Access Your Bot

```
https://trading.example.com  ✅ SECURE
```

Your browser should show a green lock 🔒

---

## Option B: Manual Setup (Step-by-Step)

### Step 1: Install Certbot

```bash
ssh root@74.208.146.203

apt-get update
apt-get install -y certbot python3-certbot-nginx
```

### Step 2: Generate Certificate

```bash
# Replace with YOUR domain
DOMAIN="trading.example.com"
EMAIL="admin@example.com"

certbot certonly \
  --nginx \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"
```

**Note**: If DNS isn't set up yet, you'll get an error. Make sure your domain's A record points to `74.208.146.203`.

### Step 3: Configure Nginx

Edit the Nginx config:

```bash
nano /etc/nginx/sites-available/botija
```

Replace the entire content with:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name trading.example.com www.trading.example.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name trading.example.com www.trading.example.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/trading.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trading.example.com/privkey.pem;
    
    # SSL security configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Root directory
    root /root/botija/frontend;
    
    # Serve dashboard
    location / {
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }
    
    # Static files (long cache)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8002;
    }
    
    # Deny dot files
    location ~ /\. {
        deny all;
    }
}
```

**Remember to replace `trading.example.com` with YOUR domain!**

### Step 4: Test Nginx Config

```bash
nginx -t

# Should output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 5: Reload Nginx

```bash
systemctl reload nginx
```

### Step 6: Enable Auto-Renewal

```bash
# Enable and start the renewal timer
systemctl enable certbot.timer
systemctl start certbot.timer

# Verify it's running
systemctl status certbot.timer
```

---

## Verifying HTTPS Setup

### From VPS

```bash
# Check certificates
certbot certificates

# View certificate details
certbot show trading.example.com

# Test renewal (dry-run, won't actually renew)
certbot renew --dry-run
```

### From Your Browser

1. Go to: `https://trading.example.com`
2. Look for green lock 🔒 in address bar
3. Click lock → Certificate info
4. Verify domain name matches

### From Command Line

```bash
# Test SSL certificate
curl https://trading.example.com -v

# Should output:
# Connected to trading.example.com
# SSL: certificate verify OK
```

---

## What Happens Now

### Auto-Renewal Process

Let's Encrypt certificates expire after **90 days**. The renewal process:

1. **Automatic**: Certbot timer runs daily
2. **Smart**: Only renews if certificate is 30+ days old
3. **Silent**: No action needed from you
4. **Logs**: Check with `journalctl -u certbot.timer`

### Certificate Renewal Logs

```bash
# View renewal attempts
journalctl -u certbot.timer -n 50

# View renewal details
ls -la /var/log/letsencrypt/
```

---

## Troubleshooting SSL

### Issue: Certificate Not Found

```bash
# Check if certificate was created
ls /etc/letsencrypt/live/

# If empty, run certbot again
certbot certonly --nginx -d trading.example.com
```

### Issue: Domain Validation Failed

```bash
# Error: "Validating domain..."
# Cause: DNS not pointing to VPS
# Fix: Update your domain's A record to 74.208.146.203
# Then try again after 15 minutes (DNS propagation)
```

### Issue: Certificate Renewal Failed

```bash
# Check renewal logs
journalctl -u certbot.timer -n 100

# Try manual renewal
certbot renew --force-renewal

# Check for errors
certbot renew --verbose
```

### Issue: Nginx won't reload

```bash
# Test syntax
nginx -t

# View errors
tail -20 /var/log/nginx/error.log

# Restart (not reload)
systemctl restart nginx
```

---

## Performance Impact

### Before SSL (HTTP only)
- ⚠️ Unencrypted traffic
- 🚫 Browser shows "Not Secure"
- ❌ HSTS not available

### After SSL (HTTPS)
- ✅ Encrypted traffic (TLS 1.3)
- 🔒 Browser shows "Secure"
- ✅ HSTS enabled (security headers)
- ✅ HTTP/2 enabled (faster)

### Security Improvements
- Traffic can't be eavesdropped
- Man-in-the-middle attacks prevented
- Browser warnings eliminated
- Better for public networks

---

## DNS Configuration Examples

### If using AWS Route 53
```
Record Type: A
Name: trading
Value: 74.208.146.203
TTL: 300
```

### If using Cloudflare
```
Type: A
Name: trading
IPv4 Address: 74.208.146.203
Proxy Status: DNS only (or proxied)
TTL: Auto
```

### If using Namecheap
```
Type: A (Address)
Host: trading
Value: 74.208.146.203
TTL: 3600
```

**Wait 15-30 minutes for DNS to propagate.**

---

## Test DNS Propagation

```bash
# Check if DNS is ready
nslookup trading.example.com
# Should show: 74.208.146.203

# Or use dig
dig trading.example.com +short
# Should show: 74.208.146.203

# Once it shows correct IP, run certbot
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Check certificate | `certbot certificates` |
| Renew now | `certbot renew` |
| Test renewal | `certbot renew --dry-run` |
| View renewal logs | `journalctl -u certbot.timer` |
| Reload Nginx | `systemctl reload nginx` |
| Test Nginx config | `nginx -t` |
| Check SSL certificate | `curl -v https://trading.example.com` |

---

## Security Best Practices

✅ **Enabled**:
- TLS 1.2 + 1.3
- Strong ciphers
- HSTS (Strict-Transport-Security)
- HTTP/2 multiplexing
- Auto certificate renewal

⚠️ **Manual Optional**:
- Domain validation email
- Backup certificates
- Rate limit alerts

---

## Common Questions

**Q: Does this cost anything?**
A: No, Let's Encrypt certificates are completely free.

**Q: How often do I need to renew?**
A: Certificates last 90 days, but renewal is automatic. You don't need to do anything.

**Q: What if I don't have a domain?**
A: You can use a temporary domain or use IP address (not recommended for production).

**Q: Can I use HTTP after setup?**
A: Yes, but it will redirect to HTTPS. HTTP is still accessible for the redirect.

**Q: Will my API still work?**
A: Yes, all API endpoints work via HTTPS with proper headers.

---

## Next Steps

1. **Get a domain** (if you don't have one)
2. **Point DNS to VPS IP** (74.208.146.203)
3. **Run the SSL setup script** (`scripts/setup-ssl.sh`)
4. **Verify certificate** (`certbot certificates`)
5. **Access via HTTPS** (`https://your-domain.com`)
6. **Monitor renewal** (automatic, but check logs sometimes)

---

## Support Commands (All from VPS)

```bash
# Complete status check
certbot certificates && \
systemctl status certbot.timer && \
nginx -t && \
journalctl -u certbot.timer -n 5

# Full diagnostic
curl -v https://74.208.146.203 2>&1 | grep -i tls
curl https://your-domain.com -v 2>&1 | grep -i certificate
```

---

**Last Updated**: November 15, 2025
**Status**: Ready for SSL setup
**Next Action**: Point your domain to 74.208.146.203 and run setup-ssl.sh
