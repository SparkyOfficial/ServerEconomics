"""
Trade policy management system
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from chart_generator import ChartGenerator
from utils.embeds import EconomicEmbeds
from utils.constants import TRADE_POLICIES, TRADE_POLICY_EFFECTS, BOT_COLOR

class Trade(commands.Cog):
    """Trade policy management commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.chart_gen = ChartGenerator()
        self.embeds = EconomicEmbeds()
    
    @app_commands.command(name="trade-policy", description="View current trade policy status")
    async def trade_policy_status(self, interaction: discord.Interaction):
        """Display current trade policy and its effects."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Generate trade policy chart
            chart_file = await self.chart_gen.generate_trade_policy_chart(
                economy['trade_policy'], interaction.guild.name
            )
            
            # Create embed with trade policy information
            embed = self.embeds.create_trade_policy_embed(economy)
            
            await interaction.response.send_message(embed=embed, file=chart_file)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching trade policy data.",
                ephemeral=True
            )
    
    @app_commands.command(name="change-trade-policy", description="[ADMIN] Change the server's trade policy")
    @app_commands.describe(new_policy="New trade policy to implement")
    @app_commands.choices(new_policy=[
        app_commands.Choice(name="Autarky (Complete Trade Isolation)", value="Autarky"),
        app_commands.Choice(name="Limited Trade (Restricted Partners)", value="Limited Trade"),
        app_commands.Choice(name="Controlled Trade (Government Oversight)", value="Controlled Trade"),
        app_commands.Choice(name="Balanced Trade (Moderate Openness)", value="Balanced Trade"),
        app_commands.Choice(name="Open Trade (Low Barriers)", value="Open Trade"),
        app_commands.Choice(name="Free Trade (No Barriers)", value="Free Trade")
    ])
    @app_commands.default_permissions(administrator=True)
    async def change_trade_policy(self, interaction: discord.Interaction, new_policy: str):
        """Change the server's trade policy (admin only)."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            current_policy = economy['trade_policy']
            
            if new_policy == current_policy:
                await interaction.response.send_message(
                    f"❌ The trade policy is already set to {new_policy}.",
                    ephemeral=True
                )
                return
            
            # Calculate transition effects
            effects = self.bot.economic_engine.calculate_trade_policy_effects(
                current_policy, new_policy
            )
            
            transition_cost = effects['transition_cost']
            
            # Check if enough treasury for transition
            if economy['treasury'] < transition_cost:
                await interaction.response.send_message(
                    f"❌ Insufficient treasury funds for trade policy transition!\n"
                    f"Required: ${transition_cost:,}\n"
                    f"Available: ${economy['treasury']:,}",
                    ephemeral=True
                )
                return
            
            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Trade Policy Change",
                description=f"This will change the trade policy from **{current_policy}** to **{new_policy}**.",
                color=0xFFA500
            )
            embed.add_field(name="Transition Cost", value=f"${transition_cost:,}", inline=True)
            embed.add_field(
                name="New Income Effect", 
                value=f"${effects['treasury_change_per_hour']:+,}/hour", 
                inline=True
            )
            
            # Show policy effects
            new_effects = effects['new_effects']
            effects_text = []
            if new_effects.get('treasury_per_hour'):
                effects_text.append(f"Treasury: {new_effects['treasury_per_hour']:+,}/hour")
            if new_effects.get('stability_bonus'):
                effects_text.append(f"Stability: {new_effects['stability_bonus']:+}%")
            if new_effects.get('growth_modifier'):
                effects_text.append(f"Growth: {new_effects['growth_modifier']:+}%")
            
            if effects_text:
                embed.add_field(name="Policy Effects", value="\n".join(effects_text), inline=False)
            
            view = ConfirmTradePolicyView(
                self.bot, guild_id, interaction.user.id, 
                current_policy, new_policy, transition_cost
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing the trade policy change.",
                ephemeral=True
            )
    
    @app_commands.command(name="trade-effects", description="Compare effects of different trade policies")
    async def trade_effects_comparison(self, interaction: discord.Interaction):
        """Display a comparison of all trade policy effects."""
        try:
            embed = discord.Embed(
                title="📊 Trade Policy Effects Comparison",
                description="Compare the effects of different trade policies",
                color=BOT_COLOR
            )
            
            for policy in TRADE_POLICIES:
                effects = TRADE_POLICY_EFFECTS.get(policy, {})
                
                effect_text = []
                if effects.get('treasury_per_hour'):
                    effect_text.append(f"Treasury: {effects['treasury_per_hour']:+,}/hour")
                if effects.get('stability_bonus'):
                    effect_text.append(f"Stability: {effects['stability_bonus']:+}%")
                if effects.get('growth_modifier'):
                    effect_text.append(f"Growth: {effects['growth_modifier']:+}%")
                
                if not effect_text:
                    effect_text = ["Neutral effects"]
                
                embed.add_field(
                    name=policy,
                    value="\n".join(effect_text),
                    inline=True
                )
            
            embed.set_footer(text="Use /change-trade-policy to modify your server's policy")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while generating the trade effects comparison.",
                ephemeral=True
            )
    
    @app_commands.command(name="trade-history", description="View trade policy change history")
    async def trade_history(self, interaction: discord.Interaction):
        """Display the history of trade policy changes."""
        try:
            guild_id = interaction.guild.id
            
            # Get policy history from database
            # This would need to be implemented in the database manager
            # For now, we'll show current policy info
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            embed = discord.Embed(
                title="📋 Trade Policy History",
                description=f"Trade policy change history for {interaction.guild.name}",
                color=BOT_COLOR
            )
            
            embed.add_field(
                name="Current Policy",
                value=economy['trade_policy'],
                inline=True
            )
            
            embed.add_field(
                name="In Effect Since",
                value=economy['last_update'],
                inline=True
            )
            
            embed.set_footer(text="Detailed history tracking coming soon")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching trade policy history.",
                ephemeral=True
            )

class ConfirmTradePolicyView(discord.ui.View):
    """Confirmation view for trade policy changes."""
    
    def __init__(self, bot, guild_id: int, user_id: int, current_policy: str, new_policy: str, cost: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.current_policy = current_policy
        self.new_policy = new_policy
        self.cost = cost
    
    @discord.ui.button(label="Confirm Change", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_policy_change(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the command user can confirm this change.",
                ephemeral=True
            )
            return
        
        try:
            # Deduct transition cost
            success = await self.bot.db.deduct_treasury(self.guild_id, self.cost)
            
            if not success:
                await interaction.response.send_message(
                    "❌ Insufficient treasury funds to complete the policy change.",
                    ephemeral=True
                )
                return
            
            # Update trade policy
            await self.bot.db.update_trade_policy(self.guild_id, self.new_policy)
            
            # Log the action
            await self.bot.db.log_admin_action(
                guild_id=self.guild_id,
                user_id=self.user_id,
                action_type="trade_policy_change",
                cost=self.cost,
                description=f"Changed trade policy from {self.current_policy} to {self.new_policy}",
                success=True
            )
            
            embed = discord.Embed(
                title="✅ Trade Policy Changed",
                description=f"Trade policy has been changed from **{self.current_policy}** to **{self.new_policy}**.",
                color=0x00FF00
            )
            embed.add_field(name="Transition Cost", value=f"${self.cost:,}", inline=True)
            embed.add_field(name="Changed by", value=f"<@{self.user_id}>", inline=True)
            embed.set_footer(text="New policy effects will take place immediately")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while applying the policy change.",
                ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_policy_change(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the command user can cancel this change.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="❌ Policy Change Cancelled",
            description="Trade policy change has been cancelled.",
            color=0x808080
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Trade(bot))
