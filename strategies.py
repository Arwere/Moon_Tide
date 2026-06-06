import numpy as np
from typing import List, Dict

def calculate_multi_timeframe_indicators(prices: List[float]) -> Dict:
    if len(prices) < 50 or max(prices) == min(prices):
        return {
            "overall_trend": "neutral",
            "strength": 0.0,
            "summary": "⚠️ FLAT / INSUFFICIENT DATA",
            "tf5m": {"trend": "neutral", "momentum": 0.0},
            "tf15m": {"trend": "neutral", "momentum": 0.0},
            "tf1h": {"trend": "neutral", "momentum": 0.0},
            "tf4h": {"trend": "neutral", "momentum": 0.0},
            "tf1d": {"trend": "neutral", "momentum": 0.0},
            "tf4d": {"trend": "neutral", "momentum": 0.0},
            "tf1w": {"trend": "neutral", "momentum": 0.0}
        }

    prices = np.array(prices, dtype=float)
    current = prices[-1]

    def tf_analysis(data, name: str):
        if len(data) < 10:
            return {"trend": "neutral", "momentum": 0.0}
        mom = (data[-1] / data[-min(10, len(data))] - 1) * 100
        sma20 = np.mean(data[-20:]) if len(data) >= 20 else data[-1]
        trend = "bullish" if current > sma20 else "bearish" if current < sma20 else "neutral"
        return {"trend": trend, "momentum": round(mom, 2)}

    # Short-term
    tf5m  = tf_analysis(prices[-120:], "5m")
    tf15m = tf_analysis(prices[-300:], "15m")
    tf1h  = tf_analysis(prices[-600:], "1h")
    tf4h  = tf_analysis(prices[-1200:] if len(prices) >= 1200 else prices[-600:], "4h")

    # Higher timeframes
    tf1d  = tf_analysis(prices[-int(len(prices)*0.2):], "1D")
    tf4d  = tf_analysis(prices[-int(len(prices)*0.45):], "4D")
    tf1w  = tf_analysis(prices[-int(len(prices)*0.75):], "1W")

    trends = [tf5m, tf15m, tf1h, tf4h, tf1d, tf4d, tf1w]
    bullish_count = sum(1 for tf in trends if tf["trend"] == "bullish")
    overall = "strong_bullish" if bullish_count >= 5 else "bullish" if bullish_count >= 4 else "neutral" if bullish_count >= 3 else "bearish"

    summary = f"{overall.upper()} | 1D:{tf1d['trend']}({tf1d['momentum']}%) | 4D:{tf4d['trend']} | 1W:{tf1w['trend']}"

    return {
        "overall_trend": overall,
        "strength": round(bullish_count / 7, 2),
        "summary": summary,
        "tf5m": tf5m, "tf15m": tf15m, "tf1h": tf1h, "tf4h": tf4h,
        "tf1d": tf1d, "tf4d": tf4d, "tf1w": tf1w
    }


class TrendStrategy:
    def analyze(self, prices: List[float]) -> Dict:
        if len(prices) < 100: return {"score": 5.0}
        prices = np.array(prices)
        current = prices[-1]
        sma50 = np.mean(prices[-50:])
        sma200 = np.mean(prices[-200:]) if len(prices) >= 200 else sma50
        score = 8.5 if current > sma200 > sma50 else 3.5 if current < sma200 < sma50 else 5.5
        return {"score": min(max(score, 2.0), 9.9)}

class MomentumStrategy:
    def analyze(self, prices: List[float]) -> Dict:
        if len(prices) < 20: return {"score": 5.0}
        prices = np.array(prices)
        mom = (prices[-1] / prices[-15] - 1) * 100
        score = 5.0 + (mom / 6)
        return {"score": min(max(score, 2.0), 9.9), "momentum": round(mom, 2)}

class MeanReversionStrategy:
    def analyze(self, prices: List[float]) -> Dict:
        if len(prices) < 30: return {"score": 5.0}
        prices = np.array(prices)
        sma = np.mean(prices[-30:])
        std = np.std(prices[-30:]) or 0.0001
        z = (prices[-1] - sma) / std
        score = 7.5 if z < -1.8 else 3.0 if z > 1.8 else 5.0
        return {"score": min(max(score, 2.0), 9.9)}

class VolatilityStrategy:
    def analyze(self, prices: List[float]) -> Dict:
        if len(prices) < 30: return {"score": 5.0}
        prices = np.array(prices)
        vol = np.std(prices[-30:]) / np.mean(prices[-30:]) * 100
        score = 7.5 if vol > 15 else 4.5
        return {"score": min(max(score, 2.0), 9.9)}
