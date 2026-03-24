import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home():
    return "Bot Aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot aktif: {bot.user}')

@bot.command()
async def selam(ctx):
    await ctx.send('Selam! Bot 7/24 aktif.')

keep_alive()
bot.run('MTQ4NTg0OTUzNzk5MzExMzYyMA.GF9vor.qsOhFsOSIf8q8gCRuZCmTcEOt7oYaEfQOKtaig')
