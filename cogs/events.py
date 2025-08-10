"""
Economic events system - random events that affect the economy
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import asyncio

from utils.embeds import EconomicEmbeds
from utils.constants import BOT_COLOR

class Events(commands.Cog):
    """Handles random economic events."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = EconomicEmbeds()
        
        # Define economic events
        self.positive_events = [
            {
                'name': 'Foreign Investment Surge',
                'description': 'International investors have shown significant interest in the economy, bringing in substantial capital.',
                'treasury_impact': random.randint(3000, 8000),
                'probability': 0.15
            },
            {
                'name': 'Technological Breakthrough',
                'description': 'A major technological innovation has been developed, boosting productivity across sectors.',
                'treasury_impact': random.randint(2000, 6000),
                'status_impact': None,
                'probability': 0.12
            },
            {
                'name': 'Export Boom',
                'description': 'International demand for domestic products has skyrocketed, boosting export revenues.',
                'treasury_impact': random.randint(4000, 10000),
                'probability': 0.13
            },
            {
                'name': 'Resource Discovery',
                'description': 'New valuable natural resources have been discovered, attracting mining investments.',
                'treasury_impact': random.randint(5000, 12000),
                'probability': 0.08
            },
            {
                'name': 'Tourism Surge',
                'description': 'A viral social media campaign has attracted millions of tourists, boosting the service sector.',
                'treasury_impact': random.randint(2500, 7000),
                'probability': 0.14
            },
            {
                'name': 'Infrastructure Grant',
                'description': 'International development organizations have approved major infrastructure funding.',
                'treasury_impact': random.randint(6000, 15000),
                'probability': 0.06
            }
        ]
        
        self.negative_events = [
            {
                'name': 'Market Crash',
                'description': 'Sudden market volatility has caused widespread panic selling and economic uncertainty.',
                'treasury_impact': random.randint(-8000, -3000),
                'status_impact': 'Economic Recession',
                'probability': 0.12
            },
            {
                'name': 'Natural Disaster',
                'description': 'A severe natural disaster has damaged critical infrastructure and disrupted economic activity.',
                'treasury_impact': random.randint(-10000, -5000),
                'probability': 0.10
            },
            {
                'name': 'Trade War',
                'description': 'International trade disputes have resulted in tariffs and reduced export opportunities.',
                'treasury_impact': random.randint(-6000, -2000),
                'probability': 0.11
            },
            {
                'name': 'Banking Crisis',
                'description': 'Major financial institutions are facing liquidity problems, affecting business loans.',
                'treasury_impact': random.randint(-7000, -3000),
                'status_impact': 'Economic Stagnation',
                'probability': 0.09
            },
            {
                'name': 'Energy Crisis',
                'description': 'Sudden spike in energy prices has increased operational costs across all sectors.',
                'treasury_impact': random.randint(-5000, -1500),
                'probability': 0.13
            },
            {
                'name': 'Labor Strike',
                'description': 'Widespread labor strikes have disrupted production and transportation networks.',
                'treasury_impact': random.randint(-4000, -1000),
                'probability': 0.14
            },
            {
                'name': 'Cyber Attack',
                'description': 'A major cyber attack has disrupted financial systems and e-commerce platforms.',
                'treasury_impact': random.randint(-6000, -2500),
                'probability': 0.08
            }
        ]
        
        self.neutral_events = [
            {
                'name': 'Policy Announcement',
                'description': 'Government has announced new economic policies that are receiving mixed reactions.',
                'treasury_impact': random.randint(-1000, 1000),
                'probability': 0.18
            },
            {
                'name': 'Currency Fluctuation',
                'description': 'The national currency has experienced moderate fluctuations against major currencies.',
                'treasury_impact': random.randint(-2000, 2000),
                'probability': 0.16
            },
            {
                'name': 'Market Speculation',
                'description': 'Investors are speculating about future market conditions, causing minor volatility.',
                'treasury_impact': random.randint(-1500, 1500),
                'probability': 0.15
            }
        ]
    
    async def trigger_random_event(self, guild_id: int):
        """Trigger a random economic event for a guild."""
        try:
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Select event type based on current economic status
            event_weights = self.get_event_weights(economy['economic_status'])
            
            event_type = random.choices(
                ['positive', 'negative', 'neutral'],
                weights=event_weights
            )[0]
            
            # Select specific event
            if event_type == 'positive':
                event = random.choice(self.positive_events)
            elif event_type == 'negative':
                event = random.choice(self.negative_events)
            else:
                event = random.choice(self.neutral_events)
            
            # Randomize treasury impact
            base_impact = event['treasury_impact']
            if isinstance(base_impact, int):
                # Add some randomness (±20%)
                variance = int(abs(base_impact) * 0.2)
                if base_impact > 0:
                    final_impact = random.randint(base_impact - variance, base_impact + variance)
                else:
                    final_impact = random.randint(base_impact - variance, base_impact + variance)
            else:
                final_impact = base_impact
            
            # Apply event effects
            event_data = {
                'type': event_type,
                'name': event['name'],
                'description': event['description'],
                'treasury_impact': final_impact,
                'status_impact': event.get('status_impact')
            }
            
            await self.bot.economic_engine.apply_economic_event(guild_id, event_data)
            
            # Send event notification to the guild
            guild = self.bot.get_guild(guild_id)
            if guild:
                await self.send_event_notification(guild, event_data)
            
        except Exception as e:
            print(f"Error triggering random event for guild {guild_id}: {e}")
    
    async def trigger_positive_event(self, guild_id: int):
        """Trigger a positive economic event (for admin boost)."""
        try:
            event = random.choice(self.positive_events)
            
            # Boost the impact for admin-triggered events
            base_impact = event['treasury_impact']
            if isinstance(base_impact, int):
                boosted_impact = int(base_impact * 1.5)  # 50% boost
            else:
                boosted_impact = base_impact
            
            event_data = {
                'type': 'positive',
                'name': f"[BOOSTED] {event['name']}",
                'description': f"{event['description']} (Enhanced by administrative action)",
                'treasury_impact': boosted_impact,
                'status_impact': event.get('status_impact')
            }
            
            await self.bot.economic_engine.apply_economic_event(guild_id, event_data)
            
            guild = self.bot.get_guild(guild_id)
            if guild:
                await self.send_event_notification(guild, event_data)
                
        except Exception as e:
            print(f"Error triggering positive event for guild {guild_id}: {e}")
    
    def get_event_weights(self, economic_status: str) -> list:
        """Get event probability weights based on current economic status."""
        # [positive_weight, negative_weight, neutral_weight]
        weights = {
            'Economic Crash': [0.4, 0.1, 0.5],      # More positive events during crash
            'Economic Recession': [0.35, 0.2, 0.45],
            'Economic Stagnation': [0.3, 0.3, 0.4],
            'Stable Growth': [0.25, 0.25, 0.5],     # Balanced
            'Rapid Growth': [0.2, 0.35, 0.45],      # More risk of negative events
            'Economic Boom': [0.15, 0.4, 0.45]      # High risk during boom
        }
        
        return weights.get(economic_status, [0.25, 0.25, 0.5])
    
    async def send_event_notification(self, guild: discord.Guild, event_data: dict):
        """Send event notification to the guild."""
        try:
            # Find a suitable channel to send the notification
            # Priority: 'economy' channel, 'general' channel, first text channel
            target_channel = None
            
            for channel in guild.text_channels:
                if 'economy' in channel.name.lower():
                    target_channel = channel
                    break
                elif 'general' in channel.name.lower() and target_channel is None:
                    target_channel = channel
                elif target_channel is None:
                    target_channel = channel
            
            if not target_channel:
                return  # No suitable channel found
            
            # Create embed based on event type
            event_type = event_data['type']
            if event_type == 'positive':
                color = 0x00FF00
                emoji = "📈"
            elif event_type == 'negative':
                color = 0xFF0000
                emoji = "📉"
            else:
                color = 0xFFFF00
                emoji = "📊"
            
            embed = discord.Embed(
                title=f"{emoji} Economic Event: {event_data['name']}",
                description=event_data['description'],
                color=color,
                timestamp=datetime.now()
            )
            
            treasury_impact = event_data.get('treasury_impact', 0)
            if treasury_impact != 0:
                embed.add_field(
                    name="Treasury Impact",
                    value=f"${treasury_impact:+,}",
                    inline=True
                )
            
            status_impact = event_data.get('status_impact')
            if status_impact:
                embed.add_field(
                    name="Economic Status Change",
                    value=status_impact,
                    inline=True
                )
            
            embed.set_footer(text="Economic Event System")
            
            await target_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error sending event notification to guild {guild.id}: {e}")
    
    @commands.command(name="trigger_event")
    @commands.has_permissions(administrator=True)
    async def manual_trigger_event(self, ctx, event_type: str = "random"):
        """Manually trigger an economic event (admin only)."""
        if event_type and event_type.lower() not in ['positive', 'negative', 'neutral']:
            await ctx.send("❌ Event type must be 'positive', 'negative', or 'neutral'.")
            return
        
        try:
            if event_type:
                if event_type.lower() == 'positive':
                    await self.trigger_positive_event(ctx.guild.id)
                else:
                    # For manual triggers, just use the random system
                    await self.trigger_random_event(ctx.guild.id)
            else:
                await self.trigger_random_event(ctx.guild.id)
            
            await ctx.send("✅ Economic event has been triggered!")
            
        except Exception as e:
            await ctx.send("❌ An error occurred while triggering the event.")
    
    @app_commands.command(name="next-event", description="Check when the next random event is scheduled")
    async def next_event(self, interaction: discord.Interaction):
        """Check when the next random economic event is scheduled."""
        try:
            guild_id = interaction.guild.id
            next_event_time = await self.bot.db.get_next_event_time(guild_id)
            
            if next_event_time is None:
                await interaction.response.send_message(
                    "⏰ Next economic event will be scheduled soon.",
                    ephemeral=True
                )
                return
            
            now = datetime.now()
            if next_event_time <= now:
                await interaction.response.send_message(
                    "⏰ An economic event should occur soon!",
                    ephemeral=True
                )
                return
            
            time_until = next_event_time - now
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏰ Next Economic Event",
                description=f"The next random economic event is scheduled to occur in **{hours}h {minutes}m**.",
                color=BOT_COLOR
            )
            embed.add_field(
                name="Event Window",
                value="Random events occur every 1-24 hours",
                inline=True
            )
            embed.set_footer(text="Economic Event System")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while checking the event schedule.",
                ephemeral=True
            )
    
    @app_commands.command(name="recent-events", description="View recent economic events")
    async def recent_events(self, interaction: discord.Interaction):
        """Display recent economic events for this server."""
        try:
            guild_id = interaction.guild.id
            events = await self.bot.db.get_recent_events(guild_id, 10)
            
            if not events:
                await interaction.response.send_message(
                    "📋 No recent economic events found.",
                    ephemeral=True
                )
                return
            
            embed = self.embeds.create_events_history_embed(events, interaction.guild.name)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching recent events.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Events(bot))
