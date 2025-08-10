#!/usr/bin/env python3
"""
Discord Economic Simulation Bot
Inspired by The New Order and Millennium Dawn mods
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot import EconomicBot

def main():
    """Main entry point for the bot."""
    bot = EconomicBot()
    
    # Get token from environment
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set!")
        print("Please set your Discord bot token in the environment variables.")
        sys.exit(1)
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\nBot shutdown requested by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
