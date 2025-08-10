"""
Chart generation for economic data visualization
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import discord
from typing import List, Dict, Any
import numpy as np

class ChartGenerator:
    """Generates charts and graphs for economic data."""
    
    def __init__(self):
        # Set matplotlib to use non-interactive backend
        plt.switch_backend('Agg')
        
        # Define color scheme
        self.colors = {
            'Economic Crash': '#FF0000',
            'Economic Recession': '#FF6B6B',
            'Economic Stagnation': '#FFA500',
            'Stable Growth': '#32CD32',
            'Rapid Growth': '#00CED1',
            'Economic Boom': '#FFD700'
        }
        
        self.trade_colors = {
            'Autarky': '#8B0000',
            'Limited Trade': '#CD853F',
            'Controlled Trade': '#DAA520',
            'Balanced Trade': '#32CD32',
            'Open Trade': '#00CED1',
            'Free Trade': '#1E90FF'
        }
    
    async def generate_treasury_chart(self, history_data: List[Dict[str, Any]], 
                                    current_status: str, 
                                    guild_name: str = "Server") -> discord.File:
        """Generate a treasury history chart."""
        if not history_data:
            return await self.generate_empty_chart("No treasury data available")
        
        # Prepare data
        timestamps = [datetime.fromisoformat(h['timestamp']) for h in history_data]
        treasury_values = [h['treasury_amount'] for h in history_data]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#2F3136')
        ax.set_facecolor('#36393F')
        
        # Plot treasury line
        line_color = self.colors.get(current_status, '#32CD32')
        ax.plot(timestamps, treasury_values, color=line_color, linewidth=2, marker='o', markersize=4)
        
        # Fill area under curve
        ax.fill_between(timestamps, treasury_values, alpha=0.3, color=line_color)
        
        # Formatting
        ax.set_title(f'{guild_name} - Treasury History\nCurrent Status: {current_status}', 
                    color='white', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time', color='white')
        ax.set_ylabel('Treasury Amount', color='white')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Style
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        
        # Grid
        ax.grid(True, alpha=0.3, color='white')
        
        # Add current value annotation
        if treasury_values:
            current_value = treasury_values[-1]
            ax.annotate(f'Current: ${current_value:,}',
                       xy=(timestamps[-1], current_value),
                       xytext=(10, 10), textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor=line_color, alpha=0.8),
                       color='white', fontweight='bold')
        
        plt.tight_layout()
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2F3136', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return discord.File(buffer, filename='treasury_chart.png')
    
    async def generate_forecast_chart(self, forecast_data: Dict[str, Any], 
                                    current_economy: Dict[str, Any],
                                    guild_name: str = "Server") -> discord.File:
        """Generate a 24-hour forecast chart."""
        hourly_forecast = forecast_data['hourly_forecast']
        
        # Prepare data
        hours = [h['hour'] for h in hourly_forecast]
        treasury_values = [h['treasury'] for h in hourly_forecast]
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        fig.patch.set_facecolor('#2F3136')
        
        # Main forecast plot
        ax1.set_facecolor('#36393F')
        current_color = self.colors.get(current_economy['economic_status'], '#32CD32')
        predicted_color = self.colors.get(forecast_data['predicted_status'], '#32CD32')
        
        # Create gradient effect
        ax1.plot(hours, treasury_values, color=current_color, linewidth=3)
        ax1.fill_between(hours, treasury_values, alpha=0.4, color=current_color)
        
        # Formatting
        ax1.set_title(f'{guild_name} - 24 Hour Economic Forecast', 
                     color='white', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Treasury Amount', color='white')
        ax1.tick_params(colors='white')
        ax1.grid(True, alpha=0.3, color='white')
        
        # Style axes
        for spine in ax1.spines.values():
            spine.set_color('white')
        
        # Change indicators
        ax2.set_facecolor('#36393F')
        changes = [h['change'] for h in hourly_forecast]
        colors = ['green' if c >= 0 else 'red' for c in changes]
        
        bars = ax2.bar(hours, changes, color=colors, alpha=0.7)
        ax2.set_ylabel('Hourly Change', color='white', fontsize=10)
        ax2.set_xlabel('Hours from Now', color='white')
        ax2.tick_params(colors='white')
        ax2.axhline(y=0, color='white', linestyle='-', alpha=0.5)
        
        for spine in ax2.spines.values():
            spine.set_color('white')
        
        # Add prediction text
        prediction_text = (
            f"Current: {current_economy['economic_status']}\n"
            f"Predicted: {forecast_data['predicted_status']}\n"
            f"24h Change: ${forecast_data['total_24h_change']:,}"
        )
        
        ax1.text(0.02, 0.98, prediction_text, transform=ax1.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', 
                facecolor='black', alpha=0.8), color='white', fontsize=10)
        
        plt.tight_layout()
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2F3136', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return discord.File(buffer, filename='forecast_chart.png')
    
    async def generate_economic_status_pie_chart(self, 
                                               current_status: str,
                                               guild_name: str = "Server") -> discord.File:
        """Generate a pie chart showing economic status distribution."""
        # Create mock data for visual appeal (in real implementation, 
        # this could show historical distribution)
        statuses = list(self.colors.keys())
        
        # Give current status higher weight
        values = [10 if status == current_status else 1 for status in statuses]
        colors = [self.colors[status] for status in statuses]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('#2F3136')
        
        # Create pie chart
        result = ax.pie(values, labels=statuses, colors=colors,
                       autopct='', startangle=90, 
                       textprops={'color': 'white'})
        wedges = result[0]
        texts = result[1] if len(result) > 1 else []
        
        # Highlight current status
        for i, status in enumerate(statuses):
            if status == current_status:
                wedges[i].set_edgecolor('white')
                wedges[i].set_linewidth(3)
        
        ax.set_title(f'{guild_name} - Current Economic Status\n{current_status}', 
                    color='white', fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2F3136', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return discord.File(buffer, filename='economic_status.png')
    
    async def generate_trade_policy_chart(self, current_policy: str,
                                        guild_name: str = "Server") -> discord.File:
        """Generate a trade policy visualization."""
        policies = list(self.trade_colors.keys())
        current_index = policies.index(current_policy) if current_policy in policies else 0
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#2F3136')
        ax.set_facecolor('#36393F')
        
        # Create horizontal bar chart
        y_pos = np.arange(len(policies))
        values = [100 if i == current_index else 20 for i in range(len(policies))]
        colors = [self.trade_colors[policy] for policy in policies]
        
        bars = ax.barh(y_pos, values, color=colors, alpha=0.8)
        
        # Highlight current policy
        bars[current_index].set_alpha(1.0)
        bars[current_index].set_edgecolor('white')
        bars[current_index].set_linewidth(2)
        
        # Formatting
        ax.set_yticks(y_pos)
        ax.set_yticklabels(policies, color='white')
        ax.set_xlabel('Policy Strength', color='white')
        ax.set_title(f'{guild_name} - Trade Policy Status\nCurrent: {current_policy}', 
                    color='white', fontsize=14, fontweight='bold')
        
        # Remove x-axis ticks and labels
        ax.set_xticks([])
        
        # Style
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        
        plt.tight_layout()
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2F3136', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return discord.File(buffer, filename='trade_policy.png')
    
    async def generate_empty_chart(self, message: str) -> discord.File:
        """Generate an empty chart with a message."""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#2F3136')
        ax.set_facecolor('#36393F')
        
        ax.text(0.5, 0.5, message, ha='center', va='center',
               transform=ax.transAxes, color='white', fontsize=16)
        
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2F3136', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return discord.File(buffer, filename='empty_chart.png')
