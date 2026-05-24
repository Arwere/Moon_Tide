import asyncio
import json
import time
from typing import Dict, Optional, List, Any
import httpx
import logging
import os

logger = logging.getLogger(__name__)

class HybridDataFetcher:
    def __init__(self, birdeye_api_key: Optional[str] = None, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.birdeye_key = birdeye_api_key or os.getenv("BIRDEYE_API_KEY")
        self.rpc_url = rpc_url
        self.client = httpx.AsyncClient(timeout=12.0, limits=httpx.Limits(max_connections=30, max_keepalive_connections=10))
        self.cache = {}
        self.cache_ttl = 25  # seconds

    async def close(self):
        await self.client.aclose()

    async def get_price(self, token_mint: str, vs_token: str = "USDC") -> Optional[float]:
        """Priority: Jupiter V3 → DexScreener → Birdeye (if key)"""
        if not token_mint:
            return None

        cache_key = f"price_{token_mint}"
        now = time.time()
        if cache_key in self.cache and now - self.cache[cache_key]['ts'] < self.cache_ttl:
            return self.cache[cache_key]['price']

        # 1. Jupiter V3 (best executable price)
        try:
            url = f"https://api.jup.ag/price/v3?ids={token_mint}"
            resp = await self.client.get(url)
            data = resp.json()
            if data.get('data', {}).get(token_mint):
                price = float(data['data'][token_mint].get('price') or data['data'][token_mint].get('usdPrice', 0))
                if price > 0:
                    self.cache[cache_key] = {'price': price, 'ts': now}
                    return price
        except Exception as e:
            logger.debug(f"Jupiter V3 failed for {token_mint}: {e}")

        # 2. DexScreener fallback
        try:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_mint}"
            resp = await self.client.get(url)
            data = resp.json()
            if isinstance(data, list) and data:
                # Take best pair by liquidity
                best = max(data, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                price = float(best.get('priceUsd') or best.get('priceNative', 0))
                if price > 0:
                    self.cache[cache_key] = {'price': price, 'ts': now}
                    return price
        except Exception as e:
            logger.debug(f"DexScreener failed: {e}")

        # 3. Birdeye (only if key present)
        if self.birdeye_key:
            try:
                url = f"https://public-api.birdeye.so/defi/price?address={token_mint}"
                headers = {"X-API-KEY": self.birdeye_key, "x-chain": "solana"}
                resp = await self.client.get(url, headers=headers)
                data = resp.json()
                if data.get('success') and data.get('data'):
                    price = float(data['data'].get('value', 0))
                    if price > 0:
                        self.cache[cache_key] = {'price': price, 'ts': now}
                        return price
            except Exception as e:
                logger.debug(f"Birdeye price failed: {e}")

        logger.warning(f"All sources failed to get price for {token_mint}")
        return None

    async def get_token_info(self, token_mint: str) -> Dict:
        """Rich info combining all sources"""
        info = {
            "mint": token_mint,
            "price": None,
            "liquidity_usd": 0,
            "volume_24h": 0,
            "mc": 0,
            "dex": None
        }

        # DexScreener (great for pair data)
        try:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_mint}"
            resp = await self.client.get(url)
            data = resp.json()
            if isinstance(data, list) and data:
                best = max(data, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                info['price'] = float(best.get('priceUsd') or 0)
                info['liquidity_usd'] = float(best.get('liquidity', {}).get('usd', 0))
                info['volume_24h'] = float(best.get('volume', {}).get('h24', 0))
                info['dex'] = best.get('dexId')
        except:
            pass

        # Birdeye enrichment
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

    # Add more methods later (OHLCV, wallet via RPC, etc.)
