import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta
import asyncio
import random
from typing import Optional, Dict, List, Tuple

class EconomicInfluence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # {user_id: cooldown_end_time}
        self.active_events = {}  # {guild_id: {event_type: event_data}}
        self.initialize_database()
        self.cleanup_expired_events.start()

    def initialize_database(self):
        """Инициализация таблиц базы данных"""
        # Эта функция будет заменена на async версию в setup_hook
        pass
    
    @tasks.loop(minutes=5)
    async def cleanup_expired_events(self):
        """Очистка истекших событий"""
        try:
            async with aiosqlite.connect(self.bot.db_path) as conn:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Проверяем существование колонки is_active
                cursor = await conn.execute("PRAGMA table_info(economic_events)")
                columns = [column[1] for column in await cursor.fetchall()]
                await cursor.close()
                
                # Удаляем истекшие события и модификаторы
                if 'is_active' in columns:
                    await conn.execute(
                        "UPDATE economic_events SET is_active = 0 WHERE expires_at < ? AND is_active = 1",
                        (now,)
                    )
                else:
                    # Если колонки is_active нет, просто удаляем истекшие записи
                    await conn.execute(
                        "DELETE FROM economic_events WHERE expires_at < ?",
                        (now,)
                    )
                
                # Удаляем истекшие модификаторы
                await conn.execute(
                    "DELETE FROM economic_modifiers WHERE expires_at < ?",
                    (now,)
                )
                await conn.commit()
        except Exception as e:
            print(f"Ошибка при очистке истекших событий: {e}")
    
    def cog_unload(self):
        """Очистка при выгрузке кога"""
        self.cleanup_expired_events.cancel()
    
    @app_commands.command(name="влияние", description="Показать доступные действия для влияния на экономику")
    async def influence(self, interaction: discord.Interaction):
        """Показать меню влияния на экономику"""
        embed = discord.Embed(
            title="💼 Влияние на экономику",
            description="Используйте команды ниже, чтобы влиять на экономику сервера:",
            color=0x3498db
        )
        
        commands_list = [
            ("/распродажа", "Провести массовую распродажу товаров"),
            ("/фонд_помощи", "Создать фонд взаимопомощи"),
            ("/теневой_рынок", "Инвестировать в теневую экономику"),
            ("/налоговая_реформа", "Предложить налоговую реформу"),
            ("/рабочая_бригада", "Организовать рабочую бригаду"),
            ("/кредитный_рынок", "Войти в кредитный рынок"),
            ("/информационная_кампания", "Запустить инфо-кампанию"),
            ("/долгосрочные_инвестиции", "Инвестировать в долгосрочные проекты")
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        # Показать текущие активные модификаторы
        active_modifiers = self.get_active_modifiers(interaction.guild.id)
        if active_modifiers:
            mods_text = "\n".join(
                f"• {m['description']} ({m['value']:+}%)" 
                f"{f' (истекает: {m["expires_at"].strftime("%d.%m %H:%M")})' if m['expires_at'] else ''}"
                for m in active_modifiers
            )
            embed.add_field(
                name="📊 Активные эффекты",
                value=mods_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def get_active_modifiers(self, guild_id: int) -> List[Dict]:
        """Получить активные модификаторы экономики"""
        async with aiosqlite.connect(self.bot.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT modifier_type, value, description, expires_at 
                FROM economic_modifiers 
                WHERE guild_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """,
                (guild_id,)
            )
            
            results = await cursor.fetchall()
            await cursor.close()
            
            modifiers = []
            for row in results:
                modifiers.append({
                    'type': row[0],
                    'value': row[1],
                    'description': row[2],
                    'expires_at': row[3]
                })
            
            return modifiers
    
    async def add_economic_modifier(
        self, 
        guild_id: int, 
        modifier_type: str, 
        value: float, 
        description: str, 
        duration_hours: Optional[int] = None
    ) -> bool:
        """Добавить модификатор экономики"""
        try:
            expires_at = None
            if duration_hours:
                expires_at = (datetime.now() + timedelta(hours=duration_hours)).strftime('%Y-%m-%d %H:%M:%S')
            
            async with aiosqlite.connect(self.bot.db_path) as conn:
                # Удаляем существующий модификатор такого же типа
                await conn.execute(
                    "DELETE FROM economic_modifiers WHERE guild_id = ? AND modifier_type = ?",
                    (guild_id, modifier_type)
                )
                
                # Добавляем новый модификатор
                await conn.execute(
                    """
                    INSERT INTO economic_modifiers 
                    (guild_id, modifier_type, value, description, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, modifier_type, value, description, expires_at)
                )
                
                await conn.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка при добавлении модификатора: {e}")
            return False

    async def log_economic_event(
        self, 
        guild_id: int, 
        user_id: int, 
        event_type: str, 
        effect: int, 
        description: str, 
        duration_hours: Optional[int] = None
    ) -> bool:
        """Записать экономическое событие в историю"""
        try:
            expires_at = None
            if duration_hours:
                expires_at = (datetime.now() + timedelta(hours=duration_hours)).strftime('%Y-%m-%d %H:%M:%S')
            
            async with aiosqlite.connect(self.bot.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO economic_events 
                    (guild_id, user_id, event_type, effect, description, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (guild_id, user_id, event_type, effect, description, expires_at)
                )
                await conn.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка при записи события: {e}")
            return False
    
    def check_cooldown(self, user_id: int, command_name: str, cooldown_hours: int) -> Tuple[bool, Optional[timedelta]]:
        """Проверить кд на команду"""
        now = datetime.now()
        key = f"{user_id}_{command_name}"
        
        if key in self.cooldowns and now < self.cooldowns[key]:
            return False, self.cooldowns[key] - now
        
        self.cooldowns[key] = now + timedelta(hours=cooldown_hours)
        return True, None
    
    # ===== КОМАНДЫ ВЛИЯНИЯ =====
    
    @app_commands.command(name="распродажа", description="Провести массовую распродажу товаров")
    async def mass_sale(self, interaction: discord.Interaction):
        """Массовая распродажа товаров"""
        # Проверка кд (раз в 24 часа)
        can_use, time_left = self.check_cooldown(interaction.user.id, "mass_sale", 24)
        if not can_use:
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            await interaction.response.send_message(
                f"❌ Вы уже проводили распродажу недавно. Попробуйте снова через {hours}ч {minutes}м.",
                ephemeral=True
            )
            return
        
        # Расчет эффекта
        effect = random.randint(50, 150)  # Случайный бонус к доходу
        duration = random.randint(2, 6)   # Длительность эффекта в часах
        
        # Применение эффекта
        await self.add_economic_modifier(
            interaction.guild.id,
            "income_boost",
            effect,
            f"Массовая распродажа (организатор: {interaction.user.display_name})",
            duration
        )
        
        # Логирование события
        await self.log_economic_event(
            interaction.guild.id,
            interaction.user.id,
            "mass_sale",
            effect,
            f"Проведена массовая распродажа (+{effect}% к доходам на {duration}ч)",
            duration
        )
        
        # Отправка уведомления
        embed = discord.Embed(
            title="🏷️ Массовая распродажа!",
            description=f"{interaction.user.mention} организовал(а) массовую распродажу на сервере!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="Эффект",
            value=f"+{effect}% к доходам всех участников на {duration} часов",
            inline=False
        )
        
        embed.add_field(
            name="Последствия",
            value="• Временный рост экономики\n• Снижение цен на товары\n• Повышение активности на рынке",
            inline=False
        )
        
        embed.set_footer(text=f"Следующая распродажа будет доступна через 24 часа")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="фонд_помощи", description="Создать фонд взаимопомощи")
    @app_commands.describe(взнос="Сумма взноса в фонд (должна быть положительной)")
    async def help_fund(self, interaction: discord.Interaction, взнос: int):
        """Создать фонд взаимопомощи"""
        # Проверка баланса
        if взнос <= 0:
            await interaction.response.send_message(
                "❌ Сумма взноса должна быть положительной.",
                ephemeral=True
            )
            return
            
        balance = await self.bot.get_user_balance(interaction.guild, interaction.user)
        if balance < взнос:
            await interaction.response.send_message(
                f"❌ Недостаточно средств для создания фонда. Ваш баланс: {balance:,} монет.",
                ephemeral=True
            )
            return
        
        # Списание средств
        success, new_balance = await self.bot.spend_user_money(
            interaction.guild, interaction.user, взнос, "Взнос в фонд взаимопомощи"
        )
        
        if not success:
            await interaction.response.send_message("❌ Ошибка при списании средств.", ephemeral=True)
            return
        
        # Расчет эффекта (чем больше взнос, тем сильнее эффект)
        effect = min(взнос // 10, 50)  # Максимум +50% к доходам
        duration = min(взнос // 1000, 24)  # Максимум 24 часа
        
        if duration < 1:  # Минимум 1 час
            duration = 1
        
        # Применение эффекта
        await self.add_economic_modifier(
            interaction.guild.id,
            "help_fund_boost",
            effect,
            f"Фонд взаимопомощи (от {interaction.user.display_name}): +{effect}% к доходам",
            duration
        )
        
        # Логирование события
        await self.log_economic_event(
            interaction.guild.id,
            interaction.user.id,
            "help_fund",
            effect,
            f"Создан фонд взаимопомощи на сумму {взнос:,} монет (+{effect}% к доходам на {duration}ч)",
            duration
        )
        
        # Отправка уведомления
        embed = discord.Embed(
            title="🤝 Фонд взаимопомощи",
            description=f"{interaction.user.mention} создал(а) фонд взаимопомощи на сумму **{взнос:,}** монет!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="Эффект",
            value=f"+{effect}% к доходам всех участников на {duration} часов",
            inline=False
        )
        
        embed.add_field(
            name="Как это работает",
            value=(
                "• Ваш взнос стимулирует экономику сервера\n"
                "• Все участники получают бонус к доходам\n"
                "• Чем больше сумма взноса, тем сильнее и дольше эффект"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Новый баланс: {new_balance:,} монет")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="теневой_рынок", description="Инвестировать в теневую экономику")
    @app_commands.describe(сумма="Сумма инвестиций (должна быть положительной)")
    async def black_market(self, interaction: discord.Interaction, сумма: int):
        """Инвестировать в теневую экономику"""
        # Проверка суммы
        if сумма <= 0:
            await interaction.response.send_message(
                "❌ Сумма инвестиций должна быть положительной.",
                ephemeral=True
            )
            return
            
        # Проверка баланса
        balance = await self.bot.get_user_balance(interaction.guild, interaction.user)
        if balance < сумма:
            await interaction.response.send_message(
                f"❌ Недостаточно средств для инвестиций. Ваш баланс: {balance:,} монет.",
                ephemeral=True
            )
            return
        
        # Шанс успеха (70%)
        success = random.random() < 0.7
        
        if success:
            # Успешная инвестиция (прибыль 20-100%)
            multiplier = 1 + random.uniform(0.2, 1.0)
            profit = int(сумма * (multiplier - 1))
            
            # Начисление прибыли
            new_balance = await self.bot.add_user_money(
                interaction.guild, interaction.user, profit, "black_market_profit"
            )
            
            # Логирование события
            await self.log_economic_event(
                interaction.guild.id,
                interaction.user.id,
                "black_market_success",
                profit,
                f"Успешная инвестиция в теневой рынок: +{profit:,} монет"
            )
            
            # Случайный эффект на экономику (30% шанс)
            if random.random() < 0.3:
                effect = random.randint(-20, 20)  # Случайный эффект от -20% до +20%
                duration = random.randint(1, 6)   # 1-6 часов
                
                await self.add_economic_modifier(
                    interaction.guild.id,
                    "black_market_effect",
                    effect,
                    f"Теневые операции: {effect:+}% к экономике",
                    duration
                )
                
                effect_text = f"\n\n📊 Эффект на экономику: {effect:+}% на {duration}ч"
            else:
                effect_text = ""
            
            # Отправка уведомления
            embed = discord.Embed(
                title="💰 Успешная инвестиция!",
                description=(
                    f"{interaction.user.mention} успешно инвестировал(а) **{сумма:,}** монет в теневой рынок "
                    f"и получил(а) прибыль **+{profit:,}** монет!"
                    f"{effect_text}"
                ),
                color=0x2ecc71
            )
            
            embed.set_footer(text=f"Новый баланс: {new_balance:,} монет")
            
        else:
            # Неудачная инвестиция (потеря 50-100%)
            loss = int(сумма * random.uniform(0.5, 1.0))
            
            # Списание средств
            success, new_balance = await self.bot.spend_user_money(
                interaction.guild, interaction.user, loss, "black_market_loss"
            )
            
            if not success:
                await interaction.response.send_message("❌ Ошибка при списании средств.", ephemeral=True)
                return
            
            # Логирование события
            await self.log_economic_event(
                interaction.guild.id,
                interaction.user.id,
                "black_market_fail",
                -loss,
                f"Неудачная инвестиция в теневой рынок: -{loss:,} монет"
            )
            
            # Отправка уведомления
            embed = discord.Embed(
                title="💸 Инвестиция провалилась!",
                description=(
                    f"{interaction.user.mention} потерял(а) **{loss:,}** монет "
                    f"из-за неудачной инвестиции в теневой рынок."
                ),
                color=0xe74c3c
            )
    @app_commands.command(name="налоговая_реформа", description="Предложить налоговую реформу")
    async def tax_reform(self, interaction: discord.Interaction):
        """Предложить налоговую реформу"""
        # Проверка кд (раз в 48 часов)
        can_use, time_left = self.check_cooldown(interaction.user.id, "tax_reform", 48)
        if not can_use:
            hours = time_left.seconds // 3600 + time_left.days * 24
            minutes = (time_left.seconds % 3600) // 60
            await interaction.response.send_message(
                f"❌ Вы уже предлагали реформу недавно. Попробуйте снова через {hours}ч {minutes}м.",
                ephemeral=True
            )
            return
        
        # Случайный эффект реформы (от -10% до +10% к налогам)
        tax_change = random.randint(-10, 10)
        duration = random.randint(6, 24)  # 6-24 часа
        
        # Применение эффекта
        await self.add_economic_modifier(
            interaction.guild.id,
            "tax_rate",
            tax_change,
            f"Налоговая реформа: {tax_change:+}% к налогам",
            duration
        )
        
        # Логирование события
        await self.log_economic_event(
            interaction.guild.id,
            interaction.user.id,
            "tax_reform",
            tax_change,
            f"Проведена налоговая реформа: {tax_change:+}% к налогам на {duration}ч",
            duration
        )
        
        # Определение типа реформы
        if tax_change > 0:
            reform_type = "Увеличение налогов"
            color = 0xe74c3c
            effects = [
                "• Увеличение доходов казны",
                "• Снижение личных доходов игроков",
                "• Возможное замедление экономики"
            ]
        elif tax_change < 0:
            reform_type = "Снижение налогов"
            color = 0x2ecc71
            effects = [
                "• Снижение доходов казны",
                "• Увеличение личных доходов игроков",
                "• Стимуляция экономической активности"
            ]
        else:
            reform_type = "Нейтральная реформа"
            color = 0x3498db
            effects = [
                "• Незначительные изменения в экономике",
                "• Баланс между доходами игроков и казны",
                "• Стабильность экономики"
            ]
        
        # Отправка уведомления
        embed = discord.Embed(
            title=f"📊 {reform_type}",
            description=(
                f"{interaction.user.mention} предложил(а) налоговую реформу!\n"
                f"**Изменение налогов:** {tax_change:+}%\n"
                f"**Действует:** {duration} часов"
            ),
            color=color
        )
        
        embed.add_field(
            name="Эффекты реформы",
            value="\n".join(effects),
            inline=False
        )
        
        embed.set_footer(text="Следующая реформа будет доступна через 48 часов")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="рабочая_бригада", description="Организовать рабочую бригаду")
    async def work_brigade(self, interaction: discord.Interaction):
        """Организовать рабочую бригаду"""
        # Проверка кд (раз в 8 часов)
        can_use, time_left = self.check_cooldown(interaction.user.id, "work_brigade", 8)
        if not can_use:
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            await interaction.response.send_message(
                f"❌ Вы уже организовывали бригаду недавно. Попробуйте снова через {hours}ч {minutes}м.",
                ephemeral=True
            )
            return
        
        # Расчет эффекта (зависит от количества участников онлайн)
        online_members = sum(1 for m in interaction.guild.members if m.status != discord.Status.offline and not m.bot)
        effect = min(online_members * 2, 100)  # Максимум +100% к доходам
        duration = 4  # 4 часа
        
        # Применение эффекта
        await self.add_economic_modifier(
            interaction.guild.id,
            "work_brigade_boost",
            effect,
            f"Рабочая бригада (организатор: {interaction.user.display_name}): +{effect}% к доходам",
            duration
        )
        
        # Логирование события
        await self.log_economic_event(
            interaction.guild.id,
            interaction.user.id,
            "work_brigade",
            effect,
            f"Организована рабочая бригада: +{effect}% к доходам на {duration}ч",
            duration
        )
        
        # Отправка уведомления
        embed = discord.Embed(
            title="👷 Рабочая бригада",
            description=f"{interaction.user.mention} организовал(а) рабочую бригаду на сервере!",
            color=0xf39c12
        )
        
        embed.add_field(
            name="Эффект",
            value=f"+{effect}% к доходам всех участников на {duration} часов",
            inline=False
        )
        
        embed.add_field(
            name="Детали",
            value=(
                f"• Участников онлайн: {online_members}\n"
                "• Коллективная работа увеличивает эффективность\n"
                "• Чем больше участников, тем сильнее эффект"
            ),
            inline=False
        )
        
        embed.set_footer(text="Следующая бригада будет доступна через 12 часов")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="информационная_кампания", description="Запустить информационную кампанию")
    @app_commands.describe(тема="Тема кампании")
    async def info_campaign(self, interaction: discord.Interaction, тема: str):
        """Запустить информационную кампанию"""
        # Проверка кд (раз в 24 часа)
        can_use, time_left = self.check_cooldown(interaction.user.id, "info_campaign", 24)
        if not can_use:
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            await interaction.response.send_message(
                f"❌ Вы уже запускали кампанию недавно. Попробуйте снова через {hours}ч {minutes}м.",
                ephemeral=True
            )
            return
        
        # Определение эффекта на основе темы
        topic_effects = {
            # Позитивные темы
            "рост": (15, "Экономический рост"),
            "развитие": (10, "Развитие инфраструктуры"),
            "инновации": (20, "Технологические инновации"),
            # Негативные темы
            "кризис": (-15, "Экономический кризис"),
            "инфляция": (-10, "Высокая инфляция"),
            "безработица": (-20, "Рост безработицы")
        }
        
        # Поиск совпадений в теме
        effect = 0
        effect_desc = "Нейтральный эффект"
        
        for keyword, (e, desc) in topic_effects.items():
            if keyword in тема.lower():
                effect = e
                effect_desc = desc
                break
        
        # Если не нашли совпадений - случайный эффект
        if effect == 0:
            effect = random.randint(-10, 10)
            effect_desc = "Смешанные новости"
        
        duration = random.randint(6, 12)  # 6-12 часов
        
        # Применение эффекта
        await self.add_economic_modifier(
            interaction.guild.id,
            "info_campaign_effect",
            effect,
            f"Инфо-кампания: {effect_desc} ({effect:+}%)",
            duration
        )
        
        # Логирование события
        await self.log_economic_event(
            interaction.guild.id,
            interaction.user.id,
            "info_campaign",
            effect,
            f"Запущена инфо-кампания: {effect_desc} ({effect:+}%) на {duration}ч",
            duration
        )
        
        # Определение цвета и иконки
        if effect > 0:
            color = 0x2ecc71
            icon = "📈"
        elif effect < 0:
            color = 0xe74c3c
            icon = "📉"
        else:
            color = 0x3498db
            icon = "📊"
        
        # Отправка уведомления
        embed = discord.Embed(
            title=f"{icon} Информационная кампания",
            description=(
                f"{interaction.user.mention} запустил(а) информационную кампанию!\n"
                f"**Тема:** {тема}\n"
                f"**Эффект:** {effect_desc} ({effect:+}%)\n"
                f"**Действует:** {duration} часов"
            ),
            color=color
        )
        
        embed.add_field(
            name="Как это работает",
            value=(
                "• Новости влияют на настроения на рынке\n"
                "• Позитивные новости стимулируют экономику\n"
                "• Негативные новости могут вызвать панику"
            ),
            inline=False
        )
        
        embed.set_footer(text="Следующая кампания будет доступна через 36 часов")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomicInfluence(bot))
