import httpx
import os
import json
from typing import Dict

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "8662648328:AAF68vXslSCW6VIrna-NkPe7mnvMipp1-DY")
        self.chat_id = int(os.getenv("TELEGRAM_CHAT_ID", -1003770619404))
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_message(self, message: str, topic_id: int = 19):
        """Send rich formatted message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "message_thread_id": topic_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            await self.client.post(url, json=payload)
        except Exception as e:
            print(f"Telegram send failed: {e}")

    async def send_trade_alert(self, bot_name: str, action: str, symbol: str, score: float, 
                             amount_sol: float, price: float, reason: str = ""):
        emoji = "🟢" if "BUY" in action else "🔴"
        msg = f"""<b>{emoji} {bot_name} {action}</b>

Symbol: <b>{symbol}</b>
Score: <b>{score:.1f}</b>
Amount: <b>{amount_sol:.4f} SOL</b>
Price: <b>{price:.8f}</b>
Reason: {reason}"""

        await self.send_message(msg)

    async def send_portfolio_summary(self, summary: str):
        await self.send_message(f"<b>🌊 Moon Tide Portfolio Update</b>\n\n{summary}", topic_id=19)

# Global instance
notifier = TelegramNotifier()
