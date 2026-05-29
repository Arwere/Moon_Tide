import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Position:
    token_key: str
    symbol: str
    entry_price: float
    amount: float
    sol_amount: float
    status: str = "OPEN"
    entry_time: str = None

class Portfolio:
    def __init__(self, total_capital_sol: float = 50.0, wallet_manager=None):
        self.total_capital_sol = total_capital_sol
        self.wallet_manager = wallet_manager
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0

    async def refresh_capital(self):
        if self.wallet_manager:
            try:
                balance = await self.wallet_manager.get_balance()
                if balance > 0:
                    self.total_capital_sol = balance
                    logger.info(f"💰 Portfolio capital updated: {balance:.4f} SOL")
            except Exception as e:
                logger.warning(f"Wallet refresh failed: {e}")

    def get_position(self, token_key: str) -> Optional[Position]:
        return self.positions.get(token_key)

    def open_position(self, token_key: str, symbol: str, entry_price: float, 
                     sol_amount: float, token_amount: float):
        self.positions[token_key] = Position(
            token_key=token_key,
            symbol=symbol,
            entry_price=entry_price,
            amount=token_amount,
            sol_amount=sol_amount,
            entry_time=datetime.now().strftime("%H:%M")
        )

    def close_partial(self, token_key: str, percent: float, current_price: float, reason: str):
        pos = self.get_position(token_key)
        if not pos:
            return
        sold_tokens = pos.amount * percent
        entry_cost = sold_tokens * pos.entry_price
        exit_value = sold_tokens * current_price
        pnl = exit_value - entry_cost
        self.realized_pnl += pnl

        if percent >= 0.95:
            del self.positions[token_key]
        else:
            pos.amount -= sold_tokens

    def should_exit(self, token_key: str, current_price: float) -> Dict:
        pos = self.get_position(token_key)
        if not pos:
            return {"action": "HOLD", "reason": "No position", "percent": 0.0}

        pnl_pct = ((current_price / pos.entry_price) - 1) * 100

        if pnl_pct <= -20.0:
            return {"action": "SELL", "reason": f"Stop Loss hit", "percent": 1.0}
        elif pnl_pct >= 50.0:
            return {"action": "SELL", "reason": f"Take Profit hit", "percent": 1.0}

        return {"action": "HOLD", "reason": f"PnL: {pnl_pct:+.1f}%", "percent": 0.0}

    def calculate_position_size(self, token_config, current_price: float, suggested_percent: float) -> float:
        available = self.total_capital_sol - self.get_deployed_value()
        return min(available * suggested_percent, self.total_capital_sol * 0.25, 2.0)

    def get_deployed_value(self) -> float:
        return sum(p.sol_amount for p in self.positions.values())

    def get_summary_dict(self) -> Dict:                     # ← Added this method
        deployed = self.get_deployed_value()
        deployed_pct = (deployed / self.total_capital_sol * 100) if self.total_capital_sol > 0 else 0
        return {
            "total_capital": self.total_capital_sol,
            "deployed": deployed,
            "deployed_pct": deployed_pct,
            "realized_pnl": self.realized_pnl,
            "open_positions": len(self.positions)
        }

    def get_summary(self) -> str:
        s = self.get_summary_dict()
        return f"🌊 Portfolio | Capital: {s['total_capital']:.4f} | Deployed: {s['deployed']:.4f} ({s['deployed_pct']:.1f}%) | PnL: {s['realized_pnl']:+.4f}"


# Global instance (optional)
portfolio = Portfolio()
