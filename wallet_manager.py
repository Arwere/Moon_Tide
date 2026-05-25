import json
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import asyncio
import httpx

class WalletManager:
    def __init__(self):
        self.keypair = None
        self.pubkey = None
        self._load_wallet()

    def _load_wallet(self):
        try:
            with open("wallet.json", "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.keypair = Keypair.from_bytes(bytes(data))
                else:
                    self.keypair = Keypair.from_base58_string(data["private_key"])
                self.pubkey = self.keypair.pubkey()
                print("✅ Wallet loaded (private key only)")
        except Exception as e:
            print(f"❌ Wallet load failed: {e}")

    async def get_balance(self) -> float:
        """Get SOL balance in SOL (not lamports)"""
        if not self.pubkey:
            return 50.0  # fallback

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.mainnet-beta.solana.com",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getBalance",
                        "params": [str(self.pubkey)]
                    }
                )
                data = resp.json()
                lamports = data.get("result", {}).get("value", 0)
                return round(lamports / 1_000_000_000, 4)  # Convert to SOL
        except Exception as e:
            print(f"Balance fetch failed: {e}")
            return 50.0  # safe fallback for dry-run

    def get_pubkey(self):
        return str(self.pubkey) if self.pubkey else None
