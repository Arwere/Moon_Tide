from typing import Dict, List, Any
from config import config
from strategies import TrendStrategy, MomentumStrategy, MeanReversionStrategy, VolatilityStrategy
from risk_manager import RiskManager
from claude_brain import claude

class Poseidon:
    def __init__(self):
        self.strategies = {
            "trend": TrendStrategy(),
            "momentum": MomentumStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "volatility": VolatilityStrategy()
        }
        self.risk_manager = RiskManager()
        self.use_claude = True

    async def get_risk_adjusted_decision(self, token_config, market_data: Dict, prices: List[float], 
                                       bot_name: str, portfolio_summary: Dict = None, 
                                       specialization: Dict = None) -> Dict:
        
        if len(prices) < 80:
            return {"action": "HOLD", "final_score": 5.0, "suggested_capital_percent": 0.0, 
                    "reason": "Not enough price history"}

        specialization = specialization or {}
        technical_score = self._calculate_multi_tf_score(prices, specialization.get("strategy_weights"))

        claude_context = {
            "bot_name": bot_name,
            "symbol": token_config.symbol,
            "price": market_data.get("price_sol", 0),
            "liquidity": market_data.get("liquidity", 0),
            "volume_24h": market_data.get("volume_24h", 0),
            "mc": market_data.get("mc", 0),
            "price_change_24h": market_data.get("price_change_24h", 0),
            "technical_summary": self._generate_technical_summary(prices),
            "total_capital": portfolio_summary.get("total_capital", 50.0) if portfolio_summary else 50.0,
            "deployed": portfolio_summary.get("deployed", 0.0) if portfolio_summary else 0.0,
            "deployed_pct": portfolio_summary.get("deployed_pct", 0.0) if portfolio_summary else 0.0,
            "open_positions_summary": portfolio_summary.get("open_positions_summary", "None") if portfolio_summary else "None",
        }

        if self.use_claude:
            claude_result = await claude.get_decision(claude_context)
            final_score = round((technical_score * 0.48) + (claude_result.get("final_score", 5.5) * 0.52), 1)

            return {
                "action": claude_result.get("action", "HOLD"),
                "final_score": final_score,
                "suggested_capital_percent": claude_result.get("suggested_capital_percent", 0.12),
                "tp": claude_result.get("tp", 0.15),
                "sl": claude_result.get("sl", -0.085),
                "bot_name": bot_name,
                "reason": claude_result.get("reason", "Hybrid Analysis")
            }
        else:
            return {
                "action": "BUY" if technical_score >= 6.8 else "HOLD",
                "final_score": round(technical_score, 1),
                "suggested_capital_percent": 0.12,
                "tp": 0.15,
                "sl": -0.085,
                "bot_name": bot_name,
                "reason": "Technical Rules Only"
            }

    def _calculate_multi_tf_score(self, prices: List[float], weights_override: Dict = None) -> float:
        default_weights = {"trend": 0.35, "momentum": 0.25, "mean_reversion": 0.20, "volatility": 0.20}
        weights = weights_override or default_weights
        score = 0.0
        for name, strat in self.strategies.items():
            w = weights.get(name, 0.25)
            score += strat.analyze(prices).get("score", 5.0) * w
        return min(score, 9.9)

    def _generate_technical_summary(self, prices: List[float]) -> str:
        if len(prices) < 60:
            return "Insufficient price history"

        current = prices[-1]
        change_5m = (current / prices[-30] - 1) * 100 if len(prices) > 30 else 0
        change_15m = (current / prices[-90] - 1) * 100 if len(prices) > 90 else 0
        change_30m = (current / prices[-180] - 1) * 100 if len(prices) > 180 else 0

        volatility = (max(prices[-60:]) - min(prices[-60:])) / current * 100 if current > 0 else 0
        momentum = (current - prices[-120]) / prices[-120] * 100 if len(prices) > 120 else 0

        if change_30m > 12: trend = "Strong Bullish Breakout"
        elif change_30m > 5: trend = "Bullish"
        elif change_30m < -12: trend = "Strong Bearish"
        elif change_30m < -5: trend = "Bearish"
        else: trend = "Sideways"

        return (f"{trend} | 5m: {change_5m:+.1f}% | 15m: {change_15m:+.1f}% | 30m: {change_30m:+.1f}% | "
                f"Vol: {volatility:.1f}% | Momentum: {momentum:+.1f}%")
