import asyncio
import logging
from datetime import datetime
from portfolio import Portfolio
from tide_titan import TideTitan
from depth_destroyer import DepthDestroyer
from liquidity_kraken import LiquidityKraken
from telegram_notifier import notifier
from config import config

# ==================== CLEAN LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# Suppress noisy HTTP libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
# ============================================================

async def main():
    logger.info("🚀 Initializing specialized trading bots...")

    portfolio = Portfolio(total_capital_sol=50.0)

    bots = [
        TideTitan(portfolio, dry_run=True),
        DepthDestroyer(portfolio, dry_run=True),
        LiquidityKraken(portfolio, dry_run=True)
    ]

    logger.info(f"✅ Loaded {len(bots)} bots | Monitoring {len(config.get_enabled_tokens())} tokens")
    logger.info(f"Active Tokens: {config.get_enabled_tokens()}")
    logger.info("🌊 Moon Tide Master started - Dry Run: True")

    try:
        while True:
            tasks = [bot.tick(token_key) for bot in bots for token_key in bot.tokens]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(8)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("🛑 Shutting down gracefully...")
    finally:
        logger.info("🌊 Moon Tide stopped.")

if __name__ == "__main__":
    asyncio.run(main())
