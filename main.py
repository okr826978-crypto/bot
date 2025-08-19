import os
import discord
from discord.ext import commands
from datetime import datetime

# ================= CONFIG =================
TOKEN = os.environ["DISCORD_TOKEN"]  # ใส่ TOKEN ไว้ใน ENV
TARGET_CHANNEL_ID = 123456789012345678  # ห้องที่ฝากบอก (ข้อความถึงผู้รับ)
ADMIN_CHANNEL_ID = 123456789012345678   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องที่ให้บอทโพสต์คู่มือ

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= ฝากบอก Command =================
@bot.tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
async def send_message(interaction: discord.Interaction,
                       user: discord.Member,
                       message: str,
                       reveal: str):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    # เนื้อหาสำหรับห้องฝากบอก
    public_content = f"**ถึง {user.mention}**\n{message}"

    # ส่งเข้าห้องฝากบอก
    await target_channel.send(public_content)

    # ส่ง DM ถึงผู้รับ
    try:
        sender_name = interaction.user.display_name if reveal.strip().lower() == "ใช่" else "ไม่เปิดเผยตัวตน"
        await user.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
    except:
        pass

    # Log ไปห้องแอดมิน
    now = datetime.now().strftime("%d/%m/%Y เวลา %H:%M")
    embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
    embed.add_field(
        name="ผู้ส่ง",
        value=f"{interaction.user.mention} ({'เปิดเผย' if reveal.strip().lower() == 'ใช่' else 'ไม่เปิดเผย'})",
        inline=False
    )
    embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="ข้อความ", value=message, inline=False)
    embed.set_footer(text=f"📅 {now}")
    await admin_channel.send(embed=embed)

    # ตอบกลับผู้ใช้ (เห็นคนเดียว)
    await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)

# ================= Bot Events =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ถ้าต้องการฝากข้อความถึงใคร ให้ใช้คำสั่ง:\n\n"
                        "`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:ใช่/ไม่`\n\n"
                        "🔹 ตัวอย่าง: `/ฝากบอก @Jojo วันนี้เจอกันหน่อย reveal:ไม่`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= Run Bot =================
bot.run(TOKEN)
