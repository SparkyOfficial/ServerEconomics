import sqlite3
import random
from datetime import datetime, timedelta
import asyncio

async def check_and_trigger_event(bot, guild):
    """Проверка и запуск случайных событий"""
    try:
        conn = sqlite3.connect(bot.db_path)
        cursor = conn.cursor()
        
        # Проверка последнего события
        cursor.execute(
            "SELECT timestamp FROM events WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild.id,)
        )
        
        last_event = cursor.fetchone()
        conn.close()
        
        if last_event:
            last_event_time = datetime.fromisoformat(last_event[0])
            time_since_last = datetime.now() - last_event_time
            
            # Случайный интервал от 1 до 12 часов
            min_hours = bot.config["event_min_hours"]
            max_hours = bot.config["event_max_hours"]
            
            # Вероятность события увеличивается со временем
            hours_passed = time_since_last.total_seconds() / 3600
            
            if hours_passed < min_hours:
                return False
            
            # Вероятность от 0% (в min_hours) до 100% (в max_hours)
            probability = min(1.0, (hours_passed - min_hours) / (max_hours - min_hours))
            
            if random.random() < probability:
                from cogs.events import Events
                events_cog = bot.get_cog('Events')
                if events_cog:
                    await events_cog.create_random_event(guild)
                    return True
        else:
            # Первое событие - запускаем с вероятностью 10%
            if random.random() < 0.1:
                from cogs.events import Events
                events_cog = bot.get_cog('Events')
                if events_cog:
                    await events_cog.create_random_event(guild)
                    return True
        
        return False
        
    except Exception as e:
        print(f"Ошибка проверки событий: {e}")
        return False

def get_economic_status(treasury, growth):
    """Определение экономического статуса"""
    if treasury < 0:
        return "💥 Крах", 0xFF0000
    elif growth <= 0:
        return "📉 Рецессия", 0xFF4500
    elif growth <= 10:
        return "😐 Стагнация", 0xFFA500
    elif growth <= 50:
        return "📈 Стабильный рост", 0x32CD32
    elif growth <= 200:
        return "🚀 Быстрый рост", 0x00FF00
    else:
        return "💎 Экономический бум", 0xFFD700

def calculate_growth(bot, guild_id, minutes=10):
    """Расчет роста экономики за указанный период"""
    try:
        conn = sqlite3.connect(bot.db_path)
        cursor = conn.cursor()
        
        time_ago = datetime.now() - timedelta(minutes=minutes)
        
        cursor.execute(
            """SELECT treasury, timestamp 
               FROM economy 
               WHERE guild_id = ? AND timestamp >= ? 
               ORDER BY timestamp""",
            (guild_id, time_ago)
        )
        
        data = cursor.fetchall()
        conn.close()
        
        if len(data) < 2:
            return 0
        
        return data[-1][0] - data[0][0]
        
    except Exception as e:
        print(f"Ошибка расчета роста: {e}")
        return 0

async def get_guild_statistics(bot, guild_id):
    """Получение статистики сервера"""
    try:
        conn = sqlite3.connect(bot.db_path)
        cursor = conn.cursor()
        
        # Текущая казна
        cursor.execute(
            "SELECT treasury FROM economy WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 1",
            (guild_id,)
        )
        treasury_result = cursor.fetchone()
        current_treasury = treasury_result[0] if treasury_result else bot.config["initial_treasury"]
        
        # Рост за 10 минут
        growth = calculate_growth(bot, guild_id, 10)
        
        # Общий доход и расходы за сутки
        day_ago = datetime.now() - timedelta(days=1)
        
        cursor.execute(
            """SELECT 
                   SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                   SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses
               FROM transactions 
               WHERE guild_id = ? AND timestamp >= ?""",
            (guild_id, day_ago)
        )
        
        income_expenses = cursor.fetchone()
        total_income = income_expenses[0] or 0
        total_expenses = income_expenses[1] or 0
        
        # Количество событий за неделю
        week_ago = datetime.now() - timedelta(days=7)
        
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE guild_id = ? AND timestamp >= ?",
            (guild_id, week_ago)
        )
        
        events_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'treasury': current_treasury,
            'growth': growth,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'events_count': events_count,
            'net_change': total_income - total_expenses
        }
        
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return None
