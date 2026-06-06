import time
import logging
from typing import Dict
from data_fetcher import get_price_in_sol, get_token_info, get_historical_prices
from agent import Poseidon
from portfolio import Portfolio
from jupiter_client import jupiter
from telegram_notifier import notifier
from config import config

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, name: str, portfolio: Portfolio, specialization: Dict = None, dry_run: bool = True):
        self.name = name
        self.portfolio = portfolio
        self.jupiter = jupiter
        self.agent = Poseidon()
        self.dry_run = dry_run
        self.specialization = specialization or {"min_score": 6.5}
        
        # Analysis control
        self.last_analysis = {}
        self.score_history = {}           # token_key -> recent scores
        self.analysis_interval = 240      # 4 minutes

    async def tick(self, token_key: str):
        now = time.time()
        if now - self.last_analysis.get(token_key, 0) < self.analysis_interval:
            return
        self.last_analysis[token_key] = now

        try:
            token_config = config.TOKENS[token_key]
            current_price = await get_price_in_sol(token_config.address) or 0.0005

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
            raw_score = decision.get("final_score", 5.0)

            # Score smoothing
            if token_key not in self.score_history:
                self.score_history[token_key] = []
            self.score_history[token_key].append(raw_score)
            if len(self.score_history[token_key]) > 5:
                self.score_history[token_key].pop(0)
            
            avg_score = sum(self.score_history[token_key]) / len(self.score_history[token_key])

            logger.info(f"[{self.name}] {token_config.symbol} | Raw: {raw_score:.1f} → Avg: {avg_score:.1f} | {action}")

            # Send alert
            alert_decision = {**decision, "final_score": round(avg_score, 1), "raw_score": round(raw_score, 1)}
            await notifier.send_claude_decision(self.name, token_config.symbol, alert_decision)

            # === EXECUTION WITH RISK CHECKS ===
            if action == "BUY" and avg_score >= self.specialization.get("min_score", 6.5):
                liquidity = market_data.get("liquidity", 0)
                fdv = market_data.get("fdv", 0)
                
                # Pass token_key for per-token logic
                if not self.portfolio.can_open_new_position(token_key, liquidity, fdv):
                    return
                
                await self._execute_buy(token_key, decision, current_price)

            elif action == "SELL":
                await self._execute_sell(token_key, decision, current_price)

        except Exception as e:
            logger.error(f"[{self.name}] Error on {token_key}: {e}")

    async def _execute_buy(self, token_key: str, decision: Dict, current_price: float):
        if self.portfolio.get_position(token_key):
            logger.info(f"[{self.name}] Already holding {token_key} — skipping")
            return

        token_config = config.TOKENS[token_key]
        sol_amount = self.portfolio.calculate_position_size(decision.get("suggested_capital_percent", 0.20))

        if sol_amount < 0.25:
            logger.info(f"[{self.name}] Position too small ({sol_amount:.3f} SOL)")
            return

        logger.info(f"[{self.name}] 🚀 EXECUTING BUY → {token_config.symbol} | {sol_amount:.3f} SOL (Dry: {self.dry_run})")

        result = await self.jupiter.execute_swap(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint=token_config.address,
            amount=sol_amount,
            dry_run=self.dry_run
        )

        if result.get("success"):
            token_amount = sol_amount / current_price
            self.portfolio.open_position(token_key, token_config.symbol, current_price, sol_amount, token_amount)
            await notifier.send_trade_alert(
                self.name, "BUY", token_config.symbol,
                decision.get("final_score", 0), sol_amount, current_price, decision.get("reason", "")
            )

    async def _execute_sell(self, token_key: str, decision: Dict, current_price: float):
        pos = self.portfolio.get_position(token_key)
        if not pos:
            return

        exit_info = self.portfolio.should_exit(token_key, current_price)
        if exit_info["action"] == "SELL":
            percent = exit_info.get("percent", 1.0)
            self.portfolio.close_partial(token_key, percent, current_price, exit_info["reason"])
            await notifier.send_trade_alert(
                self.name, "SELL", pos.symbol,
                decision.get("final_score", 0), pos.sol_amount * percent,
                current_price, exit_info["reason"]
            )
