import os
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(self):
        self.rpc_url = os.getenv("HELIUS_RPC_URL") or os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        self.client = httpx.AsyncClient(timeout=15.0)
        
        self.private_key = self._load_private_key()
        
        if self.private_key:
            logger.info("✅ Private key loaded from wallet.json")
        else:
            logger.error("❌ Failed to load private key from wallet.json")

    def _load_private_key(self) -> Optional[str]:
        """Load from wallet.json (single source of truth)"""
        try:
            if os.path.exists("wallet.json"):
                with open("wallet.json", "r") as f:
                    data = json.load(f)
                    pk = data.get("private_key")
                    if pk and len(pk) > 10:   # basic validation
                        return pk.strip()
        except Exception as e:
            logger.error(f"Error reading wallet.json: {e}")
        
        return None

    async def get_balance(self) -> float:
        if not self.private_key:
            logger.warning("No private key available - using 0 SOL")
            return 0.0

        try:
            pubkey = os.getenv("WALLET_PUBLIC_KEY")
            if not pubkey:
                logger.warning("WALLET_PUBLIC_KEY not set in .env")
                return 0.0

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [pubkey]
            }

            resp = await self.client.post(self.rpc_url, json=payload, timeout=10.0)
            data = resp.json()

            if "result" in data and "value" in data["result"]:
                lamports = data["result"]["value"]
                return round(lamports / 1_000_000_000, 6)
        except Exception as e:
            logger.error(f"Balance fetch failed: {e}")

        return 0.0

    async def close(self):
        await self.client.aclose()


# Global instance
wallet_manager = WalletManager()
