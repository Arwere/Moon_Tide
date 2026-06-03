import time
import logging
from typing import Dict
from data_fetcher import get_price_in_sol, get_token_info, get_historical_prices
from agent import Poseidon
from portfolio import Portfolio
from jupiter_client import JupiterClient
from telegram_notifier import notifier
from config import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')

class TradingBot:
    def __init__(self, name: str, portfolio: Portfolio, specialization: Dict = None, dry_run: bool = True):
        self.name = name
        self.portfolio = portfolio
        self.jupiter = JupiterClient()
        self.agent = Poseidon()
        self.dry_run = dry_run
        self.specialization = specialization or {"min_score": 6.0}
        self.last_analysis = 0

    async def tick(self, token_key: str):
        if time.time() - self.last_analysis < 25:   # Analysis every 25 seconds
            return
        self.last_analysis = time.time()

        try:
            token_config = config.TOKENS[token_key]
            current_price = await get_price_in_sol(token_config.address)
            if current_price is None or current_price <= 0:
                return

            logger.info(f"[{self.name}] Analyzing {token_config.symbol} @ {current_price:.8f} SOL")

            market_data = await get_token_info(token_config.address)
            prices = await get_historical_prices(token_config.address)

            decision = await self.agent.get_risk_adjusted_decision(
                token_config=token_config,
                market_data=market_data,
                prices=prices,
                bot_name=self.name,
                portfolio_summary=self.portfolio.get_summary_dict()
            )

            action = decision.get("action", "HOLD")
            score = decision.get("final_score", 5.0)
            recommended = decision.get("recommended_bot", "None")

            logger.info(f"[{self.name}] {token_config.symbol} → {action} | Score: {score:.1f} | Rec: {recommended}")

            # Send to Telegram more often for testing
            await notifier.send_claude_decision(self.name, token_config.symbol, decision)

        except Exception as e:
            logger.error(f"[{self.name}] Error on {token_key}: {e}")
