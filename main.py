import discord
from discord.ext import commands
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==== CONFIG ====
BUTTON_CHANNEL_ID = 1406523355460272208
TARGET_CHANNEL_ID = 1406523340297863179
ADMIN_CHANNEL_ID = 1406528484066590822

# ================= Modal =================
class MessageModal(discord.ui.Modal, title="ฝากบอกข้อความ"):
    user_message = discord.ui.TextInput(
        label="ข้อความของคุณ",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="พิมพ์ข้อความที่อยากบอกผู้รับ"
    )
    reveal = discord.ui.TextInput(
        label="เปิดเผยตัวตน?",
        style=discord.TextStyle.short,
        required=False,
        placeholder="พิมพ์ 'ใช่' ถ้าต้องการแสดงชื่อ (ถ้าไม่พิมพ์ = ไม่เปิดเผย)"
    )

    def __init__(self, member_select: discord.ui.Select):
        super().__init__()
        self.member_select = member_select

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        target_channel = guild.get_channel(TARGET_CHANNEL_ID)
        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

        target_member = guild.get_member(int(self.member_select.values[0]))
        if target_member is None:
            await interaction.response.send_message("❌ ไม่พบผู้รับในเซิร์ฟเวอร์", ephemeral=True)
            return

        # เนื้อหาที่จะส่ง
        public_content = f"**ถึง {target_member.mention}**\n{self.user_message.value}"

        # ตอบกลับผู้ส่ง
        await interaction.response.send_message("✅ ฝากบอกสำเร็จ! ส่งเรียบร้อยแล้ว", ephemeral=True)

        # ส่งด้วย webhook (เปิดเผย / ไม่เปิดเผย)
        webhook = None
        try:
            if self.reveal.value.strip().lower() == "ใช่":
                webhook = await target_channel.create_webhook(
                    name=interaction.user.display_name,
                    avatar=await interaction.user.display_avatar.read()
                )
            else:
                webhook = await target_channel.create_webhook(name="Anonymous")

            await webhook.send(public_content)
        finally:
            if webhook:
                await webhook.delete()

        # DM ไปยังผู้รับ
        try:
            sender_name = interaction.user.display_name if self.reveal.value.strip().lower() == "ใช่" else "ไม่เปิดเผยตัวตน"
            dm_msg = f"คุณได้รับข้อความจาก {sender_name}:\n\n{self.user_message.value}"
            await target_member.send(dm_msg)
        except:
            await interaction.followup.send("⚠️ ไม่สามารถส่ง DM ให้ผู้รับได้", ephemeral=True)

        # แจ้งเตือนแอดมินแบบ Embed
        now = datetime.now().strftime("%d/%m/%Y เวลา %H:%M")
        embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x5865F2)
        embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="ผู้รับ", value=f"{target_member.mention} ({target_member.id})", inline=False)
        embed.add_field(name="ข้อความ", value=self.user_message.value, inline=False)
        embed.set_footer(text=f"📅 {now}")
        await admin_channel.send(embed=embed)

# ================= Select =================
class MemberSelect(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=member.display_name, 
                value=str(member.id),
                description=f"ส่งข้อความถึง {member.display_name}"
            )
            for member in members
        ]
        super().__init__(placeholder="🟢 เลือกคนที่คุณต้องการฝากบอก", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        modal = MessageModal(self)
        await interaction.response.send_modal(modal)

# ================= Button =================
class OpenButton(discord.ui.View):
    @discord.ui.button(label="📝 เขียนข้อความ", style=discord.ButtonStyle.success)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        members = [m for m in interaction.guild.members if not m.bot]
        dropdown = MemberSelect(members)
        view = discord.ui.View()
        view.add_item(dropdown)
        await interaction.response.send_message("📌 เลือกคนที่คุณอยากฝากบอก:", view=view, ephemeral=True)

# ================= Bot Events =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(BUTTON_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="💌 ฝากบอก",
            description="แอบมีอะไรอยู่ในใจ อยากบอกใคร ลองกระซิบดูสิ 👇",
            color=0x2ECC71
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/112233445566/123456789012345678/banner.png")  # <-- ใส่รูป banner ได้
        await channel.send(embed=embed, view=OpenButton())

bot.run("YOUR_BOT_TOKEN")
