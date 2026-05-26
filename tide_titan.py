from base_bot import TradingBot

class TideTitan(TradingBot):
    """
    TideTitan - Trend + Momentum Specialist
    Best for strong trending tokens with good momentum.
    """
    def __init__(self, portfolio, dry_run: bool = True):
        # You can override specialization here if you want, but we recommend using config.py
        specialization = {
            "strategy_weights": {
                "trend": 0.45,
                "momentum": 0.30,
                "mean_reversion": 0.10,
                "volatility": 0.15
            },
            "min_score": 6.8
        }
        super().__init__(
            name="TideTitan",
            portfolio=portfolio,
            specialization=specialization,
            dry_run=dry_run
        )
