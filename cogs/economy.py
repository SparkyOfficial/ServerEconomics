import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import asyncio

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(name="казна", description="Показать текущий баланс казны")
    async def treasury(self, ctx):
        """Команда для показа текущей казны"""
        treasury = await self.bot.get_treasury(ctx.guild)
        
        embed = discord.Embed(
            title="💰 Государственная казна",
            description=f"**Текущий баланс:** {treasury:,} монет",
            color=0x2F3136
        )
        
        # Добавление информации о доходе
        income_per_minute = ctx.guild.member_count * self.bot.config["income_per_member"]
        embed.add_field(
            name="📈 Доход",
            value=f"{income_per_minute} монет/мин\n({ctx.guild.member_count} участников × {self.bot.config['income_per_member']})",
            inline=True
        )
        
        # Последние транзакции
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT amount, description, timestamp 
               FROM transactions 
               WHERE guild_id = ? 
               ORDER BY timestamp DESC 
               LIMIT 5""",
            (ctx.guild.id,)
        )
        
        transactions = cursor.fetchall()
        conn.close()
        
        if transactions:
            transaction_text = ""
            for amount, desc, timestamp in transactions:
                sign = "+" if amount > 0 else ""
                transaction_text += f"{sign}{amount} - {desc}\n"
            
            embed.add_field(
                name="📋 Последние операции",
                value=transaction_text[:1024],
                inline=False
            )
        
        await ctx.respond(embed=embed)
    
    @commands.slash_command(name="экономика", description="Показать статус экономики")
    async def economy_status(self, ctx):
        """Команда для показа статуса экономики"""
        # Получение данных за последние 10 минут
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        
        cursor.execute(
            """SELECT treasury, timestamp 
               FROM economy 
               WHERE guild_id = ? AND timestamp >= ? 
               ORDER BY timestamp""",
            (ctx.guild.id, ten_minutes_ago)
        )
        
        recent_data = cursor.fetchall()
        conn.close()
        
        if len(recent_data) < 2:
            growth = 0
        else:
            growth = recent_data[-1][0] - recent_data[0][0]
        
        # Определение статуса экономики
        current_treasury = await self.bot.get_treasury(ctx.guild)
        
        if current_treasury < 0:
            status = "💥 Крах"
            color = 0xFF0000
            description = "Казна в минусе! Срочно нужны меры по восстановлению экономики."
        elif growth <= 0:
            status = "📉 Рецессия"
            color = 0xFF4500
            description = "Экономика не растет. Рост за 10 минут: 0 или отрицательный."
        elif growth <= 10:
            status = "😐 Стагнация"
            color = 0xFFA500
            description = "Медленный рост экономики. Нужны стимулирующие меры."
        elif growth <= 50:
            status = "📈 Стабильный рост"
            color = 0x32CD32
            description = "Экономика развивается стабильно."
        elif growth <= 200:
            status = "🚀 Быстрый рост"
            color = 0x00FF00
            description = "Экономика быстро растет!"
        else:
            status = "💎 Экономический бум"
            color = 0xFFD700
            description = "Невероятный экономический рост!"
        
        embed = discord.Embed(
            title="📊 Статус экономики",
            description=description,
            color=color
        )
        
        embed.add_field(
            name="Текущий статус",
            value=status,
            inline=True
        )
        
        embed.add_field(
            name="Рост за 10 минут",
            value=f"{growth:+} монет",
            inline=True
        )
        
        embed.add_field(
            name="Текущая казна",
            value=f"{current_treasury:,} монет",
            inline=True
        )
        
        # Прогноз
        income_per_hour = ctx.guild.member_count * self.bot.config["income_per_member"] * 60
        embed.add_field(
            name="📈 Прогноз на час",
            value=f"+{income_per_hour:,} монет",
            inline=True
        )
        
        # Генерация изображения статуса
        from utils.visualization import create_status_image
        
        status_image_path = create_status_image(status, current_treasury, growth, ctx.guild.name)
        
        file = None
        if status_image_path:
            file = discord.File(status_image_path, filename="status.png")
            embed.set_image(url="attachment://status.png")
        
        await ctx.respond(embed=embed, file=file)
        
        if status_image_path:
            import os
            os.remove(status_image_path)
    
    @commands.slash_command(name="график", description="Сгенерировать график экономики")
    async def force_chart(self, ctx):
        """Принудительная генерация графика"""
        await ctx.defer()
        
        try:
            from utils.visualization import create_economy_chart
            chart_path = await create_economy_chart(self.bot, ctx.guild.id)
            
            if chart_path:
                embed = discord.Embed(
                    title="📊 График экономики",
                    description="Состояние казны за последние 12 часов",
                    color=0x2F3136
                )
                
                file = discord.File(chart_path, filename="economy_chart.png")
                embed.set_image(url="attachment://economy_chart.png")
                
                await ctx.followup.send(embed=embed, file=file)
                
                # Удаление временного файла
                import os
                os.remove(chart_path)
            else:
                await ctx.followup.send("❌ Не удалось создать график. Недостаточно данных.")
                
        except Exception as e:
            await ctx.followup.send(f"❌ Ошибка при создании графика: {str(e)}")
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Обработка создания канала"""
        cost = self.bot.config["costs"]["channel_create"]
        success, new_balance = await self.bot.spend_money(
            channel.guild, 
            cost, 
            f"Создание канала #{channel.name}"
        )
        
        if not success:
            # Отправка предупреждения в лог-канал
            log_channel = self.bot.get_channel(self.bot.chart_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="⚠️ Недостаточно средств",
                    description=f"Не удалось списать {cost} монет за создание канала #{channel.name}",
                    color=0xFF0000
                )
                embed.add_field(name="Текущий баланс", value=f"{new_balance} монет")
                await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Обработка удаления канала"""
        cost = self.bot.config["costs"]["channel_delete"]
        success, new_balance = await self.bot.spend_money(
            channel.guild, 
            cost, 
            f"Удаление канала #{channel.name}"
        )
        
        if not success:
            log_channel = self.bot.get_channel(self.bot.chart_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="⚠️ Недостаточно средств",
                    description=f"Не удалось списать {cost} монет за удаление канала #{channel.name}",
                    color=0xFF0000
                )
                embed.add_field(name="Текущий баланс", value=f"{new_balance} монет")
                await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Обработка изменения ролей участника"""
        if before.roles != after.roles:
            # Проверка добавления новых ролей
            new_roles = set(after.roles) - set(before.roles)
            if new_roles:
                cost = self.bot.config["costs"]["role_assign"] * len(new_roles)
                success, new_balance = await self.bot.spend_money(
                    after.guild,
                    cost,
                    f"Выдача {len(new_roles)} роли(ей) пользователю {after.display_name}"
                )
                
                if not success:
                    log_channel = self.bot.get_channel(self.bot.chart_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="⚠️ Недостаточно средств",
                            description=f"Не удалось списать {cost} монет за выдачу ролей",
                            color=0xFF0000
                        )
                        embed.add_field(name="Текущий баланс", value=f"{new_balance} монет")
                        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        """Обработка создания эмодзи"""
        new_emojis = len(after) - len(before)
        if new_emojis > 0:
            cost = self.bot.config["costs"]["emoji_create"] * new_emojis
            success, new_balance = await self.bot.spend_money(
                guild,
                cost,
                f"Создание {new_emojis} эмодзи"
            )
            
            if not success:
                log_channel = self.bot.get_channel(self.bot.chart_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="⚠️ Недостаточно средств",
                        description=f"Не удалось списать {cost} монет за создание эмодзи",
                        color=0xFF0000
                    )
                    embed.add_field(name="Текущий баланс", value=f"{new_balance} монет")
                    await log_channel.send(embed=embed)

    @commands.slash_command(name="модификаторы", description="Показать активные экономические модификаторы")
    async def modifiers(self, ctx):
        """Команда для показа активных модификаторов"""
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT description, value, modifier_type, expires_at FROM modifiers WHERE guild_id = ? AND expires_at > CURRENT_TIMESTAMP",
            (ctx.guild.id,)
        )
        
        active_modifiers = cursor.fetchall()
        conn.close()
        
        embed = discord.Embed(
            title="📜 Активные экономические модификаторы",
            color=0x2F3136
        )
        
        if not active_modifiers:
            embed.description = "Нет активных модификаторов."
        else:
            for desc, value, mod_type, expires_at_str in active_modifiers:
                expires_at = datetime.fromisoformat(expires_at_str)
                remaining_time = expires_at - datetime.now()
                
                if mod_type == 'income_multiplier':
                    effect = f"{value*100-100:+.0f}% к доходу"
                elif mod_type == 'cost_reduction':
                    effect = f"-{value*100:.0f}% к расходам"
                else:
                    effect = f"Значение: {value}"
                
                embed.add_field(
                    name=desc,
                    value=f"**Эффект:** {effect}\n**Осталось:** {str(remaining_time).split('.')[0]}",
                    inline=False
                )
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Economy(bot))
