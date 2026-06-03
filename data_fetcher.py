import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

async def get_price_in_sol(token_address: str) -> Optional[float]:
    """Get current price in SOL"""
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_address}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    pair = data[0]
                    price_usd = pair.get("priceUsd")
                    if price_usd:
                        sol_resp = await client.get("https://api.dexscreener.com/tokens/v1/solana/So11111111111111111111111111111111111111112")
                        if sol_resp.status_code == 200:
                            sol_data = sol_resp.json()
                            sol_usd = float(sol_data[0].get("priceUsd", 150)) if isinstance(sol_data, list) else 150
                            return float(price_usd) / sol_usd
    except Exception as e:
        logger.debug(f"Price fetch error: {e}")
    return None


async def get_token_info(token_address: str) -> Dict:
    """Get aggregated liquidity from ALL pools"""
    total_liquidity = 0.0
    fdv = 0.0
    volume_24h = 0.0

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://api.dexscreener.com/tokens/v1/solana/{token_address}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for pair in data:
                        liq = pair.get("liquidity", {}).get("usd", 0)
                        total_liquidity += liq
                        if fdv == 0:
                            fdv = pair.get("fdv") or pair.get("marketCap") or 0
                        volume_24h += pair.get("volume", {}).get("h24", 0)

                # Fallback FDV estimation
                if fdv == 0 and total_liquidity > 0:
                    fdv = total_liquidity * 25

                liquidity_ratio = round((total_liquidity / fdv * 100), 2) if fdv > 0 else 0.0

                return {
                    "liquidity": total_liquidity,
                    "fdv": fdv,
                    "volume_24h": volume_24h,
                    "price_change_24h": 0,  # can be improved later
                    "liquidity_ratio": liquidity_ratio
                }
    except Exception as e:
        logger.debug(f"Token info error for {token_address}: {e}")

    return {"liquidity": 0, "fdv": 0, "volume_24h": 0, "price_change_24h": 0, "liquidity_ratio": 0.0}


async def get_historical_prices(token_address: str, limit: int = 300) -> List[float]:
    """Safe historical prices"""
    return [0.0005] * limit   # Will be replaced with real data later


# Aliases
get_price = get_price_in_sol
