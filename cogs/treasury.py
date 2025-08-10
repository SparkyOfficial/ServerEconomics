"""
Treasury management commands and functionality
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from chart_generator import ChartGenerator
from utils.embeds import EconomicEmbeds
from utils.constants import ECONOMIC_STATUS, BOT_COLOR

class Treasury(commands.Cog):
    """Treasury management and monitoring commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.chart_gen = ChartGenerator()
        self.embeds = EconomicEmbeds()
    
    @app_commands.command(name="treasury", description="View current treasury status")
    async def treasury_status(self, interaction: discord.Interaction):
        """Display current treasury status with chart."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Generate treasury chart
            history = await self.bot.db.get_treasury_history(guild_id, 24)
            chart_file = await self.chart_gen.generate_treasury_chart(
                history, economy['economic_status'], interaction.guild.name
            )
            
            # Create embed
            embed = self.embeds.create_treasury_embed(economy, interaction.guild.name)
            
            await interaction.followup.send(embed=embed, file=chart_file)
            
        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while fetching treasury data.",
                ephemeral=True
            )
    
    @app_commands.command(name="forecast", description="View 24-hour economic forecast")
    async def economic_forecast(self, interaction: discord.Interaction):
        """Display economic forecast for the next 24 hours."""
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Generate forecast
            forecast = self.bot.economic_engine.get_economic_forecast(economy)
            
            # Generate forecast chart
            chart_file = await self.chart_gen.generate_forecast_chart(
                forecast, economy, interaction.guild.name
            )
            
            # Create embed
            embed = self.embeds.create_forecast_embed(forecast, economy)
            
            await interaction.followup.send(embed=embed, file=chart_file)
            
        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while generating forecast.",
                ephemeral=True
            )
    
    @app_commands.command(name="economic-status", description="View detailed economic status")
    async def economic_status(self, interaction: discord.Interaction):
        """Display detailed economic status information."""
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Generate status chart
            chart_file = await self.chart_gen.generate_economic_status_pie_chart(
                economy['economic_status'], interaction.guild.name
            )
            
            # Get recent events
            recent_events = await self.bot.db.get_recent_events(guild_id, 5)
            
            # Create embed
            embed = self.embeds.create_economic_status_embed(economy, recent_events)
            
            await interaction.followup.send(embed=embed, file=chart_file)
            
        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while fetching economic status.",
                ephemeral=True
            )
    
    @app_commands.command(name="treasury-history", description="View treasury transaction history")
    @app_commands.describe(hours="Hours of history to show (default: 24)")
    async def treasury_history(self, interaction: discord.Interaction, hours: Optional[int] = 24):
        """Display treasury transaction history."""
        if hours < 1 or hours > 168:  # Max 1 week
            await interaction.response.send_message(
                "❌ Hours must be between 1 and 168 (1 week).",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild.id
            history = await self.bot.db.get_treasury_history(guild_id, hours)
            
            if not history:
                await interaction.followup.send(
                    "📊 No treasury history available for the specified period.",
                    ephemeral=True
                )
                return
            
            # Create history embed
            embed = self.embeds.create_treasury_history_embed(history, hours)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred while fetching treasury history.",
                ephemeral=True
            )
    
    @app_commands.command(name="admin-costs", description="View administrative action costs")
    async def admin_costs(self, interaction: discord.Interaction):
        """Display current administrative action costs."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Create costs embed
            embed = self.embeds.create_admin_costs_embed(economy)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching administrative costs.",
                ephemeral=True
            )
    
    @app_commands.command(name="treasury-inject", description="[ADMIN] Manually adjust treasury")
    @app_commands.describe(amount="Amount to add/subtract (use negative for subtraction)")
    @app_commands.default_permissions(administrator=True)
    async def treasury_inject(self, interaction: discord.Interaction, amount: int):
        """Manually adjust treasury (admin only)."""
        if abs(amount) > 1000000:  # Prevent extreme changes
            await interaction.response.send_message(
                "❌ Amount cannot exceed ±1,000,000.",
                ephemeral=True
            )
            return
        
        try:
            guild_id = interaction.guild.id
            
            # Log the action
            await self.bot.db.log_admin_action(
                guild_id=guild_id,
                user_id=interaction.user.id,
                action_type="treasury_injection",
                cost=0,  # No cost for injections
                description=f"Manual treasury adjustment: {amount:+,}",
                success=True
            )
            
            # Update treasury
            await self.bot.db.update_treasury(guild_id, amount)
            
            # Get updated economy
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            embed = discord.Embed(
                title="🏛️ Treasury Adjusted",
                description=f"Manual adjustment applied by {interaction.user.mention}",
                color=BOT_COLOR
            )
            embed.add_field(name="Amount", value=f"${amount:+,}", inline=True)
            embed.add_field(name="New Treasury", value=f"${economy['treasury']:,}", inline=True)
            embed.set_footer(text="Administrative Action")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while adjusting treasury.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Treasury(bot))
