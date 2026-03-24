import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from flask import Flask
from threading import Thread

# --- WEB SUNUCUSU (7/24 İÇİN) ---
app = Flask('')
@app.route('/')
def home(): return "Bot Aktif!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- BOT VE SLASH AYARLARI ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash komutları senkronize edildi!")

bot = MyBot()
DATA_FILE = "stats.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f'USL Manager Giriş Yaptı: {bot.user}')

# --- SLASH KOMUTLARI ---

@bot.tree.command(name="ekle", description="Oyuncuya istatistik ve değer ekler.")
@app_commands.describe(lig="1: Süper Lig, 2: 1. Lig", tip="gol, asist veya cs")
async def ekle(interaction: discord.Interaction, üye: discord.Member, tip: str, lig: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
    
    data = load_data()
    uid = str(üye.id)
    if uid not in data:
        data[uid] = {"isim": üye.display_name, "gol": 0, "asist": 0, "cs": 0, "deger": 0}
    
    carpan = 1 if lig == 1 else 0.5
    tip = tip.lower()
    puan = {"gol": 2, "asist": 1, "cs": 3}.get(tip, 0)
    
    if puan == 0:
        return await interaction.response.send_message("❌ Geçersiz tip! (gol/asist/cs)", ephemeral=True)

    data[uid][tip] += 1
    data[uid]["deger"] += (puan * carpan)
    save_data(data)
    await interaction.response.send_message(f"✅ {üye.mention} için {tip} eklendi! Yeni Değer: **{data[uid]['deger']}M**")

@bot.tree.command(name="sil", description="Hatalı girilen istatistiği düşer.")
@app_commands.describe(lig="1: Süper Lig, 2: 1. Lig", tip="gol, asist veya cs")
async def sil(interaction: discord.Interaction, üye: discord.Member, tip: str, lig: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
    
    data = load_data()
    uid = str(üye.id)
    tip = tip.lower()
    
    if uid not in data or data[uid].get(tip, 0) <= 0:
        return await interaction.response.send_message("❌ Silecek veri bulunamadı!", ephemeral=True)

    carpan = 1 if lig == 1 else 0.5
    puan = {"gol": 2, "asist": 1, "cs": 3}.get(tip, 0)
    
    data[uid][tip] -= 1
    data[uid]["deger"] -= (puan * carpan)
    save_data(data)
    await interaction.response.send_message(f"⚠️ {üye.mention} verisi düzeltildi. Yeni Değer: **{data[uid]['deger']}M**")

@bot.tree.command(name="bilgi", description="Oyuncu istatistiklerini ve piyasa değerini gösterir.")
async def bilgi(interaction: discord.Interaction, üye: discord.Member = None):
    üye = üye or interaction.user
    data = load_data()
    uid = str(üye.id)
    
    if uid not in data:
        return await interaction.response.send_message("Oyuncu kaydı bulunamadı.", ephemeral=True)
    
    s = data[uid]
    embed = discord.Embed(title=f"📋 {s['isim']} - Oyuncu Kartı", color=0x3498db)
    embed.add_field(name="⚽ Gol", value=s["gol"], inline=True)
    embed.add_field(name="🅰️ Asist", value=s["asist"], inline=True)
    embed.add_field(name="🛡️ Clean Sheet", value=s["cs"], inline=True)
    embed.add_field(name="💰 Piyasa Değeri", value=f"{s['deger']}M €", inline=False)
    if üye.avatar: embed.set_thumbnail(url=üye.avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siralam", description="En değerli 10 oyuncuyu listeler.")
async def siralam(interaction: discord.Interaction):
    data = load_data()
    if not data: return await interaction.response.send_message("Henüz kayıtlı oyuncu yok.")
    
    # Değere göre büyükten küçüğe sırala
    sorted_data = sorted(data.values(), key=lambda x: x['deger'], reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 EN DEĞERLİ 10 OYUNCU (TOP 10)", color=0xf1c40f)
    for i, user in enumerate(sorted_data, 1):
        embed.add_field(name=f"{i}. {user['isim']}", value=f"Değer: {user['deger']}M € | G: {user['gol']} A: {user['asist']} CS: {user['cs']}", inline=False)
    
    await interaction.response.send_message(embed=embed)

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
    
