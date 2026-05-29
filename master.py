import asyncio
import time
from datetime import datetime
import logging

from config import config
from portfolio import Portfolio
from wallet_manager import WalletManager

from tide_titan import TideTitan
from depth_destroyer import DepthDestroyer
from liquidity_kraken import LiquidityKraken

logger = logging.getLogger(__name__)

class MoonTideMaster:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.wallet = WalletManager()
        self.portfolio = Portfolio(total_capital_sol=50.0, wallet_manager=self.wallet)
        self.bots = {}
        self.running = False
        self._initialize_bots()

    def _initialize_bots(self):
        print("🚀 Initializing specialized trading bots...")

        for token_key, token_cfg in config.TOKENS.items():
            if not getattr(token_cfg, 'enabled', True):
                continue

            print(f"   → {token_key} ({token_cfg.symbol})")

            if token_key == "MM":
                bot_class = TideTitan
            elif token_key == "WHITEWHALE":
                bot_class = DepthDestroyer
            else:
                bot_class = LiquidityKraken

            self.bots[token_key] = bot_class(
                token_key=token_key,
                portfolio=self.portfolio,
                dry_run=self.dry_run
            )

        print(f"✅ Loaded {len(self.bots)} bots | Monitoring {len(self.bots)} tokens")

    async def run(self):
        self.running = True
        await self.portfolio.refresh_capital()

        print(f"🌊 Moon Tide Master started - Dry Run: {self.dry_run}")
        print(f"Active Tokens: {list(self.bots.keys())}")
        print("=" * 80)

        cycle = 0
        while self.running:
            cycle += 1
            try:
                tasks = [bot.tick(token_key) for token_key, bot in self.bots.items()]
                await asyncio.gather(*tasks, return_exceptions=True)

                if cycle % 10 == 0:
                    print(self.portfolio.get_summary())

            except Exception as e:
                logger.error(f"Master cycle error: {e}")

            await asyncio.sleep(8.0)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    master = MoonTideMaster(dry_run=True)   # Change to False for live
    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        print("\n🛑 Stopping Moon Tide Master...")
        master.stop()
    except Exception as e:
        print(f"❌ Error: {e}")
        master.stop()
