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
def home(): return "USL Sistem Aktif!"

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
        print("Profil Gözlem Sistemi Hazır!")

bot = MyBot()
DATA_FILE = "stats.json"
YETKILI_ROL_ISMI = "Değer Yetkilisi"

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

# --- KOMUTLAR ---

@bot.tree.command(name="kurulum", description="Değer Yetkilisi rolünü oluşturur.")
async def kurulum(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Sadece sunucu sahibi!", ephemeral=True)
    
    role = discord.utils.get(interaction.guild.roles, name=YETKILI_ROL_ISMI)
    if not role:
        await interaction.guild.create_role(name=YETKILI_ROL_ISMI, color=discord.Color.red())
        await interaction.response.send_message(f"✅ **{YETKILI_ROL_ISMI}** rolü oluşturuldu.")
    else:
        await interaction.response.send_message("ℹ️ Rol zaten var.", ephemeral=True)

@bot.tree.command(name="deger_ver", description="İstatistik ekler (Yetkili Özel).")
@app_commands.choices(lig=[
    app_commands.Choice(name="Süper Lig", value="super"),
    app_commands.Choice(name="1. Lig", value="birinci")
], tur=[
    app_commands.Choice(name="Gol", value="gol"),
    app_commands.Choice(name="Asist", value="asist"),
    app_commands.Choice(name="CS", value="cs")
])
async def deger_ver(interaction: discord.Interaction, oyuncu: discord.Member, lig: app_commands.Choice[str], tur: app_commands.Choice[str], miktar: int):
    if not is_yetkili(interaction):
        return await interaction.response.send_message("Yetkin yok!", ephemeral=True)
    
    data = load_data()
    uid = str(oyuncu.id)
    if uid not in data:
        data[uid] = {"isim": oyuncu.display_name, "deger": 0.0, "butce": 0, "s_gol": 0, "s_asist": 0, "s_cs": 0, "b_gol": 0, "b_asist": 0, "b_cs": 0}

    katsayilar = {"gol": {"deger": 3.0, "para": 100000}, "asist": {"deger": 1.5, "para": 50000}, "cs": {"deger": 6.0, "para": 200000}}
    lig_carpan = 1.0 if lig.value == "super" else 0.5
    prefix = "s_" if lig.value == "super" else "b_"
    
    data[uid][prefix + tur.value] += miktar
    data[uid]["deger"] += (katsayilar[tur.value]["deger"] * lig_carpan) * miktar
    data[uid]["butce"] += int((katsayilar[tur.value]["para"] * lig_carpan) * miktar)
    
    save_data(data)
    await interaction.response.send_message(f"✅ **{oyuncu.display_name}** güncellendi.")

@bot.tree.command(name="profil", description="Kendinin veya başkasının profilini gör.")
@app_commands.describe(oyuncu="Profiline bakmak istediğin oyuncuyu seç (Boş bırakırsan seninkini gösterir).")
async def profil(interaction: discord.Interaction, oyuncu: discord.Member = None):
    # Eğer oyuncu seçilmediyse, komutu yazan kişiyi hedef al
    hedef = oyuncu or interaction.user
    data = load_data()
    uid = str(hedef.id)
    
    if uid not in data:
        return await interaction.response.send_message(f"❌ **{hedef.display_name}** için henüz bir kayıt oluşturulmamış.", ephemeral=True)
    
    s = data[uid]
    embed = discord.Embed(title=f"👤 {hedef.display_name} Profili", color=0x3498db)
    embed.set_thumbnail(url=hedef.display_avatar.url)
    
    # Süper Lig
    s_stats = f"⚽ Gol: {s.get('s_gol',0)}\n🎯 Asist: {s.get('s_asist',0)}\n🛡️ CS: {s.get('s_cs',0)}"
    embed.add_field(name="🏆 SÜPER LİG", value=s_stats, inline=True)
    
    # 1. Lig
    b_stats = f"⚽ Gol: {s.get('b_gol',0)}\n🎯 Asist: {s.get('b_asist',0)}\n🛡️ CS: {s.get('b_cs',0)}"
    embed.add_field(name="🥇 1. LİG", value=b_stats, inline=True)
    
    # Ekonomi
    ekonomi = f"📈 Piyasa Değeri: `{s.get('deger',0)}M €` \n💰 Bütçe: `{s.get('butce',0):,} 💸`"
    embed.add_field(name="📊 Finansal Durum", value=ekonomi, inline=False)
    
    await interaction.response.send_message(embed=embed)

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
