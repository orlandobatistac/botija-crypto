"""
Test: Verificar que AI responde "en tiempo real" sin hindsight
Solo primeras 8 semanas de 2020
"""
import os
import json
from datetime import date, timedelta
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_TEST = """
Eres un trader profesional de BTC. IMPORTANTE: Responde como si estuvieras EN ESE MOMENTO,
sin conocimiento del futuro.

Para cada semana, imagina que ESTÁS EN ESA FECHA. Solo conoces:
- Noticias y eventos HASTA ese día
- Precio actual y tendencia reciente
- Sentimiento del mercado en ese momento

NO USES conocimiento del futuro. Ejemplos:
- En febrero 2020: NO sabes que habrá crash por COVID en marzo
- En octubre 2021: NO sabes que el ATH será en noviembre

Período: 2020-01-01 a 2020-02-29

Para CADA semana responde con estos campos EXACTOS:

- week_start: Fecha inicio (formato YYYY-MM-DD)
- regime: UNO de estos valores: BULL, BEAR, LATERAL, VOLATILE
- buy_threshold: Score mínimo para comprar (número entero).
  En tendencia clara puedes ser agresivo (40-50), en incertidumbre conservador (60-70)
- sell_threshold: Score para vender (número entero)
- capital_percent: % del capital a usar (40-100).
  Más capital en oportunidades claras, menos en incertidumbre
- confidence: Tu confianza 0.0-1.0
- reasoning: Breve explicación (max 100 chars) con info disponible EN ESA FECHA

Responde SOLO con JSON válido:
{
  "weeks": [
    {
      "week_start": "2020-01-06",
      "regime": "BULL",
      "buy_threshold": 50,
      "sell_threshold": 35,
      "capital_percent": 70,
      "confidence": 0.7,
      "reasoning": "Rally pre-halving, volumen creciente"
    }
  ]
}

Semanas a analizar:
- 2020-01-06 a 2020-01-12
- 2020-01-13 a 2020-01-19
- 2020-01-20 a 2020-01-26
- 2020-01-27 a 2020-02-02
- 2020-02-03 a 2020-02-09
- 2020-02-10 a 2020-02-16
- 2020-02-17 a 2020-02-23
- 2020-02-24 a 2020-03-01
"""

print("=" * 70)
print("🧪 TEST: AI responde 'en tiempo real' - Ene/Feb 2020")
print("=" * 70)
print("\nEnviando prompt...")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": PROMPT_TEST}],
    temperature=0.3,
    response_format={"type": "json_object"}
)

content = response.choices[0].message.content
print(f"Tokens usados: {response.usage.total_tokens}")

data = json.loads(content)
weeks = data.get("weeks", data)

print("\n📝 Raw response (primeras 500 chars):")
print(content[:500])

print("\n" + "=" * 70)
print("📊 RESULTADOS - ¿Responde sin hindsight?")
print("=" * 70)

# Realidad histórica para comparar:
reality = {
    "2020-01-06": {"price": "~$7,400", "context": "Inicio año, mercado lateral post-crash 2018"},
    "2020-01-13": {"price": "~$8,100", "context": "Subiendo, optimismo por halving en mayo"},
    "2020-01-20": {"price": "~$8,600", "context": "Rally continúa"},
    "2020-01-27": {"price": "~$9,300", "context": "Fuerte subida, FOMO"},
    "2020-02-03": {"price": "~$9,400", "context": "Consolidando en máximos"},
    "2020-02-10": {"price": "~$10,200", "context": "Rompió $10k, euforia"},
    "2020-02-17": {"price": "~$9,700", "context": "Retroceso desde máximos"},
    "2020-02-24": {"price": "~$9,600", "context": "COVID empezando a preocupar globalmente"},
}

for w in weeks:
    # Buscar la key del week_start
    week = w.get("week_start") or w.get("week") or w.get("start") or list(w.keys())[0]
    print(f"\n📅 Semana: {week}")
    print(f"   Régimen: {w.get('regime', 'N/A')}")
    print(f"   Buy: {w.get('buy_threshold', 'N/A')}, Sell: {w.get('sell_threshold', 'N/A')}, Capital: {w.get('capital_percent', 'N/A')}%")
    print(f"   Confianza: {w.get('confidence', 'N/A')}")
    print(f"   Razón AI: {w.get('reasoning', 'N/A')}")

    if week in reality:
        print(f"   📍 Realidad: {reality[week]['price']} - {reality[week]['context']}")

    # Verificar si menciona COVID crash o eventos futuros
    reasoning_lower = w['reasoning'].lower()
    if 'crash' in reasoning_lower or 'marzo' in reasoning_lower or 'march' in reasoning_lower:
        print(f"   ⚠️ ALERTA: Posible hindsight detectado!")

print("\n" + "=" * 70)
print("🔍 VALIDACIÓN MANUAL:")
print("=" * 70)
print("""
Preguntas a verificar:
1. ¿En Enero menciona el halving de mayo? ✓ (era conocido)
2. ¿En Febrero menciona el crash de marzo? ✗ (sería hindsight)
3. ¿Los thresholds son consistentes con el sentimiento de la época?
4. ¿El capital_percent aumenta con el rally de enero/febrero?
""")
