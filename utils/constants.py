"""
Constants and configuration values for the economic bot
"""

import discord

# Bot Configuration
BOT_COLOR = 0x2F3136  # Discord dark theme color
BOT_VERSION = "1.0.0"

# Economic Status Levels (in order from worst to best)
ECONOMIC_STATUS = [
    "Economic Crash",
    "Economic Recession", 
    "Economic Stagnation",
    "Stable Growth",
    "Rapid Growth",
    "Economic Boom"
]

# Trade Policy Levels (from most restrictive to most open)
TRADE_POLICIES = [
    "Autarky",
    "Limited Trade",
    "Controlled Trade", 
    "Balanced Trade",
    "Open Trade",
    "Free Trade"
]

# Color scheme for economic statuses
ECONOMIC_STATUS_COLORS = {
    "Economic Crash": 0xFF0000,      # Red
    "Economic Recession": 0xFF4500,   # Orange Red
    "Economic Stagnation": 0xFFA500,  # Orange
    "Stable Growth": 0x32CD32,        # Lime Green
    "Rapid Growth": 0x00CED1,         # Dark Turquoise
    "Economic Boom": 0xFFD700         # Gold
}

# Color scheme for trade policies
TRADE_POLICY_COLORS = {
    "Autarky": 0x8B0000,           # Dark Red
    "Limited Trade": 0xCD853F,      # Peru
    "Controlled Trade": 0xDAA520,   # Goldenrod
    "Balanced Trade": 0x32CD32,     # Lime Green
    "Open Trade": 0x00CED1,         # Dark Turquoise
    "Free Trade": 0x1E90FF          # Dodger Blue
}

# Administrative action base costs
ADMIN_ACTIONS_COSTS = {
    "mass_message": 2500,
    "server_boost_economic": 5000,
    "server_boost_stability": 7500,
    "server_boost_growth": 10000,
    "emergency_stabilize": 15000,
    "emergency_stimulus": 20000,
    "emergency_crisis": 25000,
    "policy_change": 1000,
    "event_trigger": 3000
}

# Economic status effects on treasury (per hour)
ECONOMIC_STATUS_EFFECTS = {
    "Economic Crash": {
        "treasury_per_hour": -200,
        "income_multiplier": 0.1,
        "cost_multiplier": 2.0,
        "stability": 0.1
    },
    "Economic Recession": {
        "treasury_per_hour": -100,
        "income_multiplier": 0.5,
        "cost_multiplier": 1.5,
        "stability": 0.3
    },
    "Economic Stagnation": {
        "treasury_per_hour": -25,
        "income_multiplier": 0.8,
        "cost_multiplier": 1.2,
        "stability": 0.6
    },
    "Stable Growth": {
        "treasury_per_hour": 50,
        "income_multiplier": 1.0,
        "cost_multiplier": 1.0,
        "stability": 0.8
    },
    "Rapid Growth": {
        "treasury_per_hour": 150,
        "income_multiplier": 1.3,
        "cost_multiplier": 0.8,
        "stability": 0.7
    },
    "Economic Boom": {
        "treasury_per_hour": 300,
        "income_multiplier": 1.8,
        "cost_multiplier": 0.6,
        "stability": 0.6
    }
}

# Trade policy effects
TRADE_POLICY_EFFECTS = {
    "Autarky": {
        "treasury_per_hour": -50,
        "stability_bonus": 30,
        "growth_modifier": -20,
        "description": "Self-reliant but limited growth potential"
    },
    "Limited Trade": {
        "treasury_per_hour": -20,
        "stability_bonus": 15,
        "growth_modifier": -10,
        "description": "Controlled exposure to international markets"
    },
    "Controlled Trade": {
        "treasury_per_hour": 0,
        "stability_bonus": 5,
        "growth_modifier": 0,
        "description": "Balanced approach with government oversight"
    },
    "Balanced Trade": {
        "treasury_per_hour": 25,
        "stability_bonus": 0,
        "growth_modifier": 5,
        "description": "Moderate openness with balanced benefits"
    },
    "Open Trade": {
        "treasury_per_hour": 75,
        "stability_bonus": -10,
        "growth_modifier": 15,
        "description": "Increased opportunities but higher volatility"
    },
    "Free Trade": {
        "treasury_per_hour": 150,
        "stability_bonus": -25,
        "growth_modifier": 25,
        "description": "Maximum growth potential with increased risk"
    }
}

# Event intervals (in hours)
EVENT_INTERVALS = {
    "min_hours": 1,
    "max_hours": 24
}

# Treasury limits
TREASURY_LIMITS = {
    "minimum": 0,
    "maximum": 10000000,  # 10 million cap
    "starting_amount": 10000,
    "bankruptcy_threshold": 0
}

# Member contribution rates (per active member per interval)
MEMBER_CONTRIBUTION = {
    "base_income_per_member": 10,  # Base income per member per 5-minute interval
    "max_members_counted": 1000,   # Maximum members that contribute to income
    "bot_exclusion": True          # Exclude bots from member count
}

# Passive income settings
PASSIVE_INCOME = {
    "base_rate": 10,        # Base income per member
    "interval_minutes": 5,  # How often passive income is generated
    "max_multiplier": 2.0,  # Maximum multiplier from economic status
    "min_multiplier": 0.1   # Minimum multiplier from economic status
}

# Real-time update intervals
UPDATE_INTERVALS = {
    "treasury_update_seconds": 30,     # How often treasury updates
    "passive_income_minutes": 5,       # How often passive income generates
    "event_check_hours": 1,            # How often to check for scheduled events
    "status_check_hours": 2            # How often to recalculate economic status
}

# Chart configuration
CHART_CONFIG = {
    "default_history_hours": 24,
    "max_history_hours": 168,  # 1 week
    "min_history_hours": 1,
    "chart_width": 12,
    "chart_height": 6,
    "dpi": 150
}

# Permission requirements
PERMISSIONS = {
    "admin_commands": ["administrator"],
    "economic_influence_cooldown": 6,  # hours
    "petition_supporters_required": {
        "lower_costs": 10,
        "increase_income": 15,
        "stimulus": 20,
        "trade_review": 12
    }
}

# Economic event probabilities by status
EVENT_PROBABILITIES = {
    "Economic Crash": {
        "positive": 0.4,
        "negative": 0.1,
        "neutral": 0.5
    },
    "Economic Recession": {
        "positive": 0.35,
        "negative": 0.2,
        "neutral": 0.45
    },
    "Economic Stagnation": {
        "positive": 0.3,
        "negative": 0.3,
        "neutral": 0.4
    },
    "Stable Growth": {
        "positive": 0.25,
        "negative": 0.25,
        "neutral": 0.5
    },
    "Rapid Growth": {
        "positive": 0.2,
        "negative": 0.35,
        "neutral": 0.45
    },
    "Economic Boom": {
        "positive": 0.15,
        "negative": 0.4,
        "neutral": 0.45
    }
}

# Database configuration
DATABASE_CONFIG = {
    "db_name": "economic_bot.db",
    "backup_interval_hours": 24,
    "cleanup_old_data_days": 30,
    "max_history_entries": 10000
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "economic_bot.log",
    "max_file_size": "10MB",
    "backup_count": 5
}

# API rate limits
RATE_LIMITS = {
    "commands_per_user_per_minute": 10,
    "expensive_commands_per_user_per_hour": 5,
    "admin_commands_per_user_per_hour": 20
}

# Feature flags
FEATURES = {
    "enable_random_events": True,
    "enable_passive_income": True,
    "enable_real_time_updates": True,
    "enable_economic_influence": True,
    "enable_trade_policies": True,
    "enable_admin_costs": True,
    "enable_charts": True,
    "enable_forecasting": True
}

# Error messages
ERROR_MESSAGES = {
    "insufficient_funds": "❌ Insufficient treasury funds to complete this action.",
    "permission_denied": "❌ You don't have permission to use this command.",
    "cooldown_active": "⏰ This command is on cooldown. Try again later.",
    "invalid_input": "❌ Invalid input provided. Please check your parameters.",
    "database_error": "❌ A database error occurred. Please try again later.",
    "general_error": "❌ An unexpected error occurred. Please contact an administrator."
}

# Success messages
SUCCESS_MESSAGES = {
    "action_completed": "✅ Action completed successfully!",
    "policy_changed": "✅ Policy has been updated.",
    "treasury_updated": "✅ Treasury has been updated.",
    "event_triggered": "✅ Economic event has been triggered."
}

# Embed limits (Discord restrictions)
EMBED_LIMITS = {
    "title_max": 256,
    "description_max": 4096,
    "field_name_max": 256,
    "field_value_max": 1024,
    "footer_max": 2048,
    "author_name_max": 256,
    "max_fields": 25
}
