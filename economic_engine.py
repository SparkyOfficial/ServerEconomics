"""
Economic calculation engine for the bot
"""

import random
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from utils.constants import (
    ECONOMIC_STATUS, TRADE_POLICIES, 
    ECONOMIC_STATUS_EFFECTS, TRADE_POLICY_EFFECTS
)

logger = logging.getLogger(__name__)

class EconomicEngine:
    """Handles all economic calculations and status changes."""
    
    def __init__(self, database_manager):
        self.db = database_manager
    
    async def update_real_time_treasury(self, guild_id: int):
        """Update treasury based on real-time factors."""
        try:
            economy = await self.db.get_guild_economy(guild_id)
            
            # Calculate time-based income/expenses
            last_update = datetime.fromisoformat(economy['last_update'])
            now = datetime.now()
            time_diff = (now - last_update).total_seconds() / 3600  # hours
            
            if time_diff < 0.5:  # Less than 30 minutes, no update needed
                return
            
            # Base hourly treasury change
            base_change = self.calculate_base_treasury_change(economy)
            
            # Apply time multiplier
            treasury_change = int(base_change * time_diff)
            
            if treasury_change != 0:
                await self.db.update_treasury(guild_id, treasury_change)
                
                # Check for economic status change
                await self.check_economic_status_change(guild_id)
            
        except Exception as e:
            logger.error(f"Error updating real-time treasury for guild {guild_id}: {e}")
    
    def calculate_base_treasury_change(self, economy: Dict[str, Any]) -> int:
        """Calculate base hourly treasury change."""
        base_change = 0
        
        # Economic status effects
        status_effects = ECONOMIC_STATUS_EFFECTS.get(
            economy['economic_status'], 
            {'treasury_per_hour': 0}
        )
        base_change += status_effects['treasury_per_hour']
        
        # Trade policy effects
        trade_effects = TRADE_POLICY_EFFECTS.get(
            economy['trade_policy'],
            {'treasury_per_hour': 0}
        )
        base_change += trade_effects['treasury_per_hour']
        
        # Random fluctuation (-50% to +50%)
        fluctuation = random.uniform(-0.5, 0.5)
        base_change = int(base_change * (1 + fluctuation))
        
        return base_change
    
    async def check_economic_status_change(self, guild_id: int):
        """Check if economic status should change based on treasury trends."""
        try:
            # Get recent treasury history
            history = await self.db.get_treasury_history(guild_id, 6)  # Last 6 hours
            
            if len(history) < 2:
                return
            
            # Calculate trend
            recent_values = [h['treasury_amount'] for h in history[-3:]]
            older_values = [h['treasury_amount'] for h in history[-6:-3]]
            
            if not older_values:
                return
            
            recent_avg = sum(recent_values) / len(recent_values)
            older_avg = sum(older_values) / len(older_values)
            
            change_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            # Determine new status
            new_status = self.determine_economic_status(change_rate, int(recent_avg))
            
            # Update if changed
            economy = await self.db.get_guild_economy(guild_id)
            if new_status != economy['economic_status']:
                await self.db.update_economic_status(guild_id, new_status)
                logger.info(f"Economic status changed for guild {guild_id}: {new_status}")
        
        except Exception as e:
            logger.error(f"Error checking economic status change for guild {guild_id}: {e}")
    
    def determine_economic_status(self, change_rate: float, current_treasury: int) -> str:
        """Determine economic status based on change rate and current treasury."""
        # Critical thresholds
        if current_treasury <= 0:
            return "Economic Crash"
        elif current_treasury <= 1000:
            return "Economic Recession"
        
        # Based on growth rate
        if change_rate <= -0.3:  # -30% or worse
            return "Economic Recession"
        elif change_rate <= -0.1:  # -10% to -30%
            return "Economic Stagnation"
        elif change_rate <= 0.05:  # -10% to +5%
            return "Stable Growth"
        elif change_rate <= 0.15:  # +5% to +15%
            return "Rapid Growth"
        else:  # +15% or better
            return "Economic Boom"
    
    def get_income_multiplier(self, economic_status: str) -> float:
        """Get income multiplier based on economic status."""
        multipliers = {
            "Economic Crash": 0.1,
            "Economic Recession": 0.5,
            "Economic Stagnation": 0.8,
            "Stable Growth": 1.0,
            "Rapid Growth": 1.3,
            "Economic Boom": 1.8
        }
        return multipliers.get(economic_status, 1.0)
    
    def get_action_cost_multiplier(self, economic_status: str) -> float:
        """Get administrative action cost multiplier."""
        multipliers = {
            "Economic Crash": 2.0,
            "Economic Recession": 1.5,
            "Economic Stagnation": 1.2,
            "Stable Growth": 1.0,
            "Rapid Growth": 0.8,
            "Economic Boom": 0.6
        }
        return multipliers.get(economic_status, 1.0)
    
    async def apply_economic_event(self, guild_id: int, event_data: Dict[str, Any]):
        """Apply the effects of an economic event."""
        try:
            # Apply treasury impact
            if event_data.get('treasury_impact', 0) != 0:
                await self.db.update_treasury(guild_id, event_data['treasury_impact'])
            
            # Apply status impact if specified
            if event_data.get('status_impact'):
                await self.db.update_economic_status(guild_id, event_data['status_impact'])
            
            # Log the event
            await self.db.add_economic_event(
                guild_id=guild_id,
                event_type=event_data['type'],
                event_name=event_data['name'],
                description=event_data['description'],
                treasury_impact=event_data.get('treasury_impact', 0),
                economic_impact=event_data.get('status_impact', 'None')
            )
            
        except Exception as e:
            logger.error(f"Error applying economic event for guild {guild_id}: {e}")
    
    def calculate_trade_policy_effects(self, current_policy: str, new_policy: str) -> Dict[str, Any]:
        """Calculate the effects of changing trade policy."""
        current_effects = TRADE_POLICY_EFFECTS.get(current_policy, {})
        new_effects = TRADE_POLICY_EFFECTS.get(new_policy, {})
        
        # Calculate immediate transition costs
        transition_cost = abs(
            TRADE_POLICIES.index(new_policy) - TRADE_POLICIES.index(current_policy)
        ) * 500
        
        return {
            'transition_cost': transition_cost,
            'new_effects': new_effects,
            'treasury_change_per_hour': new_effects.get('treasury_per_hour', 0) - current_effects.get('treasury_per_hour', 0)
        }
    
    def get_economic_forecast(self, economy: Dict[str, Any]) -> Dict[str, Any]:
        """Generate economic forecast for the next 24 hours."""
        base_change = self.calculate_base_treasury_change(economy)
        
        # Simulate 24 hours
        hourly_changes = []
        current_treasury = economy['treasury']
        
        for hour in range(24):
            # Add some randomness
            hourly_change = base_change + random.randint(-50, 50)
            current_treasury += hourly_change
            hourly_changes.append({
                'hour': hour,
                'change': hourly_change,
                'treasury': max(0, current_treasury)
            })
        
        predicted_status = self.determine_economic_status(
            sum([h['change'] for h in hourly_changes[-6:]]) / (economy['treasury'] or 1),
            current_treasury
        )
        
        return {
            'hourly_forecast': hourly_changes,
            'predicted_24h_treasury': current_treasury,
            'predicted_status': predicted_status,
            'total_24h_change': sum([h['change'] for h in hourly_changes])
        }
