"""
Utility functions for creating Discord embeds
"""

import discord
from datetime import datetime
from typing import List, Dict, Any, Optional

from .constants import (
    BOT_COLOR, ECONOMIC_STATUS_COLORS, TRADE_POLICY_COLORS,
    ECONOMIC_STATUS, TRADE_POLICIES, ADMIN_ACTIONS_COSTS
)

class EconomicEmbeds:
    """Helper class for creating standardized Discord embeds."""
    
    def __init__(self):
        self.bot_color = BOT_COLOR
    
    def create_treasury_embed(self, economy: Dict[str, Any], guild_name: str) -> discord.Embed:
        """Create an embed displaying treasury information."""
        status_color = ECONOMIC_STATUS_COLORS.get(economy['economic_status'], self.bot_color)
        
        embed = discord.Embed(
            title=f"🏛️ {guild_name} - Treasury Status",
            color=status_color,
            timestamp=datetime.now()
        )
        
        # Main treasury info
        embed.add_field(
            name="💰 Current Treasury",
            value=f"${economy['treasury']:,}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Economic Status",
            value=economy['economic_status'],
            inline=True
        )
        
        embed.add_field(
            name="🌐 Trade Policy",
            value=economy['trade_policy'],
            inline=True
        )
        
        # Status indicator
        status_emoji = self.get_status_emoji(economy['economic_status'])
        embed.add_field(
            name="Current Conditions",
            value=f"{status_emoji} {economy['economic_status']}",
            inline=False
        )
        
        embed.set_footer(text="Treasury updates in real-time • Use /forecast for predictions")
        
        return embed
    
    def create_forecast_embed(self, forecast: Dict[str, Any], economy: Dict[str, Any]) -> discord.Embed:
        """Create an embed displaying economic forecast."""
        embed = discord.Embed(
            title="🔮 24-Hour Economic Forecast",
            color=self.bot_color,
            timestamp=datetime.now()
        )
        
        # Current vs predicted
        embed.add_field(
            name="Current Status",
            value=economy['economic_status'],
            inline=True
        )
        
        embed.add_field(
            name="Predicted Status",
            value=forecast['predicted_status'],
            inline=True
        )
        
        embed.add_field(
            name="24h Treasury Change",
            value=f"${forecast['total_24h_change']:+,}",
            inline=True
        )
        
        # Prediction details
        embed.add_field(
            name="Current Treasury",
            value=f"${economy['treasury']:,}",
            inline=True
        )
        
        embed.add_field(
            name="Predicted Treasury",
            value=f"${forecast['predicted_24h_treasury']:,}",
            inline=True
        )
        
        # Trend indicator
        trend_emoji = "📈" if forecast['total_24h_change'] > 0 else "📉" if forecast['total_24h_change'] < 0 else "➡️"
        embed.add_field(
            name="Trend",
            value=f"{trend_emoji} {'Positive' if forecast['total_24h_change'] > 0 else 'Negative' if forecast['total_24h_change'] < 0 else 'Stable'}",
            inline=True
        )
        
        embed.set_footer(text="Forecast based on current economic conditions and historical data")
        
        return embed
    
    def create_economic_status_embed(self, economy: Dict[str, Any], recent_events: List[Dict]) -> discord.Embed:
        """Create an embed showing detailed economic status."""
        status_color = ECONOMIC_STATUS_COLORS.get(economy['economic_status'], self.bot_color)
        
        embed = discord.Embed(
            title="📊 Economic Status Report",
            color=status_color,
            timestamp=datetime.now()
        )
        
        # Main status info
        status_emoji = self.get_status_emoji(economy['economic_status'])
        embed.add_field(
            name="Current Economic Status",
            value=f"{status_emoji} **{economy['economic_status']}**",
            inline=False
        )
        
        embed.add_field(
            name="Treasury",
            value=f"${economy['treasury']:,}",
            inline=True
        )
        
        embed.add_field(
            name="Trade Policy",
            value=economy['trade_policy'],
            inline=True
        )
        
        embed.add_field(
            name="Last Updated",
            value=f"<t:{int(datetime.fromisoformat(economy['last_update']).timestamp())}:R>",
            inline=True
        )
        
        # Recent events
        if recent_events:
            event_text = []
            for event in recent_events[:3]:  # Show last 3 events
                impact = event['treasury_impact']
                impact_str = f"${impact:+,}" if impact != 0 else "No impact"
                event_text.append(f"• **{event['event_name']}** ({impact_str})")
            
            embed.add_field(
                name="Recent Economic Events",
                value="\n".join(event_text),
                inline=False
            )
        
        # Status description
        status_description = self.get_status_description(economy['economic_status'])
        if status_description:
            embed.add_field(
                name="Status Description",
                value=status_description,
                inline=False
            )
        
        embed.set_footer(text="Economic status updates based on treasury trends and events")
        
        return embed
    
    def create_treasury_history_embed(self, history: List[Dict], hours: int) -> discord.Embed:
        """Create an embed showing treasury transaction history."""
        embed = discord.Embed(
            title=f"📈 Treasury History - Last {hours} Hours",
            color=self.bot_color,
            timestamp=datetime.now()
        )
        
        if not history:
            embed.description = "No treasury history available for this period."
            return embed
        
        # Calculate statistics
        current_amount = history[-1]['treasury_amount']
        oldest_amount = history[0]['treasury_amount']
        change = current_amount - oldest_amount
        change_percent = (change / oldest_amount * 100) if oldest_amount > 0 else 0
        
        embed.add_field(
            name="Current Treasury",
            value=f"${current_amount:,}",
            inline=True
        )
        
        embed.add_field(
            name=f"{hours}h Change",
            value=f"${change:+,}",
            inline=True
        )
        
        embed.add_field(
            name="Change %",
            value=f"{change_percent:+.1f}%",
            inline=True
        )
        
        # Show recent entries
        recent_entries = history[-5:]  # Last 5 entries
        history_text = []
        
        for entry in reversed(recent_entries):
            timestamp = datetime.fromisoformat(entry['timestamp'])
            history_text.append(
                f"<t:{int(timestamp.timestamp())}:t> - ${entry['treasury_amount']:,}"
            )
        
        embed.add_field(
            name="Recent Entries",
            value="\n".join(history_text),
            inline=False
        )
        
        embed.set_footer(text="Use /treasury for real-time chart visualization")
        
        return embed
    
    def create_admin_costs_embed(self, economy: Dict[str, Any]) -> discord.Embed:
        """Create an embed showing administrative action costs."""
        embed = discord.Embed(
            title="💼 Administrative Action Costs",
            description="Cost of administrative actions based on current economic status",
            color=self.bot_color,
            timestamp=datetime.now()
        )
        
        # Get cost multiplier
        from ..economic_engine import EconomicEngine
        engine = EconomicEngine(None)  # We only need the method, not the database
        cost_multiplier = engine.get_action_cost_multiplier(economy['economic_status'])
        
        embed.add_field(
            name="Current Economic Status",
            value=economy['economic_status'],
            inline=True
        )
        
        embed.add_field(
            name="Cost Multiplier",
            value=f"{cost_multiplier:.1f}x",
            inline=True
        )
        
        embed.add_field(
            name="Treasury Available",
            value=f"${economy['treasury']:,}",
            inline=True
        )
        
        # Show action costs
        action_costs = []
        for action, base_cost in ADMIN_ACTIONS_COSTS.items():
            final_cost = int(base_cost * cost_multiplier)
            affordable = "✅" if economy['treasury'] >= final_cost else "❌"
            
            action_name = action.replace('_', ' ').title()
            action_costs.append(f"{affordable} **{action_name}**: ${final_cost:,}")
        
        embed.add_field(
            name="Action Costs",
            value="\n".join(action_costs),
            inline=False
        )
        
        embed.set_footer(text="Costs vary based on economic status • ✅ = Affordable")
        
        return embed
    
    def create_action_history_embed(self, actions: List[Dict], guild_name: str) -> discord.Embed:
        """Create an embed showing administrative action history."""
        embed = discord.Embed(
            title=f"📋 {guild_name} - Administrative Action History",
            color=self.bot_color,
            timestamp=datetime.now()
        )
        
        if not actions:
            embed.description = "No administrative actions found."
            return embed
        
        # Calculate total costs
        successful_actions = [a for a in actions if a['success']]
        total_cost = sum(a['cost'] for a in successful_actions)
        
        embed.add_field(
            name="Total Actions",
            value=str(len(actions)),
            inline=True
        )
        
        embed.add_field(
            name="Successful Actions",
            value=str(len(successful_actions)),
            inline=True
        )
        
        embed.add_field(
            name="Total Cost",
            value=f"${total_cost:,}",
            inline=True
        )
        
        # Show recent actions
        action_history = []
        for action in actions[:8]:  # Show last 8 actions
            timestamp = datetime.fromisoformat(action['timestamp'])
            status_emoji = "✅" if action['success'] else "❌"
            
            action_history.append(
                f"{status_emoji} **{action['action_type']}** - ${action['cost']:,}\n"
                f"    <t:{int(timestamp.timestamp())}:R> • <@{action['user_id']}>"
            )
        
        if action_history:
            embed.add_field(
                name="Recent Actions",
                value="\n".join(action_history),
                inline=False
            )
        
        embed.set_footer(text="Administrative actions require treasury funds")
        
        return embed
    
    def create_trade_policy_embed(self, economy: Dict[str, Any]) -> discord.Embed:
        """Create an embed showing trade policy information."""
        policy = economy['trade_policy']
        policy_color = TRADE_POLICY_COLORS.get(policy, self.bot_color)
        
        embed = discord.Embed(
            title="🌐 Trade Policy Status",
            color=policy_color,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Current Policy",
            value=f"**{policy}**",
            inline=True
        )
        
        embed.add_field(
            name="Treasury",
            value=f"${economy['treasury']:,}",
            inline=True
        )
        
        embed.add_field(
            name="Economic Status",
            value=economy['economic_status'],
            inline=True
        )
        
        # Policy description
        policy_descriptions = {
            'Autarky': 'Complete trade isolation - Maximum self-reliance, reduced foreign dependency',
            'Limited Trade': 'Restricted trade with select partners - Controlled market access',
            'Controlled Trade': 'Government oversight of trade - Regulated but open commerce',
            'Balanced Trade': 'Moderate trade openness - Balanced approach to international commerce',
            'Open Trade': 'Low trade barriers - Encourages international business',
            'Free Trade': 'No trade barriers - Maximum market freedom and competition'
        }
        
        description = policy_descriptions.get(policy, "Trade policy effects vary based on global conditions.")
        embed.add_field(
            name="Policy Description",
            value=description,
            inline=False
        )
        
        # Policy position indicator
        policy_index = TRADE_POLICIES.index(policy)
        total_policies = len(TRADE_POLICIES)
        openness_percent = (policy_index / (total_policies - 1)) * 100
        
        embed.add_field(
            name="Trade Openness",
            value=f"{openness_percent:.0f}% Open",
            inline=True
        )
        
        embed.set_footer(text="Use /trade-effects to compare all policies")
        
        return embed
    
    def create_events_history_embed(self, events: List[Dict], guild_name: str) -> discord.Embed:
        """Create an embed showing recent economic events."""
        embed = discord.Embed(
            title=f"📰 {guild_name} - Recent Economic Events",
            color=self.bot_color,
            timestamp=datetime.now()
        )
        
        if not events:
            embed.description = "No recent economic events found."
            return embed
        
        # Calculate event statistics
        positive_events = [e for e in events if e['treasury_impact'] > 0]
        negative_events = [e for e in events if e['treasury_impact'] < 0]
        total_impact = sum(e['treasury_impact'] for e in events)
        
        embed.add_field(
            name="Total Events",
            value=str(len(events)),
            inline=True
        )
        
        embed.add_field(
            name="Net Impact",
            value=f"${total_impact:+,}",
            inline=True
        )
        
        embed.add_field(
            name="Positive/Negative",
            value=f"{len(positive_events)}/{len(negative_events)}",
            inline=True
        )
        
        # Show event details
        event_list = []
        for event in events[:6]:  # Show last 6 events
            timestamp = datetime.fromisoformat(event['timestamp'])
            impact = event['treasury_impact']
            
            if impact > 0:
                impact_emoji = "📈"
                impact_color = "+"
            elif impact < 0:
                impact_emoji = "📉"
                impact_color = ""
            else:
                impact_emoji = "📊"
                impact_color = ""
            
            event_list.append(
                f"{impact_emoji} **{event['event_name']}**\n"
                f"    {impact_color}${impact:,} • <t:{int(timestamp.timestamp())}:R>"
            )
        
        if event_list:
            embed.add_field(
                name="Recent Events",
                value="\n".join(event_list),
                inline=False
            )
        
        embed.set_footer(text="Random events occur every 1-24 hours")
        
        return embed
    
    def get_status_emoji(self, status: str) -> str:
        """Get emoji representation for economic status."""
        status_emojis = {
            "Economic Crash": "💥",
            "Economic Recession": "📉",
            "Economic Stagnation": "😐",
            "Stable Growth": "📈",
            "Rapid Growth": "🚀",
            "Economic Boom": "💰"
        }
        return status_emojis.get(status, "📊")
    
    def get_status_description(self, status: str) -> str:
        """Get description for economic status."""
        descriptions = {
            "Economic Crash": "Severe economic downturn with significant treasury losses and reduced income.",
            "Economic Recession": "Economic decline with negative growth and reduced economic activity.",
            "Economic Stagnation": "Minimal economic growth with limited progress and stability concerns.",
            "Stable Growth": "Healthy economic growth with steady progress and balanced conditions.",
            "Rapid Growth": "Strong economic expansion with increased opportunities and prosperity.",
            "Economic Boom": "Exceptional economic performance with maximum growth and prosperity."
        }
        return descriptions.get(status, "Economic conditions are variable.")
