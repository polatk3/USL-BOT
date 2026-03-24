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

@bot.tree.command(name="ekle", description="İstatistik, Piyasa Değeri ve Para ekler (Miktar destekli).")
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
            "s_gol": 0, "s_asist": 0, "s_cs": 0, # Süper Lig verileri
            "b_gol": 0, "b_asist": 0, "b_cs": 0, # 1. Lig verileri (b: birinci lig)
            "deger": 0, "butce": 0
        }
    
    katsayi = 1.0 if lig.value == 1 else 0.5
    prefix = "s_" if lig.value == 1 else "b_"
    key = prefix + tip.value

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
    await interaction.response.send_message(f"⚠️ **{üye.display_name}** verisi silindi.\n❌ -{miktar} {tip.name} | 📉 -{dusecek_deger}M Değer | 💵 -{dusecek_para:,} USL Parası")

@bot.tree.command(name="bilgi", description="Detaylı lig istatistiklerini ve bütçeyi görüntüler.")
async def bilgi(interaction: discord.Interaction, üye: discord.Member = None):
    üye = üye or interaction.user
    data = load_data()
    uid = str(üye.id)
    
    if uid not in data:
        return await interaction.response.send_message("Oyuncu kaydı bulunamadı.", ephemeral=True)
    
    s = data[uid]
    embed = discord.Embed(title=f"⚽ {s['isim']} - Detaylı Kariyer", color=0x3498db)
    
    # Süper Lig Kısmı
    s_bilgi = f"🥅 G: {s.get('s_gol',0)} | 👟 A: {s.get('s_asist',0)} | 🧤 CS: {s.get('s_cs',0)}"
    embed.add_field(name="🏆 Süper Lig", value=f"```{s_bilgi}```", inline=False)
    
    # 1. Lig Kısmı
    b_bilgi = f"🥅 G: {s.get('b_gol',0)} | 👟 A: {s.get('b_asist',0)} | 🧤 CS: {s.get('b_cs',0)}"
    embed.add_field(name="🥇 1. Lig", value=f"```{b_bilgi}```", inline=False)
    
    # Genel Toplamlar
    toplam_g = s.get('s_gol',0) + s.get('b_gol',0)
    toplam_a = s.get('s_asist',0) + s.get('b_asist',0)
    toplam_cs = s.get('s_cs',0) + s.get('b_cs',0)
    
    embed.add_field(name="📊 Toplam Veriler", value=f"G: {toplam_g} / A: {toplam_a} / CS: {toplam_cs}", inline=True)
    embed.add_field(name="🏷️ Piyasa Değeri", value=f"{s['deger']}M €", inline=True)
    embed.add_field(name="💳 Mevcut Bütçe", value=f"{s.get('butce',0):,} 💸 USL Parası", inline=False)
    
    if üye.avatar: embed.set_thumbnail(url=üye.avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siralam", description="Piyasa değerine göre Top 10.")
async def siralam(interaction: discord.Interaction):
    data = load_data()
    if not data: return await interaction.response.send_message("Kayıt yok.")
    sorted_data = sorted(data.values(), key=lambda x: x['deger'], reverse=True)[:10]
    embed = discord.Embed(title="🏆 EN DEĞERLİ 10 OYUNCU", color=0xf1c40f)
    for i, u in enumerate(sorted_data, 1):
        embed.add_field(name=f"{i}. {u['isim']}", value=f"Değer: {u['deger']}M € | Bütçe: {u.get('butce',0):,} 💸", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="para_duzelt", description="Üyenin bütçesini manuel düzenler.")
async def para_duzelt(interaction: discord.Interaction, üye: discord.Member, miktar: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
    data = load_data()
    uid = str(üye.id)
    if uid not in data: return await interaction.response.send_message("Kayıt yok.", ephemeral=True)
    data[uid]["butce"] += miktar
    save_data(data)
    await interaction.response.send_message(f"💵 {üye.mention} bütçesi güncellendi. Yeni: {data[uid]['butce']:,} 💸")

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
    
    
