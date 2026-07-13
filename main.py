import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio
import os
import logging
import threading
import time
from typing import Optional
from flask import Flask, jsonify
import aiohttp

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigürasyon - Environment variables'dan al
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
REQUIRED_ROLE_ID = int(os.getenv('REQUIRED_ROLE_ID', '0'))
PORT = int(os.getenv('PORT', 5000))

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
user_states = {}

# ============ FLASK WEB SERVER ============
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "Bot is running!",
        "uptime": time.time() - start_time,
        "ping_count": ping_counter[0]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/ping')
def ping():
    """Botun canlı olduğunu kontrol etmek için"""
    return jsonify({"status": "pong", "timestamp": time.time()})

# ============ PING SİSTEMİ ============
ping_counter = [0]  # Ping sayacı
start_time = time.time()

async def keep_alive():
    """Kendine periyodik ping atarak botun uyku moduna geçmesini engeller"""
    bot_url = f"http://localhost:{PORT}/ping"
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bot_url, timeout=5) as response:
                    if response.status == 200:
                        ping_counter[0] += 1
                        logger.info(f"✅ Ping başarılı! (Toplam: {ping_counter[0]})")
                    else:
                        logger.warning(f"⚠️ Ping başarısız! Status: {response.status}")
        except Exception as e:
            logger.error(f"❌ Ping hatası: {e}")
        
        # Her 8 dakikada bir ping at (Render free tier 15 dakika)
        await asyncio.sleep(480)  # 8 dakika

def run_web_server():
    """Flask web server'ı başlat"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ============ VIEW'LAR (Buton Menüleri) ============
class MainMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📂 Komutlar", style=discord.ButtonStyle.primary, custom_id="komutlar")
    async def komutlar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = KomutlarView()
        embed = discord.Embed(
            title="⚙️ Komut Türü Seçin",
            description="Hangi tür komutları kullanmak istersiniz?",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="ℹ️ Bilgi", style=discord.ButtonStyle.secondary, custom_id="bilgi")
    async def bilgi_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="ℹ️ Bot Bilgisi",
            description="Bu bot çeşitli sorgulama işlemleri yapmanızı sağlar.",
            color=discord.Color.green()
        )
        embed.add_field(name="📌 Sürüm", value="1.1.0", inline=True)
        embed.add_field(name="👤 Yapımcı", value="@alves0000", inline=True)
        embed.add_field(name="⏱️ Çalışma Süresi", value=f"{int(time.time() - start_time)} saniye", inline=True)
        await interaction.response.edit_message(embed=embed, view=None)

class KomutlarView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🆓 Free Komutlar", style=discord.ButtonStyle.success, custom_id="free")
    async def free_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FreeKomutlarView()
        embed = discord.Embed(
            title="🆓 Free Komutlar Menüsü",
            description="Aşağıdaki sorgulama işlemlerinden birini seçin:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="💎 Premium Komutlar", style=discord.ButtonStyle.danger, custom_id="premium")
    async def premium_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 Premium Komutlar",
            description="Premium panel satın alımları için yetkiliyle iletişime geçin.",
            color=discord.Color.gold()
        )
        embed.add_field(name="📞 İletişim", value="@alves0000", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="🔙 Geri", style=discord.ButtonStyle.secondary, custom_id="geri_ana")
    async def geri_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Hoş Geldiniz!",
            description="Aşağıdaki butonlardan birini seçin:",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=MainMenuView())

class FreeKomutlarView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🧾 Ad Soyad Sorgu", style=discord.ButtonStyle.secondary, custom_id="adsoyad")
    async def adsoyad_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 Lütfen adınızı girin:", ephemeral=True)
        user_states[interaction.user.id] = {"durum": "ad_sor"}
    
    @discord.ui.button(label="🆔 TC Pro Sorgu", style=discord.ButtonStyle.secondary, custom_id="tcpro")
    async def tcpro_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🆔 Lütfen sorgulamak istediğiniz TC Kimlik Numarasını girin:", ephemeral=True)
        user_states[interaction.user.id] = {"durum": "tcpro_sor"}
    
    @discord.ui.button(label="📱 GSM Detay", style=discord.ButtonStyle.secondary, custom_id="gsmdetay")
    async def gsmdetay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📱 Lütfen sorgulamak istediğiniz GSM numarasını yazınız (başında 0 olmadan):", ephemeral=True)
        user_states[interaction.user.id] = {"durum": "gsm_sor"}
    
    @discord.ui.button(label="🚗 Plaka Sorgu", style=discord.ButtonStyle.secondary, custom_id="plaka")
    async def plaka_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚗 Lütfen sorgulamak istediğiniz plaka numarasını girin:", ephemeral=True)
        user_states[interaction.user.id] = {"durum": "plaka_sor"}
    
    @discord.ui.button(label="📞 İletişim", style=discord.ButtonStyle.link, url="https://t.me/alves0000")
    async def iletisim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Bu buton direkt Telegram'a yönlendirir
        pass
    
    @discord.ui.button(label="🔙 Geri", style=discord.ButtonStyle.secondary, custom_id="geri_komutlar")
    async def geri_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Komut Türü Seçin",
            description="Hangi tür komutları kullanmak istersiniz?",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=KomutlarView())

# ============ KOMUTLAR ============
@bot.event
async def on_ready():
    logger.info(f'{bot.user} olarak giriş yapıldı!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"{len(synced)} komut senkronize edildi.")
        
        # Bot hazır olduğunda admin'e mesaj gönder
        if ADMIN_ID != 0:
            try:
                admin = await bot.fetch_user(ADMIN_ID)
                await admin.send(f"✅ Bot başarıyla başlatıldı!\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                pass
    except Exception as e:
        logger.error(f"Senkronizasyon hatası: {e}")

@bot.tree.command(name="start", description="Bot'u başlat ve ana menüyü göster")
async def start(interaction: discord.Interaction):
    if REQUIRED_ROLE_ID != 0 and not check_roles(interaction.user):
        embed = discord.Embed(
            title="⚠️ Erişim Engellendi",
            description="Botu kullanabilmek için gerekli role sahip değilsiniz!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    view = MainMenuView()
    embed = discord.Embed(
        title="👋 Hoş Geldiniz!",
        description="Aşağıdaki butonlardan birini seçin:",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikme süresini göster")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Gecikme: {latency}ms\nÇalışma Süresi: {int(time.time() - start_time)}s",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="Bot istatistiklerini göster")
async def stats(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Bot İstatistikleri",
        color=discord.Color.blue()
    )
    embed.add_field(name="⏱️ Çalışma Süresi", value=f"{int(time.time() - start_time)} saniye", inline=True)
    embed.add_field(name="📡 Ping Sayısı", value=f"{ping_counter[0]}", inline=True)
    embed.add_field(name="👥 Kullanıcı Sayısı", value=f"{len(user_states)} aktif", inline=True)
    embed.add_field(name="👤 Yapımcı", value="@alves0000", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="iletisim", description="Bot yapımcısı ile iletişime geçin")
async def iletisim(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📞 İletişim",
        description="Bot yapımcısı ile iletişime geçmek için:",
        color=discord.Color.blue()
    )
    embed.add_field(name="👤 Yapımcı", value="@alves0000", inline=False)
    embed.add_field(name="📱 Telegram", value="[t.me/alves0000](https://t.me/alves0000)", inline=True)
    embed.add_field(name="🐦 Twitter", value="[twitter.com/alves0000](https://twitter.com/alves0000)", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============ SORGU FONKSİYONLARI ============
def check_roles(member: discord.Member):
    if REQUIRED_ROLE_ID == 0:
        return True
    role = member.guild.get_role(REQUIRED_ROLE_ID)
    if role and role in member.roles:
        return True
    return False

async def adsoyad_sorgu(channel, user_id):
    veri = user_states.get(user_id, {})
    ad = veri.get("ad", "")
    soyad = veri.get("soyad", "")
    il = veri.get("il", "")
    
    await channel.send("🔍 Sorgulanıyor...")
    
    try:
        url = f"https://api.hexnox.pro/sowixapi/adsoyadilce.php?ad={ad}&soyad={soyad}&il={il}"
        response = requests.get(url, timeout=10)
        json_data = response.json()
        data_listesi = json_data.get("data")
        
        if data_listesi and isinstance(data_listesi, list):
            kisi = data_listesi[0]
            sonuc = "\n".join([f"🔹 {k}: {v}" for k, v in kisi.items()])
            embed = discord.Embed(
                title="✅ Sorgu Sonucu",
                description=sonuc,
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        else:
            await channel.send("❌ Sonuç bulunamadı.")
    except Exception as e:
        logger.error(f"Adsoyad sorgu hatası: {e}")
        await channel.send(f"⚠️ Hata oluştu. Lütfen tekrar deneyin.")
    
    user_states.pop(user_id, None)

async def tcpro_sorgu(channel, tc):
    await channel.send("🔍 TC Pro sorgulanıyor...")
    try:
        url = f"https://api.hexnox.pro/sowixapi/tcpro.php?tc={tc}"
        response = requests.get(url, timeout=10)
        data = response.json().get("data")
        if data:
            sonuc = "\n".join([f"🔹 {k}: {v}" for k, v in data.items()])
            embed = discord.Embed(
                title="✅ TC Pro Sonuç",
                description=sonuc,
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        else:
            await channel.send("❌ TC bulunamadı.")
    except Exception as e:
        logger.error(f"TC Pro sorgu hatası: {e}")
        await channel.send(f"⚠️ Hata oluştu. Lütfen tekrar deneyin.")

async def gsmdetay_sorgu(channel, gsm):
    url = f"https://api.hexnox.pro/sowixapi/gsmdetay.php?gsm={gsm}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("success") and data.get("Data"):
            d = data["Data"]
            sonuc = f"""📱 GSM Detay Sorgu Sonucu

👤 Ad Soyad: {d.get('AD', 'Yok')} {d.get('SOYAD', 'Yok')}
🆔 TC: {d.get('TC', 'Yok')}
🎂 Doğum Tarihi: {d.get('DOGUMTARIHI', 'Yok')}
📍 Adres: {d.get('Ikametgah', 'Yok')}
👩 Anne Adı: {d.get('ANNEADI', 'Yok')}
👨 Baba Adı: {d.get('BABAADI', 'Yok')}"""
            embed = discord.Embed(
                title="📱 GSM Detay Sonucu",
                description=sonuc,
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
        else:
            await channel.send("❌ Sonuç bulunamadı.")
    except Exception as e:
        logger.error(f"GSM detay sorgu hatası: {e}")
        await channel.send(f"⚠️ Hata oluştu. Lütfen tekrar deneyin.")

async def plaka_sorgu(channel, plaka):
    url = f"https://quantrexsystems.alwaysdata.net/diger/plaka.php?plaka={plaka}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("success") and data.get("Data"):
            d = data["Data"]
            sonuc = f"""🚗 Plaka Sorgu Sonucu

Plaka: {d.get('plaka', 'N/A')}
Borç Türü: {d.get('borcTuru', 'N/A')}
İsim Soyisim: {d.get('Isimsoyisim', 'N/A')}
T.C.: {d.get('Tc', 'N/A')}
Yazılan Ceza: {d.get('YazilanCeza', 'N/A')}
Toplam Ceza: {d.get('ToplamCeza', 'N/A')}"""
            embed = discord.Embed(
                title="🚗 Plaka Sorgu Sonucu",
                description=sonuc,
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)
        else:
            await channel.send("❌ Veri bulunamadı.")
    except Exception as e:
        logger.error(f"Plaka sorgu hatası: {e}")
        await channel.send(f"❌ Hata oluştu. Lütfen tekrar deneyin.")

# ============ MESAJ YAKALAMA ============
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    if not isinstance(message.channel, discord.DMChannel):
        return
    
    user_id = message.author.id
    if user_id not in user_states:
        return
    
    durum = user_states[user_id].get("durum")
    text = message.content.strip()
    
    if durum == "ad_sor":
        user_states[user_id]["ad"] = text
        user_states[user_id]["durum"] = "soyad_sor"
        await message.channel.send("👤 Lütfen soyadınızı girin:")
    
    elif durum == "soyad_sor":
        user_states[user_id]["soyad"] = text
        user_states[user_id]["durum"] = "il_sor"
        await message.channel.send("🌆 Lütfen ili yazın veya 'bilmiyorum' yazın:")
    
    elif durum == "il_sor":
        if text.lower() == "bilmiyorum":
            user_states[user_id]["il"] = ""
        else:
            user_states[user_id]["il"] = text
        await adsoyad_sorgu(message.channel, user_id)
    
    elif durum == "tcpro_sor":
        if len(text) == 11 and text.isdigit():
            await tcpro_sorgu(message.channel, text)
            user_states.pop(user_id, None)
        else:
            await message.channel.send("❌ Geçerli bir 11 haneli TC giriniz.")
    
    elif durum == "gsm_sor":
        if text.isdigit() and len(text) >= 10:
            await gsmdetay_sorgu(message.channel, text)
            user_states.pop(user_id, None)
        else:
            await message.channel.send("❌ Geçerli bir GSM numarası giriniz.")
    
    elif durum == "plaka_sor":
        if text.isalnum() and len(text) < 10:
            await plaka_sorgu(message.channel, text)
            user_states.pop(user_id, None)
        else:
            await message.channel.send("❌ Geçerli bir plaka giriniz.")

# ============ BOT'U ÇALIŞTIR ============
def run_bot():
    """Bot'u ayrı bir thread'de çalıştır"""
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot hatası: {e}")

if __name__ == "__main__":
    # Flask web server'ı thread'de başlat
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    logger.info(f"🌐 Web server başlatıldı: http://localhost:{PORT}")
    
    # Ping görevi
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.create_task(keep_alive())
    logger.info("🔄 Ping sistemi başlatıldı (her 8 dakikada bir)")
    
    # Bot'u başlat (ana thread)
    run_bot()
