import os
import discord
from datetime import datetime

# ================= CONFIG =================
TOKEN = os.environ["DISCORD_TOKEN"]
TARGET_CHANNEL_ID = 123456789012345678  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 123456789012345678   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
async def send_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str,
    reveal: discord.app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    # ส่งเข้าห้องฝากบอก
    await target_channel.send(f"**ถึง {user.mention}**\n{message}")

    # ส่ง DM ถึงผู้รับ
    try:
        sender_name = interaction.user.display_name if reveal.value == "yes" else "ไม่เปิดเผยตัวตน"
        await user.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
    except:
        pass

    # Log ไปห้องแอดมิน
    now = datetime.now().strftime("%d/%m/%Y เวลา %H:%M")
    embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
    embed.add_field(
        name="ผู้ส่ง",
        value=f"{interaction.user.mention} ({'เปิดเผย' if reveal.value == 'yes' else 'ไม่เปิดเผย'})",
        inline=False
    )
    embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="ข้อความ", value=message, inline=False)
    embed.set_footer(text=f"📅 {now}")
    await admin_channel.send(embed=embed)

    await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)

# ================= Choices =================
@send_message.autocomplete("reveal")
async def reveal_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        discord.app_commands.Choice(name="ใช่ (เปิดเผยชื่อ)", value="yes"),
        discord.app_commands.Choice(name="ไม่ (ไม่เปิดเผยชื่อ)", value="no"),
    ]
    return [c for c in choices if current.lower() in c.name.lower()]

# ================= Bot Events =================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n\n"
                        "`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:(เลือกได้)`\n\n"
                        "🔹 ตัวอย่าง: `/ฝากบอก @Jojo วันนี้เจอกันหน่อย reveal:ไม่`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= Run Bot =================
bot.run(TOKEN)
