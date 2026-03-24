import discord
from discord.ext import commands
import os
import json
import random
import asyncio
from flask import Flask
from threading import Thread

# --- WEB SUNUCUSU ---
app = Flask('')
@app.route('/')
def home(): return "Bot Aktif!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- BOT AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Çekiliş için üye listesi şart
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "stats.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f'Lig ve Çekiliş Sistemi Hazır: {bot.user}')

# --- LİG İSTATİSTİK SİSTEMİ ---

@bot.command()
@commands.has_permissions(administrator=True)
async def ekle(ctx, member: discord.Member, tip: str, lig: int):
    """Kullanım: !ekle @üye [gol/asist/cs] [1=Süper, 2=1.Lig]"""
    data = load_data()
    uid = str(member.id)
    if uid not in data:
        data[uid] = {"isim": member.display_name, "gol": 0, "asist": 0, "cs": 0, "deger": 0}
    
    carpan = 1 if lig == 1 else 0.5
    tip = tip.lower()
    artis = {"gol": 2, "asist": 1, "cs": 3}.get(tip, 0) * carpan
    
    if artis == 0:
        return await ctx.send("❌ Geçersiz tip! (gol/asist/cs)")

    data[uid][tip] += 1
    data[uid]["deger"] += artis
    save_data(data)
    await ctx.send(f"✅ {member.display_name} istatistiği işlendi. Yeni Değer: {data[uid]['deger']}M")

@bot.command()
@commands.has_permissions(administrator=True)
async def sil(ctx, member: discord.Member, tip: str, lig: int):
    """Hata düzeltme: !sil @üye [gol/asist/cs] [1=Süper, 2=1.Lig]"""
    data = load_data()
    uid = str(member.id)
    if uid not in data or data[uid][tip.lower()] <= 0:
        return await ctx.send("❌ Silecek veri bulunamadı!")

    carpan = 1 if lig == 1 else 0.5
    azalis = {"gol": 2, "asist": 1, "cs": 3}.get(tip.lower(), 0) * carpan
    
    data[uid][tip.lower()] -= 1
    data[uid]["deger"] -= azalis
    save_data(data)
    await ctx.send(f"⚠️ {member.display_name} verisi düzeltildi. Yeni Değer: {data[uid]['deger']}M")

@bot.command()
async def bilgi(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    uid = str(member.id)
    
    if uid not in data:
        return await ctx.send("Kayıt bulunamadı.")
    
    s = data[uid]
    embed = discord.Embed(title=f"📊 {s['isim']} Kariyeri", color=0x2ecc71)
    embed.add_field(name="⚽ Gol", value=s["gol"], inline=True)
    embed.add_field(name="🅰️ Asist", value=s["asist"], inline=True)
    embed.add_field(name="🛡️ CS", value=s["cs"], inline=True)
    embed.add_field(name="💰 Piyasa Değeri", value=f"{s['deger']}M €", inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    await ctx.send(embed=embed)

# --- RENKLİ ÇEKİLİŞ SİSTEMİ ---

@bot.command()
@commands.has_permissions(administrator=True)
async def cekilis(ctx, süre: int, görsel_url: str, *, ödül: str):
    """Kullanım: !cekilis [saniye] [görsel_link] [ödül ismi]"""
    embed = discord.Embed(title="🎉 DEV ÇEKİLİŞ BAŞLADI! 🎉", description=f"**Ödül:** {ödül}\n**Süre:** {süre} saniye\n\nKatılmak için 🎉 tepkisine tıkla!", color=0xff5733)
    embed.set_image(url=görsel_url)
    embed.set_footer(text="Bol şanslar!")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    
    await asyncio.sleep(süre)
    
    new_msg = await ctx.channel.fetch_message(msg.id)
    users = [user async for user in new_msg.reactions[0].users() if not user.bot]
    
    if len(users) > 0:
        kazanan = random.choice(users)
        basari_embed = discord.Embed(title="🎊 ÇEKİLİŞ SONUÇLANDI 🎊", description=f"**Kazanan:** {kazanan.mention}\n**Ödül:** {ödül}\n\nTebrikler!", color=0xf1c40f)
        basari_embed.set_image(url=görsel_url)
        await ctx.send(embed=basari_embed)
    else:
        await ctx.send("😢 Çekilişe kimse katılmadı.")

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
    
