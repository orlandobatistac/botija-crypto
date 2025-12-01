"""
OpenAI AI signal validation
"""

from openai import OpenAI
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AISignalValidator:
    """AI-based signal validation using OpenAI"""

    def __init__(self, api_key: str):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=api_key)
        self.logger = logger

    def get_signal(
        self,
        price: float,
        ema20: float,
        ema50: float,
        rsi: float,
        btc_balance: float,
        usd_balance: float,
        macd: float = 0,
        macd_signal: float = 0,
        macd_hist: float = 0,
        bb_position: float = 0.5,
        tech_score: int = 50
    ) -> Dict:
        """Get AI signal for trading decision with enhanced indicators"""
        try:
            # Calculate additional context
            ema_trend = "ALCISTA" if ema20 > ema50 else "BAJISTA"
            ema_gap = abs(ema20 - ema50) / ema50 * 100 if ema50 > 0 else 0
            macd_trend = "ALCISTA" if macd > macd_signal else "BAJISTA"

            # Bollinger position interpretation
            if bb_position < 0.2:
                bb_zone = "SOBREVENTA (cerca banda inferior)"
            elif bb_position > 0.8:
                bb_zone = "SOBRECOMPRA (cerca banda superior)"
            else:
                bb_zone = "NEUTRAL"

            prompt = f"""
Eres un trader experto en Bitcoin swing trading. Tu objetivo es generar ganancias consistentes.

📊 INDICADORES TÉCNICOS:
- Precio BTC: ${price:,.2f}
- EMA20: ${ema20:,.2f} | EMA50: ${ema50:,.2f}
- Tendencia EMA: {ema_trend} (gap: {ema_gap:.2f}%)
- RSI14: {rsi:.1f}
- MACD: {macd:.2f} | Signal: {macd_signal:.2f} | Hist: {macd_hist:.2f}
- Tendencia MACD: {macd_trend}
- Bollinger: {bb_zone} (posición: {bb_position:.2f})
- Score Técnico: {tech_score}/100

💰 BALANCE:
- BTC: {btc_balance:.8f}
- USD: ${usd_balance:,.2f}

🎯 ESTRATEGIA SWING TRADING:
- Objetivo: capturar movimientos del 2-8%
- Solo entrar cuando múltiples indicadores confirmen

📈 CRITERIOS BUY (score >= 65):
- EMA20 > EMA50 (tendencia alcista)
- MACD cruzando hacia arriba o positivo
- RSI 35-65 (no sobrecomprado)
- Bollinger < 0.5 (rebote desde zona baja)

📉 CRITERIOS SELL (score <= 35):
- Debilidad en tendencia o reversión
- RSI > 70 o MACD cruzando hacia abajo
- Bollinger > 0.8 (sobreextendido)

⏸️ CRITERIOS HOLD:
- Indicadores mixtos o sin confirmación clara
- Score entre 35-65

IMPORTANTE: El Score Técnico ya combina todos los indicadores.
Si score >= 65 → fuerte señal de compra
Si score <= 35 → fuerte señal de venta
Usa tu criterio para confirmar o ajustar.

Responde SOLO en este formato:
SIGNAL: BUY/SELL/HOLD
CONFIDENCE: [0.0-1.0]
REASON: [Explicación técnica breve]
"""

            response = self.client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {"role": "system", "content": "Eres un trader profesional de Bitcoin. Analizas indicadores técnicos y generas señales precisas. Responde solo en el formato solicitado."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Más consistente
                max_tokens=150
            )

            content = response.choices[0].message.content.strip()

            # Parse response
            signal = 'HOLD'
            confidence = 0.5
            reason = ''

            lines = content.split('\n')
            for line in lines:
                if line.startswith('SIGNAL:'):
                    signal_text = line.replace('SIGNAL:', '').strip()
                    signal = signal_text if signal_text in ['BUY', 'SELL', 'HOLD'] else 'HOLD'
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.replace('CONFIDENCE:', '').strip())
                        confidence = min(max(confidence, 0.0), 1.0)
                    except ValueError:
                        confidence = 0.5
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()

            self.logger.info(f"AI Signal: {signal} (confidence: {confidence})")

            return {
                'signal': signal,
                'confidence': confidence,
                'reason': reason,
                'raw_response': content
            }

        except Exception as e:
            self.logger.error(f"Error getting AI signal: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': f'Error: {str(e)}',
                'raw_response': ''
            }
