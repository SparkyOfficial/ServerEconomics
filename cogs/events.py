import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from datetime import datetime, timedelta
import asyncio

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_types = [
            {
                "name": "Обнаружена коррупция",
                "description": "В правительстве обнаружены коррупционные схемы. Требуются срочные меры!",
                "icon": "🕵️",
                "options": [
                    {"text": "Провести расследование", "effect": -200, "desc": "Дорогостоящее расследование", "modifier": {"type": "cost_reduction", "value": 0.1, "duration_hours": 24, "description": "Антикоррупционные меры (-10% к расходам)"}},
                    {"text": "Замять дело", "effect": -500, "desc": "Потеря доверия населения", "modifier": {"type": "income_multiplier", "value": 0.8, "duration_hours": 6, "description": "Снижение доверия (-20% к доходам)"}},
                    {"text": "Публичное осуждение", "effect": -100, "desc": "Минимальные потери"}
                ]
            },
            {
                "name": "Праздничный приток налогов",
                "description": "Праздничный сезон принес дополнительные налоговые поступления!",
                "icon": "🎉",
                "options": [
                    {"text": "Потратить на инфраструктуру", "effect": 300, "desc": "Долгосрочные инвестиции"},
                    {"text": "Сохранить в резерве", "effect": 500, "desc": "Пополнение казны"},
                    {"text": "Раздать населению", "effect": 200, "desc": "Повышение лояльности"}
                ]
            },
            {
                "name": "Политическая нестабильность",
                "description": "В стране начались политические волнения. Экономика под угрозой!",
                "icon": "⚡",
                "options": [
                    {"text": "Ввести чрезвычайное положение", "effect": -300, "desc": "Дорогие меры безопасности"},
                    {"text": "Провести переговоры", "effect": -150, "desc": "Дипломатическое решение"},
                    {"text": "Игнорировать", "effect": -400, "desc": "Ситуация ухудшается"}
                ]
            },
            {
                "name": "Поддержка ООН",
                "description": "Международная организация предлагает финансовую помощь!",
                "icon": "🌍",
                "options": [
                    {"text": "Принять помощь", "effect": 600, "desc": "Международная поддержка"},
                    {"text": "Принять с условиями", "effect": 400, "desc": "Частичная помощь"},
                    {"text": "Отказаться", "effect": 100, "desc": "Сохранение независимости"}
                ]
            },
            {
                "name": "Технологический прорыв",
                "description": "Местные ученые совершили важное открытие!",
                "icon": "🔬",
                "options": [
                    {"text": "Инвестировать в исследования", "effect": 800, "desc": "Долгосрочная выгода"},
                    {"text": "Продать технологию", "effect": 400, "desc": "Быстрая прибыль"},
                    {"text": "Засекретить", "effect": 200, "desc": "Стратегическое преимущество"}
                ]
            },
            {
                "name": "Природная катастрофа",
                "description": "Стихийное бедствие нанесло ущерб экономике!",
                "icon": "🌪️",
                "options": [
                    {"text": "Экстренная помощь", "effect": -400, "desc": "Быстрое восстановление"},
                    {"text": "Постепенное восстановление", "effect": -200, "desc": "Медленное восстановление"},
                    {"text": "Минимальная помощь", "effect": -600, "desc": "Долгосрочные проблемы"}
                ]
            }
        ]
    
    @app_commands.command(name="событие", description="Проверить текущее событие или создать новое")
    @app_commands.describe(
        force="Принудительно создать новое событие, даже если есть активное"
    )
    async def event_command(self, interaction: discord.Interaction, force: bool = False):
        """Команда для работы с событиями"""
        # Проверка на администратора
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только администраторы могут управлять событиями.", ephemeral=True)
            return
        
        # Если не принудительно, проверяем, есть ли активное событие
        if not force:
            async with aiosqlite.connect(self.bot.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT id FROM events WHERE guild_id = ? AND status = 'active' AND (expires_at > datetime('now') OR expires_at IS NULL)",
                    (interaction.guild.id,)
                )
                active_event = await cursor.fetchone()
                await cursor.close()
            
            if active_event:
                await interaction.response.send_message(
                    "ℹ️ Уже есть активное событие. Используйте параметр `force=True`, чтобы создать новое.", 
                    ephemeral=True
                )
                return
        
        # Создаем новое событие
        message = await self.create_random_event(interaction.guild)
        if message:
            await interaction.response.send_message(
                f"✅ Создано новое событие: {message.jump_url}", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Не удалось создать событие. Проверьте настройки бота.", 
                ephemeral=True
            )

    @app_commands.command(name="событие", description="Создать новое событие для голосования")
    @app_commands.describe(
        title="Название события",
        description="Описание события",
        option1="Первый вариант",
        effect1="Эффект первого варианта",
        option2="Второй вариант",
        effect2="Эффект второго варианта",
        option3="Третий вариант (опционально)",
        effect3="Эффект третьего варианта (опционально)",
        duration="Продолжительность голосования в минутах (по умолчанию 30)"
    )
    async def event_command(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        option1: str,
        effect1: int,
        option2: str,
        effect2: int,
        option3: str = None,
        effect3: int = 0,
        duration: int = 30
    ):
        """Создать новое событие для голосования"""
        # Проверка прав администратора
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только администраторы могут создавать события.", ephemeral=True)
            return

        # Создание опций события
        options = [
            {"text": option1, "effect": effect1, "desc": ""},
            {"text": option2, "effect": effect2, "desc": ""}
        ]
        
        if option3 and effect3 != 0:
            options.append({"text": option3, "effect": effect3, "desc": ""})

        # Создание события в базе данных
        async with aiosqlite.connect(self.bot.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO events (guild_id, title, description, status, created_at, expires_at)
                VALUES (?, ?, ?, 'active', datetime('now'), datetime('now', ? || ' minutes'))
                """,
                (interaction.guild.id, title, description, duration)
            )
            
            event_id = cursor.lastrowid
            await cursor.close()
        
        # Создание кнопок для голосования
        view = EventView(self.bot, event_id, options)
        
        # Создание embed с информацией о событии
        embed = discord.Embed(
            title=f"📢 {title}",
            description=description,
            color=0x2F3136
        )
        
        for i, option in enumerate(options, 1):
            effect_sign = '+' if option['effect'] >= 0 else ''
            embed.add_field(
                name=f"Вариант {i}: {option['text']}",
                value=f"Эффект: {effect_sign}{option['effect']} монет",
                inline=False
            )
        
        embed.set_footer(text=f"Голосование активно {duration} минут")
        
        # Отправка сообщения с кнопками
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        
        # Сохранение ссылки на сообщение в базе данных
        cursor.execute(
            "UPDATE events SET message_id = ?, channel_id = ? WHERE id = ?",
            (message.id, message.channel.id, event_id)
        )
        
        # Сохранение ссылки на сообщение в объекте view
        view.message = message
        
        conn.commit()
        conn.close()

    async def create_random_event(self, guild):
        """Создание случайного события"""
        event_data = random.choice(self.event_types)
        
        # Создание события в базе данных
        async with aiosqlite.connect(self.bot.db_path) as conn:
            # Создаем событие с временем истечения (30 минут по умолчанию)
            duration = 30  # minutes
            cursor = await conn.execute(
                """
                INSERT INTO events (guild_id, title, description, status, created_at, expires_at)
                VALUES (?, ?, ?, 'active', datetime('now'), datetime('now', ? || ' minutes'))
                """,
                (guild.id, event_data['name'], event_data['description'], duration)
            )
            
            event_id = cursor.lastrowid
            await cursor.close()
        
        # Создаем view с кнопками для голосования
        view = EventView(self.bot, event_id, event_data['options'])
        
        # Создаем embed с информацией о событии
        embed = discord.Embed(
            title=f"{event_data['icon']} {event_data['name']}",
            description=event_data["description"],
            color=0x2F3136
        )
        
        # Добавляем варианты ответа с эффектами
        for i, option in enumerate(event_data['options'], 1):
            effect_sign = '+' if option['effect'] >= 0 else ''
            embed.add_field(
                name=f"Вариант {i}: {option['text']}",
                value=f"{option['desc']}\nЭффект: {effect_sign}{option['effect']} монет",
                inline=False
            )
        
        embed.set_footer(text=f"Голосование активно {duration} минут")
        
        # Отправка сообщения в канал событий
        channel = guild.get_channel(self.bot.config['events_channel_id'])
        if channel:
            try:
                message = await channel.send(embed=embed, view=view)
                
                # Сохраняем информацию о сообщении в БД
                cursor.execute(
                    "UPDATE events SET message_id = ?, channel_id = ? WHERE id = ?",
                    (message.id, message.channel.id, event_id)
                )
                
                # Сохраняем ссылку на сообщение в view
                view.message = message
                
                conn.commit()
                return message
                
            except Exception as e:
                print(f"Ошибка при отправке сообщения о событии: {e}")
        
        conn.close()
        return None

    async def auto_resolve_event(self, event_id, guild):
        """Автоматическое разрешение события"""
        conn = sqlite3.connect(self.bot.db_path)
        conn.row_factory = sqlite3.Row  # Для доступа к полям по имени
        cursor = conn.cursor()
        
        # Получаем полные данные о событии
        cursor.execute(
            """
            SELECT e.*, m.channel_id, m.message_id
            FROM events e
            LEFT JOIN (
                SELECT event_id, channel_id, message_id
                FROM events
                WHERE id = ?
            ) m ON e.id = m.event_id
            WHERE e.id = ?
            """,
            (event_id, event_id)
        )
        
        event = cursor.fetchone()
        if not event or event['status'] != 'active':
            conn.close()
            return
            
        # Получаем данные о событии из конфига
        event_data = next((e for e in self.event_types if e['name'] == event['title']), None)
        if not event_data:
            conn.close()
            return
            
        # Выбираем случайный вариант
        option = random.choice(event_data['options'])
        
        # Применяем эффект к казне
        success, new_balance = await self.bot.spend_money(
            guild,
            -option['effect'],  # Отрицательный эффект для увеличения казны
            f"Событие: {event_data['name']} (автоматически)",
            apply_modifiers=False
        )
        
        # Обновляем статус события
        cursor.execute(
            "UPDATE events SET status = 'auto_resolved', amount = ? WHERE id = ?",
            (option['effect'], event_id)
        )
        
        # Применяем модификатор (если есть)
        if 'modifier' in option:
            mod = option['modifier']
            expires_at = (datetime.now() + timedelta(hours=mod['duration_hours'])).isoformat()
            
            cursor.execute(
                """
                INSERT INTO modifiers (guild_id, modifier_type, value, description, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild.id, mod['type'], mod['value'], mod['description'], expires_at)
            )
        
        # Получаем канал и сообщение
        channel_id = event['channel_id']
        message_id = event['message_id']
        
        conn.commit()
        conn.close()
        
        # Обновляем сообщение с событием
        if channel_id and message_id:
            try:
                channel = guild.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(message_id)
                    
                    # Создаем новый embed с результатом
                    embed = message.embeds[0]
                    embed.color = 0xFFA500  # Оранжевый цвет для автоматически решенного события
                    
                    # Обновляем описание
                    effect_sign = '+' if option['effect'] >= 0 else ''
                    embed.add_field(
                        name="⏰ Автоматический результат",
                        value=f"Выбрано: **{option['text']}**\nЭффект: {effect_sign}{option['effect']} монет",
                        inline=False
                    )
                    
                    # Отключаем кнопки
                    for item in message.components[0].children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True
                    
                    await message.edit(embed=embed, view=message.components[0])
                    
            except Exception as e:
                print(f"Ошибка при обновлении сообщения о событии: {e}")
                
            # Отправляем уведомление в канал экономики
            channel = guild.get_channel(self.bot.config['events_channel_id'])
            if channel:
                embed = discord.Embed(
                    title=f"⏰ Событие автоматически завершено: {event_data['name']}",
                    description=f"Выбрано: **{option['text']}**\nЭффект: {effect_sign}{option['effect']} монет",
                    color=0xFFA500
                )
                await channel.send(embed=embed)

class EventView(discord.ui.View):
    def __init__(self, bot, event_id, options):
        super().__init__(timeout=1800)  # 30 минут
        self.bot = bot
        self.event_id = event_id
        self.options = options
        self.votes = {}
        
        # Создание кнопок
        for i, option in enumerate(options):
            button = EventButton(i, option)
            self.add_item(button)
    
    async def on_timeout(self):
        # Отключение кнопок по истечении времени
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        try:
            # Обновление сообщения, если оно доступно
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
            
            # Закрытие события в БД
            conn = sqlite3.connect(self.bot.db_path)
            cursor = conn.cursor()
            
            # Обновляем статус события
            cursor.execute(
                "UPDATE events SET status = 'expired' WHERE id = ?",
                (self.event_id,)
            )
            
            # Получаем данные о событии для уведомления
            cursor.execute(
                "SELECT title, description FROM events WHERE id = ?",
                (self.event_id,)
            )
            event_data = cursor.fetchone()
            
            conn.commit()
            conn.close()
            
            # Отправляем уведомление о завершении события
            if event_data and hasattr(self, 'message') and self.message:
                embed = discord.Embed(
                    title=f"⏰ Время голосования истекло: {event_data[0]}",
                    description=event_data[1],
                    color=0xFFA500
                )
                await self.message.channel.send(embed=embed)
                
        except Exception as e:
            print(f"Ошибка при обработке таймаута события: {e}")
        conn.close()


class EventButton(discord.ui.Button):
    def __init__(self, option_id, option_data):
        super().__init__(
            style=discord.ButtonStyle.primary if option_data['effect'] >= 0 else discord.ButtonStyle.danger,
            label=option_data['text'],
            custom_id=f"event_option_{option_id}"
        )
        self.option_id = option_id
        self.option_data = option_data
        self.effect = option_data['effect']
        self.description = option_data['desc']
        self.votes = set()
    
    async def callback(self, interaction: discord.Interaction):
        # Обработка голосования
        self.votes.add(interaction.user.id)
        
        # Обновление сообщения
        await interaction.response.edit_message(
            content=f"✅ {interaction.user.mention} проголосовал за: {self.option_data['text']}",
            view=self.view
        )
        
        # Если голосовал администратор, сразу применяем результат
        if interaction.user.guild_permissions.administrator:
            await self.apply_event_result(interaction)
    
    async def apply_event_result(self, interaction):
        # Применение эффекта события
        conn = sqlite3.connect(self.view.bot.db_path)
        cursor = conn.cursor()
        
        # Обновление казны
        success, new_balance = await self.view.bot.spend_money(
            interaction.guild,
            -self.effect,  # Отрицательный эффект для увеличения казны
            f"Событие: {self.option_data['text']}",
            apply_modifiers=False
        )
        
        # Обновление статуса события
        cursor.execute(
            "UPDATE events SET status = 'completed', amount = ? WHERE id = ?",
            (self.effect, self.view.event_id)
        )
        
        # Применение модификатора (если есть)
        if 'modifier' in self.option_data:
            mod = self.option_data['modifier']
            expires_at = (datetime.now() + timedelta(hours=mod['duration_hours'])).isoformat()
            
            cursor.execute(
                """
                INSERT INTO modifiers (guild_id, modifier_type, value, description, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (interaction.guild.id, mod['type'], mod['value'], mod['description'], expires_at)
            )
        
        conn.commit()
        conn.close()
        
        # Отправка результата
        embed = discord.Embed(
            title=f"🎯 Результат события",
            description=f"**Выбрано:** {self.option_data['text']}\n**Эффект:** {self.effect} монет",
            color=0x2F3136
        )
        
        if success:
            embed.add_field(name="Новый баланс", value=f"{new_balance:,} монет")
        
        if 'modifier' in self.option_data:
            mod = self.option_data['modifier']
            embed.add_field(
                name="🔧 Применен модификатор",
                value=f"{mod['description']} на {mod['duration_hours']} часов",
                inline=False
            )
        
        # Отключение всех кнопок
        for item in self.view.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        # Обновление сообщения с результатом
        await interaction.followup.send(embed=embed)
        
        # Обновление исходного сообщения
        await interaction.edit_original_response(view=self.view)

async def setup(bot):
    await bot.add_cog(Events(bot))
