import os
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ
PORT = int(os.environ.get("PORT", 8000))  # Render จะกำหนด PORT ให้

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= HELP / GUIDE =================
async def send_guide():
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:เลือกว่าจะเปิดเผยตัวตนหรือไม่`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= CRASH LOG =================
async def send_crash_log(error_msg):
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(title="💥 Bot เกิดข้อผิดพลาด", description=error_msg, color=0xE74C3C)
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

# ================= Choices ENUM =================
class RevealChoice(discord.Enum):
    เปิดเผยตัวตน = "yes"
    ไม่เปิดเผยตัวตน = "no"

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
@app_commands.describe(user="ผู้รับข้อความ", message="ข้อความที่จะฝากบอก", reveal="เลือกว่าจะเปิดเผยตัวตนหรือไม่")
async def send_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str,
    reveal: RevealChoice
):
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        # ส่งเข้าห้องฝากบอก
        await target_channel.send(f"💌 **ข้อความถึง {user.mention}**\n\n{message}")

        # ส่ง DM
        try:
            sender_name = interaction.user.display_name if reveal.value == "yes" else "ไม่เปิดเผยตัวตน"
            await user.send(f"💌 คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
        except:
            pass

        # Log แอดมิน
        embed = discord.Embed(title="📩 มีข้อความฝากบอกใหม่", color=0x1ABC9C)
        embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} ({'เปิดเผยตัวตน' if reveal.value == 'yes' else 'ไม่เปิดเผยตัวตน'})", inline=False)
        embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

        await interaction.followup.send("✅ ส่งข้อความฝากบอกเรียบร้อยแล้ว!", ephemeral=True)

    except Exception as e:
        await send_crash_log(str(e))

# ================= Bot Events =================
@bot.event
async def on_ready():
    try:
        await tree.sync()
        print(f"✅ Logged in as {bot.user}")
        await send_guide()
    except Exception as e:
        await send_crash_log(str(e))

# ================= WEB SERVER =================
async def handle(request):
    return web.Response(text="Bot is online ✅")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# ================= RUN BOT =================
async def main():
    await start_web_server()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
