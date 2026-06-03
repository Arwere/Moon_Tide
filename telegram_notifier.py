import os
import logging
import requests
from typing import Dict

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.bots_topic = int(os.getenv("TELEGRAM_BOTS_TOPIC", 19))
        self.claude_topic = int(os.getenv("TELEGRAM_CLAUDE_TOPIC", 135))

        self.enabled = bool(self.token and self.chat_id)

        if self.enabled:
            logger.info("✅ Telegram notifications enabled")

    async def send_claude_decision(self, bot_name: str, symbol: str, decision: Dict):
        if not self.enabled:
            return

        action = decision.get("action", "HOLD")
        score = decision.get("final_score", 5.0)
        recommended = decision.get("recommended_bot", "TideTitan")
        reason = decision.get("reason", "No clear reasoning")

        message = f"""*🧠 Poseidon Analysis — {bot_name}*

*Token:* `{symbol}`
*Action:* `{action}`
*Score:* `{score:.1f}`
*Recommended Bot:* `{recommended}`

*Reasoning:* ```{reason}```"""

        await self._send_message(message, self.claude_topic)

    async def send_trade_alert(self, bot_name: str, action: str, symbol: str, 
                              score: float, sol_amount: float, price: float, reason: str):
        if not self.enabled:
            return

        message = f"""*{bot_name}*
*{action}* `{symbol}`
Price: `{price:.8f}` SOL
Score: `{score:.1f}`
Amount: `{sol_amount:.4f}` SOL
Reason: {reason}"""

        await self._send_message(message, self.bots_topic)

    async def _send_message(self, text: str, thread_id: int):
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "message_thread_id": thread_id
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")


# Global instance
notifier = TelegramNotifier()
