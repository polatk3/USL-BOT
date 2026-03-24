import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# Render'ın botu kapatmaması için gerekli web sunucusu
app = Flask('')
@app.route('/')
def home():
    return "Bot Aktif!"

def run():
    # Render'ın zorunlu kıldığı PORT ayarı
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'BOT BASARIYLA ACILDI: {bot.user}')

@bot.command()
async def selam(ctx):
    await ctx.send('Selam! Bot şu an 7/24 aktif.')

# Önce web sunucusunu, sonra botu başlatıyoruz
if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"Hata oluştu: {e}")
    else:
        print("TOKEN BULUNAMADI! Render Environment ayarlarına bak.")
        
