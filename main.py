import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
import asyncio
import random
from datetime import datetime
from flask import Flask
from threading import Thread

# --- WEB SUNUCUSU ---
app = Flask('')
@app.route('/')
def home(): return "USL Aktif!"

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
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Görevleri burada başlatıyoruz
        self.siralama_dongusu.start()
        self.aktiflik_yarisi.start()
        await self.tree.sync()
        print("Sistem hatasız başlatıldı!")

    # --- SIRALAMA GÖREVİ ---
    @tasks.loop(minutes=10)
    async def siralama_dongusu(self):
        for guild in self.guilds:
            channel = discord.utils.get(guild.text_channels, name="aktiflik-siralamasi")
            if channel:
                data = load_data()
                sorted_users = sorted(data.items(), key=lambda x: x[1].get('xp', 0), reverse=True)[:10]
                embed = discord.Embed(title="📊 EN AKTİF 10 OYUNCU", color=0x3498db)
                desc = ""
                for i, (uid, info) in enumerate(sorted_users, 1):
                    lvl = (info.get('xp', 0) // 100) + 1
                    desc += f"**{i}.** <@{uid}> - Lv.{lvl} | {info.get('deger', 0)}M\n"
                embed.description = desc
                async for m in channel.history(limit=5):
                    if m.author == self.user:
                        await m.edit(embed=embed)
                        break
                else:
                    await channel.send(embed=embed)

    # --- AKTİFLİK YARIŞI ---
    @tasks.loop(hours=2)
    async def aktiflik_yarisi(self):
        for guild in self.guilds:
            channel = discord.utils.get(guild.text_channels, name="sohbet") or guild.text_channels[0]
            if channel:
                try:
                    await channel.send("📢 **USL AKTİFLİK!** İlk `USL AKTİFLİK` yazan **500K Değer** kazanır!")
                    def check(m): return m.content.upper() == "USL AKTİFLİK" and not m.author.bot
                    msg = await self.wait_for('message', check=check, timeout=300)
                    data = load_data()
                    uid = str(msg.author.id)
                    if uid not in data: data[uid] = {"isim": msg.author.display_name, "xp": 0, "deger": 0, "butce": 0}
                    data[uid]["deger"] += 0.5
                    save_data(data)
                    await channel.send(f"🎉 {msg.author.mention} kazandı!")
                except: pass

bot = MyBot()
DATA_FILE = "stats.json"

# --- VERİ FONKSİYONLARI ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

# --- İSİM GÜNCELLEME ---
async def update_member_status(member, data):
    try:
        uid = str(member.id)
        lvl = (data[uid].get("xp", 0) // 100) + 1
        new_nick = f"{member.display_name.split(' [')[0]} [Lv.{lvl} | {data[uid]['deger']}M]"
        if member.nick != new_nick: await member.edit(nick=new_nick)
    except: pass

# --- EVENTLER ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    data = load_data()
    uid = str(message.author.id)
    if uid not in data: data[uid] = {"isim": message.author.display_name, "xp": 0, "deger": 0, "butce": 0}
    
    old_xp = data[uid].get("xp", 0)
    data[uid]["xp"] += 1
    
    # Seviye Ödülü (5, 10, 20, 30)
    old_lvl, new_lvl = (old_xp//100)+1, (data[uid]["xp"]//100)+1
    if new_lvl > old_lvl:
        oduller = {5: 5.0, 10: 10.0, 20: 20.0, 30: 30.0}
        if new_lvl in oduller:
            data[uid]["deger"] += oduller[new_lvl]
            await message.channel.send(f"🎊 {message.author.mention} Level {new_lvl} oldu! +{oduller[new_lvl]}M Değer kazandı.")

    if data[uid]["xp"] % 15 == 0: await update_member_status(message.author, data)
    save_data(data)

# --- KOMUTLAR ---
@bot.tree.command(name="ekle", description="İstatistik ekler.")
async def ekle(interaction: discord.Interaction, üye: discord.Member, miktar: int):
    if not interaction.user.guild_permissions.administrator: return
    data = load_data()
    uid = str(üye.id)
    if uid not in data: data[uid] = {"isim": üye.display_name, "xp": 0, "deger": 0, "butce": 0}
    data[uid]["butce"] += miktar
    save_data(data)
    await interaction.response.send_message(f"✅ {üye.display_name} hesabına {miktar} eklendi.")

@bot.tree.command(name="cekilis", description="Çekiliş başlatır.")
async def cekilis(interaction: discord.Interaction, odul_para: int, kisi_sayisi: int, sure_dakika: int):
    if not interaction.user.guild_permissions.administrator: return
    embed = discord.Embed(title="🎁 ÇEKİLİŞ!", description=f"Ödül: {odul_para:,}\nSüre: {sure_dakika} dk", color=0xf1c40f)
    await interaction.response.send_message("Başladı!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(sure_dakika * 60)
    msg = await interaction.channel.fetch_message(msg.id)
    users = [u async for u in msg.reactions[0].users() if not u.bot]
    if len(users) >= kisi_sayisi:
        winners = random.sample(users, kisi_sayisi)
        data = load_data()
        for w in winners:
            if str(w.id) not in data: data[str(w.id)] = {"isim": w.display_name, "xp": 0, "deger": 0, "butce": 0}
            data[str(w.id)]["butce"] += odul_para
        save_data(data)
        await interaction.channel.send(f"🎊 Kazananlar: {', '.join([w.mention for w in winners])}")

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
                
