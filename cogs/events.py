import discord
from discord.ext import commands
import sqlite3
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
    
    @commands.slash_command(name="событие", description="Проверить текущее событие или создать новое")
    async def event_command(self, ctx, force: bool = False):
        """Команда для работы с событиями"""
        if force and not ctx.author.guild_permissions.administrator:
            await ctx.respond("❌ Только администраторы могут принудительно создавать события!", ephemeral=True)
            return
        
        # Проверка активного события
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM events WHERE guild_id = ? AND status = 'active' ORDER BY timestamp DESC LIMIT 1",
            (ctx.guild.id,)
        )
        
        active_event = cursor.fetchone()
        conn.close()
        
        if active_event and not force:
            # Показать активное событие
            event_id, guild_id, event_type, description, amount, status, timestamp = active_event
            
            embed = discord.Embed(
                title=f"📋 Активное событие",
                description=f"**{event_type}**\n{description}",
                color=0xFFD700
            )
            embed.add_field(name="Время создания", value=timestamp)
            embed.add_field(name="Статус", value="Ожидает решения")
            
            await ctx.respond(embed=embed)
        else:
            # Создать новое событие
            if force:
                await ctx.defer()
            
            await self.create_random_event(ctx.guild)
            
            if force:
                await ctx.followup.send("✅ Новое событие создано!")
            else:
                await ctx.respond("✅ Новое событие создано!")
    
    async def create_random_event(self, guild):
        """Создание случайного события"""
        event_data = random.choice(self.event_types)
        
        # Сохранение в базу данных
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO events (guild_id, event_type, description, amount, status) VALUES (?, ?, ?, ?, ?)",
            (guild.id, event_data["name"], event_data["description"], 0, "active")
        )
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Отправка в канал
        channel = self.bot.get_channel(self.bot.chart_channel_id)
        if not channel:
            return
        
        from utils.visualization import create_event_image
        
        # Создание изображения для события
        image_path = create_event_image(event_data['name'], event_data['description'], event_data['icon'])
        
        embed = discord.Embed(
            title=f"{event_data['icon']} {event_data['name']}",
            description="**Внимание! Новое экономическое событие!**\n\nВыберите один из вариантов ниже.",
            color=0xFF6B35
        )
        embed.set_footer(text=f"ID события: {event_id} | Время на решение: 30 минут")

        file = None
        if image_path:
            file = discord.File(image_path, filename="event.png")
            embed.set_image(url="attachment://event.png")

        # Создание кнопок для выбора
        view = EventView(self.bot, event_id, event_data["options"])
        
        message = await channel.send(embed=embed, file=file, view=view)

        if image_path:
            import os
            os.remove(image_path)
        
        # Автоматическое закрытие через 30 минут
        await asyncio.sleep(1800)  # 30 минут
        await self.auto_resolve_event(event_id, guild)
    
    async def auto_resolve_event(self, event_id, guild):
        """Автоматическое разрешение события"""
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT status FROM events WHERE id = ?",
            (event_id,)
        )
        
        result = cursor.fetchone()
        if result and result[0] == "active":
            # Событие не было разрешено, применяем случайный исход
            cursor.execute(
                "UPDATE events SET status = 'auto_resolved' WHERE id = ?",
                (event_id,)
            )
            
            # Случайный штраф за бездействие
            penalty = random.randint(100, 300)
            await self.bot.spend_money(guild, penalty, "Штраф за нерешенное событие")
            
            # Уведомление
            channel = self.bot.get_channel(self.bot.chart_channel_id)
            if channel:
                embed = discord.Embed(
                    title="⏰ Событие автоматически закрыто",
                    description=f"Событие не было разрешено вовремя. Штраф: {penalty} монет",
                    color=0xFF0000
                )
                await channel.send(embed=embed)
        
        conn.commit()
        conn.close()

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
        """Обработка таймаута"""
        for item in self.children:
            item.disabled = True

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
        """Обработка нажатия кнопки"""
        user_id = interaction.user.id
        
        # Проверка, голосовал ли уже пользователь
        for item in self.view.children:
            if isinstance(item, EventButton) and user_id in item.votes:
                item.votes.remove(user_id)
        
        # Добавление голоса
        self.votes.add(user_id)
        
        # Обновление сообщения
        embed = discord.Embed(
            title="📊 Голосование по событию",
            description="Текущие результаты голосования:",
            color=0x2F3136
        )
        
        total_votes = sum(len(item.votes) for item in self.view.children if isinstance(item, EventButton))
        
        for item in self.view.children:
            if isinstance(item, EventButton):
                vote_count = len(item.votes)
                percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
                
                embed.add_field(
                    name=f"{item.label} ({vote_count} голосов)",
                    value=f"{item.description}\nЭффект: {item.effect:+} монет\n{percentage:.1f}%",
                    inline=False
                )
        
        await interaction.response.edit_message(embed=embed, view=self.view)
        
        # Проверка на администратора для мгновенного применения
        if interaction.user.guild_permissions.administrator:
            await self.apply_event_result(interaction)
    
    async def apply_event_result(self, interaction):
        """Применение результата события"""
        # Определение победившего варианта
        max_votes = max(len(item.votes) for item in self.view.children if isinstance(item, EventButton))
        winning_options = [item for item in self.view.children 
                          if isinstance(item, EventButton) and len(item.votes) == max_votes]
        
        if len(winning_options) == 1:
            winner = winning_options[0]
        else:
            # В случае ничьей выбираем случайно
            winner = random.choice(winning_options)
        
        # Применение эффекта
        guild = interaction.guild
        # Применение модификатора, если он есть
        if 'modifier' in winner.option_data:
            mod = winner.option_data['modifier']
            expires_at = datetime.now() + timedelta(hours=mod['duration_hours'])
            
            cursor.execute(
                "INSERT INTO modifiers (guild_id, modifier_type, value, description, expires_at) VALUES (?, ?, ?, ?, ?)",
                (guild.id, mod['type'], mod['value'], mod['description'], expires_at)
            )

        if winner.effect > 0:
            # Добавление денег
            conn = sqlite3.connect(self.view.bot.db_path)
            cursor = conn.cursor()
            
            current_treasury = await self.view.bot.get_treasury(guild)
            new_treasury = current_treasury + winner.effect
            
            cursor.execute(
                "INSERT INTO economy (guild_id, treasury) VALUES (?, ?)",
                (guild.id, new_treasury)
            )
            
            cursor.execute(
                "INSERT INTO transactions (guild_id, amount, description) VALUES (?, ?, ?)",
                (guild.id, winner.effect, f"Событие: {winner.label}")
            )
            
            conn.commit()
            conn.close()
        else:
            # Трата денег
            await self.view.bot.spend_money(guild, abs(winner.effect), f"Событие: {winner.label}")
        
        # Обновление статуса события
        conn = sqlite3.connect(self.view.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE events SET status = 'resolved', amount = ? WHERE id = ?",
            (winner.effect, self.view.event_id)
        )
        
        conn.commit()
        conn.close()
        
        # Финальное сообщение
        embed = discord.Embed(
            title="✅ Событие разрешено",
            description=f"Выбран вариант: **{winner.label}**\n{winner.description}",
            color=0x00FF00 if winner.effect >= 0 else 0xFF0000
        )
        
        embed.add_field(
            name="Эффект на экономику",
            value=f"{winner.effect:+} монет",
            inline=True
        )
        
        current_treasury = await self.view.bot.get_treasury(guild)
        embed.add_field(
            name="Текущая казна",
            value=f"{current_treasury:,} монет",
            inline=True
        )
        
        # Отключение кнопок
        for item in self.view.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self.view)

def setup(bot):
    bot.add_cog(Events(bot))
