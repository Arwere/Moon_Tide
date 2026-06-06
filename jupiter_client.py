import os
import logging
import httpx
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class JupiterClient:
    def __init__(self):
        self.rpc_url = os.getenv("HELIUS_RPC_URL") or os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        self.client = httpx.AsyncClient(timeout=20.0)

    async def get_quote(self, input_mint: str, output_mint: str, amount: float):
        """Get best quote from Jupiter"""
        try:
            url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": int(amount * 1_000_000_000),  # lamports for SOL
                "slippageBps": 100,  # 1%
                "onlyDirectRoutes": False
            }
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"Quote failed: {resp.text}")
        except Exception as e:
            logger.error(f"Quote error: {e}")
        return None

    async def execute_swap(self, input_mint: str, output_mint: str, amount: float, dry_run: bool = True) -> Dict:
        """Execute or simulate swap"""
        if dry_run:
            logger.info(f"[DRY-RUN] Would swap {amount:.4f} SOL → {output_mint}")
            return {"success": True, "simulated": True, "outAmount": amount * 1.05}  # fake positive

        # Real swap flow (quote → swap → sign & send)
        quote = await self.get_quote(input_mint, output_mint, amount)
        if not quote:
            return {"success": False, "error": "No quote"}

        try:
            # TODO: Full swap transaction (requires wallet signing)
            # For now we return quote for future implementation
            logger.info(f"Real swap would use quote: {quote.get('outAmount')}")
            return {"success": True, "quote": quote, "note": "Full tx signing coming next"}
        except Exception as e:
            logger.error(f"Jupiter swap failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        await self.client.aclose()


# Global instance
jupiter = JupiterClient()
