import os
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime
import aiohttp

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 123456789012345678
ADMIN_CHANNEL_ID = 123456789012345678
GUIDE_CHANNEL_ID = 123456789012345678
PING_URL = os.environ.get("https://bot-zo60.onrender.com")  # ตัวอย่าง: https://bot-zo60.onrender.com

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

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
    reveal: app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    # ส่งเข้าห้องฝากบอก
    await target_channel.send(f"**ถึง {user.mention}**\n{message}")

    # ส่ง DM
    sender_name = interaction.user.display_name if reveal.value == "yes" else "ไม่เปิดเผยตัวตน"
    try:
        await user.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
    except:
        pass

    # Log แอดมิน
    embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
    embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} ({'เปิดเผย' if reveal.value == 'yes' else 'ไม่เปิดเผย'})", inline=False)
    embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="ข้อความ", value=message, inline=False)
    embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
    await admin_channel.send(embed=embed)

    await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)

# ================= Choices =================
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
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")
    ping_self.start()

# ================= RUN BOT =================
bot.run(TOKEN)
