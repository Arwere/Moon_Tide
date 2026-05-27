from typing import Dict, List
import logging
from config import config
from strategies import TrendStrategy, MomentumStrategy, MeanReversionStrategy, VolatilityStrategy
from claude_brain import claude

logger = logging.getLogger(__name__)

class Poseidon:
    def __init__(self):
        self.strategies = {
            "trend": TrendStrategy(),
            "momentum": MomentumStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "volatility": VolatilityStrategy()
        }
        self.use_claude = True

    async def get_risk_adjusted_decision(self, token_config, market_data: Dict, prices: List[float], 
                                       bot_name: str, portfolio_summary: Dict = None) -> Dict:
        
        if len(prices) < 80:
            return {
                "action": "HOLD", 
                "final_score": 5.0, 
                "suggested_capital_percent": 0.0,
                "recommended_bot": "TideTitan",
                "reason": "Not enough price history"
            }

        technical_score = self._calculate_multi_tf_score(prices)

        # Build context for Claude
        claude_context = {
            "bot_name": bot_name,
            "symbol": token_config.symbol,
            "price": market_data.get("price_sol", 0),
            "liquidity": market_data.get("liquidity_usd", 0),
            "volume_24h": market_data.get("volume_24h", 0),
            "mc": market_data.get("mc", 0),
            "price_change_24h": market_data.get("price_change_24h", 0),
            "technical_summary": self._generate_technical_summary(prices),
            "total_capital": portfolio_summary.get("total_capital", 50.0) if portfolio_summary else 50.0,
            "deployed": portfolio_summary.get("deployed", 0.0) if portfolio_summary else 0.0,
        }

        if self.use_claude:
            try:
                claude_result = await claude.get_decision(claude_context)
                
                final_score = round((technical_score * 0.45) + (claude_result.get("final_score", 5.5) * 0.55), 1)
                
                decision = {
                    "action": claude_result.get("action", "HOLD"),
                    "final_score": final_score,
                    "suggested_capital_percent": claude_result.get("suggested_capital_percent", 0.12),
                    "tp": claude_result.get("tp", 0.15),
                    "sl": claude_result.get("sl", -0.085),
                    "recommended_bot": claude_result.get("recommended_bot", "TideTitan"),
                    "reason": claude_result.get("reason", "Hybrid Analysis")
                }

                return decision

            except Exception as e:
                logger.error(f"Claude failed: {e}")
                return self._technical_fallback(technical_score, bot_name)

        else:
            return self._technical_fallback(technical_score, bot_name)

    def _calculate_multi_tf_score(self, prices: List[float]) -> float:
        default_weights = {"trend": 0.35, "momentum": 0.25, "mean_reversion": 0.20, "volatility": 0.20}
        score = 0.0
        for name, strat in self.strategies.items():
            try:
                result = strat.analyze(prices)
                w = default_weights.get(name, 0.25)
                score += result.get("score", 5.0) * w
            except Exception as e:
                logger.debug(f"Strategy {name} failed: {e}")
        return min(max(round(score, 1), 1.0), 9.9)

    def _generate_technical_summary(self, prices: List[float]) -> str:
        if len(prices) < 60:
            return "Insufficient price history"
        current = prices[-1]
        change_30m = (current / prices[-180] - 1) * 100 if len(prices) > 180 else 0
        volatility = (max(prices[-60:]) - min(prices[-60:])) / current * 100 if current > 0 else 0

        if change_30m > 12: trend = "Strong Bullish"
        elif change_30m > 5: trend = "Bullish"
        elif change_30m < -12: trend = "Strong Bearish"
        elif change_30m < -5: trend = "Bearish"
        else: trend = "Sideways"

        return f"{trend} | 30m: {change_30m:+.1f}% | Vol: {volatility:.1f}%"

    def _technical_fallback(self, technical_score: float, bot_name: str) -> Dict:
        return {
            "action": "BUY" if technical_score >= 6.8 else "HOLD",
            "final_score": round(technical_score, 1),
            "suggested_capital_percent": 0.12,
            "tp": 0.15,
            "sl": -0.085,
            "recommended_bot": "TideTitan",
            "reason": "Technical Rules Only (Claude fallback)"
        }
