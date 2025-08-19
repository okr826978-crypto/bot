import os
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ
GUILD_ID = 1209931632782344243           # ID เซิร์ฟเวอร์ที่ใช้ (guild commands)

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
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:(เลือกได้)`\n\nตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย reveal:ไม่เปิดเผย`",
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

# ================= ENUM =================
class RevealOption(discord.Enum):
    เปิดเผย = "yes"
    ไม่เปิดเผย = "no"

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
@app_commands.describe(user="ผู้รับข้อความ", message="ข้อความที่จะฝากบอก", reveal="เปิดเผยตัวตนหรือไม่")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, reveal: RevealOption):
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        # ส่งเข้าห้องฝากบอก
        await target_channel.send(f"**ถึง {user.mention}**\n{message}")

        # ส่ง DM
        try:
            sender_name = interaction.user.display_name if reveal.value == "yes" else "ไม่เปิดเผยตัวตน"
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

    except Exception as e:
        await send_crash_log(str(e))

# ================= Bot Events =================
@bot.event
async def on_ready():
    try:
        # ลบคำสั่งเก่าของ guild ก่อน
        guild_obj = discord.Object(id=GUILD_ID)
        for cmd in await tree.fetch_commands(guild=guild_obj):
            await tree.delete_command(cmd.id, guild=guild_obj)

        # ซิงค์คำสั่งใหม่
        await tree.sync(guild=guild_obj)

        print(f"✅ Logged in as {bot.user}")
        await send_guide()

    except Exception as e:
        await send_crash_log(str(e))

# ================= RUN BOT =================
bot.run(TOKEN)


