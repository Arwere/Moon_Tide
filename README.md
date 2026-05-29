 Here's a clean README.md without any personal/env details:bash

cat << 'EOF' > README.md
# 🌊 Moon Tide - Solana Memecoin Trading System

**Advanced multi-agent AI trading bot for Solana memecoins.**

Combines real-time technical analysis, Claude AI intelligence, and three specialized bots that dynamically select the best strategy for each opportunity.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt

2. Setup Environment VariablesCreate a .env file in the root folder and add your API keys:env

ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=...
WALLET_PUBLIC_KEY=...

3. Configure TokensEdit config.py and add your token contract addresses.4. Run the Botbash

python master.py

Default mode is Dry Run (safe testing — no real trades). Key FeaturesDynamic Bot Selection — Claude decides which bot is best in real-time
Three Specialized Bots:TideTitan → Strong trends & momentum
DepthDestroyer → High volatility & explosive moves
LiquidityKraken → Mean reversion & pullbacks

Hybrid Decision Engine — Technical Analysis (45%) + Claude AI (55%)
Real-time Data — DexScreener + Birdeye fallback
Telegram Alerts — Separate topics for decisions and trades
Risk Controls — Position sizing, stop-loss, take-profit

 Project StructureFile
Purpose
master.py
Main controller
base_bot.py
Core trading logic
agent.py
Poseidon decision engine
claude_brain.py
Claude AI integration
portfolio.py
Risk & position management
data_fetcher.py
Market data & prices
config.py
Token configuration
strategies.py
Technical analysis strategies
jupiter_client.py
Jupiter swap execution
wallet_manager.py
Wallet balance

 How It WorksEvery ~8 seconds the system:Fetches real-time price and market data
Runs technical analysis (4 strategies)
Asks Claude for analysis + best bot recommendation
Only the chosen bot can execute trades
Manages entries, exits, and risk automatically

 Important NotesAlways start in Dry Run mode
Monitor Claude decisions in your Telegram group
Never commit real private keys or wallet data to GitHub
Use small amounts when going live

 DocumentationQUICK_REFERENCE.md — How to run and troubleshoot
PROJECT_OVERVIEW.md — Technical deep dive
EXECUTIVE_SUMMARY.md — Project vision

Built for intelligent Solana memecoin trading Last Updated: May 2026

