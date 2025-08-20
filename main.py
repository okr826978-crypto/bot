import os
import discord
from discord import app_commands
from datetime import datetime
from aiohttp import web
import asyncio

# ================= CONFIG =================
# ตั้งค่าต่าง ๆ ของบอท
TOKEN = os.environ.get("DISCORD_TOKEN")  # Token ของบอท
GUILD_ID = 1209931632782344243           # Server ID ของคุณ
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้องเก็บ Log ของ Admin
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องแสดงคู่มือคำสั่ง /ฝากบอก
CHECK_ROLE_ID = 1407172158223814676      # Role ตรวจสอบ (ใช้ในอนาคต)
ROLE_GUIDE_CHANNEL_ID = 1407702878017159329  # ห้องคู่มือยศ
ROLE_COMMAND_CHANNEL_ID = 1407702892789502054 # ห้องใช้คำสั่งยศ
PORT = int(os.environ.get("PORT", 3000))      # พอร์ตสำหรับเว็บเซิร์ฟเวอร์

# ================= INTENTS =================
# ตั้งค่า intents เพื่อให้บอทสามารถเข้าถึงสมาชิก
intents = discord.Intents.default()
intents.members = True  # ต้องเปิดเพื่อดึงข้อมูลสมาชิก
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)  # สำหรับ Slash commands

# ================= ตัวเก็บข้อความล่าสุด =================
# ใช้เก็บข้อความล่าสุด ถ้าต้องการทำการแก้ไขหรือดูย้อนหลัง
last_messages = {}

# ================= ฟังก์ชันส่งคู่มือ /ฝากบอก =================
async def send_guide():
    """
    ลบข้อความเดิมในห้องคู่มือแล้วส่ง embed ใหม่อธิบายวิธีใช้คำสั่ง /ฝากบอก
    """
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)  # ลบข้อความเก่า
        embed = discord.Embed(
            title="🌅 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ hint:คำใบ้`\n\n"
                        "ตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย hint:เรื่องงาน`",
            color=0x5865F2
        )
        embed.set_footer(text="📬 ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= ฟังก์ชันส่งคู่มือ /ย้ายยศ =================
async def send_role_guide():
    """
    ลบข้อความเดิมในห้องคู่มือแล้วส่ง embed ใหม่อธิบายวิธีใช้คำสั่ง /ย้ายยศ
    """
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(ROLE_GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title="🌅 วิธีใช้คำสั่งย้ายยศ",
            description=(f"ใช้คำสั่งในห้อง <#{ROLE_COMMAND_CHANNEL_ID}> เท่านั้น\n\n"
                         "`/ย้ายยศ user:@ชื่อ role:@Role duration:เวลา`\n\n"
                         "ตัวอย่าง:\n`/ย้ายยศ @โจ @VIP 10m` (ยศชั่วคราว 10 นาที)\n"
                         "`/ย้ายยศ @โจ @VIP` (ยศถาวร)"),
            color=0x5865F2
        )
        embed.set_footer(text="📬 ระบบย้ายยศอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= ฟังก์ชันแจ้ง Error =================
async def send_crash_log(error_msg):
    """
    ส่งข้อความแจ้งข้อผิดพลาดไปยัง Admin
    """
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(
            title="⚠️ Bot Crash/Error",
            description=error_msg,
            color=0xE74C3C
        )
        embed.set_footer(text=f"⚠️ {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=embed)

# ================= Modal สำหรับตอบกลับ =================
class ReplyModal(discord.ui.Modal, title="💬 ตอบกลับข้อความ"):
    """
    Modal ให้ผู้ดูแลตอบข้อความฝากบอกแบบไม่เปิดเผยตัวตน
    """
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__()
        self.sender_id = sender_id              # ID ของผู้ส่ง
        self.original_embed = original_embed    # Embed ต้นฉบับ
        self.original_message = original_message # Message ที่ส่งใน Channel

        self.reply_input = discord.ui.TextInput(
            label="พิมพ์ข้อความตอบกลับ",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.reply_input)

    async def on_submit(self, interaction: discord.Interaction):
        # ดึงข้อความที่พิมพ์
        reply_text = self.reply_input.value
        sender = await bot.fetch_user(self.sender_id)
        if sender:
            # ส่ง DM กลับผู้ส่ง
            await sender.send(f"💌 คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")

        # แก้ไข Embed เดิมให้เพิ่ม field ของข้อความตอบกลับ
        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)
        await interaction.response.send_message("💬 ส่งข้อความตอบกลับแล้ว!", ephemeral=True)

# ================= VIEW ปุ่มตอบกลับ =================
class ReplyView(discord.ui.View):
    """
    ปุ่มให้กดตอบกลับข้อความฝากบอก
    """
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label="💬 ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรวจสอบห้องก่อน
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("💬 ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)
        await interaction.response.send_modal(ReplyModal(self.sender_id, self.original_embed, self.original_message))

# ================= คำสั่ง /ฝากบอก =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    """
    Slash command /ฝากบอก
    - user: สมาชิกที่รับข้อความ
    - message: ข้อความที่ส่ง
    - hint: คำใบ้ (optional)
    """
    try:
        # ตรวจสอบ Server และ Channel
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("🚫 ใช้คำสั่งนี้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("🚫 ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        target_channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)

        # สร้าง Embed ของข้อความฝากบอก
        embed = discord.Embed(
            title="📬 มีข้อความฝากบอกถึงคุณ",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        embed.set_footer(text="📬 ระบบฝากบอกอัตโนมัติ")

        # ส่ง Embed พร้อมปุ่มตอบกลับ
        msg_sent = await target_channel.send(content=f"{user.mention}", embed=embed)
        view = ReplyView(sender_id=interaction.user.id, original_embed=embed, original_message=msg_sent)
        await msg_sent.edit(view=view)

        # ส่ง DM ให้ผู้รับด้วย (ถ้าอนุญาต)
        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        # Log ไปยัง Admin
        log_embed = discord.Embed(title="📬 ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f"📬 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการฝากบอก", ephemeral=True)

# ================= คำสั่ง /ย้ายยศ =================
@tree.command(name="ย้ายยศ", description="ให้สมาชิกย้ายยศกันเอง สามารถกำหนดระยะเวลาได้")
async def move_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role, duration: str = None):
    """
    Slash command /ย้ายยศ
    - user: สมาชิกที่จะให้ยศ
    - role: ยศที่ให้
    - duration: เวลา เช่น 10m หรือ 2h (optional)
    """
    try:
        # ตรวจสอบ Server และ Channel
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("🚫 ใช้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)
        if interaction.channel.id != ROLE_COMMAND_CHANNEL_ID:
            return await interaction.response.send_message("🚫 ใช้ได้เฉพาะในห้องคำสั่งยศ", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # เพิ่ม Role
        await user.add_roles(role)
        await interaction.followup.send(f"✅ เพิ่มยศ {role.name} ให้ {user.display_name}", ephemeral=True)

        # ถ้ามี duration ให้ลบ Role หลังหมดเวลา
        if duration:
            time_seconds = 0
            if duration.endswith("m"):
                time_seconds = int(duration[:-1]) * 60
            elif duration.endswith("h"):
                time_seconds = int(duration[:-1]) * 3600
            else:
                return await interaction.followup.send("❌ ระบุเวลาผิด เช่น 10m หรือ 2h", ephemeral=True)

            async def remove_role_later():
                await asyncio.sleep(time_seconds)
                await user.remove_roles(role)
                await interaction.followup.send(f"⌛ หมดเวลา {duration} ยศ {role.name} ถูกลบจาก {user.display_name}")

            bot.loop.create_task(remove_role_later())

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการย้ายยศ", ephemeral=True)

# ================= WEB SERVER PING =================
async def start_webserver():
    """
    สร้างเว็บเซิร์ฟเวอร์ง่าย ๆ เพื่อ Ping บอทให้อยู่ตลอด
    """
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
    print(f"Bot Logged in as {bot.user}")
    await send_guide()      # ส่งคู่มือ /ฝากบอก
    await send_role_guide() # ส่งคู่มือ /ย้ายยศ
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)  # Sync Slash commands
    print("Slash commands synced.")
    bot.loop.create_task(start_webserver())  # เริ่มเว็บเซิร์ฟเวอร์

# ================= RUN BOT =================
bot.run(TOKEN)
