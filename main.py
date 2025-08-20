import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")  # ดึง Token ของบอทจาก Environment Variable

GUILD_ID = 1209931632782344243           # ใส่ ID ของ Server
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ / วิธีใช้คำสั่ง
CHECK_ROLE_ID = 1209948561387683921      # Role สำหรับ /ตรวจสอบ
PORT = int(os.environ.get("PORT", 3000)) # พอร์ตสำหรับ Web server ping

# Emoji placeholders (เปลี่ยนตรงนี้เป็นอิโมจิใน Server ของคุณ)
EMOJI_REPLY = "💌"  # ตรงนี้สำหรับใส่อิโมจิ Reply
EMOJI_ALERT = "📨"  # ตรงนี้สำหรับใส่อิโมจิ ฝากบอก
EMOJI_CRASH = "💥"  # ตรงนี้สำหรับใส่อิโมจิ Crash/Error
EMOJI_LOG = "📩"    # ตรงนี้สำหรับใส่อิโมจิ Log
EMOJI_CHECK = "🔎"  # ตรงนี้สำหรับใส่อิโมจิ ตรวจสอบ

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# เก็บข้อความล่าสุดของสมาชิก
last_messages = {}  # {user.id: {"msg": str, "hint": str, "time": datetime, "sender": int}}

# ================= HELP / GUIDE =================
async def send_guide():
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title=f"{EMOJI_ALERT} วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ hint:คำใบ้`\n\n"
                        "ตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย hint:เรื่องงาน`\n\n"
                        f"**/ย้ายยศ user:@ชื่อ role:@Role** - ให้สมาชิกย้ายยศกันเอง",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= CRASH LOG =================
async def send_crash_log(error_msg):
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(
            title=f"{EMOJI_CRASH} Bot Crash/Error",
            description=error_msg,
            color=0xE74C3C
        )
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

# ================= Modal ตอบกลับ =================
class ReplyModal(discord.ui.Modal, title=f"{EMOJI_REPLY} ตอบกลับข้อความ"):
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__()
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

        self.reply_input = discord.ui.TextInput(
            label="พิมพ์ข้อความตอบกลับ",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.reply_input)

    async def on_submit(self, interaction: discord.Interaction):
        reply_text = self.reply_input.value
        sender = await bot.fetch_user(self.sender_id)

        if sender:
            await sender.send(f"{EMOJI_REPLY} คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")

        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message("✅ ส่งข้อความตอบกลับแล้ว!", ephemeral=True)

# ================= VIEW ปุ่ม =================
class ReplyView(discord.ui.View):
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label=f"{EMOJI_REPLY} ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("❌ ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)
        await interaction.response.send_modal(
            ReplyModal(self.sender_id, self.original_embed, self.original_message)
        )

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("❌ ใช้คำสั่งนี้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("❌ ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        embed = discord.Embed(
            title=f"{EMOJI_ALERT} มีข้อความฝากบอกถึงคุณ",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")

        msg_sent = await target_channel.send(content=f"{user.mention}", embed=embed)

        view = ReplyView(sender_id=interaction.user.id, original_embed=embed, original_message=msg_sent)
        await msg_sent.edit(view=view)

        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        log_embed = discord.Embed(title=f"{EMOJI_LOG} ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

        last_messages[user.id] = {
            "msg": message,
            "hint": hint,
            "time": datetime.now(),
            "sender": interaction.user.id
        }

        await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)
    except Exception as e:
        await send_crash_log(str(e))

# ================= ตรวจสอบ Command =================
@tree.command(name="ตรวจสอบ", description="ตรวจสอบข้อความล่าสุด (สำหรับแอดมิน)")
async def check_message(interaction: discord.Interaction, user: discord.Member):
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("❌ ใช้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)

        role = interaction.guild.get_role(CHECK_ROLE_ID)
        if role not in interaction.user.roles:
            return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)

        data = last_messages.get(user.id)
        if not data:
            return await interaction.response.send_message("⚠️ ไม่พบข้อความล่าสุดของคนนี้", ephemeral=True)

        sender = await bot.fetch_user(data["sender"])
        embed = discord.Embed(title=f"{EMOJI_CHECK} ตรวจสอบข้อความล่าสุด", color=0xF1C40F)
        embed.add_field(name="ผู้รับ", value=user.mention, inline=False)
        embed.add_field(name="ข้อความ", value=data["msg"], inline=False)
        embed.add_field(name="คำใบ้", value=data["hint"], inline=False)
        embed.add_field(name="ผู้ส่ง (ชื่อ)", value=f"{sender.name}#{sender.discriminator}", inline=False)
        embed.set_footer(text=f"📅 {data['time'].strftime('%d/%m/%Y เวลา %H:%M')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await send_crash_log(str(e))

# ================= ย้ายยศ Command =================
@tree.command(name="ย้ายยศ", description="ให้สมาชิกย้ายยศกันเอง")
async def move_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("❌ ใช้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)

        # ตรวจสอบว่าผู้ส่งมีสิทธิ์ (ตัวอย่าง: ต้องเป็นสมาชิกใน Server)
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"✅ ลบยศ {role.name} ของ {user.display_name} เรียบร้อย", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ เพิ่มยศ {role.name} ให้ {user.display_name} เรียบร้อย", ephemeral=True)
    except Exception as e:
        await send_crash_log(str(e))
        await interaction.response.send_message("❌ เกิดข้อผิดพลาดในการย้ายยศ", ephemeral=True)

# ================= Bot Events =================
@bot.event
async def on_ready():
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"{bot.user} พร้อมใช้งานแล้ว!")
        await send_guide()
    except Exception as e:
        await send_crash_log(str(e))

# ================= Web server ping =================
async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get('/', handle)])

# ================= Run bot =================
import asyncio

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    await bot.start(TOKEN)

asyncio.run(main())
