import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    amount: float
    entry_price: float
    entry_time: float
    status: str = "OPEN"

class Portfolio:
    def __init__(self, total_capital_sol: float = 50.0, wallet_manager=None):
        self.total_capital_sol = total_capital_sol
        self.wallet_manager = wallet_manager
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0

    async def refresh_capital(self):
        """Refresh balance from wallet"""
        try:
            if self.wallet_manager:
                balance = await self.wallet_manager.get_balance()
                self.total_capital_sol = balance
                print(f"💰 Portfolio capital updated from wallet: {self.total_capital_sol:.4f} SOL")
        except Exception as e:
            print(f"Portfolio refresh error: {e}")

    def get_summary(self) -> str:
        deployed = sum(p.amount * p.entry_price for p in self.positions.values() if p.status == "OPEN")
        deployed_pct = (deployed / self.total_capital_sol * 100) if self.total_capital_sol > 0 else 0
        return f"🌊 Moon Tide Portfolio | Capital: {self.total_capital_sol:.4f} SOL\n" \
               f"Deployed: {deployed:.4f} SOL ({deployed_pct:.1f}%) | Realized PnL: +{self.realized_pnl:.4f} SOL"

    def get_summary_dict(self) -> Dict:
        deployed = sum(p.amount * p.entry_price for p in self.positions.values() if p.status == "OPEN")
        deployed_pct = (deployed / self.total_capital_sol * 100) if self.total_capital_sol > 0 else 0
        return {
            "total_capital": self.total_capital_sol,
            "deployed": deployed,
            "deployed_pct": deployed_pct,
            "open_positions_summary": f"{len([p for p in self.positions.values() if p.status == 'OPEN'])} open"
        }

    def open_position(self, token_key: str, symbol: str, entry_price: float, sol_amount: float, token_amount: float) -> bool:
        self.positions[token_key] = Position(
            symbol=symbol, 
            amount=token_amount, 
            entry_price=entry_price, 
            entry_time=time.time()
        )
        return True

    def get_position(self, token_key: str) -> Optional[Position]:
        return self.positions.get(token_key)

    def close_partial(self, token_key: str, percent: float, current_price: float, reason: str):
        if token_key in self.positions:
            pos = self.positions[token_key]
            sold_amount = pos.amount * percent
            pnl = sold_amount * (current_price - pos.entry_price)
            self.realized_pnl += pnl
            pos.amount *= (1 - percent)
            if pos.amount < 0.0001:
                pos.status = "CLOSED"
            print(f"Closed {percent*100:.0f}% of {pos.symbol} | PnL: {pnl:.4f} SOL")

    def should_exit(self, token_key: str, current_price: float) -> Dict:
        pos = self.get_position(token_key)
        if not pos or pos.status != "OPEN":
            return {"action": "HOLD", "reason": "No position"}
        # TODO: Add real stop-loss / take-profit logic later
        return {"action": "HOLD", "reason": "No exit signal yet"}
