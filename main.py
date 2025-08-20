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
        # ลบข้อความเก่าทั้งหมดก่อน
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ`\n\nตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย`",
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
class ReplyView(discord.ui.View):
    def __init__(self, sender_id):
        super().__init__(timeout=None)
        self.sender_id = sender_id

    @discord.ui.button(label="💌 ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✍️ พิมพ์ข้อความตอบกลับที่คุณต้องการส่ง:", ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            sender = await bot.fetch_user(self.sender_id)
            if sender:
                await sender.send(f"📨 คุณได้รับการตอบกลับจาก {interaction.user.display_name}:\n\n{msg.content}")
                await interaction.followup.send("✅ ส่งข้อความตอบกลับแล้ว!", ephemeral=True)
        except:
            await interaction.followup.send("⏰ หมดเวลา! กรุณากดปุ่มอีกครั้งหากต้องการตอบกลับ", ephemeral=True)


@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(
    interaction: discord.Interaction,
    user: discord.Member,
    message: str
):
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        # Embed สำหรับห้องฝากบอก
        embed = discord.Embed(
            title="📨 มีข้อความฝากบอกถึงคุณ",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.add_field(name="คำใบ้", value="ไม่มี (ไม่เปิดเผยตัวตน)", inline=False)
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")

        # ปุ่มตอบกลับ
        view = ReplyView(sender_id=interaction.user.id)

        # ส่งเข้าห้องฝากบอก
        await target_channel.send(content=f"{user.mention}", embed=embed, view=view)

        # ส่ง DM
        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        # Log แอดมิน
        log_embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

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
