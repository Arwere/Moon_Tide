from base_bot import TradingBot

class LiquidityKraken(TradingBot):
    """
    LiquidityKraken - Mean Reversion + Volatility Specialist
    Best for tokens that pull back and then rebound.
    """
    def __init__(self, portfolio, dry_run: bool = True):
        specialization = {
            "strategy_weights": {
                "mean_reversion": 0.40,
                "volatility": 0.30,
                "momentum": 0.20,
                "trend": 0.10
            },
            "min_score": 6.3
        }
        super().__init__(
            name="LiquidityKraken",
            portfolio=portfolio,
            specialization=specialization,
            dry_run=dry_run
        )
