import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TokenConfig:
    address: str
    symbol: str
    enabled: bool = True
    max_position_size_usd: float = 150.0
    stop_loss_pct: float = 20.0
    take_profit_pct: float = 60.0

class Config:
    def __init__(self):
        self.RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        self.WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
        self.BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

        # === ALL TOKENS DEFINED HERE ONLY ===
        self.TOKENS: Dict[str, TokenConfig] = {
            "MM": TokenConfig(
                address="Ax8PSfCXxmxb8C8kYTzN5CPpTe6PyeZfFf8rrXNCjupx",
                symbol="MM",
                enabled=True,
                max_position_size_usd=150.0,
                stop_loss_pct=20.0,
                take_profit_pct=60.0,
            ),
            "WHITEWHALE": TokenConfig(
                address="a3W4qutoEJA4232T2gwZUfgYJTetr96pU4SJMwppump",
                symbol="WHITEWHALE",
                enabled=True,
            ),
            "TROLL": TokenConfig(
                address="5UUH9RTDiSpq6HKS6bp4NdU9PNJpXRXuiw6ShBTBhgH2",
                symbol="TROLL",
                enabled=True,
            ),
            # Add new tokens here easily:
            # "NEWONE": TokenConfig(address="...", symbol="NEW", enabled=False),
        }

    def get_enabled_tokens(self) -> List[TokenConfig]:
        return [t for t in self.TOKENS.values() if t.enabled]

    def get_token_by_address(self, address: str) -> Optional[TokenConfig]:
        for token in self.TOKENS.values():
            if token.address.lower() == address.lower():
                return token
        return None

    def get_token_by_symbol(self, symbol: str) -> Optional[TokenConfig]:
        return self.TOKENS.get(symbol.upper())

# Global instance
config = Config()
