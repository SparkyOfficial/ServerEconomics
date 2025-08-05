import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import discord
from discord.ext import commands, tasks
import aiosqlite

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание директорий
Path("data").mkdir(exist_ok=True)
Path("cogs").mkdir(exist_ok=True)
Path("utils").mkdir(exist_ok=True)

class EconomyBot(commands.Bot):
    def __init__(self):
        # Only request the minimum required intents
        intents = discord.Intents.default()
        intents.message_content = True  # For reading message content
        intents.guilds = True           # For server-related events
        intents.members = False         # Disable if not needed for member tracking
        intents.presences = False       # Disable if not needed for presence tracking
        
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
        
        # Инициализация базы данных будет в setup_hook
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных (синхронная версия для совместимости)"""
        pass
    
    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            "initial_treasury": 1000,
            "income_per_member": 2,
            "costs": {
                # Основные действия
                "channel_create": 100,
                "channel_delete": 30,
                "role_assign": 50,
                "role_remove": 25,
                "emoji_create": 200,
                "emoji_delete": 50,
                # Модерация
                "member_ban": 150,
                "member_kick": 75,
                "member_timeout": 40,
                "message_delete": 5,
                "bulk_message_delete": 25,
                # Серверные изменения
                "server_name_change": 300,
                "server_icon_change": 250,
                "webhook_create": 80,
                "integration_add": 120,
                # Автомодерация
                "automod_rule_create": 200,
                "automod_action": 10
            },
            "personal_economy": {
                "starting_balance": 100,
                "work_cooldown_hours": 4,
                "work_min_reward": 50,
                "work_max_reward": 200,
                "daily_reward": 150,
                "tax_rate": 0.05,  # 5% налог с заработка
                "transfer_fee": 0.02  # 2% комиссия за переводы
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
    
    async def init_database_async(self):
        """
        Асинхронная инициализация и миграция базы данных
        
        Создает все необходимые таблицы, если они не существуют,
        и выполняет миграцию данных при необходимости.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            # Включаем поддержку внешних ключей
            await conn.execute('PRAGMA foreign_keys = ON')
            
            # Создаем таблицы в правильном порядке с учетом зависимостей
            tables = [
                # Таблица кошельков пользователей
                '''
                CREATE TABLE IF NOT EXISTS wallets (
                    user_id INTEGER,
                    guild_id INTEGER,
                    balance INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    last_work TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
                ''',
                
                # Таблица экономики сервера
                '''
                CREATE TABLE IF NOT EXISTS economy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER UNIQUE,
                    treasury INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                
                # Единая таблица для ВСЕХ транзакций
                '''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    from_user_id INTEGER,      -- NULL для операций с казной
                    to_user_id INTEGER,        -- NULL для операций с казной
                    amount INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL, -- 'treasury_income', 'treasury_expense', 'transfer', 'work', 'daily', 'tax', etc.
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES economy(guild_id) ON DELETE CASCADE
                )
                ''',
                
                # Таблица модификаторов экономики
                '''
                CREATE TABLE IF NOT EXISTS economic_modifiers (
                    guild_id INTEGER,
                    modifier_type TEXT,  -- 'income_multiplier', 'cost_reduction', 'tax_rate', etc.
                    value REAL NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    created_by INTEGER,
                    event_id INTEGER,
                    PRIMARY KEY (guild_id, modifier_type),
                    FOREIGN KEY (guild_id) REFERENCES economy(guild_id) ON DELETE CASCADE
                )
                ''',
                
                # Таблица экономических событий
                '''
                CREATE TABLE IF NOT EXISTS economic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    event_type TEXT,
                    effect INTEGER,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    FOREIGN KEY (guild_id) REFERENCES economy(guild_id) ON DELETE CASCADE
                )
                ''',
                
                # Таблица кд для команд экономического влияния
                '''
                CREATE TABLE IF NOT EXISTS influence_cooldowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    command_name TEXT NOT NULL,
                    cooldown_until DATETIME NOT NULL,
                    UNIQUE(guild_id, user_id, command_name),
                    FOREIGN KEY (guild_id) REFERENCES economy(guild_id) ON DELETE CASCADE
                )
                '''
            ]
            
            # Выполняем создание всех таблиц
            for table_sql in tables:
                try:
                    await conn.execute(table_sql)
                except aiosqlite.Error as e:
                    print(f"Ошибка при создании таблицы: {e}")
            
            # Создаем индексы для ускорения запросов
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_transactions_guild ON transactions(guild_id)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user_id)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user_id)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_economic_events_guild ON economic_events(guild_id)',
                'CREATE INDEX IF NOT EXISTS idx_economic_events_user ON economic_events(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_economic_modifiers_guild ON economic_modifiers(guild_id)'
            ]
            
            for index_sql in indexes:
                try:
                    await conn.execute(index_sql)
                except aiosqlite.Error as e:
                    print(f"Ошибка при создании индекса: {e}")
            
            # Проверяем, нужно ли мигрировать данные из старой схемы
            try:
                # Проверяем существование старой таблицы транзакций
                cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions_old'")
                if await cursor.fetchone() is None:
                    # Проверяем, есть ли старая таблица транзакций
                    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
                    if await cursor.fetchone() is not None:
                        # Мигрируем данные из старой таблицы
                        await conn.execute('''
                            INSERT INTO transactions 
                            (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                            SELECT 
                                guild_id, 
                                NULL as from_user_id, 
                                NULL as to_user_id, 
                                amount, 
                                CASE 
                                    WHEN amount < 0 THEN 'treasury_expense' 
                                    ELSE 'treasury_income' 
                                END as transaction_type,
                                COALESCE(description, 'Миграция из старой схемы') as description,
                                COALESCE(timestamp, CURRENT_TIMESTAMP) as timestamp
                            FROM transactions
                            WHERE guild_id IS NOT NULL
                        ''')
                        
                        # Переименовываем старую таблицу, чтобы не мигрировать повторно
                        await conn.execute("ALTER TABLE transactions RENAME TO transactions_old")
                        print("Успешно мигрированы данные из старой таблицы транзакций")
            except aiosqlite.Error as e:
                print(f"Ошибка при миграции данных: {e}")
            
            await conn.commit()
    
    async def setup_hook(self):
        """
        Загрузка cogs и запуск задач
        
        Этот метод вызывается при запуске бота и выполняет:
        1. Инициализацию базы данных (создание таблиц, миграцию данных)
        2. Загрузку всех когов
        3. Запуск фоновых задач
        """
        print("Инициализация базы данных...")
        try:
            await self.init_database_async()
            print("База данных успешно инициализирована")
        except Exception as e:
            print(f"Критическая ошибка при инициализации БД: {e}")
            raise
        
        # Загружаем коги
        cogs = [
            'cogs.economy',
            'cogs.events',
            'cogs.visualization',
            'cogs.personal',
            'cogs.economic_influence'
        ]
        
        print("Загрузка когов...")
        for extension in cogs:
            try:
                await self.load_extension(extension)
                print(f'  ✓ {extension}')
            except Exception as e:
                print(f'  ✗ {extension}: {str(e)}')
        
        # Запускаем фоновые задачи, если они не запущены
        print("Запуск фоновых задач...")
        if not self.economy_update.is_running():
            self.economy_update.start()
            print("  ✓ Задача обновления экономики запущена")
            
        if not self.chart_update.is_running():
            self.chart_update.start()
            print("  ✓ Задача обновления графиков запущена")
            
        if not self.random_events.is_running():
            self.random_events.start()
            print("  ✓ Задача случайных событий запущена")
        
        # Синхронизируем команды с Discord
        print("Синхронизация команд с Discord...")
        try:
            synced = await self.tree.sync()
            print(f"  Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"  Ошибка при синхронизации команд: {e}")
    
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
        """Обновление казны сервера с учетом модификаторов экономики"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Получение текущей казны
            cursor = await conn.execute(
                "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
                (guild.id,)
            )
            result = await cursor.fetchone()
            current_treasury = result[0] if result else self.config["initial_treasury"]
            await cursor.close()
            
            # Получение активных модификаторов экономики
            cursor = await conn.execute(
                """
                SELECT modifier_type, value 
                FROM economic_modifiers 
                WHERE guild_id = ? 
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """,
                (guild.id,)
            )
            
            # Инициализация модификаторов
            income_multiplier = 1.0
            cost_reduction = 0.0
            tax_rate = 0.1  # Базовая ставка налогов 10%
            
            # Применение модификаторов
            modifiers = await cursor.fetchall()
            await cursor.close()
            
            for modifier_type, value in modifiers:
                if modifier_type == 'income_multiplier':
                    income_multiplier *= value
                elif modifier_type == 'cost_reduction':
                    cost_reduction = min(0.5, cost_reduction + value)  # Максимальное снижение затрат 50%
                elif modifier_type == 'tax_rate':
                    tax_rate = max(0, min(0.5, tax_rate + value))  # Налоги от 0% до 50%
            
            # Расчет базового дохода
            base_income = guild.member_count * self.config["income_per_member"]
            
            # Применение модификаторов дохода
            income = int(base_income * income_multiplier)
            
            # Расчет налогов с пользователей
            cursor = await conn.execute(
                """
                SELECT user_id, balance 
                FROM wallets 
                WHERE guild_id = ? AND balance > 0
                """,
                (guild.id,)
            )
            
            total_tax_income = 0
            users = await cursor.fetchall()
            await cursor.close()
            
            for user_id, balance in users:
                tax_amount = int(balance * tax_rate)
                if tax_amount > 0:
                    # Вычитаем налог у пользователя
                    await conn.execute(
                        "UPDATE wallets SET balance = balance - ? WHERE user_id = ? AND guild_id = ?",
                        (tax_amount, user_id, guild.id)
                    )
                    # Записываем транзакцию
                    await conn.execute(
                        """
                        INSERT INTO transactions 
                        (guild_id, from_user_id, amount, transaction_type, description) 
                        VALUES (?, ?, ?, 'tax', ?)
                        """,
                        (guild.id, user_id, tax_amount, f"Налог {int(tax_rate*100)}%")
                    )
                    total_tax_income += tax_amount
            
            # Обновление казны с учетом дохода и налогов
            new_treasury = current_treasury + income + total_tax_income
            
            # Сохранение в базу
            await conn.execute(
                "INSERT OR REPLACE INTO economy (guild_id, treasury) VALUES (?, ?)",
                (guild.id, new_treasury)
            )
        
            # Логируем доход
            await conn.execute(
                """
                INSERT INTO transactions 
                (guild_id, amount, transaction_type, description)
                VALUES (?, ?, 'income', ?)
                """,
                (guild.id, total_tax_income, f"Налоговые поступления ({int(tax_rate*100)}%)")
            )
        
        # Очистка истекших модификаторов
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                DELETE FROM economic_modifiers 
                WHERE guild_id = ? AND expires_at <= CURRENT_TIMESTAMP
                """,
                (guild.id,)
            )
            await conn.commit()
        
        return True, new_treasury
        
    async def spend_money(self, guild, amount, description, apply_modifiers=True):
        """
        Трата денег из казны с учетом модификаторов экономики
        
        Args:
            guild: Объект гильдии Discord
            amount: Сумма для списания (должна быть положительной)
            description: Описание транзакции
            apply_modifiers: Применять ли модификаторы стоимости
            
        Returns:
            tuple: (success: bool, result: Union[int, str])
                   - success: Успешно ли прошла операция
                   - result: Новый баланс казны или сообщение об ошибке
        """
        if amount < 0:
            # Если сумма отрицательная, используем add_money
            return await self.add_money(guild, -amount, description)
            
        # Применяем модификаторы, если нужно
        if apply_modifiers:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT SUM(value) FROM economic_modifiers 
                    WHERE guild_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    AND modifier_type = 'cost_multiplier'
                """, (guild.id,))
                
                result = await cursor.fetchone()
                await cursor.close()
                if result and result[0]:
                    # Увеличиваем стоимость, если есть модификатор
                    modified_amount = int(amount * (1 + result[0]))
                    description = f"{description} (было {amount}, с модификатором {modified_amount})"
                    amount = modified_amount
        
        # Получаем текущий баланс казны
        current_balance = await self.get_treasury(guild)
        
        # Проверяем, достаточно ли средств
        if current_balance < amount:
            return False, f"Недостаточно средств в казне. Текущий баланс: {current_balance} монет"
        
        # Вычитаем сумму из казны
        new_balance = current_balance - amount
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Обновляем баланс казны
            await conn.execute("""
                INSERT OR REPLACE INTO economy (guild_id, treasury, timestamp)
                VALUES (?, ?, datetime('now'))
            """, (guild.id, new_balance))
            
            # Записываем транзакцию в новом формате
            await conn.execute("""
                INSERT INTO transactions 
                (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                VALUES (?, NULL, NULL, ?, 'treasury_expense', ?, datetime('now'))
            """, (guild.id, amount, description))
            
            await conn.commit()
        
        return True, new_balance
    
    async def add_money(self, guild, amount, description):
        """
        Добавить деньги в казну
        
        Args:
            guild: Объект гильдии Discord
            amount: Сумма для добавления (должна быть положительной)
            description: Описание транзакции
            
        Returns:
            tuple: (success: bool, result: Union[int, str])
                   - success: Успешно ли прошла операция
                   - result: Новый баланс казны или сообщение об ошибке
        """
        if amount <= 0:
            # Если сумма отрицательная, используем spend_money
            return await self.spend_money(guild, -amount, description, apply_modifiers=False)
        
        # Получаем текущий баланс казны
        current_balance = await self.get_treasury(guild)
        
        # Добавляем сумму к казне
        new_balance = current_balance + amount
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Обновляем баланс казны
            await conn.execute("""
                INSERT OR REPLACE INTO economy (guild_id, treasury, timestamp)
                VALUES (?, ?, datetime('now'))
            """, (guild.id, new_balance))
            
            # Записываем транзакцию в новом формате
            await conn.execute("""
                INSERT INTO transactions 
                (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                VALUES (?, NULL, NULL, ?, 'treasury_income', ?, datetime('now'))
            """, (guild.id, amount, description))
            
            await conn.commit()
        
        return True, new_balance
    
    async def get_treasury(self, guild):
        """
        Получение текущего баланса казны
        
        Args:
            guild: Объект гильдии Discord
            
        Returns:
            int: Текущий баланс казны
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT treasury 
                FROM economy 
                WHERE guild_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
                """,
                (guild.id,)
            )
            result = await cursor.fetchone()
            await cursor.close()
            
            if result:
                return result[0]
            else:
                # Если записей о казне еще нет, создаем начальную запись
                initial_balance = self.config.get("initial_treasury", 1000)  # Значение по умолчанию
                
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO economy (guild_id, treasury, timestamp)
                    VALUES (?, ?, datetime('now'))
                    """, 
                    (guild.id, initial_balance)
                )
                await conn.commit()
                
                return initial_balance
    
    async def get_user_balance(self, guild, user):
        """
        Получить баланс пользователя
        
        Args:
            guild: Объект гильдии Discord
            user: Объект пользователя Discord
            
        Returns:
            int: Текущий баланс пользователя
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT balance 
                FROM wallets 
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild.id, user.id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            return result[0] if result else 0
    
    async def create_wallet(self, guild, user):
        """
        Создать кошелек для пользователя с начальным балансом
        
        Args:
            guild: Объект гильдии Discord
            user: Объект пользователя Discord
            
        Returns:
            int: Начальный баланс пользователя
        """
        initial_balance = self.config.get("personal_economy", {}).get("starting_balance", 100)
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Проверяем, не существует ли уже кошелек
            cursor = await conn.execute(
                """
                SELECT 1 FROM wallets 
                WHERE user_id = ? AND guild_id = ?
                """,
                (user.id, guild.id)
            )
            
            if await cursor.fetchone() is None:
                # Создаем новую запись о кошельке
                await conn.execute(
                    """
                    INSERT INTO wallets (user_id, guild_id, balance)
                    VALUES (?, ?, ?)
                    """,
                    (user.id, guild.id, initial_balance)
                )
                
                # Записываем начальную транзакцию
                await conn.execute(
                    """
                    INSERT INTO transactions 
                    (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                    VALUES (?, NULL, ?, ?, 'initial_balance', 'Начальный баланс', datetime('now'))
                    """,
                    (guild.id, user.id, initial_balance)
                )
                
                await conn.commit()
                print(f"Создан новый кошелек для пользователя {user.name} (ID: {user.id}) с балансом {initial_balance} монет")
            else:
                print(f"Кошелек для пользователя {user.name} (ID: {user.id}) уже существует")
                
            return initial_balance   
    
    async def add_user_money(self, guild, user, amount, transaction_type="other", description=""):
        """
        Добавить деньги пользователю
        
        Args:
            guild: Объект гильдии Discord
            user: Объект пользователя Discord
            amount: Количество монет для добавления
            transaction_type: Тип транзакции (по умолчанию "other")
            description: Описание транзакции (по умолчанию пустая строка)
            
        Returns:
            int: Новый баланс пользователя
        """
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
            
        # Рассчитываем налог для определенных типов транзакций
        tax_rate = self.config.get("personal_economy", {}).get("tax_rate", 0.1)
        tax_amount = int(amount * tax_rate) if transaction_type in ["work", "daily"] else 0
        net_amount = amount - tax_amount
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Проверяем существование кошелька
            cursor = await conn.execute(
                "SELECT balance FROM wallets WHERE user_id = ? AND guild_id = ?",
                (user.id, guild.id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            
            if result is None:
                # Если кошелька нет, создаем его
                return await self.create_wallet(guild, user)
            
            # Обновляем баланс пользователя
            cursor = await conn.execute(
                """
                UPDATE wallets 
                SET balance = balance + ? 
                WHERE user_id = ? AND guild_id = ?
                RETURNING balance
                """,
                (net_amount, user.id, guild.id)
            )
            
            result = await cursor.fetchone()
            if not result:
                raise ValueError(f"Не удалось обновить баланс пользователя {user.id}")
                
            new_balance = result[0]
            await cursor.close()
            
            # Логируем основную транзакцию
            await conn.execute(
                """
                INSERT INTO transactions 
                (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                VALUES (?, NULL, ?, ?, ?, ?, datetime('now'))
                """,
                (guild.id, user.id, net_amount, transaction_type, description)
            )
            
            # Если есть налог, добавляем его в казну и логируем
            if tax_amount > 0:
                # Добавляем налог в казну
                await self.add_money(guild, tax_amount, f"Налог с {user.display_name}")
                
                # Логируем налоговую транзакцию
                await conn.execute(
                    """
                    INSERT INTO transactions 
                    (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                    VALUES (?, ?, NULL, ?, 'tax', ?, datetime('now'))
                    """, 
                    (guild.id, user.id, tax_amount, f"Налог ({tax_rate*100:.0f}%) с {transaction_type}")
                )
                
                print(f"Удержан налог {tax_amount} монет с пользователя {user.display_name}")
            
            await conn.commit()
            
        print(f"Добавлено {net_amount} монет пользователю {user.name} (ID: {user.id}). "
                      f"Налог: {tax_amount} монет. Новый баланс: {new_balance}")
                
        return new_balance
    
    async def spend_user_money(self, guild, user, amount, description=""):
        """
        Списать деньги у пользователя
        
        Args:
            guild: Объект гильдии Discord
            user: Объект пользователя Discord
            amount: Количество монет для списания
            description: Описание транзакции
            
        Returns:
            tuple: (success: bool, result: Union[int, str])
                   - success: Успешно ли прошла операция
                   - result: Новый баланс пользователя или сообщение об ошибке
        """
        if amount <= 0:
            return False, "Сумма должна быть положительной"
            
        # Получаем текущий баланс пользователя
        current_balance = await self.get_user_balance(guild, user)
        
        if current_balance < amount:
            return False, f"Недостаточно средств. Текущий баланс: {current_balance} монет"
        
        # Списываем деньги
        new_balance = current_balance - amount
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Обновляем баланс пользователя
            await conn.execute(
                """
                UPDATE wallets 
                SET balance = ? 
                WHERE user_id = ? AND guild_id = ?
                """,
                (new_balance, user.id, guild.id)
            )
            
            # Записываем транзакцию
            await conn.execute(
                """
                INSERT INTO transactions 
                (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                VALUES (?, ?, NULL, ?, 'user_expense', ?, datetime('now'))
                """,
                (guild.id, user.id, amount, description)
            )
            
            await conn.commit()
        
        return True, new_balance
    
    async def transfer_money(self, guild, from_user, to_user, amount, description=""):
        """
        Перевести деньги между пользователями
        
        Args:
            guild: Объект гильдии Discord
            from_user: Объект пользователя-отправителя
            to_user: Объект пользователя-получателя
            amount: Количество монет для перевода
            description: Описание перевода (по умолчанию пустая строка)
            
        Returns:
            tuple: (success: bool, result: Union[int, str])
                   - success: Успешно ли прошла операция
                   - result: Новый баланс отправителя или сообщение об ошибке
        """
        if from_user.id == to_user.id:
            return False, "Нельзя перевести деньги самому себе"
            
        if amount <= 0:
            return False, "Сумма перевода должна быть положительной"
            
        # Получаем текущие балансы
        from_balance = await self.get_user_balance(guild, from_user)
        
        if from_balance < amount:
            return False, f"Недостаточно средств. Текущий баланс: {from_balance} монет"
            
        # Рассчитываем комиссию
        transfer_fee = self.config.get("personal_economy", {}).get("transfer_fee", 0.05)  # 5% комиссии
        fee_amount = int(amount * transfer_fee)
        net_amount = amount - fee_amount
        
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                # Начинаем транзакцию
                await conn.execute("BEGIN")
                
                # Списываем деньги у отправителя
                cursor = await conn.execute(
                    """
                    UPDATE wallets 
                    SET balance = balance - ? 
                    WHERE user_id = ? AND guild_id = ?
                    RETURNING balance
                    """,
                    (amount, from_user.id, guild.id)
                )
                
                from_new_balance = (await cursor.fetchone())[0]
                await cursor.close()
                
                # Добавляем деньги получателю (за вычетом комиссии)
                cursor = await conn.execute(
                    """
                    UPDATE wallets 
                    SET balance = balance + ? 
                    WHERE user_id = ? AND guild_id = ?
                    RETURNING balance
                    """,
                    (net_amount, to_user.id, guild.id)
                )
                
                to_new_balance = (await cursor.fetchone())[0]
                await cursor.close()
                
                # Если есть комиссия, добавляем её в казну
                if fee_amount > 0:
                    await conn.execute(
                        """
                        INSERT OR IGNORE INTO economy (guild_id, treasury, timestamp)
                        VALUES (?, 0, datetime('now'))
                        """,
                        (guild.id,)
                    )
                    
                    await conn.execute(
                        """
                        UPDATE economy 
                        SET treasury = treasury + ?, timestamp = datetime('now')
                        WHERE guild_id = ?
                        """,
                        (fee_amount, guild.id)
                    )
                
                # Логируем перевод
                await conn.execute(
                    """
                    INSERT INTO transactions 
                    (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                    VALUES (?, ?, ?, ?, 'transfer', ?, datetime('now'))
                    """,
                    (guild.id, from_user.id, to_user.id, amount, description)
                )
                
                # Если была комиссия, логируем её отдельно
                if fee_amount > 0:
                    await conn.execute(
                        """
                        INSERT INTO transactions 
                        (guild_id, from_user_id, to_user_id, amount, transaction_type, description, timestamp)
                        VALUES (?, NULL, NULL, ?, 'transfer_fee', ?, datetime('now'))
                        """,
                        (guild.id, fee_amount, f"Комиссия за перевод от {from_user.display_name} к {to_user.display_name}")
                    )
                
                await conn.commit()
                
                print(f"Переведено {amount} монет от {from_user.name} к {to_user.name}.")
                if fee_amount > 0:
                    print(f"Удержана комиссия: {fee_amount} монет")
                
                return True, from_new_balance
                
            except aiosqlite.Error as e:
                await conn.rollback()
                error_msg = f"Ошибка при переводе денег: {e}"
                print(error_msg)
                return False, error_msg
                
            except Exception as e:
                await conn.rollback()
                error_msg = f"Неожиданная ошибка при переводе денег: {e}"
                print(error_msg)
                return False, error_msg

if __name__ == "__main__":
    # Загрузка переменных окружения из .env файла
    from dotenv import load_dotenv
    load_dotenv()
    
    # Отладочный вывод
    token = os.getenv('DISCORD_TOKEN')
    print(f"Токен загружен: {'Да' if token else 'Нет'}")
    print(f"Длина токена: {len(token) if token else 0} символов" )
    print(f"Начинается с: {token[:10]}..." if token else "Токен пуст")
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Файл .env существует: {os.path.exists('.env')}")
    
    # Читаем .env напрямую для отладки
    try:
        with open('.env', 'r') as f:
            print("Содержимое .env:", f.read())
    except Exception as e:
        print(f"Ошибка чтения .env: {e}")
    
    if not token:
        print("Ошибка: Не удалось загрузить токен из переменных окружения")
        print("Проверьте, что файл .env существует и содержит DISCORD_TOKEN")
        exit(1)
        
    bot = EconomyBot()
    
    bot.run(token)
