
import asyncio, json, os, time, statistics
from collections import deque
from matplotlib import pyplot as plt
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
GRAPH_FILE = os.path.join(os.path.dirname(__file__), "treasury_graph.png")

# Economic statuses thresholds (treasury value growth rate per tick)
STATUSES = [
    ("Collapse", -1.0),
    ("Recession", -0.2),
    ("Stagnation", -0.01),
    ("Stable growth", 0.02),
    ("Fast growth", 0.1),
    ("Boom", 0.5),
]

TRADE_POLICIES = ["Autarky", "Protectionism", "Balanced", "Free Trade"]

class Economy:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        else:
            # default initial state
            self.state = {
                "treasury": 100000.0,
                "history": [],  # list of (timestamp_iso, treasury_value)
                "players": {},  # user_id -> {"balance": float, "passive_rate": float}
                "trade_policy": "Balanced",
                "last_tick": time.time(),
                "events": [],
            }
            self._save()
        # keep a rolling deque for plotting last 48 points
        self._history = deque(self.state.get("history", []), maxlen=48)

    def _save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    async def tick(self):
        """Perform a periodic tick: collect passive income, apply events, update history, redraw graph."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.state.get("last_tick", now)
            # treat elapsed in seconds -> convert to hours for rates if needed
            hours = max(1/3600, elapsed/3600.0)
            # Passive income from players: sum of passive_rate * hours
            total_passive = 0.0
            for uid, p in self.state["players"].items():
                rate = p.get("passive_rate", 0.0)  # currency units per hour
                income = rate * hours
                p["balance"] = p.get("balance", 0.0) + income
                total_passive += income
            # passive income collected into treasury? design choice: a portion goes to treasury (tax)
            tax_rate = self._trade_tax()
            tax_collected = total_passive * tax_rate
            self.state["treasury"] += tax_collected
            # update last_tick and history
            self.state["last_tick"] = now
            self.state["history"].append((datetime.utcnow().isoformat(), self.state["treasury"]))
            # keep history length reasonable
            if len(self.state["history"]) > 1000:
                self.state["history"] = self.state["history"][-1000:]
            self._save()
            try:
                self._draw_graph()
            except Exception:
                pass
            return {
                "treasury": self.state["treasury"],
                "tax_collected": tax_collected,
                "total_passive": total_passive,
            }

    def _trade_tax(self):
        """Tax rate depends on trade policy: Autarky = high internal tax, Free Trade = low tax."""
        policy = self.state.get("trade_policy", "Balanced")
        mapping = {
            "Autarky": 0.3,
            "Protectionism": 0.2,
            "Balanced": 0.12,
            "Free Trade": 0.05,
        }
        return mapping.get(policy, 0.12)

    async def admin_action(self, cost, description, admin_id=None):
        """Try to perform admin action costing 'cost' from treasury. If not enough, cancel and return False."""
        async with self._lock:
            if self.state["treasury"] >= cost:
                self.state["treasury"] -= cost
                self.state["events"].append({
                    "time": datetime.utcnow().isoformat(),
                    "type": "admin_action",
                    "desc": description,
                    "admin": admin_id,
                    "cost": cost,
                })
                self._save()
                return True
            else:
                return False

    async def player_influence(self, user_id, amount):
        """Player spends personal balance to influence economy (e.g., donations). This increases treasury."""
        async with self._lock:
            players = self.state.setdefault("players", {})
            p = players.setdefault(str(user_id), {"balance": 0.0, "passive_rate": 0.0})
            if p["balance"] >= amount:
                p["balance"] -= amount
                self.state["treasury"] += amount
                self.state["events"].append({
                    "time": datetime.utcnow().isoformat(),
                    "type": "player_influence",
                    "user": str(user_id),
                    "amount": amount,
                })
                self._save()
                return True
            else:
                return False

    def get_status(self):
        """Interpret current economy status by recent growth rate."""
        # compute growth rate from last N points
        hist = list(self.state.get("history", []))
        if len(hist) < 2:
            return "Stagnation"
        # use last 6 points if available
        sample = hist[-6:]
        times = [i for i, _ in enumerate(sample)]
        values = [v for _, v in sample]
        try:
            # compute simple average percentage change per point
            changes = []
            for i in range(1, len(values)):
                if values[i-1] == 0: continue
                changes.append((values[i] - values[i-1]) / values[i-1])
            if not changes:
                return "Stagnation"
            avg = sum(changes)/len(changes)
        except Exception:
            return "Stagnation"
        # map avg to status
        if avg < -0.5:
            return "Collapse"
        if avg < -0.05:
            return "Recession"
        if avg < 0.005:
            return "Stagnation"
        if avg < 0.05:
            return "Stable growth"
        if avg < 0.2:
            return "Fast growth"
        return "Boom"

    def set_trade_policy(self, policy):
        if policy in TRADE_POLICIES:
            self.state["trade_policy"] = policy
            self._save()
            return True
        return False

    def add_player(self, user_id, initial_balance=0.0, passive_rate=0.0):
        players = self.state.setdefault("players", {})
        players.setdefault(str(user_id), {"balance": float(initial_balance), "passive_rate": float(passive_rate)})
        self._save()

    def get_player(self, user_id):
        return self.state.get("players", {}).get(str(user_id), {"balance": 0.0, "passive_rate": 0.0})

    def _draw_graph(self):
        """Draw a simple line chart of recent treasury history to GRAPH_FILE."""
        hist = self.state.get("history", [])[-48:]
        if len(hist) < 2:
            return
        timestamps = [datetime.fromisoformat(t) for t, _ in hist]
        values = [v for _, v in hist]
        plt.figure(figsize=(8,3))
        plt.plot(timestamps, values)
        plt.title(f"Treasury over time — {datetime.utcnow().date().isoformat()}")
        plt.xlabel("Time (UTC)")
        plt.tight_layout()
        plt.savefig(GRAPH_FILE)
        plt.close()
