"""
Script para poblar la base de datos con regímenes de mercado analizados por AI.
Genera parámetros de trading óptimos por semana basados en contexto histórico.
"""

import asyncio
import os
import sys
import json
from datetime import date, timedelta
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI
import sqlite3

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_TEMPLATE = """
Eres un trader profesional de BTC. IMPORTANTE: Responde como si estuvieras EN ESE MOMENTO,
sin conocimiento del futuro.

Para cada semana, imagina que ESTÁS EN ESA FECHA. Solo conoces:
- Noticias y eventos HASTA ese día
- Precio actual y tendencia reciente
- Sentimiento del mercado en ese momento

NO USES conocimiento del futuro. Ejemplos:
- En febrero 2020: NO sabes que habrá crash por COVID en marzo
- En octubre 2021: NO sabes que el ATH será en noviembre
- En octubre 2022: NO sabes que FTX quebrará en noviembre

Período: {start_date} a {end_date}

Para CADA semana responde con estos campos EXACTOS:

- week_start: Fecha inicio (formato YYYY-MM-DD)
- regime: UNO de estos valores: BULL, BEAR, LATERAL, VOLATILE
- buy_threshold: Score mínimo para comprar (número entero).
  En tendencia clara puedes ser agresivo (40-50), en incertidumbre conservador (60-70)
- sell_threshold: Score para vender (número entero)
- capital_percent: % del capital a usar (40-100).
  Más capital en oportunidades claras, menos en incertidumbre
- atr_multiplier: Multiplicador para stop loss (1.0-2.5)
- stop_loss_percent: Stop loss de respaldo (1.5-4.0)
- confidence: Tu confianza 0.0-1.0
- reasoning: Breve explicación (max 100 chars) con info disponible EN ESA FECHA

Responde SOLO con JSON válido:
{{
  "weeks": [
    {{
      "week_start": "2020-01-06",
      "regime": "BULL",
      "buy_threshold": 50,
      "sell_threshold": 35,
      "capital_percent": 70,
      "atr_multiplier": 1.5,
      "stop_loss_percent": 2.0,
      "confidence": 0.7,
      "reasoning": "Rally pre-halving, volumen creciente"
    }}
  ]
}}

Semanas a analizar:
{weeks_list}
"""


def get_weeks(start: date, end: date) -> list[dict]:
    """Genera lista de semanas entre dos fechas."""
    weeks = []
    # Ajustar al lunes más cercano
    current = start - timedelta(days=start.weekday())
    while current <= end:
        week_end = current + timedelta(days=6)
        weeks.append({
            "start": current.isoformat(),
            "end": week_end.isoformat()
        })
        current += timedelta(days=7)
    return weeks


def fetch_regimes_batch(weeks: list[dict]) -> list[dict]:
    """Llama a OpenAI para un batch de semanas."""
    weeks_str = "\n".join([f"- {w['start']} a {w['end']}" for w in weeks])

    print(f"   Enviando prompt para {len(weeks)} semanas...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": PROMPT_TEMPLATE.format(
                start_date=weeks[0]["start"],
                end_date=weeks[-1]["end"],
                weeks_list=weeks_str
            )
        }],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    print(f"   Tokens usados: {response.usage.total_tokens}")

    data = json.loads(content)
    return data.get("weeks", data) if isinstance(data, dict) else data


def init_database(db_path: str):
    """Crear tabla si no existe."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Eliminar tabla existente para repoblar
    cursor.execute("DROP TABLE IF EXISTS ai_market_regimes")

    cursor.execute("""
        CREATE TABLE ai_market_regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL UNIQUE,
            week_end DATE NOT NULL,
            regime TEXT NOT NULL,
            buy_threshold INTEGER DEFAULT 50,
            sell_threshold INTEGER DEFAULT 35,
            capital_percent INTEGER DEFAULT 75,
            atr_multiplier REAL DEFAULT 1.5,
            stop_loss_percent REAL DEFAULT 2.0,
            confidence REAL DEFAULT 0.7,
            reasoning TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_week_start ON ai_market_regimes(week_start)")

    conn.commit()
    conn.close()
    print("✅ Tabla ai_market_regimes creada")


def save_regimes(db_path: str, regimes: list[dict]):
    """Guardar regímenes en la base de datos."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    saved = 0
    for r in regimes:
        try:
            week_start = r.get("week_start")
            if not week_start:
                continue

            week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO ai_market_regimes
                (week_start, week_end, regime, buy_threshold, sell_threshold,
                 capital_percent, atr_multiplier, stop_loss_percent, confidence, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                week_start,
                week_end,
                r.get("regime", "LATERAL"),
                r.get("buy_threshold", 50),
                r.get("sell_threshold", 35),
                r.get("capital_percent", 75),
                r.get("atr_multiplier", 1.5),
                r.get("stop_loss_percent", 2.0),
                r.get("confidence", 0.7),
                r.get("reasoning", "")
            ))
            saved += 1
        except Exception as e:
            print(f"   ⚠️ Error guardando {r}: {e}")

    conn.commit()
    conn.close()
    return saved


def populate_database():
    """Poblar DB con regímenes AI."""
    start = date(2020, 1, 1)
    end = date(2025, 11, 30)

    db_path = Path(__file__).parent.parent / "backend" / "data" / "trading_bot.db"

    print("=" * 60)
    print("🤖 POBLANDO BASE DE DATOS CON REGÍMENES AI")
    print("=" * 60)
    print(f"📅 Período: {start} a {end}")

    # Generar semanas
    all_weeks = get_weeks(start, end)
    print(f"📆 Total semanas: {len(all_weeks)}")

    # Inicializar DB
    init_database(str(db_path))

    # Procesar en batches de 15 semanas (para no exceder tokens)
    batch_size = 15
    all_regimes = []
    total_tokens = 0

    for i in range(0, len(all_weeks), batch_size):
        batch = all_weeks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(all_weeks) + batch_size - 1) // batch_size

        print(f"\n🔄 Batch {batch_num}/{total_batches}: semanas {i+1}-{i+len(batch)}")

        try:
            regimes = fetch_regimes_batch(batch)

            if regimes:
                saved = save_regimes(str(db_path), regimes)
                all_regimes.extend(regimes)
                print(f"   ✅ {saved} semanas guardadas")
            else:
                print(f"   ⚠️ No se recibieron datos")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Rate limiting - esperar entre llamadas
        if i + batch_size < len(all_weeks):
            print("   ⏳ Esperando 2s (rate limiting)...")
            import time
            time.sleep(2)

    print("\n" + "=" * 60)
    print(f"✅ COMPLETADO: {len(all_regimes)} semanas procesadas")
    print(f"📁 Base de datos: {db_path}")
    print("=" * 60)

    # Mostrar resumen
    if all_regimes:
        print("\n📊 Resumen de regímenes:")
        regimes_count = {}
        for r in all_regimes:
            regime = r.get("regime", "UNKNOWN")
            regimes_count[regime] = regimes_count.get(regime, 0) + 1

        for regime, count in sorted(regimes_count.items()):
            print(f"   {regime}: {count} semanas")


if __name__ == "__main__":
    populate_database()
