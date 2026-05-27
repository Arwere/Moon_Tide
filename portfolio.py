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
    amount: float          # token amount
    sol_amount: float      # SOL spent
    status: str = "OPEN"
    entry_time: str = None

class Portfolio:
    def __init__(self, total_capital_sol: float = 50.0, wallet_manager=None):
        self.total_capital_sol = total_capital_sol
        self.wallet_manager = wallet_manager
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0
        self.last_refresh = None

    async def refresh_capital(self):
        """Update total capital from wallet"""
        if self.wallet_manager:
            try:
                balance = await self.wallet_manager.get_balance()
                if balance > 0:
                    self.total_capital_sol = balance
                    logger.info(f"💰 Portfolio capital updated from wallet: {balance:.4f} SOL")
                self.last_refresh = datetime.now()
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
        logger.info(f"📍 Opened position: {symbol} | {sol_amount:.4f} SOL")

    def close_partial(self, token_key: str, percent: float, current_price: float, reason: str):
        pos = self.get_position(token_key)
        if not pos:
            return

        sold_tokens = pos.amount * percent
        entry_cost = sold_tokens * pos.entry_price
        exit_value = sold_tokens * current_price
        pnl = exit_value - entry_cost

        self.realized_pnl += pnl

        if percent >= 0.99:
            del self.positions[token_key]
            logger.info(f"💰 Closed full position {pos.symbol} | PnL: {pnl:+.4f} SOL | Reason: {reason}")
        else:
            pos.amount -= sold_tokens
            pos.sol_amount -= entry_cost
            logger.info(f"💰 Closed partial {pos.symbol} ({percent*100:.0f}%) | PnL: {pnl:+.4f} SOL")

    def should_exit(self, token_key: str, current_price: float) -> Dict:
        """Improved exit logic"""
        pos = self.get_position(token_key)
        if not pos:
            return {"action": "HOLD", "reason": "No position", "percent": 0.0}

        pnl_pct = ((current_price / pos.entry_price) - 1) * 100

        if pnl_pct <= -20.0:   # Stop loss
            return {"action": "SELL", "reason": f"Stop Loss hit ({pnl_pct:.1f}%)", "percent": 1.0}
        elif pnl_pct >= 50.0:  # Take profit
            return {"action": "SELL", "reason": f"Take Profit hit ({pnl_pct:.1f}%)", "percent": 1.0}

        return {"action": "HOLD", "reason": f"Unrealized PnL: {pnl_pct:+.1f}%", "percent": 0.0}

    def calculate_position_size(self, token_config, current_price: float, suggested_percent: float) -> float:
        """Calculate safe position size in SOL"""
        available = self.total_capital_sol - self.get_deployed_value()
        max_allowed = self.total_capital_sol * 0.25  # Max 25% per position

        target = available * suggested_percent
        return min(target, max_allowed, 2.0)  # Hard cap at 2 SOL per trade for safety

    def get_deployed_value(self) -> float:
        """Current deployed capital (entry cost basis)"""
        return sum(p.sol_amount for p in self.positions.values())

    def get_summary_dict(self) -> Dict:
        deployed = self.get_deployed_value()
        deployed_pct = (deployed / self.total_capital_sol * 100) if self.total_capital_sol > 0 else 0

        return {
            "total_capital": self.total_capital_sol,
            "deployed": deployed,
            "deployed_pct": deployed_pct,
            "realized_pnl": self.realized_pnl,
            "open_positions": len(self.positions),
            "open_positions_summary": ", ".join(self.positions.keys()) or "None"
        }

    def get_summary(self) -> str:
        summary = self.get_summary_dict()
        return (f"🌊 Moon Tide Portfolio | Capital: {summary['total_capital']:.4f} SOL\n"
                f"Deployed: {summary['deployed']:.4f} SOL ({summary['deployed_pct']:.1f}%) | "
                f"Realized PnL: {summary['realized_pnl']:+.4f} SOL | "
                f"Positions: {summary['open_positions']}")
