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
        self.model = "claude-haiku-4-5-20251001"
        self.memory_file = "claude_memory.json"
        self.memory = self._load_memory()

    def _load_memory(self) -> list:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_memory(self):
        try:
            with open(self.memory_file, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def get_decision(self, context: Dict) -> Dict:
        try:
            prompt = self._build_rich_prompt(context)

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "{" in text:
                text = text[text.find("{"):text.rfind("}")+1]

            decision = json.loads(text)
            self._update_memory(context, decision)
            return decision

        except Exception as e:
            logger.error(f"Claude decision error: {e}")
            return {
                "action": "HOLD",
                "final_score": 5.5,
                "suggested_capital_percent": 0.0,
                "recommended_bot": "TideTitan",
                "reason": "Claude unavailable - fallback HOLD"
            }

    def _build_rich_prompt(self, ctx: Dict) -> str:
        memory_text = "\n".join([
            f"{m['time']} | {m['token']}: {m['action']} ({m['score']}) → {m['reason']}" 
            for m in self.memory[-12:]
        ]) or "No previous trades."

        return f"""You are Poseidon, elite Solana memecoin trader.

Token: {ctx.get('symbol')} @ {ctx.get('price', 0):.10f} SOL
Liquidity: ${ctx.get('liquidity', 0):,.0f} | Ratio: {ctx.get('liquidity_ratio', 0):.1f}% of FDV
24h Vol: ${ctx.get('volume_24h', 0):,.0f} | Est FDV: ~${ctx.get('fdv', 'Unknown')}

{ctx.get('technical_summary', 'No technical data')}

Recent Memory:
{memory_text}

**Realistic Liquidity Rules for Solana Memecoins (2026):**
- Micro-caps (< $5M FDV): **3.0%+** liquidity ratio is acceptable with strong momentum
- 4-8%+ is good, 8%+ is excellent
- Absolute liquidity < $40k is still risky, but >$80k with good ratio is tradable

**Priorities:**
- Multi-timeframe alignment (especially 1h + 4h)
- Strong momentum + volume
- Relative liquidity over absolute dollars

Return **only** valid JSON:
{{
  "action": "BUY",
  "final_score": 7.8,
  "suggested_capital_percent": 0.18,
  "tp": 0.25,
  "sl": -0.12,
  "recommended_bot": "TideTitan",
  "reason": "Strong multi-timeframe setup with acceptable relative liquidity"
}}
"""

    def _update_memory(self, context: Dict, decision: Dict):
        self.memory.append({
            "time": datetime.now().strftime("%H:%M"),
            "token": context.get("symbol", "UNKNOWN"),
            "action": decision.get("action"),
            "score": decision.get("final_score"),
            "reason": decision.get("reason", "")[:120]
        })
        if len(self.memory) > 30:
            self.memory.pop(0)
        self._save_memory()


# Global instance
claude = ClaudeBrain()
