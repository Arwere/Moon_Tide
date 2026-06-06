import logging
from typing import Dict
from data_fetcher import get_price_in_sol, get_token_info   # ← Added this
from strategies import (
    calculate_multi_timeframe_indicators,
    TrendStrategy, MomentumStrategy,
    MeanReversionStrategy, VolatilityStrategy
)
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

    async def get_risk_adjusted_decision(self, token_config, market_data: Dict, prices: list, 
                                        bot_name: str, portfolio_summary: Dict) -> Dict:
        try:
            technical = calculate_multi_timeframe_indicators(prices)
            technical_summary = technical.get("summary", "No data")

            # Run technical strategies
            scores = {}
            for name, strategy in self.strategies.items():
                result = strategy.analyze(prices)
                scores[name] = result.get("score", 5.0)

            technical_score = sum(scores.values()) / len(scores)

            # Get current price for Claude context
            current_price = await get_price_in_sol(token_config.address) or 0.0005

            # Build rich context for Claude
            context = {
                "symbol": token_config.symbol,
                "price": current_price,
                "liquidity": market_data.get("liquidity", 0),
                "fdv": market_data.get("fdv", 0),
                "volume_24h": market_data.get("volume_24h", 0),
                "liquidity_ratio": market_data.get("liquidity_ratio", 0),
                "technical_summary": technical_summary,
                "portfolio_summary": str(portfolio_summary)
            }

            claude_decision = await claude.get_decision(context)

            # Blend scores
            final_score = round((technical_score * 0.45) + (claude_decision.get("final_score", 5.5) * 0.55), 1)

            return {
                "action": claude_decision.get("action", "HOLD"),
                "final_score": final_score,
                "suggested_capital_percent": claude_decision.get("suggested_capital_percent", 0.18),
                "recommended_bot": claude_decision.get("recommended_bot", bot_name),
                "reason": claude_decision.get("reason", "No reason provided"),
                "technical_score": round(technical_score, 1),
                "claude_score": claude_decision.get("final_score", 5.5)
            }

        except Exception as e:
            logger.error(f"Poseidon decision error: {e}")
            return {
                "action": "HOLD",
                "final_score": 5.0,
                "suggested_capital_percent": 0.0,
                "recommended_bot": "NONE",
                "reason": "Decision engine error - safe HOLD"
            }
