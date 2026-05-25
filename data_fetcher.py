import time
from typing import Dict, Optional, List
import httpx
import logging
import os
import random

logger = logging.getLogger(__name__)

class HybridDataFetcher:
    def __init__(self, birdeye_api_key: Optional[str] = None, rpc_url: str = None):
        self.birdeye_key = birdeye_api_key or os.getenv("BIRDEYE_API_KEY")
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = httpx.AsyncClient(timeout=15.0, limits=httpx.Limits(max_connections=30))
        self.cache = {}
        self.cache_ttl = 20

    async def close(self):
        await self.client.aclose()

    async def get_price(self, token_mint: str) -> Optional[float]:
        # ... (keep your existing price logic) ...
        # (Jupiter → DexScreener → Birdeye)
        # I'll keep it short here for space - use your previous version
        pass  # placeholder - replace with your working get_price

    async def get_token_info(self, token_mint: str) -> Dict:
        """Return rich token data for Claude"""
        info = {
            "mint": token_mint,
            "price": None,
            "liquidity_usd": 0,
            "volume_24h": 0,
            "volume_6h": 0,
            "mc": 0,
            "price_change_24h": 0,
            "dex": None
        }

        # DexScreener (best free source)
        try:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_mint}"
            resp = await self.client.get(url)
            data = resp.json()
            if isinstance(data, list) and data:
                best = max(data, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                info['price'] = float(best.get('priceUsd') or 0)
                info['liquidity_usd'] = float(best.get('liquidity', {}).get('usd', 0))
                info['volume_24h'] = float(best.get('volume', {}).get('h24', 0))
                info['price_change_24h'] = float(best.get('priceChange', {}).get('h24', 0))
                info['dex'] = best.get('dexId')
        except:
            pass

        # Birdeye enrichment if available
        if self.birdeye_key:
            try:
                url = f"https://public-api.birdeye.so/defi/token_overview?address={token_mint}"
                headers = {"X-API-KEY": self.birdeye_key, "x-chain": "solana"}
                resp = await self.client.get(url, headers=headers)
                data = resp.json()
                if data.get('success') and data.get('data'):
                    d = data['data']
                    info['price'] = info['price'] or float(d.get('price', 0))
                    info['liquidity_usd'] = max(info['liquidity_usd'], float(d.get('liquidity', 0)))
                    info['volume_24h'] = max(info['volume_24h'], float(d.get('v24hUSD', 0)))
                    info['mc'] = float(d.get('mc', 0))
            except:
                pass

        return info

# Global instance
fetcher = HybridDataFetcher()

async def get_price_in_sol(token_mint: str):
    return await fetcher.get_price(token_mint)

async def get_historical_prices(token_mint: str, limit: int = 400):
    # Realistic stub (as before)
    current = await fetcher.get_price(token_mint) or 0.006
    prices = [current * (1 + random.uniform(-0.2, 0.2)) for _ in range(limit)]
    return prices
