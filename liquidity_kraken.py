from base_bot import TradingBot
from config import config

class LiquidityKraken(TradingBot):
    def __init__(self, portfolio, dry_run=True):
        super().__init__(
            name="LiquidityKraken",
            portfolio=portfolio,
            specialization={"min_score": 6.5},
            dry_run=dry_run
        )
        self.tokens = config.get_enabled_tokens()
