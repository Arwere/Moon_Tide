from base_bot import TradingBot

class DepthDestroyer(TradingBot):
    """
    DepthDestroyer - Volatility + Momentum Specialist
    Best for explosive, high-volatility moves.
    """
    def __init__(self, portfolio, dry_run: bool = True):
        specialization = {
            "strategy_weights": {
                "volatility": 0.40,
                "momentum": 0.35,
                "trend": 0.15,
                "mean_reversion": 0.10
            },
            "min_score": 6.5
        }
        super().__init__(
            name="DepthDestroyer",
            portfolio=portfolio,
            specialization=specialization,
            dry_run=dry_run
        )
