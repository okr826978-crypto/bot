import os
import discord
from discord import app_commands
from datetime import datetime
from aiohttp import web
import asyncio

# ================= CONFIG =================
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
intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ================= ฟังก์ชัน =================
async def send_guide():
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title="🌅 วิธีใช้คำสั่งฝากบอก",
            description="ใช้คำสั่ง:\n`/ฝากบอก user:@ชื่อ message:ข้อความ hint:คำใบ้`\n\n"
                        "ตัวอย่าง: `/ฝากบอก @โจ วันนี้เจอกันหน่อย hint:เรื่องงาน`",
            color=0x5865F2
        )
        embed.set_footer(text="📬 ระบบฝากบอกอัตโนมัติ")
        await guide_channel.send(embed=embed)

async def send_role_guide():
    await bot.wait_until_ready()
    guide_channel = bot.get_channel(ROLE_GUIDE_CHANNEL_ID)
    if guide_channel:
        await guide_channel.purge(limit=100)
        embed = discord.Embed(
            title="🌅 วิธีใช้คำสั่งย้ายยศ",
            description=(f"ใช้คำสั่งในห้อง <#{ROLE_COMMAND_CHANNEL_ID}> เท่านั้น\n\n"
                         "`/ย้ายยศ user:@ชื่อ role:@Role duration:เวลา`\n\n"
                         "ตัวอย่าง:\n`/ย้ายยศ @โจ @VIP 10m`\n`/ย้ายยศ @โจ @VIP`"),
            color=0x5865F2
        )
        embed.set_footer(text="📬 ระบบย้ายยศอัตโนมัติ")
        await guide_channel.send(embed=embed)

async def send_crash_log(error_msg):
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

# ================= Modal ตอบกลับ =================
class ReplyModal(discord.ui.Modal, title="💬 ตอบกลับข้อความ"):
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
            await sender.send(f"💌 คุณได้รับข้อความใหม่จาก {interaction.user.display_name}:\n\n{reply_text}")

        updated_embed = self.original_embed.copy()
        updated_embed.add_field(name="ข้อความตอบกลับ", value=reply_text, inline=False)
        await self.original_message.edit(embed=updated_embed, view=None)
        await interaction.response.send_message("💬 ส่งข้อความตอบกลับแล้ว!", ephemeral=True)

class ReplyView(discord.ui.View):
    def __init__(self, sender_id, original_embed, original_message):
        super().__init__(timeout=None)
        self.sender_id = sender_id
        self.original_embed = original_embed
        self.original_message = original_message

    @discord.ui.button(label="💬 ตอบกลับ", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("💬 ใช้ปุ่มนี้ได้เฉพาะในห้องฝากบอก", ephemeral=True)
        await interaction.response.send_modal(ReplyModal(self.sender_id, self.original_embed, self.original_message))

# ================= คำสั่ง =================
@tree.command(name="ฝากบอก", description="ฝากข้อความถึงใครบางคน (ไม่เปิดเผยตัวตน)", guild=discord.Object(id=GUILD_ID))
async def send_message(interaction: discord.Interaction, user: discord.Member, message: str, hint: str = "ไม่มี"):
    try:
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("🚫 ใช้ได้เฉพาะในห้องฝากบอก", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        target_channel = interaction.guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)

        embed = discord.Embed(
            title="📬 มีข้อความฝากบอกถึงคุณ",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        embed.add_field(name="ข้อความ", value=message, inline=False)
        embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        embed.set_footer(text="📬 ระบบฝากบอกอัตโนมัติ")

        msg_sent = await target_channel.send(content=f"{user.mention}", embed=embed)
        view = ReplyView(sender_id=interaction.user.id, original_embed=embed, original_message=msg_sent)
        await msg_sent.edit(view=view)

        try:
            await user.send(embed=embed, view=view)
        except:
            pass

        log_embed = discord.Embed(title="📬 ข้อความฝากบอกใหม่", color=0x1ABC9C)
        log_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention}", inline=False)
        log_embed.add_field(name="ผู้รับ", value=f"{user.mention} ({user.id})", inline=False)
        log_embed.add_field(name="ข้อความ", value=message, inline=False)
        log_embed.add_field(name="คำใบ้", value=hint if hint else "ไม่มี", inline=False)
        log_embed.set_footer(text=f"📬 {datetime.now().strftime('%d/%m/%Y เวลา %H:%M')}")
        await admin_channel.send(embed=log_embed)

        await interaction.followup.send("✅ ฝากบอกสำเร็จ!", ephemeral=True)

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.followup.send("❌ เกิดข้อผิดพลาด", ephemeral=True)

@tree.command(name="ย้ายยศ", description="ให้สมาชิกย้ายยศกันเอง", guild=discord.Object(id=GUILD_ID))
async def move_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role, duration: str = None):
    try:
        if interaction.channel.id != ROLE_COMMAND_CHANNEL_ID:
            return await interaction.response.send_message("🚫 ใช้ได้เฉพาะในห้องคำสั่งยศ", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await user.add_roles(role)
        await interaction.followup.send(f"✅ เพิ่มยศ {role.name} ให้ {user.display_name}", ephemeral=True)

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
                await interaction.channel.send(f"⌛ หมดเวลา {duration} ยศ {role.name} ถูกลบจาก {user.display_name}")

            bot.loop.create_task(remove_role_later())

    except Exception as e:
        await send_crash_log(str(e))
        await interaction.followup.send("❌ เกิดข้อผิดพลาด", ephemeral=True)

# ================= WEB SERVER =================
async def start_webserver():
    async def handle(request):
        return web.Response(text="Bot is running ✅")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Web server started on port {PORT} ✅")

# ================= EVENT =================
@bot.event
async def on_ready():
    print(f"✅ Bot Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Jojo 💖"))

    await send_guide()
    await send_role_guide()

    try:
        guild = discord.Object(id=GUILD_ID)
        await tree.sync(guild=guild)   # sync ลง server
        await tree.sync()              # sync global (กันพลาด)
        print("✅ Slash commands synced.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    bot.loop.create_task(start_webserver())

# ================= RUN =================
bot.run(TOKEN)
