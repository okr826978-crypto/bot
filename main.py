import os
import discord
from discord import app_commands
from datetime import datetime
from aiohttp import web

# ================= CONFIG =================
TOKEN = os.environ.get("DISCORD_TOKEN")  # ดึง Token ของบอทจาก Environment Variable

GUILD_ID = 1209931632782344243           # ใส่ ID ของ Server
TARGET_CHANNEL_ID = 1406537424947122266  # ห้องฝากบอก
ADMIN_CHANNEL_ID = 1406539787594240041   # ห้อง log แอดมิน
GUIDE_CHANNEL_ID = 1406537337676103742   # ห้องคู่มือ / วิธีใช้คำสั่งฝากบอก
CHECK_ROLE_ID = 1209948561387683921      # Role สำหรับ /ตรวจสอบ
ROLE_GUIDE_CHANNEL_ID = 1406540000000000000  # ห้องคู่มือ/คำอธิบายเกี่ยวกับยศ
ROLE_COMMAND_CHANNEL_ID = 1406541111111111111  # ห้องสำหรับใช้คำสั่ง /ย้ายยศ
PORT = int(os.environ.get("PORT", 3000)) # พอร์ตสำหรับ Web server ping

# ตั้งค่า Intents ของ Discord bot
intents = discord.Intents.default()
intents.members = True  # ต้องใช้เพื่อดึงข้อมูลสมาชิก
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)  # สำหรับ Slash command

# เก็บข้อความล่าสุดไว้ให้ตรวจสอบ (key = user.id)
last_messages = {}  # {"msg": str, "hint": str, "time": datetime, "sender": int}

# ================= HELP / GUIDE =================
async def send_guide():
    """ส่งคู่มือคำสั่งฝากบอกไปที่ GUIDE_CHANNEL_ID"""
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title="[ICON_PLACEHOLDER] วิธีใช้คำสั่งฝากบอก",  # ตรงนี้สำหรับใส่อิโมจิ
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
            title="[ICON_PLACEHOLDER] วิธีใช้คำสั่งย้ายยศ",  # ตรงนี้สำหรับใส่อิโมจิ
            description=(
                f"ใช้คำสั่งในห้อง <#{ROLE_COMMAND_CHANNEL_ID}> เท่านั้น\n\n"
                "`/ย้ายยศ user:@ชื่อ role:@Role`\n\n"
                "ตัวอย่าง:\n`/ย้ายยศ @โจ @VIP`"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="ระบบย้ายยศอัตโนมัติ")
        await guide_channel.send(embed=embed)

# ================= CRASH LOG =================
async def send_crash_log(error_msg):
    """ส่งข้อความแจ้งบอทเกิด Error ไปที่ ADMIN_CHANNEL_ID"""
    await bot.wait_until_ready()
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(
            title="[ICON_PLACEHOLDER] Bot Crash/Error",  # ตรงนี้สำหรับใส่อิโมจิ
            description=error_msg,
            color=0xE74C3C
        )
        embed.set_footer(text=f"[ICON_PLACEHOLDER] {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")  # ตรงนี้สำหรับใส่อิโมจิ
        await admin_channel.send(embed=embed)

# ================= Modal ตอบกลับ =================
class ReplyModal(discord.ui.Modal, title="[ICON_PLACEHOLDER] ตอบกลับข้อความ"):  # ตรงนี้สำหรับใส่อิโมจิ
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
        reply_text = self.reply_input.value
        sender = await bot.fetch_user(self.sender_id)
        if sender:
            await sender.send(f"[ICON_PLACEHOLDER] คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")  # ตรงนี้สำหรับใส่อิโมจิ

        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)
        await interaction.response.send_message("[ICON_PLACEHOLDER] ส่งข้อความตอบกลับแล้ว!", ephemeral=True)  # ตรงนี้สำหรับใส่อิโมจิ

# ================= VIEW ปุ่ม =================
class ReplyView(discord.ui.View):
    """สร้างปุ่มตอบกลับใต้ข้อความฝากบอก"""
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label="[ICON_PLACEHOLDER] ตอบกลับ", style=discord.ButtonStyle.primary)  # ตรงนี้สำหรับใส่อิโมจิ
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("[ICON_PLACEHOLDER] ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)  # ตรงนี้สำหรับใส่อิโมจิ
        await interaction.response.send_modal(ReplyModal(self.sender_id, self.original_embed, self.original_message))

# ================= ฝากบอก Command =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)")
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    try:
        if interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("[ICON_PLACEHOLDER] ใช้คำสั่งนี้ได้เฉพาะ Server ที่กำหนด", ephemeral=True)  # ตรงนี้สำหรับใส่อิโมจิ
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("[ICON_PLACEHOLDER] ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)  # ตรงนี้สำหรับใส่อิโมจิ

        await interaction.response.defer(ephemeral=True)
        target_channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)

        embed = discord.Embed(
            title="[ICON_PLACEHOLDER] มีข้อความฝากบอกถึงคุณ",  # ตรงนี้สำหรับใส่อิโมจิ
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

        log_embed = discord.Embed(title="[ICON_PLACEHOLDER] ข้อความฝากบอกใหม่", color=0x1ABC9C)  # ตรงนี้สำหรับใส่อิโมจิ
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} (ไม่เปิดเผยตัวตน)", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f"[ICON_PLACEHOLDER] {datetime.now().
