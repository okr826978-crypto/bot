import os
import discord
from discord import app_commands
from datetime import datetime
import asyncio
from aiohttp import web
import traceback

# ================= CONFIG =================
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = 1407172158223814676         # ใส่ Guild ของคุณ
TARGET_CHANNEL_ID = 123456789012345678
ADMIN_CHANNEL_ID = 123456789012345678
GUIDE_CHANNEL_ID = 1406537337676103742
CRASH_LOG_CHANNEL_NAME = "bot-crash-log"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= Choices =================
REVEAL_CHOICES = [
    app_commands.Choice(name="ใช่ (เปิดเผยชื่อ)", value="yes"),
    app_commands.Choice(name="ไม่ (ไม่เปิดเผยชื่อ)", value="no"),
]

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน")
@app_commands.describe(user="ผู้รับข้อความ", message="ข้อความของคุณ", reveal="เปิดเผยชื่อหรือไม่")
@app_commands.choices(reveal=REVEAL_CHOICES)
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, reveal: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    await target_channel.send(f"**ถึง {user.mention}**\n{message}")

    try:
        sender_name = interaction.user.display_name if reveal.value == "yes" else "ไม่เปิดเผยตัวตน"
        await user.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{message}")
    except:
        pass

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

# ================= Bot Events =================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

    # สร้างห้อง Crash Log ถ้ายังไม่มี
    guild = bot.get_guild(GUILD_ID)
    global crash_channel
    crash_channel = discord.utils.get(guild.text_channels, name=CRASH_LOG_CHANNEL_NAME)
    if crash_channel is None:
        crash_channel = await guild.create_text_channel(CRASH_LOG_CHANNEL_NAME)
        print(f"🆕 สร้างห้อง {CRASH_LOG_CHANNEL_NAME} สำหรับ Crash Log")

    # ส่งคู่มือคำสั่งฝากบอก
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n\n`/ฝากบอก user:@ชื่อ message:ข้อความ reveal:(เลือกได้)`\n\n"
                        "🔹 ตัวอย่าง: `/ฝากบอก @Jojo วันนี้เจอกันหน่อย reveal:ไม่`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= Keep-Alive Web Server =================
async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.router.add_get("/", handle)

async def start_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 3000)))
    await site.start()
    print("🌐 Web server running for keep-alive")

# ================= Ping ตัวเองทุก 5 นาที =================
async def self_ping():
    import aiohttp
    while True:
        try:
            url = f"http://{os.environ.get('RENDER_INTERNAL_HOST', 'localhost')}:{os.environ.get('PORT', 3000)}"
            async with aiohttp.ClientSession() as session:
                await session.get(url)
                print("🏓 Self ping sent")
        except:
            pass
        await asyncio.sleep(300)  # 5 นาที

# ================= Main Loop with Auto Restart & Crash Log =================
async def main():
    await start_webserver()
    asyncio.create_task(self_ping())

    while True:
        try:
            await bot.start(TOKEN)
        except Exception:
            print("❌ Bot crashed! Restarting...")
            traceback.print_exc()
            try:
                if bot.is_ready():
                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    embed = discord.Embed(
                        title="❌ Bot Crash Alert",
                        description=f"เวลา: {now}\nเกิดข้อผิดพลาด:\n```{traceback.format_exc()}```",
                        color=0xE74C3C
                    )
                    await crash_channel.send(embed=embed)
            except:
                pass
            await asyncio.sleep(5)  # รอ 5 วิ ก่อน restart

asyncio.run(main())
