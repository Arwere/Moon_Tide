import asyncio
import time
from agent import Poseidon
from data_fetcher import get_price_in_sol, get_historical_prices, fetcher
from telegram_notifier import notifier
from config import config
from portfolio import Portfolio
from jupiter_client import JupiterClient

class LiquidityKraken:
    def __init__(self, token_key: str, portfolio: Portfolio, jupiter: JupiterClient, dry_run: bool = True):
        self.token_key = token_key
        self.config = config.TOKENS[token_key]
        self.agent = Poseidon()
        self.portfolio = portfolio
        self.jupiter = jupiter
        self.dry_run = dry_run
        self.cooldown_until = 0

        self.specialization = {
            "strategy_weights": {"mean_reversion": 0.50, "volatility": 0.20, "trend": 0.15, "momentum": 0.15},
            "min_score": 6.7
        }

    async def tick(self):
        try:
            current_price = await get_price_in_sol(self.config.address)
            if current_price is None or current_price <= 0:
                return

            prices = await get_historical_prices(self.config.address, limit=400)
            token_info = await fetcher.get_token_info(self.config.address)
            portfolio_summary = self._get_portfolio_summary()

            decision = await self.agent.get_risk_adjusted_decision(
                self.config,
                {
                    "price_sol": current_price,
                    "liquidity": token_info.get("liquidity_usd", 0),
                    "volume_24h": token_info.get("volume_24h", 0)
                },
                prices,
                bot_name="LiquidityKraken",
                portfolio_summary=portfolio_summary,
                specialization=self.specialization
            )

            action = decision.get("action", "HOLD")
            score = decision.get("final_score", 5.0)

            if score >= 5.5 or action != "HOLD":
                print(f"[🐙 LIQUIDITY KRAKEN - {self.config.symbol}] Price: {current_price:.8f} | Score: {score:.1f} | Action: {action}")

            if time.time() < self.cooldown_until:
                return

            # === EXIT LOGIC ===
            exit_signal = self.portfolio.should_exit(self.token_key, current_price)
            if exit_signal["action"] == "SELL":
                percent = exit_signal.get("percent", 1.0)
                reason = exit_signal["reason"]
                print(f"🛑 LIQUIDITY KRAKEN EXIT → {self.config.symbol} | {reason}")
                await self._execute_exit(percent, current_price, reason)
                self.cooldown_until = time.time() + 420
                return

            # === ENTRY LOGIC ===
            if (action in ["BUY", "STRONG_BUY"] and score >= self.specialization["min_score"] and
                not self.portfolio.get_position(self.token_key)):
                
                suggested_sol = min(decision.get("suggested_capital_percent", 0.12) * 7.0, 2.2)
                if suggested_sol < 0.06:
                    return

                token_amount = suggested_sol / current_price
                if self.portfolio.open_position(self.token_key, self.config.symbol, current_price, suggested_sol, token_amount):
                    await notifier.send_trade_alert(
                        "LiquidityKraken", "BUY", self.config.symbol, score, suggested_sol, current_price, 
                        decision.get("reason", "")
                    )
                    await self.jupiter.execute_swap(
                        "So11111111111111111111111111111111111111112", 
                        self.config.address, suggested_sol, dry_run=self.dry_run
                    )
                    self.cooldown_until = time.time() + 1800   # Longer cooldown for mean-reversion style

        except Exception as e:
            print(f"[LIQUIDITY KRAKEN - {self.config.symbol}] Error: {e}")

    def _get_portfolio_summary(self):
        try:
            if hasattr(self.portfolio, 'get_summary_dict'):
                return self.portfolio.get_summary_dict()
            return {"total_capital": 50.0, "deployed": 0.0, "deployed_pct": 0.0, "open_positions_summary": "None"}
        except:
            return {"total_capital": 50.0, "deployed": 0.0, "deployed_pct": 0.0, "open_positions_summary": "None"}

    async def _execute_exit(self, percent: float, current_price: float, reason: str):
        pos = self.portfolio.get_position(self.token_key)
        if not pos: return
        self.portfolio.close_partial(self.token_key, percent, current_price, reason)
        sell_sol_approx = (pos.amount * percent) * current_price
        await self.jupiter.execute_swap(
            self.config.address, 
            "So11111111111111111111111111111111111111112", 
            sell_sol_approx, 
            dry_run=self.dry_run
        )
