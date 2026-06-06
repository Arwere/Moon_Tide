import os
import json
import logging
from datetime import datetime
from typing import Dict
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

class ClaudeBrain:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or not api_key.startswith("sk-ant-"):
            logger.error("❌ ANTHROPIC_API_KEY is missing or invalid!")
            logger.error("Run: export ANTHROPIC_API_KEY=sk-ant-...")
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.memory_file = "claude_memory.json"
        self.memory = self._load_memory()

    def _load_memory(self) -> list:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load memory: {e}")
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
                max_tokens=700,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()

            # Robust JSON extraction
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()

            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                decision = json.loads(json_str)
            else:
                raise ValueError("No JSON found")

            self._update_memory(context, decision)
            return decision

        except Exception as e:
            logger.error(f"Claude decision error: {e}")
            return self._fallback_decision()

    def _fallback_decision(self) -> Dict:
        return {
            "action": "HOLD",
            "final_score": 5.0,
            "suggested_capital_percent": 0.0,
            "recommended_bot": "TideTitan",
            "reason": "Claude unavailable - safe HOLD"
        }

    def _build_rich_prompt(self, ctx: Dict) -> str:
        memory_text = "\n".join([
            f"{m['time']} | {m['token']}: {m['action']} ({m['score']}) → {m['reason']}" 
            for m in self.memory[-15:]
        ]) or "No previous trades."

        return f"""You are Poseidon, aggressive but disciplined Solana memecoin trader.

CURRENT TOKEN:
{ctx.get('symbol')} @ {ctx.get('price', 0):.10f} SOL
Liquidity: ${ctx.get('liquidity', 0):,.0f} | FDV Ratio: {ctx.get('liquidity_ratio', 0):.1f}%
24h Volume: ${ctx.get('volume_24h', 0):,.0f}

TECHNICAL SUMMARY: {ctx.get('technical_summary', 'No technical data available')}

PORTFOLIO: {ctx.get('portfolio_summary', 'No open positions')}

RECENT MEMORY:
{memory_text}

Be decisive. Good momentum or liquidity setups should get BUY (score >= 6.5).
Only HOLD/PASS on truly weak setups.

Return **only** valid JSON:
{{
  "action": "BUY" | "SELL" | "HOLD",
  "final_score": 7.2,
  "suggested_capital_percent": 0.22,
  "recommended_bot": "TideTitan",
  "reason": "Strong momentum across timeframes"
}}
"""

    def _update_memory(self, context: Dict, decision: Dict):
        self.memory.append({
            "time": datetime.now().strftime("%H:%M"),
            "token": context.get("symbol", "UNKNOWN"),
            "action": decision.get("action"),
            "score": decision.get("final_score"),
            "reason": decision.get("reason", "")[:150]
        })
        if len(self.memory) > 35:
            self.memory.pop(0)
        self._save_memory()


# Global instance
claude = ClaudeBrain()
