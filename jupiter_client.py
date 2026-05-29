import os
import logging
import httpx
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class JupiterClient:
    def __init__(self):
        self.rpc_url = os.getenv("HELIUS_RPC_URL") or os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        self.client = httpx.AsyncClient(timeout=20.0)

    async def execute_swap(self, input_mint: str, output_mint: str, amount: float, dry_run: bool = True):
        """Execute or simulate swap via Jupiter"""
        if dry_run:
            logger.info(f"[DRY-RUN] Would swap {amount:.4f} {input_mint} → {output_mint}")
            return {"success": True, "simulated": True}

        try:
            # Basic quote request (you can expand this)
            url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": int(amount * 1_000_000_000),  # lamports
                "slippageBps": 50
            }
            
            resp = await self.client.get(url, params=params)
            quote = resp.json()

            logger.info(f"Jupiter quote received: {quote.get('outAmount')}")

            # In real trading you would then call /swap endpoint
            # For now we simulate
            return {"success": True, "quote": quote}

        except Exception as e:
            logger.error(f"Jupiter swap failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        await self.client.aclose()


# Global instance
jupiter = JupiterClient()
