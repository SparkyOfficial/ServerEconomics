# Economic Discord Bot

## Overview

This is a Discord bot that simulates economic systems inspired by grand strategy games like The New Order (TNO) and Millennium Dawn. The bot manages guild-based economies with treasury systems, trade policies, economic statuses, and interactive events. Users can participate in economic activities, administrators can make policy decisions that affect the treasury, and the system features real-time economic updates with data visualization through charts and graphs.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
The application is built on discord.py using the commands extension framework with application commands (slash commands). The main bot class (`EconomicBot`) inherits from `commands.Bot` and manages the core bot lifecycle, including cog loading and database initialization.

### Database Layer
Uses SQLite with aiosqlite for asynchronous database operations. The database design includes:
- Guild economies table for storing treasury, economic status, and trade policy per Discord server
- Treasury history table for tracking changes over time (used for chart generation)
- Admin actions table for logging administrative decisions and their costs

### Economic Engine
A dedicated `EconomicEngine` class handles all economic calculations including:
- Real-time treasury updates based on time elapsed and current economic factors
- Economic status transitions based on treasury levels and events
- Cost calculations for administrative actions with economic status multipliers
- Base treasury change calculations considering both economic status and trade policy effects

### Modular Cog System
The bot uses Discord.py's cog system for organized command grouping:
- **Treasury**: Treasury monitoring and forecasting commands
- **Trade**: Trade policy management and visualization
- **Economy**: User participation through economic influence actions
- **Administration**: Admin-only commands that cost treasury funds
- **Events**: Random economic events system (positive and negative)

### Data Visualization
Custom chart generation using matplotlib for creating economic data visualizations:
- Treasury history charts showing trends over time
- Trade policy status displays with color-coded indicators
- Economic status visualizations with appropriate color schemes

### Real-time Updates
The bot implements time-based economic changes where treasury values update based on:
- Elapsed time since last update
- Current economic status effects
- Active trade policy impacts
- Automatic economic status transitions based on treasury thresholds

### User Interaction Design
Commands are implemented as slash commands with:
- Role-based permissions (admin commands require administrator permissions)
- User cooldowns for economic influence actions (6-hour cooldowns)
- Ephemeral responses for error messages and cooldown notifications
- Rich embeds with color coding based on economic status

## External Dependencies

### Core Dependencies
- **discord.py**: Discord API wrapper for bot functionality and slash command implementation
- **aiosqlite**: Asynchronous SQLite database operations for persistent data storage
- **matplotlib**: Chart and graph generation for economic data visualization

### System Dependencies
- **asyncio**: Asynchronous programming support built into Python
- **logging**: Built-in Python logging for error tracking and debugging
- **datetime**: Time-based calculations for real-time economic updates
- **random**: Event probability calculations and economic randomization
- **json**: Data serialization for complex database storage
- **pathlib**: File system path management

### Environment Configuration
- **DISCORD_TOKEN**: Environment variable for Discord bot authentication
- **SQLite Database**: Local file-based storage (economic_bot.db)

The bot is designed to be self-contained with no external API dependencies beyond Discord, making it suitable for deployment in various environments while maintaining data persistence through local SQLite storage.