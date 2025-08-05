import discord
from discord.ext import commands, tasks
import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание директорий
Path("data").mkdir(exist_ok=True)
Path("cogs").mkdir(exist_ok=True)
Path("utils").mkdir(exist_ok=True)

class EconomyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.db_path = "data/economy.db"
        self.config_path = "data/config.json"
        self.chart_channel_id = 1402226865023881237
        
        # Загрузка конфигурации
        self.load_config()
        
        # Инициализация базы данных
        self.init_database()
    
    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            "initial_treasury": 1000,
            "income_per_member": 2,
            "costs": {
                "channel_create": 100,
                "channel_delete": 30,
                "role_assign": 50,
                "emoji_create": 200
            },
            "update_interval": 60,  # секунды
            "chart_interval": 600,  # 10 минут
            "event_min_hours": 1,
            "event_max_hours": 12
        }
        
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица экономики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS economy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                treasury INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                amount INTEGER,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица событий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                event_type TEXT,
                description TEXT,
                amount INTEGER,
                status TEXT DEFAULT 'active',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица модификаторов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modifiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                modifier_type TEXT, -- 'income_multiplier', 'cost_reduction'
                value REAL,
                description TEXT,
                expires_at DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def setup_hook(self):
        """Загрузка cogs и запуск задач"""
        # Загрузка cogs
        await self.load_extension('cogs.economy')
        await self.load_extension('cogs.events')
        await self.load_extension('cogs.visualization')
        
        # Запуск задач
        self.economy_update.start()
        self.chart_update.start()
        self.random_events.start()
        
        logger.info("Бот инициализирован и готов к работе")
    
    @tasks.loop(seconds=60)  # Каждую минуту
    async def economy_update(self):
        """Обновление экономики"""
        try:
            for guild in self.guilds:
                await self.update_treasury(guild)
        except Exception as e:
            logger.error(f"Ошибка обновления экономики: {e}")
    
    @tasks.loop(seconds=600)  # Каждые 10 минут
    async def chart_update(self):
        """Отправка графиков"""
        try:
            channel = self.get_channel(self.chart_channel_id)
            if channel:
                from utils.visualization import create_economy_chart
                chart_path = await create_economy_chart(self)
                if chart_path and os.path.exists(chart_path):
                    await channel.send(file=discord.File(chart_path))
                    os.remove(chart_path)
        except Exception as e:
            logger.error(f"Ошибка отправки графика: {e}")
    
    @tasks.loop(hours=1)  # Проверка каждый час
    async def random_events(self):
        """Случайные события"""
        try:
            from utils.events import check_and_trigger_event
            for guild in self.guilds:
                await check_and_trigger_event(self, guild)
        except Exception as e:
            logger.error(f"Ошибка событий: {e}")
    
    async def update_treasury(self, guild):
        """Обновление казны сервера"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получение текущей казны
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        result = cursor.fetchone()
        current_treasury = result[0] if result else self.config["initial_treasury"]
        
        # Получение модификаторов дохода
        cursor.execute(
            "SELECT value FROM modifiers WHERE guild_id = ? AND modifier_type = 'income_multiplier' AND expires_at > CURRENT_TIMESTAMP",
            (guild.id,)
        )
        income_multiplier = 1.0
        for row in cursor.fetchall():
            income_multiplier *= row[0]

        # Расчет дохода
        base_income = guild.member_count * self.config["income_per_member"]
        income = int(base_income * income_multiplier)
        new_treasury = current_treasury + income
        
        # Сохранение в базу
        cursor.execute(
            "INSERT INTO economy (guild_id, treasury) VALUES (?, ?)",
            (guild.id, new_treasury)
        )
        
        cursor.execute(
            "INSERT INTO transactions (guild_id, amount, description) VALUES (?, ?, ?)",
            (guild.id, income, f"Доход от {guild.member_count} участников")
        )
        
        conn.commit()
        conn.close()
    
    async def spend_money(self, guild, amount, description):
        """Трата денег из казны"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получение текущей казны
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        result = cursor.fetchone()
        current_treasury = result[0] if result else self.config["initial_treasury"]
        
        # Получение модификаторов расходов
        cursor.execute(
            "SELECT value, description FROM modifiers WHERE guild_id = ? AND modifier_type = 'cost_reduction' AND expires_at > CURRENT_TIMESTAMP",
            (guild.id,)
        )
        cost_reduction = 1.0
        for row in cursor.fetchall():
            # Предполагаем, что скидки применяются к определенным типам расходов
            # Для простоты, применим все скидки
            cost_reduction *= (1 - row[0]) # value - это % скидки (0.1 = 10%)

        final_amount = int(amount * cost_reduction)

        if current_treasury < final_amount:
            conn.close()
            return False, current_treasury
        
        # Списание средств
        new_treasury = current_treasury - amount
        
        cursor.execute(
            "INSERT INTO economy (guild_id, treasury) VALUES (?, ?)",
            (guild.id, new_treasury)
        )
        
        cursor.execute(
            "INSERT INTO transactions (guild_id, amount, description) VALUES (?, ?, ?)",
            (guild.id, -amount, description)
        )
        
        conn.commit()
        conn.close()
        
        return True, new_treasury
    
    async def get_treasury(self, guild):
        """Получение текущей казны"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else self.config["initial_treasury"]

if __name__ == "__main__":
    bot = EconomyBot()
    
    # Получение токена
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Ошибка: Установите переменную окружения DISCORD_TOKEN")
        print("Или создайте файл .env с токеном бота")
        exit(1)
    
    bot.run(token)
