import os
import threading
from datetime import datetime
from flask import Flask
import discord
from discord.ext import commands

# ================= Flask =================
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    t = threading.Thread(target=run)
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
        placeholder="พิมพ์ข้อความที่อยากบอกผู้รับ"
    )
    reveal = discord.ui.TextInput(
        label="เปิดเผยตัวตน?",
        style=discord.TextStyle.short,
        required=False,
        placeholder="พิมพ์ 'ใช่' ถ้าอยากเปิดเผย (ถ้าเว้นว่าง = ไม่เปิดเผย)"
    )

    def __init__(self, target_member: discord.Member):
        super().__init__()
        self.target_member = target_member

    async def on_submit(self, interaction: discord.Interaction):
        await send_message(interaction, self.user_message.value, self.reveal.value, self.target_member)

# ================= Modal ตอบกลับ =================
class ReplyModal(discord.ui.Modal, title="ตอบกลับข้อความ"):
    reply_message = discord.ui.TextInput(
        label="ข้อความตอบกลับ",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="พิมพ์ข้อความตอบกลับ"
    )

    def __init__(self, sender: discord.Member):
        super().__init__()
        self.sender = sender

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.sender.send(
                f"📩 {interaction.user.display_name} ตอบกลับข้อความของคุณ:\n\n{self.reply_message.value}"
            )
            await interaction.response.send_message("✅ ส่งข้อความตอบกลับสำเร็จ", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ไม่สามารถส่ง DM หาผู้ส่งได้", ephemeral=True)

# ================= ฟังก์ชันส่งข้อความ =================
async def send_message(interaction, user_message, reveal, target_member):
    guild = interaction.guild
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)

    sender_name = interaction.user.display_name if reveal.strip().lower() == "ใช่" else "ไม่เปิดเผยตัวตน"

    # Embed ฝากบอก
    embed = discord.Embed(
        title=f"💌 ข้อความถึง {target_member.display_name}",
        description=user_message,
        color=0x2ECC71
    )
    embed.add_field(name="จาก", value=sender_name, inline=False)
    embed.set_footer(text="ฝากบอกโดยระบบ")

    # ปุ่มตอบกลับ
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(label="💬 ตอบกลับ", style=discord.ButtonStyle.primary, custom_id=f"reply_{interaction.user.id}")
    )

    # ส่งไปยัง target
    await target_channel.send(content=f"{target_member.mention}", embed=embed, view=view)

    # Embed แอดมิน
    now = datetime.now().strftime("%d/%m/%Y เวลา %H:%M")
    admin_embed = discord.Embed(title="📩 ข้อความฝากบอกใหม่", color=0x5865F2)
    admin_embed.add_field(name="ผู้ส่ง", value=f"{interaction.user.mention} ({sender_name})", inline=False)
    admin_embed.add_field(name="ผู้รับ", value=f"{target_member.mention} ({target_member.id})", inline=False)
    admin_embed.add_field(name="ข้อความ", value=user_message, inline=False)
    admin_embed.set_footer(text=f"📅 {now}")
    await admin_channel.send(embed=admin_embed)

    await interaction.response.send_message("✅ ฝากบอกสำเร็จ! ส่งเรียบร้อยแล้ว", ephemeral=True)

# ================= จัดการปุ่มตอบกลับ =================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id", "").startswith("reply_"):
            sender_id = int(interaction.data["custom_id"].split("_")[1])
            sender = interaction.guild.get_member(sender_id)
            if sender:
                await interaction.response.send_modal(ReplyModal(sender))
            else:
                await interaction.response.send_message("❌ ไม่พบผู้ส่ง", ephemeral=True)

# ================= Modal ค้นหาผู้รับ =================
class SearchMemberModal(discord.ui.Modal, title="ค้นหาผู้รับข้อความ"):
    search_name = discord.ui.TextInput(
        label="พิมพ์ชื่อผู้รับ",
        style=discord.TextStyle.short,
        required=True,
        placeholder="ชื่อผู้ใช้หรือ nickname"
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
                super().__init__(placeholder="🟢 เลือกผู้รับ", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                member_id = int(self.values[0])
                target_member = guild.get_member(member_id)
                if target_member:
                    await select_interaction.response.send_modal(MessageModal(target_member))
                else:
                    await select_interaction.response.send_message("❌ ไม่พบผู้รับ", ephemeral=True)

        view = discord.ui.View()
        view.add_item(MemberSelect(matched_members))
        await interaction.response.send_message("เลือกผู้รับจากผลลัพธ์:", view=view, ephemeral=True)

# ================= Button =================
class OpenButton(discord.ui.View):
    @discord.ui.button(label="📝 เขียนข้อความ", style=discord.ButtonStyle.success)
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
        embed = discord.Embed(
            title="💌 ฝากบอก",
            description="อยากบอกอะไรกับใคร กดปุ่มด้านล่างแล้วเริ่มเลย!",
            color=0x2ECC71
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1406523355460272208/1406982406258298930/ggt.png?ex=68a471fa&is=68a3207a&hm=fc6df791cddc887bde522e0b02b06750ba90f6d5ecbdbbf5003970189e63da85&")  # <- ใส่ banner ได้
        await channel.send(embed=embed, view=OpenButton())

# ================= Run Bot =================
keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
