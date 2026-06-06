import os
from typing import Dict
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TokenConfig:
    address: str
    symbol: str
    enabled: bool = True

class Config:
    def __init__(self):
        self.RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        
        self.TOKENS: Dict[str, TokenConfig] = {
            "MM": TokenConfig(
                address="Ax8PSfCXxmxb8C8kYTzN5CPpTe6PyeZfFf8rrXNCjupx",
                symbol="MM"
            ),
            "WHITEWHALE": TokenConfig(
                address="a3W4qutoEJA4232T2gwZUfgYJTetr96pU4SJMwppump",
                symbol="WHITEWHALE"
            ),
            "HACHI": TokenConfig(
                address="Ax8PSfCXxmxb8C8kYTzN5CPpTe6PyeZfFf8rrXNCjupx",  # ← Update with real address
                symbol="HACHI"
            ),
        }

    def get_enabled_tokens(self):
        return [key for key, token in self.TOKENS.items() if token.enabled]

config = Config()
