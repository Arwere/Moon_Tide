from base_bot import TradingBot

class TideTitan(TradingBot):
    """Trend + Momentum Specialist"""
    def __init__(self, token_key: str, portfolio, dry_run: bool = True):
        specialization = {
            "strategy_weights": {"trend": 0.45, "momentum": 0.30, "mean_reversion": 0.10, "volatility": 0.15},
            "min_score": 6.8
        }
        super().__init__(
            name="TideTitan",
            portfolio=portfolio,
            specialization=specialization,
            dry_run=dry_run
        )
