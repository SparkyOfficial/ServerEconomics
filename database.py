"""
Database management for the economic bot
"""

import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the economic bot."""
    
    def __init__(self, db_path: str = "economic_bot.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize the database with all required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Guild economies table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_economies (
                    guild_id INTEGER PRIMARY KEY,
                    treasury INTEGER DEFAULT 10000,
                    economic_status TEXT DEFAULT 'Stable Growth',
                    trade_policy TEXT DEFAULT 'Balanced Trade',
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Treasury history for charts
            await db.execute("""
                CREATE TABLE IF NOT EXISTS treasury_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    treasury_amount INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_economies (guild_id)
                )
            """)
            
            # Administrative actions log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    action_type TEXT,
                    cost INTEGER,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (guild_id) REFERENCES guild_economies (guild_id)
                )
            """)
            
            # Economic events
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    event_type TEXT,
                    event_name TEXT,
                    description TEXT,
                    treasury_impact INTEGER,
                    economic_impact TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_economies (guild_id)
                )
            """)
            
            # Event scheduling
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_schedule (
                    guild_id INTEGER PRIMARY KEY,
                    last_event_time TIMESTAMP,
                    next_event_time TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_economies (guild_id)
                )
            """)
            
            # Economic policies and decisions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economic_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    policy_type TEXT,
                    policy_value TEXT,
                    set_by INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_economies (guild_id)
                )
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def initialize_guild(self, guild_id: int):
        """Initialize a new guild in the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO guild_economies (guild_id)
                VALUES (?)
            """, (guild_id,))
            
            await db.execute("""
                INSERT OR IGNORE INTO event_schedule (guild_id, last_event_time)
                VALUES (?, ?)
            """, (guild_id, datetime.now()))
            
            await db.commit()
    
    async def get_guild_economy(self, guild_id: int) -> Dict[str, Any]:
        """Get the complete economic data for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM guild_economies WHERE guild_id = ?
            """, (guild_id,))
            
            row = await cursor.fetchone()
            if row is None:
                # Initialize guild if not exists
                await self.initialize_guild(guild_id)
                return await self.get_guild_economy(guild_id)
            
            return dict(row)
    
    async def update_treasury(self, guild_id: int, amount: int) -> bool:
        """Update treasury amount. Returns True if successful."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current treasury
            cursor = await db.execute("""
                SELECT treasury FROM guild_economies WHERE guild_id = ?
            """, (guild_id,))
            
            row = await cursor.fetchone()
            if row is None:
                await self.initialize_guild(guild_id)
                current_treasury = 10000
            else:
                current_treasury = row[0]
            
            new_treasury = max(0, current_treasury + amount)
            
            # Update treasury
            await db.execute("""
                UPDATE guild_economies 
                SET treasury = ?, last_update = CURRENT_TIMESTAMP 
                WHERE guild_id = ?
            """, (new_treasury, guild_id))
            
            # Record in history
            await db.execute("""
                INSERT INTO treasury_history (guild_id, treasury_amount)
                VALUES (?, ?)
            """, (guild_id, new_treasury))
            
            await db.commit()
            return True
    
    async def get_treasury_history(self, guild_id: int, hours: int = 24) -> list:
        """Get treasury history for the last N hours."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT treasury_amount, timestamp
                FROM treasury_history
                WHERE guild_id = ? AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp ASC
            """.format(hours), (guild_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def deduct_treasury(self, guild_id: int, amount: int) -> bool:
        """Deduct amount from treasury. Returns True if successful (enough funds)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT treasury FROM guild_economies WHERE guild_id = ?
            """, (guild_id,))
            
            row = await cursor.fetchone()
            if row is None:
                return False
            
            current_treasury = row[0]
            if current_treasury < amount:
                return False
            
            # Deduct amount
            new_treasury = current_treasury - amount
            await db.execute("""
                UPDATE guild_economies 
                SET treasury = ?, last_update = CURRENT_TIMESTAMP 
                WHERE guild_id = ?
            """, (new_treasury, guild_id))
            
            # Record in history
            await db.execute("""
                INSERT INTO treasury_history (guild_id, treasury_amount)
                VALUES (?, ?)
            """, (guild_id, new_treasury))
            
            await db.commit()
            return True
    
    async def log_admin_action(self, guild_id: int, user_id: int, action_type: str, 
                              cost: int, description: str, success: bool = True):
        """Log an administrative action."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO admin_actions 
                (guild_id, user_id, action_type, cost, description, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, user_id, action_type, cost, description, success))
            await db.commit()
    
    async def update_economic_status(self, guild_id: int, status: str):
        """Update the economic status of a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_economies 
                SET economic_status = ?, last_update = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (status, guild_id))
            await db.commit()
    
    async def update_trade_policy(self, guild_id: int, policy: str):
        """Update the trade policy of a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_economies 
                SET trade_policy = ?, last_update = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (policy, guild_id))
            await db.commit()
            
            # Log policy change
            await db.execute("""
                INSERT INTO economic_policies 
                (guild_id, policy_type, policy_value, set_by)
                VALUES (?, ?, ?, ?)
            """, (guild_id, 'trade_policy', policy, 0))  # 0 = system
            await db.commit()
    
    async def add_economic_event(self, guild_id: int, event_type: str, event_name: str,
                               description: str, treasury_impact: int, economic_impact: str):
        """Add an economic event to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO economic_events 
                (guild_id, event_type, event_name, description, treasury_impact, economic_impact)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, event_type, event_name, description, treasury_impact, economic_impact))
            await db.commit()
    
    async def get_recent_events(self, guild_id: int, limit: int = 5) -> list:
        """Get recent economic events for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM economic_events
                WHERE guild_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (guild_id, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_last_event_time(self, guild_id: int) -> Optional[datetime]:
        """Get the last event time for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT last_event_time FROM event_schedule WHERE guild_id = ?
            """, (guild_id,))
            
            row = await cursor.fetchone()
            if row is None or row[0] is None:
                return None
            
            return datetime.fromisoformat(row[0])
    
    async def get_next_event_time(self, guild_id: int) -> Optional[datetime]:
        """Get the next scheduled event time for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT next_event_time FROM event_schedule WHERE guild_id = ?
            """, (guild_id,))
            
            row = await cursor.fetchone()
            if row is None or row[0] is None:
                return None
            
            return datetime.fromisoformat(row[0])
    
    async def set_next_event_time(self, guild_id: int, next_time: datetime):
        """Set the next event time for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO event_schedule 
                (guild_id, last_event_time, next_event_time)
                VALUES (?, ?, ?)
            """, (guild_id, datetime.now().isoformat(), next_time.isoformat()))
            await db.commit()
    
    async def get_admin_action_history(self, guild_id: int, limit: int = 10) -> list:
        """Get recent administrative actions for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM admin_actions
                WHERE guild_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (guild_id, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def close(self):
        """Close database connections (placeholder for connection pooling)."""
        pass
