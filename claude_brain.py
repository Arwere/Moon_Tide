import os
import json
import logging
from datetime import datetime
from typing import Dict
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

class ClaudeBrain:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-haiku-4-5"          # ← Haiku 4.5 (fast + cheap)
        self.memory = []

    async def get_decision(self, context: Dict) -> Dict:
        try:
            prompt = self._build_rich_prompt(context)

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.65,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()

            # Extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "{" in text:
                text = text[text.find("{"):text.rfind("}") + 1]

            decision = json.loads(text)
            self._update_memory(context, decision)
            return decision

        except Exception as e:
            logger.error(f"Claude Haiku error: {e}")
            return {
                "action": "HOLD",
                "final_score": 5.5,
                "suggested_capital_percent": 0.0,
                "recommended_bot": "TideTitan",
                "reason": "Claude error - fallback HOLD"
            }

    def _build_rich_prompt(self, ctx: Dict) -> str:
        memory_text = "\n".join([
            f"{m['time']} | {m['token']}: {m['action']} ({m['score']}) → {m['reason']}" 
            for m in self.memory[-8:]
        ]) or "No previous trades."

        return f"""You are Poseidon, a fast and sharp Solana memecoin trading AI using Haiku 4.5.

Token: {ctx.get('symbol')} @ {ctx.get('price', 0):.8f} SOL
Liquidity: ${ctx.get('liquidity', 0):,.0f} | 24h Vol: ${ctx.get('volume_24h', 0):,.0f}
Technical: {ctx.get('technical_summary', 'N/A')}

Choose action + best bot for current conditions:
- TideTitan → Strong trends & momentum
- DepthDestroyer → High volatility & explosions
- LiquidityKraken → Pullbacks & mean reversion

Return **only** valid JSON:

{{
  "action": "BUY",
  "final_score": 7.4,
  "suggested_capital_percent": 0.15,
  "tp": 0.18,
  "sl": -0.09,
  "recommended_bot": "TideTitan",
  "reason": "Short clear reason"
}}
"""

    def _update_memory(self, context: Dict, decision: Dict):
        self.memory.append({
            "time": datetime.now().strftime("%H:%M"),
            "token": context.get("symbol", "UNKNOWN"),
            "action": decision.get("action"),
            "score": decision.get("final_score"),
            "reason": decision.get("reason", "")[:80]
        })
        if len(self.memory) > 12:
            self.memory.pop(0)


# Global instance
claude = ClaudeBrain()
