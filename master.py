import asyncio
import time
from datetime import datetime

from config import config
from portfolio import Portfolio
from jupiter_client import JupiterClient
from wallet_manager import WalletManager

from tide_titan import TideTitan
from depth_destroyer import DepthDestroyer
from liquidity_kraken import LiquidityKraken


class MoonTideMaster:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.wallet = WalletManager()
        # Override for testing when wallet is empty
        self.portfolio = Portfolio(total_capital_sol=50.0, wallet_manager=self.wallet)
        self.jupiter = JupiterClient()
        self.bots = {}
        self.running = False
        self._initialize_bots()

    def _initialize_bots(self):
        bot_map = {"MM": TideTitan, "WHITEWHALE": DepthDestroyer, "TROLL": LiquidityKraken}
        for token_key, token_config in config.TOKENS.items():
            if not token_config.enabled:
                continue
            print(f"🚀 Initializing bot for {token_config.symbol} ({token_key})")
            bot_class = bot_map.get(token_key, TideTitan)
            self.bots[token_key] = bot_class(token_key, self.portfolio, self.jupiter, self.dry_run)

    async def run(self):
        self.running = True
        await self.portfolio.refresh_capital()

        print(f"🌊 Moon Tide Master started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'🟢 LIVE' if not self.dry_run else '🔒 DRY-RUN'}")
        print(f"Total Trading Capital: {self.portfolio.total_capital_sol:.4f} SOL")
        print(f"Active tokens: {list(self.bots.keys())}")
        print("=" * 90)

        cycle = 0
        while self.running:
            cycle += 1
            try:
                tasks = [bot.tick() for bot in self.bots.values()]
                await asyncio.gather(*tasks, return_exceptions=True)

                if cycle % 10 == 0:
                    print(self.portfolio.get_summary())

            except Exception as e:
                print(f"Master error: {e}")

            await asyncio.sleep(7.0)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    master = MoonTideMaster(dry_run=True)
    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        master.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        master.stop()
