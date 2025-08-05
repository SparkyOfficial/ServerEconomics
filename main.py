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

        # Таблица личных кошельков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                balance INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                last_work DATETIME,
                last_daily DATETIME,
                UNIQUE(guild_id, user_id)
            )
        ''')

        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                from_user_id INTEGER,
                to_user_id INTEGER,
                amount INTEGER,
                transaction_type TEXT, -- 'transfer', 'work', 'daily', 'purchase', 'tax'
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица экономических событий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS economic_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                event_type TEXT,  -- 'mass_sale', 'help_fund', 'black_market', 'tax_reform', 'work_brigade', 'info_campaign'
                description TEXT,
                amount INTEGER,
                duration_hours INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME
            )
        ''')

        # Таблица модификаторов экономики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS economic_modifiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                modifier_type TEXT,  -- 'income_multiplier', 'cost_reduction', 'tax_rate', 'market_volatility', 'public_trust'
                value REAL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                created_by INTEGER,
                event_id INTEGER
            )
        ''')

        # Таблица кд для команд экономического влияния
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS influence_cooldowns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                command_name TEXT,
                cooldown_until DATETIME,
                UNIQUE(guild_id, user_id, command_name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def setup_hook(self):
        """Загрузка cogs и запуск задач"""
        # Загрузка cogs
        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.visualization")
        await self.load_extension("cogs.personal")
        await self.load_extension("cogs.economic_influence")
        
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
        """Обновление казны сервера с учетом модификаторов экономики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получение текущей казны
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        result = cursor.fetchone()
        current_treasury = result[0] if result else self.config["initial_treasury"]
        
        # Получение активных модификаторов экономики
        cursor.execute(
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
        for modifier_type, value in cursor.fetchall():
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
        cursor.execute(
            """
            SELECT user_id, balance 
            FROM wallets 
            WHERE guild_id = ? AND balance > 0
            """,
            (guild.id,)
        )
        
        total_tax_income = 0
        for user_id, balance in cursor.fetchall():
            tax_amount = int(balance * tax_rate)
            if tax_amount > 0:
                # Вычитаем налог у пользователя
                cursor.execute(
                    """
                    UPDATE wallets 
                    SET balance = balance - ? 
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (tax_amount, guild.id, user_id)
                )
                # Записываем транзакцию
                cursor.execute(
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
        cursor.execute(
            "INSERT INTO economy (guild_id, treasury) VALUES (?, ?)",
            (guild.id, new_treasury)
        )
        
        # Логируем доход
        cursor.execute(
            """
            INSERT INTO transactions 
            (guild_id, amount, transaction_type, description) 
            VALUES (?, ?, 'income', ?)
            """,
            (guild.id, income, f"Доход от {guild.member_count} участников")
        )
        
        # Логируем налоги, если они были собраны
        if total_tax_income > 0:
            cursor.execute(
                """
                INSERT INTO transactions 
                (guild_id, amount, transaction_type, description) 
                VALUES (?, ?, 'tax_income', ?)
                """,
                (guild.id, total_tax_income, f"Налоговые поступления ({int(tax_rate*100)}%)")
            )
        
        # Очистка истекших модификаторов
        cursor.execute(
            """
            DELETE FROM economic_modifiers 
            WHERE guild_id = ? AND expires_at <= CURRENT_TIMESTAMP
            """,
            (guild.id,)
        )
        
        conn.commit()
        conn.close()
        
        return True, new_treasury
        
    async def spend_money(self, guild, amount, description, apply_modifiers=True):
        """
        Трата денег из казны с учетом модификаторов экономики
        
        Args:
            guild: Объект гильдии Discord
            amount: Сумма для списания
            description: Описание транзакции
            apply_modifiers: Применять ли модификаторы стоимости
            
        Returns:
            tuple: (success: bool, result: Union[int, str])
                   - success: Успешно ли прошла операция
                   - result: Новый баланс казны или сообщение об ошибке
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получение текущей казны
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        result = cursor.fetchone()
        current_treasury = result[0] if result else self.config["initial_treasury"]
        
        # Применение модификаторов стоимости, если требуется
        final_amount = amount
        if apply_modifiers:
            cursor.execute(
                """
                SELECT SUM(value) 
                FROM economic_modifiers 
                WHERE guild_id = ? 
                  AND modifier_type = 'cost_reduction' 
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """,
                (guild.id,)
            )
            cost_reduction = cursor.fetchone()[0] or 0.0
            cost_reduction = min(0.5, cost_reduction)  # Максимальное снижение затрат 50%
            final_amount = int(amount * (1 - cost_reduction))
        
        if current_treasury < final_amount:
            conn.close()
            return False, f"Недостаточно средств в казне. Требуется: {final_amount:,} монет (изначально {amount:,})"
        
        new_treasury = current_treasury - final_amount
        
        # Сохранение в базу
        cursor.execute(
            "INSERT INTO economy (guild_id, treasury) VALUES (?, ?)",
            (guild.id, new_treasury)
        )
        
        # Логируем транзакцию с учетом скидки, если она была применена
        if final_amount != amount:
            description = f"{description} (со скидкой {amount - final_amount} монет)"
            
        cursor.execute(
            """
            INSERT INTO transactions 
            (guild_id, amount, transaction_type, description) 
            VALUES (?, ?, 'expense', ?)
            """,
            (guild.id, -final_amount, description)
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
    
    async def get_user_balance(self, guild, user):
        """Получить баланс пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT balance FROM wallets WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            # Создать кошелек с начальным балансом
            return await self.create_wallet(guild, user)
    
    async def create_wallet(self, guild, user):
        """Создать кошелек для пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        starting_balance = self.config["personal_economy"]["starting_balance"]
        
        cursor.execute(
            "INSERT OR IGNORE INTO wallets (guild_id, user_id, balance) VALUES (?, ?, ?)",
            (guild.id, user.id, starting_balance)
        )
        
        conn.commit()
        conn.close()
        
        return starting_balance
    
    async def add_user_money(self, guild, user, amount, transaction_type="other", description=""):
        """Добавить деньги пользователю"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получить текущий баланс или создать кошелек
        current_balance = await self.get_user_balance(guild, user)
        
        # Рассчитать налог
        tax_amount = 0
        if transaction_type in ["work", "daily"]:
            tax_amount = int(amount * self.config["personal_economy"]["tax_rate"])
            net_amount = amount - tax_amount
            
            # Добавить налог в казну
            if tax_amount > 0:
                await self.add_money(guild, tax_amount, f"Налог с {user.display_name}")
        else:
            net_amount = amount
        
        new_balance = current_balance + net_amount
        
        # Обновить баланс
        cursor.execute(
            "UPDATE wallets SET balance = ?, total_earned = total_earned + ? WHERE guild_id = ? AND user_id = ?",
            (new_balance, net_amount, guild.id, user.id)
        )
        
        # Записать транзакцию
        cursor.execute(
            "INSERT INTO transactions (guild_id, to_user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?, ?)",
            (guild.id, user.id, net_amount, transaction_type, description)
        )
        
        # Записать налоговую транзакцию
        if tax_amount > 0:
            cursor.execute(
                "INSERT INTO transactions (guild_id, from_user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?, ?)",
                (guild.id, user.id, tax_amount, "tax", f"Налог ({self.config['personal_economy']['tax_rate']*100:.0f}%)")
            )
        
        conn.commit()
        conn.close()
        
        return new_balance, tax_amount
    
    async def spend_user_money(self, guild, user, amount, description=""):
        """Потратить деньги пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_balance = await self.get_user_balance(guild, user)
        
        if current_balance < amount:
            conn.close()
            return False, current_balance
        
        new_balance = current_balance - amount
        
        cursor.execute(
            "UPDATE wallets SET balance = ? WHERE guild_id = ? AND user_id = ?",
            (new_balance, guild.id, user.id)
        )
        
        cursor.execute(
            "INSERT INTO transactions (guild_id, from_user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?, ?)",
            (guild.id, user.id, amount, "purchase", description)
        )
        
        conn.commit()
        conn.close()
        
        return True, new_balance
        
    async def transfer_money(self, guild, from_user, to_user, amount):
        """
        Перевести деньги между пользователями с учетом модификаторов экономики
        
        Args:
            guild: Объект гильдии Discord
            from_user: Пользователь, который отправляет деньги
            to_user: Пользователь, который получает деньги
            amount: Сумма для перевода
            
        Returns:
            tuple: (success: bool, from_balance: int, fee: int) или (success: bool, error_message: str)
        """
        if amount <= 0:
            return False, "Сумма должна быть положительной"
            
        if from_user == to_user:
            return False, "Нельзя перевести деньги самому себе"
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем текущий баланс отправителя
        from_balance = await self.get_user_balance(guild, from_user)
        
        # Проверяем наличие модификаторов комиссии за перевод
        transfer_fee = self.config["personal_economy"]["transfer_fee"]  # Базовая комиссия
        
        cursor.execute(
            """
            SELECT value 
            FROM economic_modifiers 
            WHERE guild_id = ? 
              AND modifier_type = 'transfer_fee' 
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """,
            (guild.id,)
        )
        
        fee_modifier = cursor.fetchone()
        if fee_modifier:
            transfer_fee += fee_modifier[0]  # Применяем модификатор комиссии
            
        # Ограничиваем комиссию разумными пределами (от 0% до 50%)
        transfer_fee = max(0, min(0.5, transfer_fee))
        
        # Вычисляем комиссию
        fee = int(amount * transfer_fee)
        total_amount = amount + fee
        
        # Проверяем, хватает ли денег с учетом комиссии
        if from_balance < total_amount:
            conn.close()
            return False, f"Недостаточно средств с учетом комиссии {int(transfer_fee*100)}%"
        
        # Получаем текущий баланс получателя
        cursor.execute(
            "SELECT balance FROM wallets WHERE guild_id = ? AND user_id = ?",
            (guild.id, to_user.id)
        )
        result = cursor.fetchone()
        to_balance = result[0] if result else self.config["personal_economy"]["starting_balance"]
        
        # Обновляем баланс отправителя
        new_from_balance = from_balance - total_amount
        cursor.execute(
            "UPDATE wallets SET balance = ? WHERE guild_id = ? AND user_id = ?",
            (new_from_balance, guild.id, from_user.id)
        )
        
        # Обновляем баланс получателя
        new_to_balance = to_balance + amount
        cursor.execute(
            "INSERT OR REPLACE INTO wallets (guild_id, user_id, balance) VALUES (?, ?, ?)",
            (guild.id, to_user.id, new_to_balance)
        )
        
        # Записываем транзакции
        cursor.execute(
            """
            INSERT INTO transactions 
            (guild_id, from_user_id, to_user_id, amount, transaction_type, description) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild.id, from_user.id, to_user.id, amount, "transfer", f"Перевод {to_user.display_name}")
        )
        
        if fee > 0:
            # Добавляем комиссию в казну
            cursor.execute(
                """
                INSERT INTO economy (guild_id, treasury) 
                SELECT ?, COALESCE(MAX(treasury), 0) + ? 
                FROM economy 
                WHERE guild_id = ?
                """,
                (guild.id, fee, guild.id)
            )
            
            # Логируем комиссию
            cursor.execute(
                """
                INSERT INTO transactions 
                (guild_id, from_user_id, amount, transaction_type, description) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild.id, from_user.id, fee, "fee", f"Комиссия за перевод ({int(transfer_fee*100)}%)")
            )
        
        conn.commit()
        conn.close()
        
        return True, new_from_balance, fee

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