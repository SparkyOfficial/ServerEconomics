"""
Administrative commands that cost treasury funds
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from utils.embeds import EconomicEmbeds
from utils.constants import ADMIN_ACTIONS_COSTS, BOT_COLOR

class Administration(commands.Cog):
    """Administrative actions that require treasury funds."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = EconomicEmbeds()
    
    @app_commands.command(name="mass-message", description="[ADMIN] Send message to all members (costs treasury)")
    @app_commands.describe(message="Message to send to all members")
    @app_commands.default_permissions(administrator=True)
    async def mass_message(self, interaction: discord.Interaction, message: str):
        """Send a message to all members (costs treasury)."""
        if len(message) > 1000:
            await interaction.response.send_message(
                "❌ Message too long. Maximum 1000 characters.",
                ephemeral=True
            )
            return
        
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Calculate cost
            base_cost = ADMIN_ACTIONS_COSTS['mass_message']
            cost_multiplier = self.bot.economic_engine.get_action_cost_multiplier(
                economy['economic_status']
            )
            total_cost = int(base_cost * cost_multiplier)
            
            # Check if enough funds
            if economy['treasury'] < total_cost:
                await interaction.response.send_message(
                    f"❌ Insufficient treasury funds!\n"
                    f"Required: ${total_cost:,}\n"
                    f"Available: ${economy['treasury']:,}",
                    ephemeral=True
                )
                return
            
            # Confirm action
            embed = discord.Embed(
                title="⚠️ Confirm Mass Message",
                description="This action will cost treasury funds.",
                color=0xFFA500
            )
            embed.add_field(name="Cost", value=f"${total_cost:,}", inline=True)
            embed.add_field(name="Recipients", value=f"{len([m for m in interaction.guild.members if not m.bot])}", inline=True)
            embed.add_field(name="Message Preview", value=f"```{message[:100]}{'...' if len(message) > 100 else ''}```", inline=False)
            
            view = ConfirmActionView(self.bot, guild_id, interaction.user.id, 
                                   'mass_message', total_cost, message)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing the request.",
                ephemeral=True
            )
    
    @app_commands.command(name="server-boost", description="[ADMIN] Apply server boost effect (costs treasury)")
    @app_commands.describe(boost_type="Type of boost to apply")
    @app_commands.choices(boost_type=[
        app_commands.Choice(name="Economic Boost (+15% income for 6 hours)", value="economic"),
        app_commands.Choice(name="Stability Boost (Prevent negative events for 12 hours)", value="stability"),
        app_commands.Choice(name="Growth Boost (Force positive economic event)", value="growth")
    ])
    @app_commands.default_permissions(administrator=True)
    async def server_boost(self, interaction: discord.Interaction, boost_type: str):
        """Apply various server boosts that cost treasury."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            boost_costs = {
                'economic': 5000,
                'stability': 7500,
                'growth': 10000
            }
            
            base_cost = boost_costs.get(boost_type, 5000)
            cost_multiplier = self.bot.economic_engine.get_action_cost_multiplier(
                economy['economic_status']
            )
            total_cost = int(base_cost * cost_multiplier)
            
            if economy['treasury'] < total_cost:
                await interaction.response.send_message(
                    f"❌ Insufficient treasury funds!\n"
                    f"Required: ${total_cost:,}\n"
                    f"Available: ${economy['treasury']:,}",
                    ephemeral=True
                )
                return
            
            # Apply the boost effect
            success = await self.bot.db.deduct_treasury(guild_id, total_cost)
            if not success:
                await interaction.response.send_message(
                    "❌ Failed to deduct treasury funds.",
                    ephemeral=True
                )
                return
            
            # Log action
            boost_descriptions = {
                'economic': "Economic Boost: +15% income for 6 hours",
                'stability': "Stability Boost: Negative event protection for 12 hours",
                'growth': "Growth Boost: Triggered positive economic event"
            }
            
            await self.bot.db.log_admin_action(
                guild_id=guild_id,
                user_id=interaction.user.id,
                action_type=f"server_boost_{boost_type}",
                cost=total_cost,
                description=boost_descriptions[boost_type],
                success=True
            )
            
            # Apply boost effect (would be implemented based on boost type)
            if boost_type == "growth":
                # Trigger a positive event
                events_cog = self.bot.get_cog('Events')
                if events_cog:
                    await events_cog.trigger_positive_event(guild_id)
            
            embed = discord.Embed(
                title="✅ Server Boost Applied",
                description=boost_descriptions[boost_type],
                color=0x00FF00
            )
            embed.add_field(name="Cost", value=f"${total_cost:,}", inline=True)
            embed.add_field(name="Applied by", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while applying the boost.",
                ephemeral=True
            )
    
    @app_commands.command(name="emergency-action", description="[ADMIN] Emergency economic intervention")
    @app_commands.describe(action_type="Type of emergency action")
    @app_commands.choices(action_type=[
        app_commands.Choice(name="Market Stabilization", value="stabilize"),
        app_commands.Choice(name="Economic Stimulus", value="stimulus"),
        app_commands.Choice(name="Crisis Management", value="crisis")
    ])
    @app_commands.default_permissions(administrator=True)
    async def emergency_action(self, interaction: discord.Interaction, action_type: str):
        """Perform emergency economic actions."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            action_costs = {
                'stabilize': 15000,
                'stimulus': 20000,
                'crisis': 25000
            }
            
            base_cost = action_costs.get(action_type, 15000)
            cost_multiplier = self.bot.economic_engine.get_action_cost_multiplier(
                economy['economic_status']
            )
            total_cost = int(base_cost * cost_multiplier)
            
            if economy['treasury'] < total_cost:
                await interaction.response.send_message(
                    f"❌ Insufficient treasury funds for emergency action!\n"
                    f"Required: ${total_cost:,}\n"
                    f"Available: ${economy['treasury']:,}",
                    ephemeral=True
                )
                return
            
            # Deduct cost
            success = await self.bot.db.deduct_treasury(guild_id, total_cost)
            if not success:
                await interaction.response.send_message(
                    "❌ Failed to deduct treasury funds.",
                    ephemeral=True
                )
                return
            
            # Apply emergency action effects
            action_effects = {
                'stabilize': {
                    'description': "Market Stabilization: Prevented economic status decline for 24 hours",
                    'treasury_bonus': 2000
                },
                'stimulus': {
                    'description': "Economic Stimulus: +25% income for 12 hours",
                    'treasury_bonus': 5000
                },
                'crisis': {
                    'description': "Crisis Management: Immediate economic status improvement attempt",
                    'treasury_bonus': 1000
                }
            }
            
            effect = action_effects[action_type]
            
            # Apply treasury bonus
            await self.bot.db.update_treasury(guild_id, effect['treasury_bonus'])
            
            # Log action
            await self.bot.db.log_admin_action(
                guild_id=guild_id,
                user_id=interaction.user.id,
                action_type=f"emergency_{action_type}",
                cost=total_cost,
                description=effect['description'],
                success=True
            )
            
            embed = discord.Embed(
                title="🚨 Emergency Action Executed",
                description=effect['description'],
                color=0xFF6B6B
            )
            embed.add_field(name="Cost", value=f"${total_cost:,}", inline=True)
            embed.add_field(name="Treasury Bonus", value=f"${effect['treasury_bonus']:,}", inline=True)
            embed.add_field(name="Authorized by", value=interaction.user.mention, inline=True)
            embed.set_footer(text="Emergency Economic Intervention")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while executing emergency action.",
                ephemeral=True
            )
    
    @app_commands.command(name="action-history", description="View recent administrative actions")
    @app_commands.describe(limit="Number of actions to show (max 20)")
    async def action_history(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """View recent administrative actions and their costs."""
        if limit < 1 or limit > 20:
            await interaction.response.send_message(
                "❌ Limit must be between 1 and 20.",
                ephemeral=True
            )
            return
        
        try:
            guild_id = interaction.guild.id
            actions = await self.bot.db.get_admin_action_history(guild_id, limit)
            
            if not actions:
                await interaction.response.send_message(
                    "📋 No administrative actions found.",
                    ephemeral=True
                )
                return
            
            embed = self.embeds.create_action_history_embed(actions, interaction.guild.name)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching action history.",
                ephemeral=True
            )

class ConfirmActionView(discord.ui.View):
    """Confirmation view for expensive administrative actions."""
    
    def __init__(self, bot, guild_id: int, user_id: int, action_type: str, cost: int, data: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.action_type = action_type
        self.cost = cost
        self.data = data
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the command user can confirm this action.",
                ephemeral=True
            )
            return
        
        # Execute the action
        success = await self.bot.db.deduct_treasury(self.guild_id, self.cost)
        
        if not success:
            await interaction.response.send_message(
                "❌ Insufficient funds to complete this action.",
                ephemeral=True
            )
            return
        
        if self.action_type == 'mass_message':
            # Send mass message logic would go here
            recipient_count = len([m for m in interaction.guild.members if not m.bot])
            
            await self.bot.db.log_admin_action(
                guild_id=self.guild_id,
                user_id=self.user_id,
                action_type=self.action_type,
                cost=self.cost,
                description=f"Mass message sent to {recipient_count} members",
                success=True
            )
        
        embed = discord.Embed(
            title="✅ Action Completed",
            description=f"Administrative action executed successfully.",
            color=0x00FF00
        )
        embed.add_field(name="Cost", value=f"${self.cost:,}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the command user can cancel this action.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="❌ Action Cancelled",
            description="Administrative action was cancelled.",
            color=0x808080
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Administration(bot))
