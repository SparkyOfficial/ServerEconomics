
# Discord Economic Bot — "The New Order" / "Millennium Dawn" style

**Features**
- Real-time treasury that updates continuously.
- Admin actions cost money; if not enough funds, action is cancelled.
- Passive income from participants.
- Players and admins can influence the economy.
- Random events occur every 1–24 hours.
- No "shop".
- Treasury includes a live-updating graph (PNG) with recent history.
- Economic statuses: Collapse, Recession, Stagnation, Stable Growth, Fast Growth, Boom.
- Trade policies: Autarky <-> Free Trade, with trade-offs.

**Contents**
- `bot.py` — main entrypoint (run this).
- `economy.py` — core economy logic.
- `events.py` — random events engine.
- `data.json` — persisted state (created/updated at runtime).
- `requirements.txt` — Python dependencies.
- `README.md` — this file.

**How to run**
1. Create a Discord bot application and get its token. Invite it to your server with bot intents.
2. Install dependencies:
   ```
   python -m pip install -r requirements.txt
   ```
3. Set environment variable `DISCORD_TOKEN` to your bot token (or paste in bot.py).
4. Run:
   ```
   python bot.py
   ```

**Notes**
- This is a prototype. You should run it on a machine that can run background tasks persistently.
- The bot persists state to `data.json`. Back it up.
- Graphs are saved to `treasury_graph.png` and updated periodically.

