import os
import logging
import httpx
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.bots_topic = os.getenv("TELEGRAM_BOTS_TOPIC", "19")
        self.agents_topic = os.getenv("TELEGRAM_AGENTS_TOPIC", "13")
        self.claude_topic = os.getenv("TELEGRAM_CLAUDE_TOPIC", "135")

        self.client = httpx.AsyncClient(timeout=10.0)

        if not self.token or not self.chat_id:
            logger.warning("⚠️ Telegram not fully configured!")
        else:
            logger.info("✅ Telegram notifier ready with topics")

    async def send_message(self, text: str, topic_id: str = None):
        if not self.token or not self.chat_id:
            return
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            if topic_id:
                payload["message_thread_id"] = int(topic_id)

            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            await self.client.post(url, json=payload)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

    # Poseidon / Claude decisions → Agents Topic
    async def send_claude_decision(self, bot_name: str, symbol: str, decision: Dict):
        score = decision.get("final_score", 5.0)
        action = decision.get("action", "HOLD")
        reason = decision.get("reason", "No reason provided")

        text = f"""🧠 <b>{bot_name}</b> — {symbol}
Action: <b>{action}</b> | Score: <b>{score:.1f}</b>

{reason}"""

        await self.send_message(text, self.agents_topic)

    # Trade executions → Bots Topic
    async def send_trade_alert(self, bot_name: str, action: str, symbol: str, score: float, amount: float, price: float, reason: str):
        text = f"""🚨 <b>TRADE EXECUTED</b>
{bot_name} | {action} {symbol}
Amount: {amount:.4f} SOL @ {price:.8f}
Score: {score:.1f}

```{reason}```"""
        await self.send_message(text, self.bots_topic)

    # Summaries → Claude Topic
    async def send_daily_summary(self, portfolio):
        summary = portfolio.get_summary_dict()
        text = f"""🌊 <b>Moon Tide Daily Summary</b>
Capital: {summary['total_capital']:.4f} SOL
Deployed: {summary['deployed']:.4f} SOL ({summary.get('open_positions', 0)} positions)"""
        await self.send_message(text, self.claude_topic)


# Global instance
notifier = TelegramNotifier()
