import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from flask import Flask
from threading import Thread

# --- RENDER İÇİN ÖZEL WEB SUNUCUSU ---
app = Flask('')

@app.route('/')
def home():
    return "USL Bot 7/24 Aktif!"

def run():
    # Render genellikle 10000 portunu kullanır
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT AYARLARI ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Tüm komutlar senkronize edildi!")

bot = MyBot()
DATA_FILE = "stats.json"
YETKILI_ROL_ISMI = "Değer Yetkilisi"

# Veri Fonksiyonları
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

def is_yetkili(interaction: discord.Interaction):
    return any(role.name == YETKILI_ROL_ISMI for role in interaction.user.roles) or interaction.user.guild_permissions.administrator

# --- AKTİFLİK VE KOMUTLAR ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    data = load_data()
    uid = str(message.author.id)
    if uid not in data:
        data[uid] = {"isim": message.author.display_name, "deger": 0.0, "butce": 0, "xp": 0, "s_gol": 0, "s_asist": 0, "s_cs": 0, "b_gol": 0, "b_asist": 0, "b_cs": 0}
    data[uid]["xp"] = data[uid].get("xp", 0) + 1
    save_data(data)
    await bot.process_commands(message)

@bot.tree.command(name="kurulum", description="Sistemi hazırlar.")
async def kurulum(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator: return
    role = discord.utils.get(interaction.guild.roles, name=YETKILI_ROL_ISMI)
    if not role:
        await interaction.guild.create_role(name=YETKILI_ROL_ISMI, color=discord.Color.red())
        await interaction.response.send_message(f"✅ **{YETKILI_ROL_ISMI}** rolü oluşturuldu.")
    else:
        await interaction.response.send_message("ℹ️ Sistem hazır.", ephemeral=True)

@bot.tree.command(name="deger_ver", description="İstatistik ve ekonomi ekler.")
@app_commands.choices(lig=[app_commands.Choice(name="Süper Lig", value="super"), app_commands.Choice(name="1. Lig", value="birinci")],
                      tur=[app_commands.Choice(name="Gol", value="gol"), app_commands.Choice(name="Asist", value="asist"), app_commands.Choice(name="CS", value="cs")])
async def deger_ver(interaction: discord.Interaction, oyuncu: discord.Member, lig: app_commands.Choice[str], tur: app_commands.Choice[str], miktar: int):
    if not is_yetkili(interaction): return await interaction.response.send_message("Yetkin yok!", ephemeral=True)
    data = load_data()
    uid = str(oyuncu.id)
    if uid not in data: data[uid] = {"isim": oyuncu.display_name, "deger": 0.0, "butce": 0, "xp": 0, "s_gol": 0, "s_asist": 0, "s_cs": 0, "b_gol": 0, "b_asist": 0, "b_cs": 0}
    
    katsayilar = {"gol": {"deger": 3.0, "para": 100000}, "asist": {"deger": 1.5, "para": 50000}, "cs": {"deger": 6.0, "para": 200000}}
    carpan = 1.0 if lig.value == "super" else 0.5
    prefix = "s_" if lig.value == "super" else "b_"
    
    data[uid][prefix + tur.value] += miktar
    data[uid]["deger"] += (katsayilar[tur.value]["deger"] * carpan) * miktar
    data[uid]["butce"] += int((katsayilar[tur.value]["para"] * carpan) * miktar)
    save_data(data)
    await interaction.response.send_message(f"✅ {oyuncu.display_name} için {miktar} {tur.name} işlendi.")

@bot.tree.command(name="deger_sil", description="Hatalı veriyi siler.")
@app_commands.choices(lig=[app_commands.Choice(name="Süper Lig", value="super"), app_commands.Choice(name="1. Lig", value="birinci")],
                      tur=[app_commands.Choice(name="Gol", value="gol"), app_commands.Choice(name="Asist", value="asist"), app_commands.Choice(name="CS", value="cs")])
async def deger_sil(interaction: discord.Interaction, oyuncu: discord.Member, lig: app_commands.Choice[str], tur: app_commands.Choice[str], miktar: int):
    if not is_yetkili(interaction): return await interaction.response.send_message("Yetkin yok!", ephemeral=True)
    data = load_data()
    uid = str(oyuncu.id)
    prefix = "s_" if lig.value == "super" else "b_"
    if uid not in data or data[uid].get(prefix+tur.value, 0) < miktar:
        return await interaction.response.send_message("Silecek veri yok!", ephemeral=True)
    
    katsayilar = {"gol": {"deger": 3.0, "para": 100000}, "asist": {"deger": 1.5, "para": 50000}, "cs": {"deger": 6.0, "para": 200000}}
    carpan = 1.0 if lig.value == "super" else 0.5
    data[uid][prefix + tur.value] -= miktar
    data[uid]["deger"] -= (katsayilar[tur.value]["deger"] * carpan) * miktar
    data[uid]["butce"] -= int((katsayilar[tur.value]["para"] * carpan) * miktar)
    save_data(data)
    await interaction.response.send_message(f"⚠️ {oyuncu.display_name} verileri silindi.")

@bot.tree.command(name="profil", description="Oyuncu profili.")
async def profil(interaction: discord.Interaction, oyuncu: discord.Member = None):
    target = oyuncu or interaction.user
    data = load_data()
    uid = str(target.id)
    if uid not in data: return await interaction.response.send_message("Kayıt yok.", ephemeral=True)
    s = data[uid]
    embed = discord.Embed(title=f"👤 {target.display_name} Profili", color=0x3498db)
    embed.add_field(name="🏆 SÜPER LİG", value=f"G: {s['s_gol']} | A: {s['s_asist']} | CS: {s['s_cs']}", inline=True)
    embed.add_field(name="🥇 1. LİG", value=f"G: {s['b_gol']} | A: {s['b_asist']} | CS: {s['b_cs']}", inline=True)
    embed.add_field(name="📊 DURUM", value=f"Değer: `{s['deger']}M €` | Bütçe: `{s['butce']:,}` | Aktiflik: `{s.get('xp',0)} msj`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siralamalar", description="En iyiler.")
@app_commands.choices(tur=[app_commands.Choice(name="En Değerliler", value="deger"), app_commands.Choice(name="En Aktifler", value="xp")])
async def siralamalar(interaction: discord.Interaction, tur: app_commands.Choice[str]):
    data = load_data()
    sorted_list = sorted(data.items(), key=lambda x: x[1].get(tur.value, 0), reverse=True)[:10]
    embed = discord.Embed(title=f"📊 {tur.name} (Top 10)", color=0xf1c40f)
    desc = ""
    for i, (uid, info) in enumerate(sorted_list, 1):
        birim = "M €" if tur.value == "deger" else " Mesaj"
        desc += f"**{i}.** <@{uid}> - `{info.get(tur.value, 0)}{birim}`\n"
    embed.description = desc
    await interaction.response.send_message(embed=embed)

# --- ÇALIŞTIR ---
keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
                                     
