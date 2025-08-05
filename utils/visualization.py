import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import aiosqlite
from datetime import datetime, timedelta
import io
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont

# Настройка стиля в духе TNO/Millennium Dawn
plt.style.use('dark_background')

COLORS = {
    'background': '#1a1a1a',
    'grid': '#333333',
    'positive': '#2d5a27',
    'negative': '#5a2727',
    'neutral': '#4a4a4a',
    'text': '#e0e0e0',
    'accent': '#8b0000',
    'treasury': '#4a90e2',
    'income': '#7ed321',
    'expense': '#d0021b'
}

async def create_economy_chart(bot, guild_id=None):
    """Создание графика экономики"""
    try:
        # Получение данных за последние 12 часов
        async with sqlite3.connect(bot.db_path) as conn:
            twelve_hours_ago = datetime.now() - timedelta(hours=12)
            
            if guild_id:
                cursor = await conn.execute(
                    """SELECT treasury, timestamp 
                       FROM economy 
                       WHERE guild_id = ? AND timestamp >= ? 
                       ORDER BY timestamp""",
                    (guild_id, twelve_hours_ago)
                )
            else:
                # Для всех серверов (берем первый найденный)
                cursor = await conn.execute(
                    """SELECT treasury, timestamp, guild_id
                       FROM economy 
                       WHERE timestamp >= ? 
                       ORDER BY timestamp""",
                    (twelve_hours_ago,)
                )
            
            data = await cursor.fetchall()
            await cursor.close()
            
            if not data:
                return None
            
            # Если guild_id не указан, берем данные первого сервера
            if not guild_id:
                guild_id = data[0][2] if len(data[0]) > 2 else data[0][0]
                data = [(row[0], row[1]) for row in data if (len(row) > 2 and row[2] == guild_id) or len(row) == 2]
            
            # Получение транзакций для пирога
            cursor = await conn.execute(
                """SELECT SUM(amount) as total, 
                          CASE 
                              WHEN amount > 0 THEN 'Доходы'
                              ELSE 'Расходы'
                          END as type
                   FROM transactions 
                   WHERE guild_id = ? AND timestamp >= ?
                   GROUP BY type""",
                (guild_id, twelve_hours_ago)
            )
            
            transaction_data = await cursor.fetchall()
            await cursor.close()
        
        # Создание фигуры с двумя подграфиками
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        fig.patch.set_facecolor(COLORS['background'])
        
        # График изменения казны
        timestamps = [datetime.fromisoformat(row[1]) for row in data]
        treasuries = [row[0] for row in data]
        
        ax1.plot(timestamps, treasuries, color=COLORS['treasury'], linewidth=3, marker='o', markersize=4)
        ax1.fill_between(timestamps, treasuries, alpha=0.3, color=COLORS['treasury'])
        
        # Настройка первого графика
        ax1.set_title('Изменение государственной казны\n(последние 12 часов)', 
                     color=COLORS['text'], fontsize=14, fontweight='bold')
        ax1.set_xlabel('Время', color=COLORS['text'])
        ax1.set_ylabel('Монеты', color=COLORS['text'])
        ax1.grid(True, color=COLORS['grid'], alpha=0.3)
        ax1.tick_params(colors=COLORS['text'])
        
        # Форматирование времени на оси X
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Добавление текущего значения
        if treasuries:
            current_value = treasuries[-1]
            ax1.annotate(f'{current_value:,} монет', 
                        xy=(timestamps[-1], current_value),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['accent'], alpha=0.8),
                        color=COLORS['text'], fontweight='bold')
        
        # Пирог доходов/расходов
        if transaction_data:
            labels = []
            values = []
            colors = []
            
            for total, type_name in transaction_data:
                labels.append(f'{type_name}\n{abs(total):,}')
                values.append(abs(total))
                colors.append(COLORS['positive'] if total > 0 else COLORS['negative'])
            
            wedges, texts, autotexts = ax2.pie(values, labels=labels, colors=colors, 
                                              autopct='%1.1f%%', startangle=90,
                                              textprops={'color': COLORS['text']})
            
            # Улучшение внешнего вида пирога
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        else:
            # Если нет данных о транзакциях
            ax2.text(0.5, 0.5, 'Нет данных\nо транзакциях', 
                    ha='center', va='center', transform=ax2.transAxes,
                    color=COLORS['text'], fontsize=12)
        
        ax2.set_title('Доходы и расходы\n(последние 12 часов)', 
                     color=COLORS['text'], fontsize=14, fontweight='bold')
        
        # Общие настройки
        plt.tight_layout()
        
        # Сохранение в временный файл
        temp_path = f"temp_chart_{guild_id}_{int(datetime.now().timestamp())}.png"
        plt.savefig(temp_path, facecolor=COLORS['background'], 
                   edgecolor='none', dpi=150, bbox_inches='tight')
        plt.close()
        
        return temp_path
        
    except Exception as e:
        print(f"Ошибка создания графика: {e}")
        return None

def create_status_image(status, treasury, growth, guild_name):
    """Создание изображения статуса экономики"""
    try:
        # Создание изображения
        width, height = 800, 400
        img = Image.new('RGB', (width, height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)
        
        # Попытка загрузить шрифт
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            text_font = ImageFont.truetype("arial.ttf", 24)
            small_font = ImageFont.truetype("arial.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Определение цвета статуса
        if treasury < 0:
            status_color = '#FF0000'
        elif growth <= 0:
            status_color = '#FF4500'
        elif growth <= 10:
            status_color = '#FFA500'
        elif growth <= 50:
            status_color = '#32CD32'
        elif growth <= 200:
            status_color = '#00FF00'
        else:
            status_color = '#FFD700'
        
        # Рисование фона статуса
        draw.rectangle([50, 50, width-50, height-50], outline=status_color, width=3)
        
        # Заголовок
        draw.text((width//2, 80), f"ЭКОНОМИЧЕСКИЙ СТАТУС", 
                 fill='#e0e0e0', font=title_font, anchor="mm")
        
        draw.text((width//2, 120), guild_name, 
                 fill='#cccccc', font=text_font, anchor="mm")
        
        # Статус
        draw.text((width//2, 180), status, 
                 fill=status_color, font=title_font, anchor="mm")
        
        # Данные
        draw.text((width//2, 240), f"Казна: {treasury:,} монет", 
                 fill='#e0e0e0', font=text_font, anchor="mm")
        
        draw.text((width//2, 280), f"Рост за 10 мин: {growth:+} монет", 
                 fill='#e0e0e0', font=text_font, anchor="mm")
        
        # Временная метка
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        draw.text((width//2, 350), f"Обновлено: {timestamp}", 
                 fill='#888888', font=small_font, anchor="mm")
        
        # Сохранение
        temp_path = f"temp_status_{int(datetime.now().timestamp())}.png"
        img.save(temp_path)
        
        return temp_path
        
    except Exception as e:
        print(f"Ошибка создания изображения статуса: {e}")
        return None

def create_event_image(event_name, description, icon):
    """Создание изображения для события"""
    try:
        width, height = 800, 500
        img = Image.new('RGB', (width, height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)
        
        # Шрифты
        try:
            title_font = ImageFont.truetype("arial.ttf", 32)
            text_font = ImageFont.truetype("arial.ttf", 20)
            icon_font = ImageFont.truetype("arial.ttf", 48)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            icon_font = ImageFont.load_default()
        
        # Рамка
        draw.rectangle([30, 30, width-30, height-30], outline='#8b0000', width=4)
        
        # Иконка
        draw.text((width//2, 100), icon, fill='#FFD700', font=icon_font, anchor="mm")
        
        # Заголовок
        draw.text((width//2, 180), "ЭКОНОМИЧЕСКОЕ СОБЫТИЕ", 
                 fill='#e0e0e0', font=text_font, anchor="mm")
        
        # Название события
        draw.text((width//2, 220), event_name, 
                 fill='#FFD700', font=title_font, anchor="mm")
        
        # Описание (с переносом строк)
        words = description.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if len(test_line) > 60:  # Примерная длина строки
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Рисование описания
        y_offset = 280
        for line in lines:
            draw.text((width//2, y_offset), line, 
                     fill='#cccccc', font=text_font, anchor="mm")
            y_offset += 30
        
        # Временная метка
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        draw.text((width//2, height-60), f"Время события: {timestamp}", 
                 fill='#888888', font=text_font, anchor="mm")
        
        # Сохранение
        temp_path = f"temp_event_{int(datetime.now().timestamp())}.png"
        img.save(temp_path)
        
        return temp_path
        
    except Exception as e:
        print(f"Ошибка создания изображения события: {e}")
        return None
