import discord
from discord.ext import commands
import os
import asyncio

# ===== KEEP ALIVE =====
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home():
    return "Alive"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    Thread(target=run).start()

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

config = {
    "CATEGORY_ID": None,
    "STAFF_ROLE_ID": None,
    "ALLOWED_ROLE_ID": None,
    "LOG_CHANNEL_ID": None
}

# ================= CLAIM =================
class ClaimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.blurple)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        staff_role = interaction.guild.get_role(config["STAFF_ROLE_ID"])

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only staff", ephemeral=True)
            return

        await interaction.channel.edit(name=f"claimed-by-{interaction.user.name}")

        embed = interaction.message.embeds[0]
        embed.set_footer(text=f"Claimed by: {interaction.user.name}")

        button.disabled = True
        button.label = "Claimed"

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Claimed", ephemeral=True)


# ================= MODAL =================
class TicketModal(discord.ui.Modal, title="Trade Ticket Form"):

    other = discord.ui.TextInput(label="Other trader (username or ID)")
    giving = discord.ui.TextInput(label="What are you giving?")
    receiving = discord.ui.TextInput(label="What are you receiving?")

    async def on_submit(self, interaction: discord.Interaction):

        try:
            guild = interaction.guild

            if not config["CATEGORY_ID"]:
                await interaction.response.send_message("❌ Category not set (!category)", ephemeral=True)
                return

            user_input = self.other.value.strip()

            # ===== FIXED USER FIND =====
            other_user = None

            if user_input.isdigit():
                other_user = guild.get_member(int(user_input))
                if not other_user:
                    other_user = await bot.fetch_user(int(user_input))
            else:
                other_user = discord.utils.find(
                    lambda m: m.name.lower() == user_input.lower(),
                    guild.members
                )

            if not other_user:
                await interaction.response.send_message("❌ User not found", ephemeral=True)
                return

            category = guild.get_channel(config["CATEGORY_ID"])

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True),
                guild.get_role(config["STAFF_ROLE_ID"]): discord.PermissionOverwrite(view_channel=True)
            }

            # only add if member exists in server
            if isinstance(other_user, discord.Member):
                overwrites[other_user] = discord.PermissionOverwrite(view_channel=True)

            channel = await guild.create_text_channel(
                name=f"sab-ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(title="📩 New Trade Ticket", color=0xff9900)
            embed.add_field(name="Creator", value=interaction.user.mention, inline=False)
            embed.add_field(name="Other Trader", value=str(other_user), inline=False)
            embed.add_field(name="Giving", value=self.giving.value, inline=True)
            embed.add_field(name="Receiving", value=self.receiving.value, inline=True)
            embed.set_footer(text="⏳ Waiting for middleman...")

            await channel.send(
                f"{interaction.user.mention} <@&{config['STAFF_ROLE_ID']}>",
                embed=embed,
                view=ClaimView()
            )

            await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# ================= DROPDOWN =================
class Dropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Blox Fruits"),
            discord.SelectOption(label="Steal a Brainrot"),
            discord.SelectOption(label="Escape Tsunami"),
            discord.SelectOption(label="Other"),
        ]
        super().__init__(placeholder="Select ticket type", options=options)

    async def callback(self, interaction: discord.Interaction):

        role = interaction.guild.get_role(config["ALLOWED_ROLE_ID"])

        if role and role not in interaction.user.roles:
            await interaction.response.send_message("❌ Not allowed", ephemeral=True)
            return

        await interaction.response.send_modal(TicketModal())


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Dropdown())


# ================= PANEL =================
@bot.command()
async def panel(ctx):

    embed = discord.Embed(
        title="🎫 Middleman Ticket Panel",
        description="""
Need a trusted middleman for your trade or deal?
Open a ticket below and our verified Middlemen will assist you safely and quickly.

📜 Rules before opening a ticket:
• Do not ping or DM staff or middlemen directly.
• Open **one ticket at a time** for each deal.
• Provide clear proof and details of your trade.
• Any attempt to scam or waste time will result in a ban.

Click the button below to open a ticket!

🎯 We ensure safe, fast, and verified transactions for everyone.
        """,
        color=0xff6600
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1457964741745180785/1491392888469454879/file_00000000f0607208b08ba98abf46985f.png")

    await ctx.send(embed=embed, view=PanelView())


# ================= COMMANDS =================
@bot.command()
async def category(ctx, id: int):
    config["CATEGORY_ID"] = id
    await ctx.send("✅ Category set")

@bot.command()
async def staffrole(ctx, id: int):
    config["STAFF_ROLE_ID"] = id
    await ctx.send("✅ Staff role set")

@bot.command()
async def supportedrole(ctx, id: int):
    config["ALLOWED_ROLE_ID"] = id
    await ctx.send("✅ Allowed role set")

@bot.command()
async def log(ctx, id: int):
    config["LOG_CHANNEL_ID"] = id
    await ctx.send("✅ Log channel set")

@bot.command()
async def help(ctx):
    await ctx.send("""
!panel
!category <id>
!staffrole <id>
!supportedrole <id>
!log <id>
/closeticket
    """)

# ================= CLOSE =================
@bot.tree.command(name="closeticket")
async def closeticket(interaction: discord.Interaction):

    staff = interaction.guild.get_role(config["STAFF_ROLE_ID"])

    if not staff or staff not in interaction.user.roles:
        await interaction.response.send_message("❌ Only staff", ephemeral=True)
        return

    await interaction.response.send_message("🔒 Closing...", ephemeral=True)
    await asyncio.sleep(2)
    await interaction.channel.delete()


# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# ================= START =================
keep_alive()
bot.run(os.getenv("TOKEN"))