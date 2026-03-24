 import discord
from discord import app_commands
from discord.ext import commands
import os
import json
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
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
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
    await bot.change_presence(activity=discord.Game(name="USL Pro Manager"))
    print(f'Sistem Aktif: {bot.user}')

# --- SLASH KOMUTLARI ---

@bot.tree.command(name="ekle", description="İstatistik, Piyasa Değeri ve Para ekler.")
@app_commands.choices(lig=[
    app_commands.Choice(name="Süper Lig", value=1),
    app_commands.Choice(name="1. Lig", value=2)
], tip=[
    app_commands.Choice(name="Gol", value="gol"),
    app_commands.Choice(name="Asist", value="asist"),
    app_commands.Choice(name="Clean Sheet (CS)", value="cs")
])
async def ekle(interaction: discord.Interaction, üye: discord.Member, tip: app_commands.Choice[str], lig: app_commands.Choice[int], miktar: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
    
    data = load_data()
    uid = str(üye.id)
    if uid not in data:
        data[uid] = {
            "isim": üye.display_name, 
            "s_gol": 0, "s_asist": 0, "s_cs": 0, 
            "b_gol": 0, "b_asist": 0, "b_cs": 0,
            "deger": 0, "butce": 0
        }
    
    katsayi = 1.0 if lig.value == 1 else 0.5
    prefix = "s_" if lig.value == 1 else "b_"
    key = prefix + tip.value

    # Ayarlar (Süper Lig bazlı)
    ayarlar = {
        "gol": {"deger": 2, "para": 100000},
        "asist": {"deger": 1, "para": 50000},
        "cs": {"deger": 3, "para": 250000}
    }
    
    secilen = ayarlar[tip.value]
    eklenecek_deger = (secilen["deger"] * katsayi) * miktar
    eklenecek_para = int((secilen["para"] * katsayi) * miktar)

    data[uid][key] += miktar
    data[uid]["deger"] += eklenecek_deger
    data[uid]["butce"] += eklenecek_para
    
    save_data(data)
    await interaction.response.send_message(f"✅ **{üye.display_name}** ({lig.name})\n⚽ +{miktar} {tip.name} | 📈 +{eklenecek_deger}M Değer | 💵 +{eklenecek_para:,} USL Parası")

@bot.tree.command(name="sil", description="İstatistik siler, değer ve bütçeyi geri düşer.")
@app_commands.choices(lig=[
    app_commands.Choice(name="Süper Lig", value=1),
    app_commands.Choice(name="1. Lig", value=2)
], tip=[
    app_commands.Choice(name="Gol", value="gol"),
    app_commands.Choice(name="Asist", value="asist"),
    app_commands.Choice(name="Clean Sheet (CS)", value="cs")
])
async def sil(interaction: discord.Interaction, üye: discord.Member, tip: app_commands.Choice[str], lig: app_commands.Choice[int], miktar: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
    
    data = load_data()
    uid = str(üye.id)
    prefix = "s_" if lig.value == 1 else "b_"
    key = prefix + tip.value

    if uid not in data or data[uid].get(key, 0) < miktar:
        return await interaction.response.send_message("❌ Silecek kadar veri bulunamadı!", ephemeral=True)

    katsayi = 1.0 if lig.value == 1 else 0.5
    ayarlar = {
        "gol": {"deger": 2, "para": 100000},
        "asist": {"deger": 1, "para": 50000},
        "cs": {"deger": 3, "para": 250000}
    }
    
    secilen = ayarlar[tip.value]
    dusecek_deger = (secilen["deger"] * katsayi) * miktar
    dusecek_para = int((secilen["para"] * katsayi) * miktar)

    data[uid][key] -= miktar
    data[uid]["deger"] -= dusecek_deger
    data[uid]["butce"] -= dusecek_para
    
    save_data(data)
    await interaction.response.send_message(f"⚠️ **{üye.display_name}** verisi silindi.\n❌ -{miktar} {tip.name} | 📈 -{dusecek_deger}M Değer | 💵 -{dusecek_para:,} USL Parası")

@bot.tree.command(name="bilgi", description="Oyuncunun detaylı profilini görüntüler.")
async def bilgi(interaction: discord.Interaction, üye: discord.Member = None):
    üye = üye or interaction.user
    data = load_data()
    uid = str(üye.id)
    
    if uid not in data:
        return await interaction.response.send_message("Oyuncu kaydı bulunamadı.", ephemeral=True)
    
    s = data[uid]
    embed = discord.Embed(title=f"⚽ {s['isim']} - Kariyer Raporu", color=0x3498db)
    
    # Süper Lig Kısmı
    s_bilgi = f"🥅 G: **{s.get('s_gol',0)}** | 👟 A: **{s.get('s_asist',0)}** | 🧤 CS: **{s.get('s_cs',0)}**"
    embed.add_field(name="🏆 Süper Lig İstatistikleri", value=s_bilgi, inline=False)
    
    # 1. Lig Kısmı
    b_bilgi = f"🥅 G: **{s.get('b_gol',0)}** | 👟 A: **{s.get('b_asist',0)}** | 🧤 CS: **{s.get('b_cs',0)}**"
    embed.add_field(name="🥇 1. Lig İstatistikleri", value=b_bilgi, inline=False)
    
    # Genel Toplamlar ve Ekonomi
    embed.add_field(name="🏷️ Piyasa Değeri", value=f"**{s['deger']}M €**", inline=True)
    embed.add_field(name="💳 Mevcut Bütçe", value=f"**{s.get('butce',0):,} 💸 USL Parası**", inline=True)
    
    if üye.avatar: embed.set_thumbnail(url=üye.avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siralam_super", description="Süper Lig'in en değerli oyuncuları.")
async def siralam_super(interaction: discord.Interaction):
    data = load_data()
    if not data: return await interaction.response.send_message("Kayıt yok.")
    # Sadece Süper Lig golü olanları filtreleyebiliriz ama burası Piyasa Değeri odaklı.
    sorted_data = sorted(data.values(), key=lambda x: x['deger'], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Süper Lig - EN DEĞERLİ 10 (Genel)", color=0xf1c40f)
    for i, u in enumerate(sorted_data, 1):
        # Profilinde Süper Lig verisi olanları gösterelim.
        if u.get('s_gol', 0) > 0 or u.get('s_asist', 0) > 0:
            val = f"Değer: **{u['deger']}M €** | G:{u.get('s_gol')} A:{u.get('s_asist')} CS:{u.get('s_cs')}"
            embed.add_field(name=f"{i}. {u['isim']}", value=val, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siralam_birinci", description="1. Lig'in en değerli oyuncuları.")
async def siralam_birinci(interaction: discord.Interaction):
    data = load_data()
    if not data: return await interaction.response.send_message("Kayıt yok.")
    sorted_data = sorted(data.values(), key=lambda x: x['deger'], reverse=True)[:10]
    embed = discord.Embed(title="🏆 1. Lig - EN DEĞERLİ 10 (Genel)", color=0xf39c12)
    for i, u in enumerate(sorted_data, 1):
        # Profilinde 1. Lig verisi olanları gösterelim.
        if u.get('b_gol', 0) > 0 or u.get('b_asist', 0) > 0:
            val = f"Değer: **{u['deger']}M €** | G:{u.get('b_gol')} A:{u.get('b_asist')} CS:{u.get('b_cs')}"
            embed.add_field(name=f"{i}. {u['isim']}", value=val, inline=False)
    await interaction.response.send_message(embed=embed)

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
    
    
    
