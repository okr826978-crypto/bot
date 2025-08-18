import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
from flask import Flask
from threading import Thread

# ================= Flask server =================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# รัน Flask server ใน Thread แยก
t = Thread(target=run)
t.start()

# ================= Discord Bot =================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==== CONFIG ====
BUTTON_CHANNEL_ID = 1406537337676103742
TARGET_CHANNEL_ID = 1406537424947122266
ADMIN_CHANNEL_ID = 1406539787594240041

# ================= Modal ฝากข้อความ =================
class MessageModal(discord.ui.Modal, title="ฝากบอกข้อความ"):
    user_message = discord.ui.TextInput(
        label="ข้อความของคุณ",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="พิมพ์ข้อความที่อยากบอกผู้รับ (คิดดีๆ ก่อนพิมพ์!)"
    )
    reveal = discord.ui.TextInput(
        label="เปิดเผยตัวตน?",
        style=discord.TextStyle.short,
        required=True,
        placeholder="พิมพ์ 'ใช่' ถ้าอยากแสดงชื่อ, 'ไม่' ถ้าไม่ต้องการ"
    )

    def __init__(self, target_member: discord.Member):
        super().__init__()
        self.target_member = target_member

    async def on_submit(self, interaction: discord.Interaction):
        view = ConfirmView(self.user_message.value, self.reveal.value, self.target_member)
        await interaction.response.send_message(
            f"คุณแน่ใจว่าจะส่งข้อความนี้ถึง {self.target_member.mention} หรือไม่?", 
            view=view,
            ephemeral=True
        )

# ================= View ยืนยัน =================
class ConfirmView(discord.ui.View):
    def __init__(self, message_text, reveal_text, target_member):
        super().__init__(timeout=60)
        self.message_text = message_text
        self.reveal_text = reveal_text
        self.target_member = target_member

    @discord.ui.button(label="✅ ใช่", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_message(interaction, self.message_text, self.reveal_text, self.target_member)
        self.stop()

    @discord.ui.button(label="❌ ไม่", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ ยกเลิกการส่งข้อความ", ephemeral=True)
        self.stop()

# ================= ฟังก์ชันส่งข้อความ =================
async def send_message(interaction, user_message, reveal, target_member):
    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    public_content = f"**ถึง {target_member.mention}**\n{user_message}"

    await interaction.response.send_message("✅ ฝากบอกสำเร็จ! ส่งเรียบร้อยแล้ว", ephemeral=True)

    # ส่ง Webhook
    webhook = None
    try:
        if reveal.strip().lower() == "ใช่":
            webhook = await target_channel.create_webhook(
                name=interaction.user.display_name,
                avatar=await interaction.user.display_avatar.read()
            )
        else:
            webhook = await target_channel.create_webhook(name="???")

        await webhook.send(public_content)
    finally:
        if webhook:
            await webhook.delete()

    # ส่ง DM
    try:
        sender_name = interaction.user.display_name if reveal.strip().lower() == 'ใช่' else "ไม่เปิดเผยตัวตน"
        await target_member.send(f"คุณได้รับข้อความจาก {sender_name}:\n\n{user_message}")
    except:
        await interaction.followup.send("⚠️ ไม่สามารถส่ง DM ให้ผู้รับได้", ephemeral=True)

    # ส่ง Embed แอดมิน
    now = datetime.now().strftime("%d/%m/%Y เวลา %H:%M")
    embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x1ABC9C)
    embed.add_field(
        name="ผู้ส่ง", 
        value=f"{interaction.user.mention} ({'เปิดเผย' if reveal.strip().lower() == 'ใช่' else 'ไม่เปิดเผย'})",
        inline=False
    )
    embed.add_field(name="ผู้รับ", value=f"{target_member.mention} ({target_member.id})", inline=False)
    embed.add_field(name="ข้อความ", value=user_message, inline=False)
    embed.set_footer(text=f"📅 {now}")
    await admin_channel.send(embed=embed)

# ================= Modal ใส่ชื่อผู้รับ =================
class SearchMemberModal(discord.ui.Modal, title="ค้นหาผู้รับข้อความ"):
    search_name = discord.ui.TextInput(
        label="พิมพ์ชื่อผู้รับ",
        style=discord.TextStyle.short,
        required=True,
        placeholder="พิมพ์ชื่อผู้ใช้หรือ nickname"
    )

    async def on_submit(self, interaction: discord.Interaction):
        name_query = self.search_name.value.lower()
        guild = interaction.guild
        matched_members = [m for m in guild.members if not m.bot and (name_query in m.display_name.lower() or name_query in m.name.lower())]

        if not matched_members:
            await interaction.response.send_message("❌ ไม่พบผู้ใช้ที่ตรงกัน", ephemeral=True)
            return

        class MemberSelect(discord.ui.Select):
            def __init__(self, members):
                options = [
                    discord.SelectOption(label=m.display_name[:45], value=str(m.id))
                    for m in members[:25]
                ]
                super().__init__(placeholder="เลือกผู้รับ", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                member_id = int(self.values[0])
                target_member = guild.get_member(member_id)
                if not target_member:
                    await select_interaction.response.send_message("❌ ไม่พบผู้รับ", ephemeral=True)
                    return
                await select_interaction.response.send_modal(MessageModal(target_member))

        view = discord.ui.View()
        view.add_item(MemberSelect(matched_members))
        await interaction.response.send_message("เลือกผู้รับจากผลลัพธ์:", view=view, ephemeral=True)

# ================= Button =================
class OpenButton(discord.ui.View):
    @discord.ui.button(label="📝 เขียนข้อความ", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchMemberModal())

# ================= Bot Events =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await send_button()

# ================= ส่งปุ่มอัตโนมัติ =================
async def send_button():
    await bot.wait_until_ready()
    channel = bot.get_channel(BUTTON_CHANNEL_ID)
    if channel:
        await channel.send("กดปุ่มเพื่อฝากบอกข้อความ 👇", view=OpenButton())

# ================= Run Bot =================
bot.run(os.environ["DISCORD_TOKEN"])
