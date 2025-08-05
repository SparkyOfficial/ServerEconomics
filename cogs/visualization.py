import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import sqlite3
from datetime import datetime, timedelta
import io
import numpy as np

class Visualization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Настройка стиля в духе TNO/Millennium Dawn
        plt.style.use('dark_background')
        self.colors = {
            'background': '#1a1a1a',
            'grid': '#333333',
            'positive': '#2d5a27',
            'negative': '#5a2727',
            'neutral': '#4a4a4a',
            'text': '#e0e0e0',
            'accent': '#8b0000'
        }

def setup(bot):
    bot.add_cog(Visualization(bot))
