
import os, asyncio, discord, math
from discord.ext import commands, tasks
from economy import Economy
from events import EventEngine
import logging
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("DISCORD_TOKEN")  # or paste token here for testing

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

eco = Economy()
event_engine = EventEngine(eco, bot=bot)

# Background tick: updates every minute (in production tune to desired frequency)
@tasks.loop(seconds=60.0)
async def periodic_tick():
    res = await eco.tick()
    logging.info(f"Tick: treasury={res['treasury']:.2f}, tax={res['tax_collected']:.2f}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await event_engine.start()
    periodic_tick.start()

# Basic commands

@bot.command()
async def help(ctx):
    em = discord.Embed(title="Economy Bot Commands", color=0x00ff00)
    em.add_field(name="!treasury", value="Show treasury amount and status")
    em.add_field(name="!balance [@user]", value="Show your or user's balance")
    em.add_field(name="!donate <amount>", value="Donate from your balance to the treasury")
    em.add_field(name="!setpolicy <policy>", value="Admins: set trade policy")
    em.add_field(name="!adminact <cost> <description>", value="Admins: perform action that costs treasury")
    em.add_field(name="!status", value="Show economy & trade statuses")
    await ctx.send(embed=em)

@bot.command()
async def treasury(ctx):
    st = eco.state
    tre = st["treasury"]
    status = eco.get_status()
    trade = st.get("trade_policy")
    em = discord.Embed(title="Treasury", color=0xFFD700)
    em.add_field(name="Amount", value=f"{tre:,.2f}")
    em.add_field(name="Status", value=status)
    em.add_field(name="Trade policy", value=trade)
    # attach graph if exists
    graph = os.path.join(os.path.dirname(__file__), "treasury_graph.png")
    if os.path.exists(graph):
        await ctx.send(file=discord.File(graph), embed=em)
    else:
        await ctx.send(embed=em)

@bot.command()
async def balance(ctx, member: discord.Member=None):
    target = member or ctx.author
    p = eco.get_player(target.id)
    await ctx.send(f"{target.display_name} balance: {p.get('balance',0):,.2f} (passive rate {p.get('passive_rate',0):.2f}/hour)")

@bot.command()
async def donate(ctx, amount: float):
    uid = str(ctx.author.id)
    p = eco.get_player(ctx.author.id)
    if p.get("balance",0) >= amount and amount>0:
        ok = await eco.player_influence(ctx.author.id, amount)
        if ok:
            await ctx.send(f"Thank you! Donated {amount:,.2f} to treasury.")
        else:
            await ctx.send("Donation failed.")
    else:
        await ctx.send("Insufficient personal funds.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setpolicy(ctx, *, policy: str):
    policy = policy.strip()
    ok = eco.set_trade_policy(policy)
    if ok:
        await ctx.send(f"Trade policy set to {policy}.")
    else:
        await ctx.send(f"Unknown policy. Choose from: {', '.join(['Autarky','Protectionism','Balanced','Free Trade'])}")

@bot.command()
@commands.has_permissions(administrator=True)
async def adminact(ctx, cost: float, *, description: str):
    cost = abs(float(cost))
    ok = await eco.admin_action(cost, description, admin_id=str(ctx.author.id))
    if ok:
        await ctx.send(f"Admin action succeeded. Cost {cost:,.2f} taken from treasury.")
    else:
        await ctx.send(f"Not enough funds in treasury. Action cancelled.")

@bot.command()
async def status(ctx):
    st = eco.state
    await ctx.send(f"Economy status: {eco.get_status()}\nTrade policy: {st.get('trade_policy')}")

# Utilities: allow admins to give players starting money and passive rates
@bot.command()
@commands.has_permissions(administrator=True)
async def grant(ctx, member: discord.Member, amount: float, passive_rate: float=0.0):
    eco.add_player(member.id, initial_balance=amount, passive_rate=passive_rate)
    await ctx.send(f"Granted {amount:,.2f} and passive rate {passive_rate:.2f}/h to {member.display_name}")

# Simple command to list recent events
@bot.command()
async def events(ctx):
    evs = eco.state.get("events", [])[-10:]
    if not evs:
        await ctx.send("No recent events.")
        return
    lines = []
    for e in evs[::-1]:
        t = e.get("time","?")
        typ = e.get("type","")
        desc = e.get("desc", str(e))
        lines.append(f"{t} — {typ} — {desc}")
    await ctx.send("Recent events:\n" + "\n".join(lines))

# Error handler
@bot.event
async def on_command_error(ctx, error):
    if hasattr(error, "original"):
        error = error.original
    await ctx.send(f"Error: {str(error)}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Set DISCORD_TOKEN environment variable.")
    else:
        bot.run(TOKEN)
