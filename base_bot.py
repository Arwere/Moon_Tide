import time
import logging
from typing import Dict, Optional
from data_fetcher import get_price_in_sol, get_token_info, get_historical_prices
from agent import Poseidon
from portfolio import Portfolio
from jupiter_client import jupiter
from telegram_notifier import notifier

logger = logging.getLogger(__name__)

class TradingBot:
    """
    Base class for all specialized trading bots.
    Eliminates ~80% duplication across TideTitan, DepthDestroyer, and LiquidityKraken.
    """
    
    def __init__(self, 
                 token_key: str, 
                 portfolio: Portfolio, 
                 specialization: Dict,
                 dry_run: bool = True):
        
        self.token_key = token_key
        self.config = config.TOKENS[token_key]  # from your config.py
        self.portfolio = portfolio
        self.jupiter = jupiter
        self.agent = Poseidon()
        self.dry_run = dry_run
        self.specialization = specialization
        self.cooldown_until = 0
        self.last_tick = 0
        self.name = self.__class__.__name__

    async def tick(self):
        """Main trading loop - shared logic for all bots"""
        if time.time() < self.cooldown_until:
            return

        try:
            current_price = await get_price_in_sol(self.config.address)
            if current_price is None or current_price <= 0:
                logger.warning(f"[{self.name}] Invalid price for {self.config.symbol}")
                return

            # Get market data
            market_data = await get_token_info(self.config.address)
            market_data["price_sol"] = current_price

            # Get historical prices for TA
            prices = await get_historical_prices(self.config.address, limit=400)

            # Portfolio summary
            portfolio_summary = self.portfolio.get_summary_dict()

            # Get decision from Poseidon
            decision = await self.agent.get_risk_adjusted_decision(
                token_config=self.config,
                market_data=market_data,
                prices=prices,
                bot_name=self.name,
                portfolio_summary=portfolio_summary,
                specialization=self.specialization
            )

            action = decision.get("action", "HOLD")
            score = decision.get("final_score", 5.0)

            # === ENTRY LOGIC ===
            if action in ["BUY", "STRONG_BUY"] and score >= self.specialization.get("min_score", 6.5):
                if not self.portfolio.get_position(self.token_key):
                    await self._execute_entry(decision, current_price)

            # === EXIT LOGIC ===
            elif action in ["SELL", "STRONG_SELL"] or self.portfolio.should_exit(self.token_key, current_price):
                pos = self.portfolio.get_position(self.token_key)
                if pos:
                    await self._execute_exit(1.0, current_price, decision.get("reason", "Signal"))

            self.last_tick = time.time()

        except Exception as e:
            logger.error(f"[{self.name}] Tick error: {e}", exc_info=True)

    async def _execute_entry(self, decision: Dict, current_price: float):
        """Execute buy"""
        sol_amount = self.portfolio.calculate_position_size(
            self.token_key, 
            decision.get("suggested_capital_percent", 0.12)
        )

        if sol_amount < 0.05:  # minimum size
            return

        try:
            await notifier.send_trade_alert(
                bot_name=self.name,
                action="BUY",
                symbol=self.config.symbol,
                score=decision.get("final_score"),
                sol_amount=sol_amount,
                price=current_price,
                reason=decision.get("reason", "")
            )

            if not self.dry_run:
                await self.jupiter.execute_swap(
                    input_mint="So11111111111111111111111111111111111111112",  # SOL
                    output_mint=self.config.address,
                    amount=sol_amount,
                    dry_run=False
                )

            self.portfolio.open_position(
                token_key=self.token_key,
                entry_price=current_price,
                sol_amount=sol_amount,
                reason=decision.get("reason", "")
            )

            self.cooldown_until = time.time() + 180  # 3 min cooldown after entry

        except Exception as e:
            logger.error(f"[{self.name}] Entry failed: {e}")

    async def _execute_exit(self, percent: float, current_price: float, reason: str):
        """Execute sell"""
        pos = self.portfolio.get_position(self.token_key)
        if not pos:
            return

        try:
            await notifier.send_trade_alert(
                bot_name=self.name,
                action="SELL",
                symbol=self.config.symbol,
                score=0.0,
                sol_amount=0.0,
                price=current_price,
                reason=reason
            )

            if not self.dry_run:
                # Approximate SOL received (real would be from Jupiter response)
                sell_sol_approx = (pos.amount * percent) * current_price * 0.98  # 2% slippage buffer
                await self.jupiter.execute_swap(
                    input_mint=self.config.address,
                    output_mint="So11111111111111111111111111111111111111112",  # SOL
                    amount=pos.amount * percent,
                    dry_run=False
                )

            self.portfolio.close_partial(self.token_key, percent, current_price, reason)

            if percent >= 0.95:
                self.cooldown_until = time.time() + 300  # 5 min cooldown after full exit

        except Exception as e:
            logger.error(f"[{self.name}] Exit failed: {e}")
