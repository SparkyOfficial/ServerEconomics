import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
import random
import asyncio

class Personal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="баланс", description="Показать свой баланс или баланс другого пользователя")
    @app_commands.describe(пользователь="Пользователь, чей баланс нужно показать")
    async def balance(self, interaction: discord.Interaction, пользователь: discord.Member = None):
        """Команда для показа баланса"""
        target_user = пользователь or interaction.user
        
        balance = await self.bot.get_user_balance(interaction.guild, target_user)
        
        # Получить статистику
        async with aiosqlite.connect(self.bot.db_path) as conn:
            # Вычисляем total_earned из транзакций
            cursor = await conn.execute(
                """SELECT COALESCE(SUM(amount), 0) as total_earned 
                   FROM transactions 
                   WHERE guild_id = ? AND to_user_id = ? AND amount > 0""",
                (interaction.guild.id, target_user.id)
            )
            result = await cursor.fetchone()
            total_earned = result[0] if result else 0
            await cursor.close()
            
            # Получить последние транзакции
            cursor = await conn.execute(
                """SELECT amount, transaction_type, description, timestamp 
                   FROM transactions 
                   WHERE guild_id = ? AND (from_user_id = ? OR to_user_id = ?) 
                   ORDER BY timestamp DESC LIMIT 5""",
                (interaction.guild.id, target_user.id, target_user.id)
            )
            recent_transactions = await cursor.fetchall()
            await cursor.close()
        
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
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="работа", description="Поработать и заработать деньги")
    async def work(self, interaction: discord.Interaction):
        """Команда для работы"""
        async with aiosqlite.connect(self.bot.db_path) as conn:
            cursor = await conn.execute(
                "SELECT last_work FROM wallets WHERE guild_id = ? AND user_id = ?",
                (interaction.guild.id, interaction.user.id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            
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
                    await interaction.response.send_message(embed=embed)
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
            new_balance = await self.bot.add_user_money(
                interaction.guild, interaction.user, reward, "work", job_description
            )
            
            # Обновить время последней работы
            await conn.execute(
                "UPDATE wallets SET last_work = ? WHERE guild_id = ? AND user_id = ?",
                (datetime.now().isoformat(), interaction.guild.id, interaction.user.id)
            )
            await conn.commit()
        
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
        
        embed.add_field(
            name="Новый баланс",
            value=f"{new_balance:,} монет",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ежедневно", description="Получить ежедневную награду")
    async def daily(self, interaction: discord.Interaction):
        """Команда для ежедневной награды"""
        async with aiosqlite.connect(self.bot.db_path) as conn:
            cursor = await conn.execute(
                "SELECT last_daily FROM wallets WHERE guild_id = ? AND user_id = ?",
                (interaction.guild.id, interaction.user.id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            
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
                    await interaction.response.send_message(embed=embed)
                    return
            
            reward = self.bot.config["personal_economy"]["daily_reward"]
            
            # Добавить деньги
            new_balance = await self.bot.add_user_money(
                interaction.guild, interaction.user, reward, "daily", "Ежедневная награда"
            )
            
            # Обновить время последней награды
            await conn.execute(
                "UPDATE wallets SET last_daily = ? WHERE guild_id = ? AND user_id = ?",
                (datetime.now().isoformat(), interaction.guild.id, interaction.user.id)
            )
            await conn.commit()
        
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
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="перевести", description="Перевести деньги другому пользователю")
    @app_commands.describe(
        получатель="Пользователь, которому переводим деньги",
        сумма="Сумма для перевода"
    )
    async def transfer(self, interaction: discord.Interaction, получатель: discord.Member, сумма: int):
        """Команда для перевода денег"""
        if получатель == interaction.user:
            await interaction.response.send_message("❌ Нельзя переводить деньги самому себе!", ephemeral=True)
            return
        
        if получатель.bot:
            await interaction.response.send_message("❌ Нельзя переводить деньги ботам!", ephemeral=True)
            return
        
        if сумма <= 0:
            await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
            return
        
        # Выполнить перевод
        success, new_balance, fee = await self.bot.transfer_money(
            interaction.guild, interaction.user, получатель, сумма
        )
        
        if not success:
            embed = discord.Embed(
                title="❌ Недостаточно средств",
                description=f"У вас {new_balance:,} монет, а нужно {сумма + fee:,} (включая комиссию {fee} монет)",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        
        await interaction.response.send_message(embed=embed)
        
        # Уведомить получателя
        try:
            recipient_balance = await self.bot.get_user_balance(interaction.guild, получатель)
            dm_embed = discord.Embed(
                title="💰 Вы получили перевод!",
                description=f"{interaction.user.mention} перевел вам **{сумма:,}** монет",
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
    
    @app_commands.command(name="лидеры", description="Показать топ самых богатых пользователей")
    async def leaderboard(self, interaction: discord.Interaction):
        """Команда для показа таблицы лидеров"""
        async with aiosqlite.connect(self.bot.db_path) as conn:
            cursor = await conn.execute(
                """SELECT w.user_id, w.balance, COALESCE(SUM(t.amount), 0) as total_earned 
                   FROM wallets w
                   LEFT JOIN transactions t ON w.guild_id = t.guild_id AND w.user_id = t.to_user_id AND t.amount > 0
                   WHERE w.guild_id = ? 
                   GROUP BY w.user_id, w.balance
                   ORDER BY w.balance DESC 
                   LIMIT 10""",
                (interaction.guild.id,)
            )
            
            results = await cursor.fetchall()
            await cursor.close()
            
            if not results:
                embed = discord.Embed(
                    title="📊 Таблица лидеров",
                    description="Пока никто не зарегистрирован в экономической системе.",
                    color=0x2F3136
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Топ-10 самых богатых",
                color=0xFFD700
            )
            
            leaderboard_text = ""
            for i, (user_id, balance, total_earned) in enumerate(results, 1):
                try:
                    user = interaction.guild.get_member(user_id)
                    if user:
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        leaderboard_text += f"{medal} **{user.display_name}** — {balance:,} монет\n"
                except:
                    continue
            
            embed.description = leaderboard_text or "Нет активных пользователей"
            
            # Показать позицию текущего пользователя
            cursor = await conn.execute(
                """SELECT COUNT(*) + 1 as position 
                   FROM wallets 
                   WHERE guild_id = ? AND balance > (
                       SELECT balance FROM wallets WHERE guild_id = ? AND user_id = ?
                   )""",
                (interaction.guild.id, interaction.guild.id, interaction.user.id)
            )
            result = await cursor.fetchone()
            await cursor.close()
            
            user_position = result[0] if result else "N/A"
            user_balance = await self.bot.get_user_balance(interaction.guild, interaction.user)
            embed.set_footer(text=f"Ваша позиция: #{user_position} ({user_balance:,} монет)")
            
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Personal(bot))
