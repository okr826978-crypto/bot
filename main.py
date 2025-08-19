import os
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime
import aiohttp

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 123456789012345678  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 123456789012345678   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 123456789012345678   # ห้องคู่มือ
PING_URL = os.environ.get("https://bot-zo60.onrender.com")    # ใส่ URL ตัวเองถ้าอยากให้ ping ทุก 5 นาที

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
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:(yes/no)`\n\nตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย reveal:yes`",
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

# ================= KEEP ALIVE =================
@tasks.loop(minutes=5)
async def ping_self():
    if PING_URL:
        try:
            async with aiohttp.ClientSession() as session:
                await session.get(PING_URL)
        except:
            pass

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
async def send_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str,
    reveal: str  # เปลี่ยนเป็น str
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

# ================= Choices / Autocomplete =================
@send_message.autocomplete("reveal")
async def reveal_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        app_commands.Choice(name="ใช่ (เปิดเผยชื่อ)", value="yes"),
        app_commands.Choice(name="ไม่ (ไม่เปิดเผยชื่อ)", value="no"),
    ]
    return [c for c in choices if current.lower() in c.name.lower()]

# ================= Bot Events =================
@bot.event
async def on_ready():
    try:
        await tree.sync()
        print(f"✅ Logged in as {bot.user}")
        await send_guide()
        ping_self.start()
    except Exception as e:
        await send_crash_log(str(e))

# ================= RUN BOT =================
bot.run(TOKEN)
