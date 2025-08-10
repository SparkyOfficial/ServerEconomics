"""
Economic influence and participation commands
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List
import random
from datetime import datetime, timedelta

from utils.embeds import EconomicEmbeds
from utils.constants import BOT_COLOR, ECONOMIC_STATUS

class Economy(commands.Cog):
    """Commands for economic participation and influence."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = EconomicEmbeds()
        self.user_cooldowns = {}  # Simple in-memory cooldown tracking
    
    @app_commands.command(name="economic-influence", description="Attempt to influence the economy (limited uses)")
    @app_commands.describe(influence_type="Type of economic influence to attempt")
    @app_commands.choices(influence_type=[
        app_commands.Choice(name="Market Confidence Boost", value="confidence"),
        app_commands.Choice(name="Investment Drive", value="investment"),
        app_commands.Choice(name="Consumer Spending Push", value="spending"),
        app_commands.Choice(name="Export Promotion", value="export"),
        app_commands.Choice(name="Innovation Initiative", value="innovation")
    ])
    async def economic_influence(self, interaction: discord.Interaction, influence_type: str):
        """Allow users to attempt economic influence."""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # Check cooldown (6 hours per user)
        cooldown_key = f"{user_id}_{guild_id}"
        if cooldown_key in self.user_cooldowns:
            last_use = self.user_cooldowns[cooldown_key]
            if datetime.now() - last_use < timedelta(hours=6):
                remaining = timedelta(hours=6) - (datetime.now() - last_use)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                
                await interaction.response.send_message(
                    f"⏰ You can use economic influence again in {hours}h {minutes}m.",
                    ephemeral=True
                )
                return
        
        try:
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Success chance based on current economic status
            success_rates = {
                "Economic Crash": 0.2,
                "Economic Recession": 0.3,
                "Economic Stagnation": 0.4,
                "Stable Growth": 0.6,
                "Rapid Growth": 0.7,
                "Economic Boom": 0.5  # Harder to improve when already booming
            }
            
            success_rate = success_rates.get(economy['economic_status'], 0.5)
            is_successful = random.random() < success_rate
            
            # Set cooldown
            self.user_cooldowns[cooldown_key] = datetime.now()
            
            influence_effects = {
                'confidence': {
                    'name': 'Market Confidence Boost',
                    'success_treasury': random.randint(500, 1500),
                    'fail_treasury': random.randint(-300, 100),
                    'success_desc': 'boosted market confidence, attracting investments!',
                    'fail_desc': 'failed to convince investors, causing minor uncertainty.'
                },
                'investment': {
                    'name': 'Investment Drive',
                    'success_treasury': random.randint(800, 2000),
                    'fail_treasury': random.randint(-500, 0),
                    'success_desc': 'attracted new investments to the economy!',
                    'fail_desc': 'scared away potential investors with unrealistic promises.'
                },
                'spending': {
                    'name': 'Consumer Spending Push',
                    'success_treasury': random.randint(400, 1200),
                    'fail_treasury': random.randint(-200, 200),
                    'success_desc': 'encouraged consumer spending, boosting local businesses!',
                    'fail_desc': 'created confusion in the marketplace.'
                },
                'export': {
                    'name': 'Export Promotion',
                    'success_treasury': random.randint(600, 1800),
                    'fail_treasury': random.randint(-400, 100),
                    'success_desc': 'successfully promoted exports, bringing in foreign currency!',
                    'fail_desc': 'failed to secure export deals, wasting promotional resources.'
                },
                'innovation': {
                    'name': 'Innovation Initiative',
                    'success_treasury': random.randint(300, 2500),
                    'fail_treasury': random.randint(-600, 200),
                    'success_desc': 'sparked innovation, creating new economic opportunities!',
                    'fail_desc': 'innovation attempt failed, consuming research resources.'
                }
            }
            
            effect = influence_effects[influence_type]
            
            if is_successful:
                treasury_change = effect['success_treasury']
                result_desc = effect['success_desc']
                color = 0x00FF00
                result_title = "✅ Economic Influence Successful!"
            else:
                treasury_change = effect['fail_treasury']
                result_desc = effect['fail_desc']
                color = 0xFF6B6B
                result_title = "❌ Economic Influence Failed"
            
            # Apply treasury change
            await self.bot.db.update_treasury(guild_id, treasury_change)
            
            embed = discord.Embed(
                title=result_title,
                description=f"{interaction.user.mention}'s {effect['name']} {result_desc}",
                color=color
            )
            embed.add_field(name="Treasury Impact", value=f"${treasury_change:+,}", inline=True)
            embed.add_field(name="Success Rate", value=f"{success_rate*100:.0f}%", inline=True)
            embed.add_field(name="Next Attempt", value="6 hours", inline=True)
            embed.set_footer(text=f"Economic Status: {economy['economic_status']}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while processing your economic influence.",
                ephemeral=True
            )
    
    @app_commands.command(name="economic-petition", description="Start a petition to influence economic policy")
    @app_commands.describe(petition_type="Type of petition to start")
    @app_commands.choices(petition_type=[
        app_commands.Choice(name="Lower Administrative Costs", value="lower_costs"),
        app_commands.Choice(name="Increase Passive Income", value="increase_income"),
        app_commands.Choice(name="Economic Stimulus Request", value="stimulus"),
        app_commands.Choice(name="Trade Policy Review", value="trade_review")
    ])
    async def economic_petition(self, interaction: discord.Interaction, petition_type: str):
        """Start a petition for economic changes."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            petition_data = {
                'lower_costs': {
                    'name': 'Lower Administrative Costs',
                    'description': 'Petition to reduce the cost of administrative actions by 25% for one week.',
                    'required_supporters': 10,
                    'effect': 'Reduced admin costs for 1 week'
                },
                'increase_income': {
                    'name': 'Increase Passive Income',
                    'description': 'Petition to temporarily increase passive income generation by 50% for 3 days.',
                    'required_supporters': 15,
                    'effect': '+50% passive income for 3 days'
                },
                'stimulus': {
                    'name': 'Economic Stimulus Request',
                    'description': 'Petition for a one-time economic stimulus package.',
                    'required_supporters': 20,
                    'effect': 'One-time treasury injection of $10,000'
                },
                'trade_review': {
                    'name': 'Trade Policy Review',
                    'description': 'Petition for a review and potential adjustment of current trade policy.',
                    'required_supporters': 12,
                    'effect': 'Allows immediate trade policy change'
                }
            }
            
            petition = petition_data[petition_type]
            
            embed = discord.Embed(
                title=f"📋 Economic Petition: {petition['name']}",
                description=petition['description'],
                color=BOT_COLOR
            )
            embed.add_field(name="Required Supporters", value=str(petition['required_supporters']), inline=True)
            embed.add_field(name="Current Supporters", value="1", inline=True)
            embed.add_field(name="Effect", value=petition['effect'], inline=False)
            embed.add_field(name="Started by", value=interaction.user.mention, inline=True)
            embed.set_footer(text="React with 👍 to support this petition")
            
            await interaction.response.send_message(embed=embed)
            # Note: Add reaction functionality would need to be implemented differently for slash commands
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while starting the petition.",
                ephemeral=True
            )
    
    @app_commands.command(name="market-report", description="View current market conditions and opportunities")
    async def market_report(self, interaction: discord.Interaction):
        """Display current market report with opportunities."""
        try:
            guild_id = interaction.guild.id
            economy = await self.bot.db.get_guild_economy(guild_id)
            
            # Generate market opportunities based on current status
            opportunities = self.generate_market_opportunities(economy)
            
            embed = discord.Embed(
                title="📊 Market Report",
                description=f"Current economic analysis for {interaction.guild.name}",
                color=BOT_COLOR
            )
            
            # Current status
            embed.add_field(
                name="Economic Status", 
                value=economy['economic_status'], 
                inline=True
            )
            embed.add_field(
                name="Trade Policy", 
                value=economy['trade_policy'], 
                inline=True
            )
            embed.add_field(
                name="Treasury", 
                value=f"${economy['treasury']:,}", 
                inline=True
            )
            
            # Market opportunities
            if opportunities:
                opp_text = "\n".join([f"• {opp}" for opp in opportunities[:3]])
                embed.add_field(
                    name="Market Opportunities",
                    value=opp_text,
                    inline=False
                )
            
            # Market sentiment
            sentiment = self.calculate_market_sentiment(economy)
            embed.add_field(name="Market Sentiment", value=sentiment, inline=True)
            
            # Next influence availability
            user_cooldown_key = f"{interaction.user.id}_{guild_id}"
            if user_cooldown_key in self.user_cooldowns:
                next_influence = self.user_cooldowns[user_cooldown_key] + timedelta(hours=6)
                time_until = next_influence - datetime.now()
                if time_until.total_seconds() > 0:
                    hours = int(time_until.total_seconds() // 3600)
                    minutes = int((time_until.total_seconds() % 3600) // 60)
                    embed.add_field(
                        name="Your Next Influence", 
                        value=f"{hours}h {minutes}m", 
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Your Next Influence", 
                        value="Available now!", 
                        inline=True
                    )
            else:
                embed.add_field(
                    name="Your Next Influence", 
                    value="Available now!", 
                    inline=True
                )
            
            embed.set_footer(text="Use /economic-influence to participate in the economy")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while generating the market report.",
                ephemeral=True
            )
    
    def generate_market_opportunities(self, economy: Dict) -> List[str]:
        """Generate market opportunities based on economic status."""
        status = economy['economic_status']
        trade_policy = economy['trade_policy']
        
        opportunities = []
        
        if status in ["Economic Crash", "Economic Recession"]:
            opportunities.extend([
                "Recovery investments showing potential returns",
                "Distressed assets available at discounted prices",
                "Government bailout programs creating opportunities"
            ])
        elif status in ["Economic Stagnation"]:
            opportunities.extend([
                "Innovation sectors showing growth potential",
                "Export markets opening for competitive products",
                "Infrastructure projects seeking funding"
            ])
        elif status in ["Stable Growth", "Rapid Growth", "Economic Boom"]:
            opportunities.extend([
                "Expansion opportunities in growing markets",
                "Technology sector investments trending upward",
                "Consumer spending driving retail growth"
            ])
        
        if trade_policy in ["Free Trade", "Open Trade"]:
            opportunities.append("International trade agreements reducing tariffs")
        elif trade_policy in ["Autarky", "Limited Trade"]:
            opportunities.append("Domestic market protection creating local opportunities")
        
        return opportunities
    
    def calculate_market_sentiment(self, economy: Dict) -> str:
        """Calculate market sentiment descriptor."""
        status = economy['economic_status']
        treasury = economy['treasury']
        
        if status == "Economic Boom":
            return "🔥 Extremely Bullish"
        elif status == "Rapid Growth":
            return "📈 Very Bullish"
        elif status == "Stable Growth":
            return "✅ Cautiously Optimistic"
        elif status == "Economic Stagnation":
            return "😐 Neutral"
        elif status == "Economic Recession":
            return "📉 Bearish"
        else:  # Economic Crash
            return "💥 Extremely Bearish"

async def setup(bot):
    await bot.add_cog(Economy(bot))
