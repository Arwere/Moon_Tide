import asyncio
import time
from agent import Poseidon
from data_fetcher import fetcher, get_price_in_sol, get_historical_prices
from telegram_notifier import notifier
from config import config
from portfolio import Portfolio
from jupiter_client import JupiterClient

class TideTitan:
    def __init__(self, token_key: str, portfolio: Portfolio, 
                 jupiter: JupiterClient, dry_run: bool = True):
        self.token_key = token_key
        self.token_config = config.TOKENS[token_key]
        self.agent = Poseidon()
        self.portfolio = portfolio
        self.jupiter = jupiter
        self.dry_run = dry_run
        self.cooldown_until = 0
        self.last_price = 0.0

    async def tick(self):
        try:
            current_price = await get_price_in_sol(self.token_config.address)
            if current_price is None or current_price <= 0:
                return

            self.last_price = current_price
            prices = await get_historical_prices(self.token_config.address, limit=400)

            decision = await self.agent.get_risk_adjusted_decision(
                self.token_config, 
                {"price_sol": current_price}, 
                prices, 
                bot_name="TideTitan"
            )

            # Rest of your logic stays exactly the same...
            # (I only changed token_config access)
            action = decision.get("action", "HOLD")
            score = decision.get("final_score", 0.0)

            if score >= 5.5 or action != "HOLD":
                print(f"[TIDE TITAN - {self.token_config.symbol}] Price: {current_price:.8f} | Score: {score:.1f} | Action: {action}")

            # ... (your full exit/entry logic remains unchanged)
            
        except Exception as e:
            print(f"[TIDE TITAN - {self.token_config.symbol}] Error: {e}")
