import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.bots_topic = int(os.getenv("TELEGRAM_BOTS_TOPIC", 19))
        self.claude_topic = int(os.getenv("TELEGRAM_CLAUDE_TOPIC", 135))

        self.enabled = bool(self.token and self.chat_id)

        if self.enabled:
            logger.info(f"✅ Telegram enabled (Bots topic: {self.bots_topic})")
        else:
            logger.debug("Telegram notifications disabled")

    async def send_trade_alert(self, bot_name: str, action: str, symbol: str, 
                              score: float, sol_amount: float, price: float, reason: str):
        """Send trade execution alerts"""
        if not self.enabled:
            logger.info(f"[{bot_name}] {action} {symbol} | Score: {score:.1f} | {reason}")
            return

        message = f"""
🪐 **{bot_name}**
**{action}** `{symbol}`
Price: `{price:.8f}` SOL
Score: `{score:.1f}`
Amount: `{sol_amount:.4f}` SOL
Reason: {reason}
        """.strip()

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "message_thread_id": self.bots_topic
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

    async def send_claude_decision(self, bot_name: str, symbol: str, decision: dict):
        """Send Claude decisions to dedicated topic"""
        if not self.enabled:
            return

        message = f"""
🧠 **Claude Decision** — {bot_name}
**Token:** `{symbol}`
**Action:** `{decision.get('action', 'HOLD')}`
**Score:** `{decision.get('final_score', 5.0):.1f}`
**Bot:** `{decision.get('recommended_bot', 'TideTitan')}`
**Reason:** {decision.get('reason', 'No reason')}
        """.strip()

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "message_thread_id": self.claude_topic
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Claude decision send failed: {e}")


# Global instance
notifier = TelegramNotifier()
