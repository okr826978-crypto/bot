import os
import discord
from discord import app_commands
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
# ดึง Token ของบอทจาก Environment Variable
TOKEN = os.environ.get("DISCORD_TOKEN")  

# กำหนด ID ของ Server และห้องต่าง ๆ
GUILD_ID = 1209931632782344243           # Server ของคุณ
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง Log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ / วิธีใช้คำสั่งฝากบอก
CHECK_ROLE_ID = 1407172158223814676      # Role สำหรับ /ตรวจสอบ
ROLE_GUIDE_CHANNEL_ID = 1407702878017159329  # ห้องคู่มือยศ
ROLE_COMMAND_CHANNEL_ID = 1407702892789502054  # ห้องใช้คำสั่ง /ย้ายยศ
PORT = int(os.environ.get("PORT", 3000)) # พอร์ตสำหรับ Web server ping

# ================= INTENTS =================
# ตั้งค่า Intents ของ Discord bot เพื่อดึงข้อมูลสมาชิก
intents = discord.Intents.default()
intents.members = True  # ต้องเปิดเพื่อเข้าถึงสมาชิก
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)  # สำหรับ Slash command

# ================= ข้อมูลข้อความล่าสุด =================
# เก็บข้อความล่าสุดเพื่อใช้ตรวจสอบ/ตอบกลับ
last_messages = {}  # ตัวอย่าง: {"msg": str, "hint": str, "time": datetime, "sender": int}

# ================= ฟังก์ชันส่งคู่มือ =================
async def send_guide():
    """ส่งคู่มือคำสั่งฝากบอกไปที่ GUIDE_CHANNEL_ID"""
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title=":GoodMorning: วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ hint:คำใบ้`\n\n"
                        "ตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย hint:เรื่องงาน`",
            color=0x5865F2
        )
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

async def send_role_guide():
    """ส่งคู่มือคำสั่งย้ายยศไปที่ ROLE_GUIDE_CHANNEL_ID"""
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(ROLE_GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title=":GoodMorning: วิธีใช้คำสั่งย้ายยศ",
            description=(f"ใช้คำสั่งในห้อง <#{ROLE_COMMAND_CHANNEL_ID}> เท่านั้น\n\n"
                         "`/ย้ายยศ user:@ชื่อ role:@Role`\n\n"
                         "ตัวอย่าง:\n`/ย้ายยศ @โจ @VIP`"),
            color=0x5865F2
        )
        embed.set_footer(text="ระบบย้ายยศอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= ฟังก์ชันแจ้ง Error =================
async def send_crash_log(error_msg):
    """ส่งข้อความแจ้งบอทเกิด Error ไปที่ ADMIN_CHANNEL_ID"""
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(
            title=":GoodMorning: Bot Crash/Error",
            description=error_msg,
            color=0xE74C3C
        )
        embed.set_footer(text=f":GoodMorning: {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

# ================= Modal สำหรับตอบกลับ =================
class ReplyModal(discord.ui.Modal, title=":55994bubblesweat: ตอบกลับข้อความ"):
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
        # ดึงข้อความที่กรอก
        reply_text = self.reply_input.value
        sender = await bot.fetch_user(self.sender_id)
        if sender:
            await sender.send(f"[ICON_PLACEHOLDER] คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")

        # อัปเดต embed เดิมด้วยข้อความตอบกลับ
        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)
        await interaction.response.send_message(":55994bubblesweat: ส่งข้อความตอบกลับแล้ว!", ephemeral=True)

# ================= VIEW ปุ่มตอบกลับ =================
class ReplyView(discord.ui.View):
    """สร้างปุ่มตอบกลับใต้ข้อความฝากบอก"""
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label=":55994bubblesweat: ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message(":55994bubblesweat: ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)
        await interaction.response.send_modal(ReplyModal(self.sender_id, self.original_embed, self.original_message))

# ================= คำสั่ง /ฝากบอก =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    """ส่งข้อความฝากบอกไปยังห้อง TARGET_CHANNEL_ID พร้อมปุ่มตอบกลับและบันทึก Log"""
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message(":guarded: ใช้คำสั่งนี้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message(":guarded: ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        target_channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)

        embed = discord.Embed(
            title=":GoodMorning: มีข้อความฝากบอกถึงคุณ",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        embed.set_footer(text="ระบบฝากบอกอัตโนมัติ")

        msg_sent = await target_channel.send(content=f"{user.mention}", embed=embed)
        view = ReplyView(sender_id=interaction.user.id, original_embed=embed, original_message=msg_sent)
        await msg_sent.edit(view=view)

        # ส่ง DM ไปยังผู้รับ
        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        # บันทึก log ไปยังแอดมิน
        log_embed = discord.Embed(title=":GoodMorning: ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f":GoodMorning: {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.followup.send(":76413patrickbuu: เกิดข้อผิดพลาดในการฝากบอก", ephemeral=True)

# ================= คำสั่ง /ย้ายยศ =================
@tree.command(name="ย้ายยศ", description="ให้สมาชิกย้ายยศกันเอง")
async def move_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    """เพิ่ม/ลบ Role ของสมาชิก พร้อมตรวจสอบ server และห้อง"""
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message(":guarded: ใช้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)
        if interaction.channel.id != ROLE_COMMAND_CHANNEL_ID:
            return await interaction.response.send_message(":guarded: ใช้ได้เฉพาะในห้องคำสั่งยศ", ephemeral=True)
        
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f":GoodMorning: ลบยศ {role.name} จาก {user.display_name}", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f":GoodMorning: เพิ่มยศ {role.name} ให้ {user.display_name}", ephemeral=True)

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.response.send_message(":76413patrickbuu: เกิดข้อผิดพลาดในการย้ายยศ", ephemeral=True)

# ================= WEB SERVER PING =================
async def start_webserver():
    """เริ่ม Web server สำหรับ Heroku / Render เพื่อไม่ให้บอท exit"""
    async def handle(request):
        return web.Response(text="Bot is running ✅")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Web server started on port {PORT} ✅")

# ================= EVENT on_ready =================
@bot.event
async def on_ready():
    """เมื่อบอทพร้อม ทำการส่งคู่มือ และ sync slash command"""
    print(f"Bot Logged in as {bot.user}")
    await send_guide()      # ส่งคู่มือฝากบอก
    await send_role_guide() # ส่งคู่มือยศ
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)  # sync คำสั่ง slash
    print("Slash commands synced.")

    # เริ่ม Web server ping
    bot.loop.create_task(start_webserver())

# ================= RUN BOT =================
bot.run(TOKEN)
