import asyncio
from datetime import datetime, date
import logging
from telegram_notifier import notifier
from portfolio import Portfolio

logger = logging.getLogger(__name__)

class DailySummary:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    async def send_daily_summary(self):
        """Send rich daily performance summary with detailed metrics"""
        summary = self.portfolio.get_daily_summary()
        win_rate = self.portfolio.get_win_rate()
        
        total_trades = summary.get('trades', 0)
        avg_pnl = round(summary.get('pnl', 0) / total_trades, 4) if total_trades > 0 else 0.0

        message = f"""
📊 **Daily Performance Report** — {datetime.now().strftime('%Y-%m-%d')}

**Capital:** `{summary.get('total_capital', 0):.4f}` SOL
**Realized PnL:** `{summary.get('pnl', 0):+.4f}` SOL
**Avg PnL per Trade:** `{avg_pnl:+.4f}` SOL
**Trades:** `{total_trades}`
**Win Rate:** `{win_rate}%`
**Total Volume:** `{summary.get('total_volume_sol', 0):.4f}` SOL
**Open Positions:** `{summary.get('open_positions', 0)}`
        """.strip()

        await notifier._send_message(message, notifier.bots_topic)

        # Ask Claude for intelligent feedback
        await self._ask_claude_for_feedback(summary, win_rate, avg_pnl)

    async def _ask_claude_for_feedback(self, summary: dict, win_rate: float, avg_pnl: float):
        """Send rich performance data to Claude for analysis"""
        try:
            from claude_brain import claude

            feedback_context = {
                "type": "daily_review",
                "date": str(date.today()),
                "summary": summary,
                "win_rate": win_rate,
                "avg_pnl_per_trade": avg_pnl,
                "instruction": "Analyze today's performance data and give 2-3 specific, actionable suggestions to improve future profitability."
            }
            
            decision = await claude.get_decision(feedback_context)
            
            feedback_message = f"""
🧠 **Poseidon Strategic Review**

{decision.get('reason', 'No specific recommendations today. Continue monitoring market conditions.')}
            """.strip()

            await notifier._send_message(feedback_message, notifier.claude_topic)

        except Exception as e:
            logger.error(f"Failed to get Claude feedback: {e}")

    async def start_daily_task(self):
        """Run at 00:05 every day"""
        while True:
            now = datetime.now()
            if now.hour == 0 and now.minute == 5:
                await self.send_daily_summary()
                self.portfolio.reset_daily_summary()
                await asyncio.sleep(86400)  # 24 hours
            await asyncio.sleep(60)  # Check every minute
