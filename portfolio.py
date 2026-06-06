import logging
import time
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
    entry_time: str

class Portfolio:
    def __init__(self, total_capital_sol: float = 50.0):
        self.total_capital_sol = total_capital_sol
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0

    def can_open_new_position(self, token_key: str, liquidity_usd: float, fdv: float) -> bool:
        if token_key in self.positions:
            logger.info(f"Already holding {token_key} — skipping")
            return False

        if len(self.positions) >= 3:
            logger.info("🚫 Max 3 positions reached")
            return False

        # Liquidity check as % of FDV (lowered for meme coins)
        if fdv > 0:
            liq_ratio = (liquidity_usd / fdv) * 100
            if liq_ratio < 7.0:   # Lowered from 20 → allows current tokens
                logger.warning(f"💰 Liquidity low ({liq_ratio:.1f}% of FDV) for {token_key} — blocked")
                return False

        return True

    def calculate_position_size(self, suggested_percent: float = 0.20) -> float:
        available = self.total_capital_sol - self.get_deployed_value()
        size = min(available * suggested_percent, 4.0)
        return max(0.25, size)

    def get_deployed_value(self) -> float:
        return sum(p.sol_amount for p in self.positions.values())

    def open_position(self, token_key: str, symbol: str, entry_price: float, sol_amount: float, token_amount: float):
        self.positions[token_key] = Position(token_key, symbol, entry_price, token_amount, sol_amount, datetime.now().strftime("%H:%M"))
        logger.info(f"📍 OPENED {symbol} | {sol_amount:.3f} SOL")

    def get_position(self, token_key: str) -> Optional[Position]:
        return self.positions.get(token_key)

    def should_exit(self, token_key: str, current_price: float, hours_held: float = 0) -> Dict:
        pos = self.get_position(token_key)
        if not pos:
            return {"action": "HOLD", "reason": "No position", "percent": 0.0}

        pnl_pct = ((current_price / pos.entry_price) - 1) * 100

        if pnl_pct <= -20.0:
            return {"action": "SELL", "reason": "Stop Loss -20%", "percent": 1.0}
        if pnl_pct >= 50.0:
            return {"action": "SELL", "reason": "Take Profit +50%", "percent": 1.0}
        if pnl_pct >= 30.0:
            return {"action": "SELL", "reason": "Partial TP", "percent": 0.6}
        if hours_held > 8 and abs(pnl_pct) < 10:
            return {"action": "SELL", "reason": "Time-based exit", "percent": 1.0}

        return {"action": "HOLD", "reason": f"PnL: {pnl_pct:+.1f}%", "percent": 0.0}

    def get_summary_dict(self) -> Dict:
        return {
            "total_capital": round(self.total_capital_sol, 4),
            "deployed": round(self.get_deployed_value(), 4),
            "open_positions": len(self.positions),
            "positions": list(self.positions.keys())
        }
