"""
OpenAI AI signal validation
"""

import openai
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AISignalValidator:
    """AI-based signal validation using OpenAI"""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI client"""
        openai.api_key = api_key
        self.logger = logger
    
    def get_signal(
        self,
        price: float,
        ema20: float,
        ema50: float,
        rsi: float,
        btc_balance: float,
        usd_balance: float
    ) -> Dict:
        """Get AI signal for trading decision"""
        try:
            prompt = f"""
Analyze the following Bitcoin trading data and provide a trading signal.

Current Data:
- Current BTC Price: ${price:,.2f}
- EMA20: ${ema20:,.2f}
- EMA50: ${ema50:,.2f}
- RSI14: {rsi:.2f}
- BTC Balance: {btc_balance:.8f}
- USD Balance: ${usd_balance:,.2f}

Trading Rules:
1. BUY signal only if:
   - EMA20 > EMA50
   - RSI between 45-60
   - USD balance >= $65
   - No existing BTC position

2. SELL signal if:
   - EMA20 < EMA50 AND RSI < 40
   - Or if profit target reached

3. HOLD signal if none of above conditions met

Respond with ONLY one word: BUY, SELL, or HOLD
Also provide a confidence score (0-1) in the format:
SIGNAL: [SIGNAL]
CONFIDENCE: [0-1]
REASON: [One sentence explanation]
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Bitcoin trading analyst. Provide concise trading signals."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            content = response['choices'][0]['message']['content'].strip()
            
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
