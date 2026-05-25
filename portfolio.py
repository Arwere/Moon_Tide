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
        self.trades = []  # For future stats tracking

    async def refresh_capital(self):
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

    def should_exit(self, token_key: str, current_price: float) -> Dict:
        """Proper risk-managed exit logic"""
        pos = self.get_position(token_key)
        if not pos or pos.status != "OPEN":
            return {"action": "HOLD", "reason": "No position", "percent": 0.0}

        pnl_pct = (current_price / pos.entry_price - 1) * 100
        hours_held = (time.time() - pos.entry_time) / 3600

        # Get token config for SL/TP levels
        from config import config
        token_config = config.get_token_by_symbol(pos.symbol) or config.TOKENS.get(token_key)

        # === HARD STOP LOSS ===
        if pnl_pct <= -token_config.stop_loss_pct:
            return {
                "action": "SELL",
                "percent": 1.0,
                "reason": f"STOP-LOSS HIT (-{pnl_pct:.1f}%)"
            }

        # === TAKE PROFIT (Scaled) ===
        if pnl_pct >= token_config.take_profit_pct:
            return {
                "action": "SELL",
                "percent": 1.0,
                "reason": f"Full Take-Profit (+{pnl_pct:.1f}%)"
            }

        if pnl_pct >= token_config.take_profit_pct * 0.6:   # 60% of target
            return {
                "action": "SELL",
                "percent": 0.5,
                "reason": f"Scale-out TP (+{pnl_pct:.1f}%)"
            }

        # === TIME-BASED EXIT ===
        if hours_held > 24 and pnl_pct < 5:   # 24 hours with weak performance
            return {
                "action": "SELL",
                "percent": 1.0,
                "reason": f"Time decay exit ({hours_held:.1f}h, P/L: {pnl_pct:.1f}%)"
            }

        if hours_held > 12 and pnl_pct < -8:
            return {
                "action": "SELL",
                "percent": 1.0,
                "reason": f"Stale losing position ({hours_held:.1f}h)"
            }

        return {"action": "HOLD", "reason": f"No exit signal | PnL: {pnl_pct:+.1f}% | Held: {hours_held:.1f}h", "percent": 0.0}

    def close_partial(self, token_key: str, percent: float, current_price: float, reason: str):
        pos = self.get_position(token_key)
        if not pos:
            return

        sold_amount = pos.amount * percent
        pnl = sold_amount * (current_price - pos.entry_price)
        self.realized_pnl += pnl

        pos.amount *= (1 - percent)
        if pos.amount < 0.0001:
            pos.status = "CLOSED"

        print(f"Closed {percent*100:.0f}% of {pos.symbol} | PnL: {pnl:+.4f} SOL | Reason: {reason}")

# Global instance will be created in master.py
