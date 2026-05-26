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
        self.client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20)
        )
        self.cache = {}
        self.cache_ttl = 18   # seconds for price/token info

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def _get_cached(self, key: str, ttl: int = None) -> Optional[Dict]:
        """Internal cache helper"""
        if key not in self.cache:
            return None
        data, timestamp = self.cache[key]
        if time.time() - timestamp < (ttl or self.cache_ttl):
            return data
        return None

    async def get_price(self, token_mint: str) -> Optional[float]:
        """Robust price fetch with caching + fallback chain"""
        cache_key = f"price_{token_mint}"
        now = time.time()

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached and "price" in cached:
            return cached["price"]

        price = None

        # 1. DexScreener (fastest, most reliable for memecoins)
        try:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_mint}"
            resp = await self.client.get(url, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    # Pick pair with highest liquidity
                    best = max(data, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                    price_usd = float(best.get('priceUsd') or 0)
                    if price_usd > 0:
                        price = price_usd
                        self.cache[cache_key] = ({"price": price}, now)
                        return price
        except Exception as e:
            logger.debug(f"DexScreener price failed for {token_mint}: {e}")

        # 2. Birdeye fallback
        if self.birdeye_key:
            try:
                url = f"https://public-api.birdeye.so/defi/price?address={token_mint}"
                headers = {"X-API-KEY": self.birdeye_key, "x-chain": "solana"}
                resp = await self.client.get(url, headers=headers, timeout=8.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('success') and data.get('data'):
                        price = float(data['data'].get('value', 0))
                        if price > 0:
                            self.cache[cache_key] = ({"price": price}, now)
                            return price
            except Exception as e:
                logger.debug(f"Birdeye price failed for {token_mint}: {e}")

        # 3. Final fallback - very low price (safety)
        if price is None:
            logger.warning(f"Could not fetch price for {token_mint}, using fallback 0.0")
            price = 0.0

        self.cache[cache_key] = ({"price": price}, now)
        return price

    async def get_token_info(self, token_mint: str) -> Dict:
        """Return rich token data for Claude / analysis"""
        cache_key = f"info_{token_mint}"
        now = time.time()

        cached = await self._get_cached(cache_key, ttl=45)
        if cached:
            return cached

        info = {
            "mint": token_mint,
            "price": None,
            "liquidity_usd": 0.0,
            "volume_24h": 0.0,
            "volume_6h": 0.0,
            "mc": 0.0,
            "price_change_24h": 0.0,
            "dex": None,
            "age_minutes": 0
        }

        # DexScreener primary source
        try:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_mint}"
            resp = await self.client.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    best = max(data, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                    pair = best
                    info['price'] = float(pair.get('priceUsd') or 0)
                    info['liquidity_usd'] = float(pair.get('liquidity', {}).get('usd', 0))
                    info['volume_24h'] = float(pair.get('volume', {}).get('h24', 0))
                    info['price_change_24h'] = float(pair.get('priceChange', {}).get('h24', 0))
                    info['dex'] = pair.get('dexId')
        except Exception as e:
            logger.debug(f"DexScreener token info failed: {e}")

        # Birdeye enrichment
        if self.birdeye_key and info['price'] is None:
            try:
                url = f"https://public-api.birdeye.so/defi/token_overview?address={token_mint}"
                headers = {"X-API-KEY": self.birdeye_key, "x-chain": "solana"}
                resp = await self.client.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('success') and data.get('data'):
                        d = data['data']
                        info['price'] = info['price'] or float(d.get('price', 0))
                        info['liquidity_usd'] = max(info['liquidity_usd'], float(d.get('liquidity', 0)))
                        info['volume_24h'] = max(info['volume_24h'], float(d.get('v24hUSD', 0)))
                        info['mc'] = float(d.get('mc', 0))
            except Exception as e:
                logger.debug(f"Birdeye enrichment failed: {e}")

        self.cache[cache_key] = (info, now)
        return info

    async def get_historical_prices(self, token_mint: str, limit: int = 400) -> List[float]:
        """Return list of recent prices for TA strategies.
        Currently uses realistic simulation + current price.
        TODO: Add real Birdeye historical endpoint later."""
        current_price = await self.get_price(token_mint) or 0.001

        if current_price <= 0:
            current_price = 0.006  # safe default

        # Generate semi-realistic price series (volatility + slight trend)
        prices = []
        price = current_price
        for _ in range(limit):
            # Random walk with slight upward bias for memecoins
            change = random.uniform(-0.18, 0.22)
            price = price * (1 + change)
            price = max(price, current_price * 0.1)   # floor
            prices.append(price)

        # Shuffle a bit and reverse to simulate time series (oldest first)
        random.shuffle(prices)
        prices = sorted(prices[:limit])  # rough approximation
        return prices


# Global singleton
fetcher = HybridDataFetcher()

# Public API used by the rest of the codebase
async def get_price_in_sol(token_mint: str) -> Optional[float]:
    """Convenience function used everywhere"""
    return await fetcher.get_price(token_mint)


async def get_token_info(token_mint: str) -> Dict:
    return await fetcher.get_token_info(token_mint)


async def get_historical_prices(token_mint: str, limit: int = 400) -> List[float]:
    return await fetcher.get_historical_prices(token_mint, limit)
