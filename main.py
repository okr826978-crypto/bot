import os
import discord
from discord import app_commands
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")  # ดึง Token ของบอทจาก Environment Variable

GUILD_ID = 1209931632782344243           # ใส่ ID ของ Server ที่จะให้ใช้ได้
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ / วิธีใช้คำสั่ง
CHECK_ROLE_ID = 1209948561387683921     # Role ที่ใช้ /ตรวจสอบ
PORT = int(os.environ.get("PORT", 3000)) # พอร์ตสำหรับ Web server ping

# ตั้งค่า Intents ของ Discord bot
intents = discord.Intents.default()     
intents.members = True  # ต้องใช้เพื่อดึงข้อมูลสมาชิก
bot = discord.Client(intents=intents)  # สร้าง bot client
tree = app_commands.CommandTree(bot)   # สำหรับใช้คำสั่ง Slash command

# เก็บข้อความล่าสุดไว้ให้ตรวจสอบ (key = user.id)
last_messages = {}  # {"msg": str, "hint": str, "time": datetime, "sender": int}


# ================= HELP / GUIDE =================
async def send_guide():
    """ส่งคู่มือคำสั่งฝากบอกไปที่ GUIDE_CHANNEL_ID"""
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)  # ลบข้อความเก่า
        embed = discord.Embed(
            title="📌 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ hint:คำใบ้`\n\n"
                        "ตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย hint:เรื่องงาน`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)


# ================= CRASH LOG =================
async def send_crash_log(error_msg):
    """ส่งข้อความแจ้งบอทเกิด Error ไปที่ ADMIN_CHANNEL_ID"""
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(title="💥 Bot Crash/Error", description=error_msg, color=0xE74C3C)
        embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)


# ================= Modal ตอบกลับ =================
class ReplyModal(discord.ui.Modal, title="✍️ ตอบกลับข้อความ"):
    """Modal สำหรับให้ผู้ใช้กรอกข้อความตอบกลับ"""
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
        """เมื่อผู้ใช้ submit ข้อความ จะส่ง DM ไปหาผู้ส่งเดิมและอัปเดต embed"""
        reply_text = self.reply_input.value
        sender = await bot.fetch_user(self.sender_id)

        if sender:
            await sender.send(f"📨 คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")

        # อัปเดต embed เดิมในห้องฝากบอก
        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message("✅ ส่งข้อความตอบกลับแล้ว!", ephemeral=True)


# ================= VIEW ปุ่ม =================
class ReplyView(discord.ui.View):
    """สร้างปุ่มตอบกลับใต้ข้อความฝากบอก"""
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label="💌 ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """เมื่อผู้ใช้กดปุ่ม จะเปิด Modal สำหรับตอบกลับ"""
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("❌ ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

        await interaction.response.send_modal(
            ReplyModal(self.sender_id, self.original_embed, self.original_message)
        )


# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    """คำสั่ง /ฝากบอก สำหรับฝากข้อความถึงสมาชิกคนอื่น"""
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("❌ ใช้คำสั่งนี้ได้เฉพาะใน Server ที่กำหนด", ephemeral=True)

        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("❌ ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

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
        embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")

        # ส่งข้อความเข้าห้องฝากบอก
        msg_sent = await target_channel.send(content=f"{user.mention}", embed=embed)

        # เพิ่มปุ่มตอบกลับใต้ข้อความ
        view = ReplyView(sender_id=interaction.user.id, original_embed=embed, original_message=msg_sent)
        await msg_sent.edit(view=view)

        # ส่ง DM ให้ผู้รับด้วย
        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        # Log แอดมิน
        log_embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f"📅 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

        # เก็บข้อความล่าสุด
        last_messages[user.id] = {
            "msg": message,
            "hint": hint,
            "time": datetime.now(),
            "sender": interaction.user.id
        }

        await interaction.followup.send("✅ ฝากบอกสำเร็จ! ข้อความถูกส่งแล้ว", ephemeral=True)

    except Exception as e:
        await send_crash_log(str(e))  # ส่ง error log


# ================= ตรวจสอบ Command =================
@tree.command(name="ตรวจสอบ", description="ตรวจสอบข้อความล่าสุด (สำหรับแอดมิน)")
async def check_message(interaction: discord.Interaction, user: discord.Member):
    """คำสั่ง /ตรวจสอบ สำหรับแอดมิน ตรวจสอบข้อความล่าสุดของสมาชิก"""
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("❌ ใช้ได้เฉพาะใน Server ที่กำหนด", ephemeral=True)

        role = interaction.guild.get_role(CHECK_ROLE_ID)
        if role not in interaction.user.roles:
            return await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)

        data = last_messages.get(user.id)
        if not data:
            return await interaction.response.send_message("⚠️ ไม่พบข้อความล่าสุดของคนนี้", ephemeral=True)

        sender = await bot.fetch_user(data["sender"])
        embed = discord.Embed(title="🔎 ตรวจสอบข้อความล่าสุด", color=0xF1C40F)
        embed.add_field(name="ผู้รับ", value=user.mention, inline=False)
        embed.add_field(name="ข้อความ", value=data["msg"], inline=False)
        embed.add_field(name="คำใบ้", value=data["hint"], inline=False)
        embed.add_field(name="ผู้ส่ง (ชื่อ)", value=f"{sender.name}#{sender.discriminator}", inline=False)
        embed.set_footer(text=f"📅 {data['time'].strftime('%d/%m/%Y เวลา %H:%M')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await send_crash_log(str(e))  # ส่ง error log


# ================= Bot Events =================
@bot.event
async def on_ready():
    """เมื่อบอทพร้อมใช้งาน"""
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))  # ซิงค์คำสั่ง Slash command
        print(f"✅ Logged in as {bot.user}")
        await send_guide()  # ส่งคู่มือไปที่ห้อง GUIDE_CHANNEL
    except Exception as e:
        await send_crash_log(str(e))


# ================= HTTP Server =================
async def handle_ping(request):
    """หน้า Ping สำหรับตรวจสอบ Bot ยังทำงานอยู่"""
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle_ping)])


# ================= RUN BOT =================
async def main():
    """รัน Web server และ Discord bot พร้อมกัน"""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
