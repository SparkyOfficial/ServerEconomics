
import asyncio, random, time
from datetime import datetime

class EventEngine:
    def __init__(self, economy, bot=None):
        self.economy = economy
        self.bot = bot
        self._running = False

    async def start(self):
        self._running = True
        asyncio.create_task(self._loop())

    async def _loop(self):
        while self._running:
            # schedule next event randomly between 1 and 24 hours (for demo, allow fast mode)
            # If environment variable FAST_MODE present or small treasury, we can scale down; here we pick seconds for demo
            delay_seconds = random.randint(3600, 24*3600)  # production: seconds in 1-24 hours
            # For demo/testing you can reduce to e.g., random.randint(60, 600)
            await asyncio.sleep(delay_seconds)
            await self._trigger_random_event()

    async def _trigger_random_event(self):
        # Choose an event: positive or negative, affecting treasury and players
        roll = random.random()
        if roll < 0.35:
            # negative event
            amount = random.uniform(1000, 20000)
            async with self.economy._lock:
                self.economy.state["treasury"] = max(0.0, self.economy.state["treasury"] - amount)
                self.economy.state["events"].append({
                    "time": datetime.utcnow().isoformat(),
                    "type": "negative_event",
                    "desc": f"Unexpected expense of {int(amount)}",
                    "amount": -amount,
                })
                self.economy._save()
        else:
            # positive event
            amount = random.uniform(500, 15000)
            async with self.economy._lock:
                self.economy.state["treasury"] += amount
                self.economy.state["events"].append({
                    "time": datetime.utcnow().isoformat(),
                    "type": "positive_event",
                    "desc": f"Windfall of {int(amount)}",
                    "amount": amount,
                })
                self.economy._save()
        # notify via bot if available
        if self.bot:
            chan = None
            try:
                # try to use a channel named 'economy' or the first text channel
                for guild in self.bot.guilds:
                    for c in guild.text_channels:
                        if c.permissions_for(guild.me).send_messages:
                            if c.name == "economy":
                                chan = c
                                break
                            if chan is None:
                                chan = c
                    if chan:
                        break
                if chan:
                    await chan.send("An economic event occurred. Check treasury status.")
            except Exception:
                pass
