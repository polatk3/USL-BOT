import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# 7/24 uyanık kalma sistemi
app = Flask('')
@app.route('/')
def home():
    return "Bot Aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot başarıyla açıldı: {bot.user}')

@bot.command()
async def selam(ctx):
    await ctx.send('Selam! Bot şu an Render üzerinden 7/24 aktif.')

# Sistemi başlat
keep_alive()

# Tokenı kodun içine yazmıyoruz, Render'daki gizli kısımdan çekecek
token = os.getenv('DISCORD_TOKEN')
bot.run(token)

