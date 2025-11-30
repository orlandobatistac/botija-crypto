"""
Technical indicators for trading signals
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical analysis indicators"""

    @staticmethod
    def calculate_ema(data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return []

        series = pd.Series(data)
        ema = series.ewm(span=period, adjust=False).mean()
        return ema.tolist()

    @staticmethod
    def calculate_rsi(data: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return []

        series = pd.Series(data)
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.tolist()

    @staticmethod
    def calculate_macd(
        data: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[List[float], List[float], List[float]]:
        """Calculate MACD indicator"""
        series = pd.Series(data)
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return (
            macd_line.tolist(),
            signal_line.tolist(),
            histogram.tolist()
        )

    @staticmethod
    def calculate_bollinger_bands(
        data: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands"""
        series = pd.Series(data)
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return (upper.tolist(), middle.tolist(), lower.tolist())

    @staticmethod
    def calculate_score(
        ema20: float,
        ema50: float,
        rsi: float,
        macd: float,
        macd_signal: float,
        macd_hist: float,
        bb_position: float
    ) -> int:
        """Calculate composite trading score (0-100)"""
        score = 50  # Base score

        # EMA trend (weight: 25)
        if ema20 > ema50:
            score += 15
            # Strong trend bonus
            ema_gap_pct = (ema20 - ema50) / ema50 * 100 if ema50 > 0 else 0
            if ema_gap_pct > 1:
                score += 10
        else:
            score -= 15

        # RSI (weight: 20)
        if 40 <= rsi <= 60:
            score += 15
        elif rsi > 70:
            score -= 20  # Overbought
        elif rsi < 30:
            score += 10  # Oversold = opportunity
        elif rsi < 40:
            score -= 10

        # MACD momentum (weight: 25)
        if macd > macd_signal and macd_hist > 0:
            score += 20
            if macd_hist > abs(macd) * 0.1:  # Strong momentum
                score += 5
        elif macd < macd_signal:
            score -= 15

        # Bollinger position (weight: 20)
        if bb_position < 0.3:  # Near lower band
            score += 15
        elif bb_position > 0.8:  # Near upper band
            score -= 15
        elif 0.4 <= bb_position <= 0.6:  # Middle zone
            score += 5

        return max(0, min(100, score))

    @staticmethod
    def analyze_signals(
        prices: List[float],
        ema20_period: int = 20,
        ema50_period: int = 50,
        rsi_period: int = 14
    ) -> Dict:
        """Analyze current signals from price data with enhanced scoring"""
        if len(prices) < max(ema50_period, rsi_period, 26) + 1:
            return {}

        try:
            # Calculate basic indicators
            ema20 = TechnicalIndicators.calculate_ema(prices, ema20_period)
            ema50 = TechnicalIndicators.calculate_ema(prices, ema50_period)
            rsi = TechnicalIndicators.calculate_rsi(prices, rsi_period)

            # Calculate advanced indicators
            macd_line, macd_signal, macd_hist = TechnicalIndicators.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(prices)

            current_price = prices[-1]
            current_ema20 = ema20[-1] if ema20 else 0
            current_ema50 = ema50[-1] if ema50 else 0
            current_rsi = rsi[-1] if rsi else 0
            current_macd = macd_line[-1] if macd_line else 0
            current_macd_signal = macd_signal[-1] if macd_signal else 0
            current_macd_hist = macd_hist[-1] if macd_hist else 0
            current_bb_upper = bb_upper[-1] if bb_upper else current_price
            current_bb_lower = bb_lower[-1] if bb_lower else current_price

            # Calculate Bollinger position (0-1)
            bb_range = current_bb_upper - current_bb_lower
            bb_position = (current_price - current_bb_lower) / bb_range if bb_range > 0 else 0.5

            # Calculate composite score
            score = TechnicalIndicators.calculate_score(
                ema20=current_ema20,
                ema50=current_ema50,
                rsi=current_rsi,
                macd=current_macd,
                macd_signal=current_macd_signal,
                macd_hist=current_macd_hist,
                bb_position=bb_position
            )

            # Determine signal based on score
            if score >= 65:
                signal = 'BUY'
            elif score <= 35:
                signal = 'SELL'
            else:
                signal = 'HOLD'

            return {
                'current_price': current_price,
                'ema20': round(current_ema20, 2),
                'ema50': round(current_ema50, 2),
                'rsi14': round(current_rsi, 2),
                'macd': round(current_macd, 2),
                'macd_signal': round(current_macd_signal, 2),
                'macd_hist': round(current_macd_hist, 2),
                'bb_upper': round(current_bb_upper, 2),
                'bb_lower': round(current_bb_lower, 2),
                'bb_position': round(bb_position, 3),
                'score': score,
                'signal': signal,
                'ema20_gt_ema50': current_ema20 > current_ema50,
                'rsi_in_buy_zone': 40 <= current_rsi <= 60,
                'macd_bullish': current_macd > current_macd_signal
            }
        except Exception as e:
            logger.error(f"Error analyzing signals: {e}")
            return {}
