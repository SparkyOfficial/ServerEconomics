import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import random
import asyncio

class Personal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(name="баланс", description="Показать свой баланс или баланс другого пользователя")
    async def balance(self, ctx, пользователь: discord.Member = None):
        """Команда для показа баланса"""
        target_user = пользователь or ctx.author
        
        balance = await self.bot.get_user_balance(ctx.guild, target_user)
        
        # Получить статистику
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT total_earned FROM wallets WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, target_user.id)
        )
        result = cursor.fetchone()
        total_earned = result[0] if result else 0
        
        # Получить последние транзакции
        cursor.execute(
            """SELECT amount, transaction_type, description, timestamp 
               FROM transactions 
               WHERE guild_id = ? AND (from_user_id = ? OR to_user_id = ?) 
               ORDER BY timestamp DESC LIMIT 5""",
            (ctx.guild.id, target_user.id, target_user.id)
        )
        recent_transactions = cursor.fetchall()
        conn.close()
        
        embed = discord.Embed(
            title=f"💰 Кошелек {target_user.display_name}",
            color=0x00FF00 if balance > 0 else 0xFF0000
        )
        
        embed.add_field(
            name="Текущий баланс",
            value=f"**{balance:,}** монет",
            inline=True
        )
        
        embed.add_field(
            name="Всего заработано",
            value=f"{total_earned:,} монет",
            inline=True
        )
        
        if recent_transactions:
            transactions_text = ""
            for amount, trans_type, desc, timestamp in recent_transactions[:3]:
                sign = "+" if trans_type in ["work", "daily", "transfer"] and amount > 0 else "-"
                transactions_text += f"{sign}{amount} - {desc}\n"
            
            embed.add_field(
                name="Последние операции",
                value=transactions_text or "Нет операций",
                inline=False
            )
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await ctx.respond(embed=embed)
    
    @commands.slash_command(name="работа", description="Поработать и заработать деньги")
    async def work(self, ctx):
        """Команда для работы"""
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        # Проверить кулдаун
        cursor.execute(
            "SELECT last_work FROM wallets WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, ctx.author.id)
        )
        result = cursor.fetchone()
        
        if result and result[0]:
            last_work = datetime.fromisoformat(result[0])
            cooldown_hours = self.bot.config["personal_economy"]["work_cooldown_hours"]
            next_work = last_work + timedelta(hours=cooldown_hours)
            
            if datetime.now() < next_work:
                remaining = next_work - datetime.now()
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏰ Слишком рано для работы",
                    description=f"Вы можете работать снова через {hours}ч {minutes}м",
                    color=0xFF6B35
                )
                await ctx.respond(embed=embed)
                return
        
        # Случайная награда
        min_reward = self.bot.config["personal_economy"]["work_min_reward"]
        max_reward = self.bot.config["personal_economy"]["work_max_reward"]
        reward = random.randint(min_reward, max_reward)
        
        # Случайная работа
        jobs = [
            "программировали Discord бота", "торговали криптовалютой", "писали документацию",
            "оптимизировали базу данных", "проводили код-ревью", "настраивали сервер",
            "разрабатывали API", "тестировали приложение", "изучали новые технологии",
            "участвовали в хакатоне", "консультировали клиентов", "создавали контент"
        ]
        job_description = f"Вы {random.choice(jobs)}"
        
        # Добавить деньги
        new_balance, tax = await self.bot.add_user_money(
            ctx.guild, ctx.author, reward, "work", job_description
        )
        
        # Обновить время последней работы
        cursor.execute(
            "UPDATE wallets SET last_work = ? WHERE guild_id = ? AND user_id = ?",
            (datetime.now().isoformat(), ctx.guild.id, ctx.author.id)
        )
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="💼 Работа выполнена!",
            description=job_description,
            color=0x00FF00
        )
        
        embed.add_field(
            name="Заработано",
            value=f"+{reward} монет",
            inline=True
        )
        
        if tax > 0:
            embed.add_field(
                name="Налог",
                value=f"-{tax} монет ({self.bot.config['personal_economy']['tax_rate']*100:.0f}%)",
                inline=True
            )
        
        embed.add_field(
            name="Новый баланс",
            value=f"{new_balance:,} монет",
            inline=True
        )
        
        await ctx.respond(embed=embed)
    
    @commands.slash_command(name="ежедневно", description="Получить ежедневную награду")
    async def daily(self, ctx):
        """Команда для ежедневной награды"""
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        # Проверить кулдаун
        cursor.execute(
            "SELECT last_daily FROM wallets WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, ctx.author.id)
        )
        result = cursor.fetchone()
        
        if result and result[0]:
            last_daily = datetime.fromisoformat(result[0])
            next_daily = last_daily + timedelta(days=1)
            
            if datetime.now() < next_daily:
                remaining = next_daily - datetime.now()
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏰ Ежедневная награда уже получена",
                    description=f"Следующая награда через {remaining.days}д {hours}ч {minutes}м",
                    color=0xFF6B35
                )
                await ctx.respond(embed=embed)
                return
        
        reward = self.bot.config["personal_economy"]["daily_reward"]
        
        # Добавить деньги
        new_balance, tax = await self.bot.add_user_money(
            ctx.guild, ctx.author, reward, "daily", "Ежедневная награда"
        )
        
        # Обновить время последней награды
        cursor.execute(
            "UPDATE wallets SET last_daily = ? WHERE guild_id = ? AND user_id = ?",
            (datetime.now().isoformat(), ctx.guild.id, ctx.author.id)
        )
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🎁 Ежедневная награда получена!",
            description="Возвращайтесь завтра за новой наградой!",
            color=0x00FF00
        )
        
        embed.add_field(
            name="Получено",
            value=f"+{reward} монет",
            inline=True
        )
        
        if tax > 0:
            embed.add_field(
                name="Налог",
                value=f"-{tax} монет ({self.bot.config['personal_economy']['tax_rate']*100:.0f}%)",
                inline=True
            )
        
        embed.add_field(
            name="Новый баланс",
            value=f"{new_balance:,} монет",
            inline=True
        )
        
        await ctx.respond(embed=embed)
    
    @commands.slash_command(name="перевести", description="Перевести деньги другому пользователю")
    async def transfer(self, ctx, получатель: discord.Member, сумма: int):
        """Команда для перевода денег"""
        if получатель == ctx.author:
            await ctx.respond("❌ Нельзя переводить деньги самому себе!", ephemeral=True)
            return
        
        if получатель.bot:
            await ctx.respond("❌ Нельзя переводить деньги ботам!", ephemeral=True)
            return
        
        if сумма <= 0:
            await ctx.respond("❌ Сумма должна быть положительной!", ephemeral=True)
            return
        
        # Выполнить перевод
        success, new_balance, fee = await self.bot.transfer_money(
            ctx.guild, ctx.author, получатель, сумма
        )
        
        if not success:
            embed = discord.Embed(
                title="❌ Недостаточно средств",
                description=f"У вас {new_balance:,} монет, а нужно {сумма + fee:,} (включая комиссию {fee} монет)",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💸 Перевод выполнен",
            description=f"Вы перевели **{сумма:,}** монет пользователю {получатель.mention}",
            color=0x00FF00
        )
        
        if fee > 0:
            embed.add_field(
                name="Комиссия",
                value=f"{fee} монет ({self.bot.config['personal_economy']['transfer_fee']*100:.0f}%)",
                inline=True
            )
        
        embed.add_field(
            name="Ваш новый баланс",
            value=f"{new_balance:,} монет",
            inline=True
        )
        
        await ctx.respond(embed=embed)
        
        # Уведомить получателя
        try:
            recipient_balance = await self.bot.get_user_balance(ctx.guild, получатель)
            dm_embed = discord.Embed(
                title="💰 Вы получили перевод!",
                description=f"{ctx.author.mention} перевел вам **{сумма:,}** монет",
                color=0x00FF00
            )
            dm_embed.add_field(
                name="Ваш баланс",
                value=f"{recipient_balance:,} монет",
                inline=True
            )
            await получатель.send(embed=dm_embed)
        except:
            pass  # Если не удалось отправить ЛС
    
    @commands.slash_command(name="лидеры", description="Показать топ самых богатых пользователей")
    async def leaderboard(self, ctx):
        """Команда для показа таблицы лидеров"""
        conn = sqlite3.connect(self.bot.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT user_id, balance, total_earned 
               FROM wallets 
               WHERE guild_id = ? 
               ORDER BY balance DESC 
               LIMIT 10""",
            (ctx.guild.id,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            embed = discord.Embed(
                title="📊 Таблица лидеров",
                description="Пока никто не зарегистрирован в экономической системе.",
                color=0x2F3136
            )
            await ctx.respond(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Топ-10 самых богатых",
            color=0xFFD700
        )
        
        leaderboard_text = ""
        for i, (user_id, balance, total_earned) in enumerate(results, 1):
            try:
                user = ctx.guild.get_member(user_id)
                if user:
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    leaderboard_text += f"{medal} **{user.display_name}** — {balance:,} монет\n"
            except:
                continue
        
        embed.description = leaderboard_text or "Нет активных пользователей"
        
        # Показать позицию текущего пользователя
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*) + 1 as position 
               FROM wallets 
               WHERE guild_id = ? AND balance > (
                   SELECT balance FROM wallets WHERE guild_id = ? AND user_id = ?
               )""",
            (ctx.guild.id, ctx.guild.id, ctx.author.id)
        )
        result = cursor.fetchone()
        user_position = result[0] if result else "N/A"
        
        user_balance = await self.bot.get_user_balance(ctx.guild, ctx.author)
        embed.set_footer(text=f"Ваша позиция: #{user_position} ({user_balance:,} монет)")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Personal(bot))
