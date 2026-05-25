import httpx
import json
import time
import os
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ClaudeBrain:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = "claude-haiku-4-5"
        self.client = httpx.AsyncClient(timeout=35.0)
        self.memory_file = "claude_memory.json"
        self.memory = self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_memory(self):
        try:
            with open(self.memory_file, "w") as f:
                json.dump(self.memory[-50:], f, indent=2)  # Keep last 50 entries
        except:
            pass

    def add_to_memory(self, token: str, action: str, score: float, reason: str):
        self.memory.append({
            "time": time.strftime("%Y-%m-%d %H:%M"),
            "token": token,
            "action": action,
            "score": score,
            "reason": reason
        })
        self._save_memory()

    async def get_decision(self, context: Dict[str, Any]) -> Dict:
        if not self.api_key or "aaron-onboarding" in str(self.api_key):
            return self._fallback_decision()

        prompt = self._build_rich_prompt(context)

        try:
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 700,
                    "temperature": 0.35,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            data = response.json()
            text = data["content"][0]["text"]

            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1:
                return self._fallback_decision()

            result = json.loads(text[start:end])

            self.add_to_memory(
                context.get("symbol", "Unknown"),
                result.get("action", "HOLD"),
                result.get("final_score", 5.5),
                result.get("reason", "")
            )

            # Ask for code suggestion on strong trades
            if result.get("final_score", 0) >= 7.5 and random.random() < 0.4:
                suggestion = await self._ask_for_improvement(context, result)
                if suggestion:
                    print(f"\n🤖 CLAUDE STRATEGY SUGGESTION: {suggestion}\n")

            return result

        except Exception as e:
            logger.error(f"Claude Error: {e}")
            return self._fallback_decision()

    def _build_rich_prompt(self, ctx: Dict) -> str:
        memory_text = "\n".join([f"{m['time']} | {m['token']}: {m['action']} ({m['score']}) → {m['reason']}" 
                               for m in self.memory[-12:]]) or "No previous trades."

        return f"""You are Poseidon, a highly skilled Solana meme coin trader.

Current Bot: {ctx.get('bot_name')}
Token: {ctx.get('symbol')} @ {ctx.get('price', 0):.8f} SOL
Liquidity: ${ctx.get('liquidity', 0):,.0f} | 24h Volume: ${ctx.get('volume_24h', 0):,.0f}

Portfolio: {ctx.get('total_capital', 50):.2f} SOL total | {ctx.get('deployed_pct', 0):.1f}% deployed

Recent Memory:
{memory_text}

Technical Context: {ctx.get('technical_summary', 'N/A')}

Make a decisive trading call. Respond **ONLY** with this exact JSON format:

{{
  "action": "STRONG_BUY | BUY | HOLD | SELL",
  "final_score": 7.8,
  "suggested_capital_percent": 0.18,
  "tp": 0.16,
  "sl": -0.085,
  "reason": "Short clear reason under 110 characters"
}}
"""

    async def _ask_for_improvement(self, context: Dict, decision: Dict) -> str:
        """Ask Claude for actionable code/strategy improvements"""
        prompt = f"""You just made a strong trade (Score: {decision.get('final_score')}) on {context.get('symbol')}.

Suggest **one specific, actionable** improvement to the bot's code or strategy that would help capture more trades like this.
Be concrete and technical. Max 2 sentences."""

        try:
            resp = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": self.model, "max_tokens": 300, "temperature": 0.5, "messages": [{"role": "user", "content": prompt}]}
            )
            text = resp.json()["content"][0]["text"]
            return text.strip()[:280]
        except:
            return ""

    def _fallback_decision(self) -> Dict:
        return {
            "action": "HOLD",
            "final_score": 5.5,
            "suggested_capital_percent": 0.08,
            "tp": 0.15,
            "sl": -0.09,
            "reason": "Fallback - Claude unavailable"
        }

claude = ClaudeBrain()
