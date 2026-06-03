import numpy as np
from typing import List, Dict

def calculate_multi_timeframe_indicators(prices: List[float]) -> Dict:
    if len(prices) < 50 or prices[-1] <= 0:
        return {"overall_trend": "neutral", "strength": 0.0, "summary": "Insufficient data"}

    prices = np.array(prices, dtype=float)

    def analyze_tf(data, name):
        if len(data) < 20:
            return {"trend": "neutral", "momentum": 0.0, "volatility": 15.0}

        sma20 = np.mean(data[-20:])
        sma50 = np.mean(data[-50:]) if len(data) >= 50 else sma20

        momentum = (data[-1] / data[-10] - 1) * 100 if len(data) >= 10 else 0.0
        volatility = (np.std(data[-20:]) / np.mean(data[-20:]) * 100) if np.mean(data[-20:]) > 0 else 20.0

        trend = "bullish" if data[-1] > sma20 > sma50 else "bearish" if data[-1] < sma20 < sma50 else "neutral"

        return {
            "trend": trend,
            "momentum": round(momentum, 2),
            "volatility": round(volatility, 2)
        }

    # Different timeframes (assuming ~5min candles)
    tf5m  = analyze_tf(prices[-100:], "5m")
    tf15m = analyze_tf(prices[-300:], "15m")
    tf1h  = analyze_tf(prices[-600:], "1h")
    tf4h  = analyze_tf(prices[-1000:], "4h") if len(prices) >= 1000 else tf1h

    # Overall assessment
    bullish_count = sum(1 for tf in [tf5m, tf15m, tf1h, tf4h] if tf["trend"] == "bullish")
    overall_trend = "strong_bullish" if bullish_count >= 3 else "bullish" if bullish_count >= 2 else "neutral"

    return {
        "overall_trend": overall_trend,
        "tf5m": tf5m,
        "tf15m": tf15m,
        "tf1h": tf1h,
        "tf4h": tf4h,
        "summary": f"{overall_trend.upper()} | 5m:{tf5m['trend']} | 1h:{tf1h['trend']} | 4h:{tf4h['trend']}"
    }
