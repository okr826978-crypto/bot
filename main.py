import os
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ
PORT = int(os.environ.get("PORT", 3000))  # สำหรับ UptimeRobot ping

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
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:(เลือกได้)`\n\nตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย reveal:ไม่`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= CRASH LOG =================
async def send_crash_log(error_msg):
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(title="💥 Bot Crash/Error", description=error_msg, color=0xE74C3C)
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
async def send_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str,
    reveal: str
):
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        # ส่งเข้าห้องฝากบอก
        await target_channel.send(f"**ถึง {user.mention}**\n{message}")

        # ส่ง DM
        try:
            sender_name = interaction.user.display_name if reveal.lower() == "yes" else "ไม่เปิดเผยตัวตน"
            await user.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
        except:
            pass

        # Log แอดมิน
        embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
        embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} ({'เปิดเผย' if reveal.lower() == 'yes' else 'ไม่เปิดเผย'})", inline=False)
        embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

        await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)

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

# ================= HTTP Server สำหรับ UptimeRobot =================
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle_ping)])

# ================= RUN BOT + HTTP SERVER =================
async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
