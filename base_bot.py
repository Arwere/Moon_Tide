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

class TradingBot:
    def __init__(self, name: str, portfolio: Portfolio, specialization: Dict = None, dry_run: bool = True):
        self.name = name
        self.portfolio = portfolio
        self.jupiter = JupiterClient()
        self.agent = Poseidon()
        self.dry_run = dry_run
        self.specialization = specialization or {"min_score": 6.5}
        self.cooldown_until = 0
        self.last_log = 0

    async def tick(self, token_key: str):
        if time.time() < self.cooldown_until:
            return

        try:
            token_config = config.TOKENS[token_key]
            current_price = await get_price_in_sol(token_config.address)
            if current_price is None or current_price <= 0:
                return

            market_data = await get_token_info(token_config.address)
            market_data["price_sol"] = current_price
            prices = await get_historical_prices(token_config.address, limit=400)

            portfolio_summary = self.portfolio.get_summary_dict()

            decision = await self.agent.get_risk_adjusted_decision(
                token_config=token_config,
                market_data=market_data,
                prices=prices,
                bot_name=self.name,
                portfolio_summary=portfolio_summary
            )

            action = decision.get("action", "HOLD")
            score = decision.get("final_score", 5.0)
            recommended_bot = decision.get("recommended_bot", "TideTitan")

            # === Only log/send high-conviction decisions ===
            now = time.time()
            if score >= 6.5 or action in ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL"]:
                if now - self.last_log > 15:   # Max 1 log every 15 seconds
                    await notifier.send_claude_decision(self.name, token_config.symbol, decision)
                    self.last_log = now

            if recommended_bot != self.name:
                return

            # ENTRY
            if action in ["BUY", "STRONG_BUY"] and score >= self.specialization.get("min_score", 6.5):
                if not self.portfolio.get_position(token_key):
                    await self._execute_entry(token_key, decision, current_price)

            # EXIT
            exit_signal = self.portfolio.should_exit(token_key, current_price)
            if action in ["SELL", "STRONG_SELL"] or exit_signal.get("action") == "SELL":
                pos = self.portfolio.get_position(token_key)
                if pos:
                    await self._execute_exit(token_key, 1.0, current_price, decision.get("reason", "Signal"))

        except Exception as e:
            logger.error(f"[{self.name}] Error on {token_key}: {e}", exc_info=False)

    async def _execute_entry(self, token_key: str, decision: Dict, current_price: float):
        token_config = config.TOKENS[token_key]
        
        sol_amount = self.portfolio.calculate_position_size(
            token_config, 
            current_price,
            decision.get("suggested_capital_percent", 0.12)
        )

        if sol_amount < 0.05:
            return

        logger.info(f"[{self.name}] 🟢 OPENING {token_config.symbol} | {sol_amount:.4f} SOL")

        try:
            await notifier.send_trade_alert(
                bot_name=self.name, action="BUY", symbol=token_config.symbol,
                score=decision.get("final_score", 0), sol_amount=sol_amount,
                price=current_price, reason=decision.get("reason", "")
            )

            if not self.dry_run:
                await self.jupiter.execute_swap(
                    input_mint="So11111111111111111111111111111111111111112",
                    output_mint=token_config.address,
                    amount=sol_amount,
                    dry_run=False
                )

            token_amount = sol_amount / current_price if current_price > 0 else 0
            self.portfolio.open_position(
                token_key=token_key,
                symbol=token_config.symbol,
                entry_price=current_price,
                sol_amount=sol_amount,
                token_amount=token_amount
            )
            self.cooldown_until = time.time() + 180

        except Exception as e:
            logger.error(f"[{self.name}] Entry failed: {e}")

    async def _execute_exit(self, token_key: str, percent: float, current_price: float, reason: str):
        pos = self.portfolio.get_position(token_key)
        if not pos: return
        token_config = config.TOKENS[token_key]

        logger.info(f"[{self.name}] 🔴 CLOSING {token_config.symbol} | {reason}")

        try:
            await notifier.send_trade_alert(
                bot_name=self.name, action="SELL", symbol=token_config.symbol,
                score=0.0, sol_amount=0.0, price=current_price, reason=reason
            )

            if not self.dry_run:
                await self.jupiter.execute_swap(
                    input_mint=token_config.address,
                    output_mint="So11111111111111111111111111111111111111112",
                    amount=pos.amount * percent,
                    dry_run=False
                )

            self.portfolio.close_partial(token_key, percent, current_price, reason)
            if percent >= 0.95:
                self.cooldown_until = time.time() + 300
        except Exception as e:
            logger.error(f"[{self.name}] Exit failed: {e}")
