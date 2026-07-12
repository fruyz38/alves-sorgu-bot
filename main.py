import os
import asyncio
import logging
import sys
import io
import json
import requests
from flask import Flask
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands

# ====================== AYARLAR ======================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "https://flaresolverr-gvbi.onrender.com")

# ====================== FLASK ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "Alves Sorgu Bot Aktif! ✅"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Flask server {port} portunda çalışıyor...")
    app.run(host='0.0.0.0', port=port, debug=False)

# ====================== DISCORD ======================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====================== SORGULAMA ======================
async def sorgu_yap(interaction: discord.Interaction, title: str, url: str):
    await interaction.response.defer(ephemeral=True)
    try:
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000
        }

        response = requests.post(f"{FLARESOLVERR_URL}/v1", json=payload, timeout=120)
        result = response.json()

        logger.info(f"FlareSolverr Response for {title}: {result}")

        if result.get("status") != "ok":
            await interaction.followup.send(f"❌ FlareSolverr Hatası: {result.get('message', str(result))[:400]}", ephemeral=True)
            return

        html = result["solution"]["response"]
        status_code = result["solution"]["statusCode"]

        if status_code != 200:
            await interaction.followup.send(f"❌ API Hatası: HTTP {status_code}", ephemeral=True)
            return

        embed = format_api_response(title, html)
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Hata ({title}): {e}")
        await interaction.followup.send(f"❌ Hata: {str(e)[:300]}", ephemeral=True)

def format_api_response(title: str, raw_text: str):
    try:
        data = json.loads(raw_text)
        if isinstance(data, list) and data:
            data = data[0]

        embed = discord.Embed(title=f"✅ {title} Sonucu", color=discord.Color.green())

        if isinstance(data, dict):
            for key, value in data.items():
                if value in [None, "", [], {}]:
                    continue
                name = key.replace("_", " ").title()
                if isinstance(value, dict):
                    val = "\n".join([f"**{k}:** `{v}`" for k, v in value.items() if v])
                    embed.add_field(name=name, value=val[:1024] or "-", inline=False)
                else:
                    embed.add_field(name=name, value=f"`{value}`", inline=len(str(value)) < 45)
        return embed
    except:
        return discord.Embed(title=f"⚠️ {title}", description="```json\n" + raw_text[:1500] + "\n```", color=discord.Color.orange())

# ====================== MODALLAR ======================
class TcModal(discord.ui.Modal, title="🔍 TC Sorgula"):
    tc = discord.ui.TextInput(label="TC Kimlik No", placeholder="11 haneli TC", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://arastir.vip/api/tc.php?tc={self.tc.value}"
        await sorgu_yap(interaction, "TC Sorgu", url)

class AdSoyadModal(discord.ui.Modal, title="👤 Ad Soyad Sorgu"):
    ad = discord.ui.TextInput(label="Ad", placeholder="Ahmet", required=True)
    soyad = discord.ui.TextInput(label="Soyad", placeholder="Yılmaz", required=True)
    il = discord.ui.TextInput(label="İl (Opsiyonel)", placeholder="İstanbul", required=False)
    ilce = discord.ui.TextInput(label="İlçe (Opsiyonel)", placeholder="Kadıköy", required=False)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://arastir.vip/api/adsoyad.php?adi={self.ad.value}&soyadi={self.soyad.value}"
        if self.il.value.strip(): url += f"&il={self.il.value}"
        if self.ilce.value.strip(): url += f"&ilce={self.ilce.value}"
        await sorgu_yap(interaction, "Ad Soyad Sorgu", url)

# Twitter
class TwitterUserModal(discord.ui.Modal, title="🐦 Twitter Kullanıcı Sorgu"):
    q = discord.ui.TextInput(label="Kullanıcı Adı", placeholder="kullanici", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/twitter.php?type=user&q={self.q.value}"
        await sorgu_yap(interaction, "Twitter Kullanıcı", url)

class TwitterEmailModal(discord.ui.Modal, title="🐦 Twitter Mail Sorgu"):
    q = discord.ui.TextInput(label="E-posta", placeholder="ornek@gmail.com", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/twitter.php?type=email&q={self.q.value}"
        await sorgu_yap(interaction, "Twitter Mail", url)

class TwitterPassModal(discord.ui.Modal, title="🐦 Twitter Şifre Sorgu"):
    q = discord.ui.TextInput(label="Şifre", placeholder="sifre123", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/twitter.php?type=pass&q={self.q.value}"
        await sorgu_yap(interaction, "Twitter Şifre", url)

# Instagram
class InstagramUserModal(discord.ui.Modal, title="📸 IG Kullanıcı"):
    q = discord.ui.TextInput(label="Kullanıcı Adı", placeholder="pompomiller", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/instagram.php?type=user&q={self.q.value}"
        await sorgu_yap(interaction, "Instagram Kullanıcı", url)

class InstagramEmailModal(discord.ui.Modal, title="📸 IG Mail"):
    q = discord.ui.TextInput(label="Mail", placeholder="ornek@gmail.com", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/instagram.php?type=email&q={self.q.value}"
        await sorgu_yap(interaction, "Instagram Mail", url)

class InstagramIdModal(discord.ui.Modal, title="📸 IG ID"):
    q = discord.ui.TextInput(label="ID", placeholder="581959613", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/instagram.php?type=id&q={self.q.value}"
        await sorgu_yap(interaction, "Instagram ID", url)

class InstagramPhoneModal(discord.ui.Modal, title="📸 IG Telefon"):
    q = discord.ui.TextInput(label="Telefon", placeholder="17814729662", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/instagram.php?type=phone&q={self.q.value}"
        await sorgu_yap(interaction, "Instagram Telefon", url)

class InstagramNameModal(discord.ui.Modal, title="📸 IG İsim"):
    q = discord.ui.TextInput(label="İsim", placeholder="Miller", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/instagram.php?type=name&q={self.q.value}"
        await sorgu_yap(interaction, "Instagram İsim", url)

class DiscordIdModal(discord.ui.Modal, title="🔵 Discord ID Sorgu"):
    q = discord.ui.TextInput(label="Discord ID", placeholder="1006067526339399711", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = f"https://ajanss.tr/api/discordid.php?id={self.q.value}"
        await sorgu_yap(interaction, "Discord ID", url)

# ====================== PANELLER ======================
class SorguPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="TC Sorgula", style=discord.ButtonStyle.primary, emoji="🔍", row=0, custom_id="btn_tc")
    async def tc_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TcModal())

    @discord.ui.button(label="Ad Soyad", style=discord.ButtonStyle.primary, emoji="👤", row=0, custom_id="btn_adsoyad")
    async def adsoyad_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdSoyadModal())

    @discord.ui.button(label="🐦 Twitter Kullanıcı", style=discord.ButtonStyle.primary, row=1, custom_id="btn_twitter_user")
    async def twitter_user_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TwitterUserModal())

    @discord.ui.button(label="🐦 Twitter Mail", style=discord.ButtonStyle.primary, row=1, custom_id="btn_twitter_email")
    async def twitter_mail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TwitterEmailModal())

    @discord.ui.button(label="🐦 Twitter Şifre", style=discord.ButtonStyle.primary, row=1, custom_id="btn_twitter_pass")
    async def twitter_pass_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TwitterPassModal())

    @discord.ui.button(label="📸 IG Kullanıcı", style=discord.ButtonStyle.primary, row=2, custom_id="btn_ig_user")
    async def ig_user_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InstagramUserModal())

    @discord.ui.button(label="📸 IG Mail", style=discord.ButtonStyle.primary, row=2, custom_id="btn_ig_email")
    async def ig_mail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InstagramEmailModal())

    @discord.ui.button(label="📸 IG ID", style=discord.ButtonStyle.primary, row=2, custom_id="btn_ig_id")
    async def ig_id_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InstagramIdModal())

    @discord.ui.button(label="📸 IG Telefon", style=discord.ButtonStyle.primary, row=3, custom_id="btn_ig_phone")
    async def ig_phone_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InstagramPhoneModal())

    @discord.ui.button(label="📸 IG İsim", style=discord.ButtonStyle.primary, row=3, custom_id="btn_ig_name")
    async def ig_name_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InstagramNameModal())

    @discord.ui.button(label="🔵 Discord ID", style=discord.ButtonStyle.primary, row=4, custom_id="btn_discord_id")
    async def discord_id_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DiscordIdModal())

class SorguGirisButon(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sorgu Panelini Aç", style=discord.ButtonStyle.success, custom_id="btn_giris_persistent")
    async def sorgu_ac(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SorguPaneli()
        embed = discord.Embed(title="🪪 ALVES SORGU PANELİ", description="Aşağıdaki butonlardan istediğini seç.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ====================== EVENTS ======================
@bot.event
async def on_ready():
    logger.info(f"[{bot.user.name}] Başarıyla giriş yaptı.")
    bot.add_view(SorguGirisButon())
    bot.add_view(SorguPaneli())
    try:
        await bot.tree.sync()
        logger.info("✅ Komutlar senkronize edildi!")
    except Exception as e:
        logger.error(f"Sync hatası: {e}")

@bot.tree.command(name="sorgula", description="Sorgu panelini açar.")
async def sorgula(interaction: discord.Interaction):
    view = SorguGirisButon()
    embed = discord.Embed(title="🔎 ALVES Sorgu Sistemi", description="Güvenli ve hızlı sorgu paneli.", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# ====================== BAŞLAT ======================
if __name__ == "__main__":
    logger.info("Bot başlatılıyor...")
    Thread(target=run_flask, daemon=True).start()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.critical("DISCORD_TOKEN bulunamadı!")
