"""
Main bot class and initialization
"""

import discord
from discord.ext import commands, tasks
import os
import asyncio
import logging
from datetime import datetime, timedelta
import random

from database import DatabaseManager
from economic_engine import EconomicEngine
from utils.constants import (
    BOT_COLOR, ECONOMIC_STATUS, TRADE_POLICIES,
    ADMIN_ACTIONS_COSTS, EVENT_INTERVALS
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EconomicBot(commands.Bot):
    """Main Discord bot class for economic simulation."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            description="Economic Simulation Bot inspired by TNO and Millennium Dawn"
        )
        
        self.db = DatabaseManager()
        self.economic_engine = EconomicEngine(self.db)
        self.start_time = datetime.now()
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        # Initialize database
        await self.db.initialize()
        
        # Load cogs
        cogs = [
            'cogs.treasury',
            'cogs.administration', 
            'cogs.economy',
            'cogs.events',
            'cogs.trade'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Start background tasks
        self.treasury_updater.start()
        self.passive_income_generator.start()
        self.random_event_scheduler.start()
        
        logger.info("Bot setup completed")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        print(f'\n{self.user} is online!')
        print(f'Bot ID: {self.user.id if self.user else "Unknown"}')
        print(f'Guilds: {len(self.guilds)}')
        print(f'Started at: {self.start_time}')
        
        try:
            synced = await self.tree.sync()
            print(f'Synced {len(synced)} slash commands')
        except Exception as e:
            print(f'Failed to sync commands: {e}')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the global economy"
            )
        )
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        await self.db.initialize_guild(guild.id)
    
    async def on_command_error(self, ctx, error):
        """Global error handler for prefix commands."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the necessary permissions to execute this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.")
        else:
            logger.error(f"Unhandled command error: {error}")
            await ctx.send("❌ An unexpected error occurred.")
    
    @tasks.loop(seconds=30)
    async def treasury_updater(self):
        """Update treasury values in real-time."""
        try:
            for guild in self.guilds:
                await self.economic_engine.update_real_time_treasury(guild.id)
        except Exception as e:
            logger.error(f"Treasury updater error: {e}")
    
    @tasks.loop(minutes=5)
    async def passive_income_generator(self):
        """Generate passive income from server participants."""
        try:
            for guild in self.guilds:
                member_count = len([m for m in guild.members if not m.bot])
                if member_count > 0:
                    # Base income per member
                    base_income = 10
                    total_income = member_count * base_income
                    
                    # Apply economic modifiers
                    economic_data = await self.db.get_guild_economy(guild.id)
                    multiplier = self.economic_engine.get_income_multiplier(
                        economic_data['economic_status']
                    )
                    
                    final_income = int(total_income * multiplier)
                    await self.db.update_treasury(guild.id, final_income)
                    
                    logger.info(f"Generated {final_income} passive income for guild {guild.id}")
        except Exception as e:
            logger.error(f"Passive income generator error: {e}")
    
    @tasks.loop(hours=1)
    async def random_event_scheduler(self):
        """Schedule random economic events."""
        try:
            for guild in self.guilds:
                # Check if it's time for an event
                last_event = await self.db.get_last_event_time(guild.id)
                now = datetime.now()
                
                if last_event is None:
                    # First event
                    next_event_hours = random.randint(1, 24)
                    await self.db.set_next_event_time(
                        guild.id, 
                        now + timedelta(hours=next_event_hours)
                    )
                    continue
                
                next_event_time = await self.db.get_next_event_time(guild.id)
                if next_event_time and now >= next_event_time:
                    # Trigger event
                    events_cog = self.get_cog('Events')
                    if events_cog and hasattr(events_cog, 'trigger_random_event'):
                        await events_cog.trigger_random_event(guild.id)
                    
                    # Schedule next event
                    next_event_hours = random.randint(1, 24)
                    await self.db.set_next_event_time(
                        guild.id,
                        now + timedelta(hours=next_event_hours)
                    )
        except Exception as e:
            logger.error(f"Random event scheduler error: {e}")
    
    @treasury_updater.before_loop
    @passive_income_generator.before_loop
    @random_event_scheduler.before_loop
    async def before_tasks(self):
        """Wait for bot to be ready before starting tasks."""
        await self.wait_until_ready()
    
    async def close(self):
        """Clean shutdown."""
        logger.info("Shutting down bot...")
        
        # Cancel tasks
        self.treasury_updater.cancel()
        self.passive_income_generator.cancel()
        self.random_event_scheduler.cancel()
        
        # Close database connections
        await self.db.close()
        
        await super().close()
