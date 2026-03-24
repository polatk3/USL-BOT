import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# --- WEB SUNUCUSU ---
app = Flask('')
@app.route('/')
def home(): return "USL Aktiflik Sistemi Aktif!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- BOT AYARLARI ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.siralama_guncelle.start()
        print("Aktiflik Takip Sistemi Başlatıldı!")

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

# --- SEVİYE VE ÖDÜL KONTROLÜ ---
async def check_level_up(member, old_xp, new_xp, data):
    old_lvl = (old_xp // 100) + 1 # Her 100 mesajda bir seviye
    new_lvl = (new_xp // 100) + 1
    uid = str(member.id)

    if new_lvl > old_lvl:
        # Seviye Ödülleri
        oduller = {5: 5.0, 10: 10.0, 20: 20.0, 30: 30.0}
        ek_deger = oduller.get(new_lvl, 0)
        
        data[uid]["deger"] = data[uid].get("deger", 0) + ek_deger
        
        # İsim Güncelleme: İsim [Lv.X | XM]
        try:
            new_nick = f"{member.display_name.split(' [')[0]} [Lv.{new_lvl} | {data[uid]['deger']}M]"
            await member.edit(nick=new_nick)
        except: pass

        return True, new_lvl, ek_deger
    return False, new_lvl, 0

# --- MESAJ VE AKTİFLİK TAKİBİ ---
user_last_message = {}

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return

    data = load_data()
    uid = str(message.author.id)
    
    if uid not in data:
        data[uid] = {"isim": message.author.display_name, "xp": 0, "deger": 0, "mesaj_sayisi": 0, "aktif_sure": 0}

    old_xp = data[uid].get("xp", 0)
    data[uid]["xp"] += 1
    data[uid]["mesaj_sayisi"] += 1
    
    # Seviye atladı mı bak
    is_up, lvl, odul = await check_level_up(message.author, old_xp, data[uid]["xp"], data)
    
    if is_up:
        await message.channel.send(f"🎊 **TEBRİKLER {message.author.mention}!** Seviye atladın: **Level {lvl}**! Hesabına **{odul}M Değer** eklendi.")

    save_data(data)

# --- AKTİFLİK SIRALAMASI PANOSU ---
@tasks.loop(minutes=10)
async def siralama_guncelle():
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name="aktiflik-siralamasi")
        if not channel: continue

        data = load_data()
        # En çok mesaj atana göre sırala (İlk 10)
        sorted_users = sorted(data.items(), key=lambda x: x[1].get('xp', 0), reverse=True)[:10]

        embed = discord.Embed(title="📊 USL AKTİFLİK SIRALAMASI (TOP 10)", color=0x3498db, timestamp=datetime.utcnow())
        
        description = ""
        for i, (uid, info) in enumerate(sorted_users, 1):
            lvl = (info.get('xp', 0) // 100) + 1
            description += f"**{i}.** <@{uid}> - **Lv.{lvl}** | ✉️ {info.get('mesaj_sayisi')} Mesaj | 🏷️ {info.get('deger')}M\n"
        
        embed.description = description
        embed.set_footer(text="Bu liste her 10 dakikada bir güncellenir.")

        # Eski mesajı silip yenisini atma veya güncelleme
        async for msg in channel.history(limit=5):
            if msg.author == bot.user:
                await msg.edit(embed=embed)
                break
        else:
            await channel.send(embed=embed)

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
