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
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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

        if staff_role not in interaction.user.roles:
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

        guild = interaction.guild
        user_input = self.other.value

        other_user = None

        if user_input.isdigit():
            other_user = guild.get_member(int(user_input))
        else:
            for member in guild.members:
                if member.name.lower() == user_input.lower():
                    other_user = member
                    break

        if not other_user:
            await interaction.response.send_message("❌ User not found", ephemeral=True)
            return

        category = guild.get_channel(config["CATEGORY_ID"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            other_user: discord.PermissionOverwrite(view_channel=True),
            guild.get_role(config["STAFF_ROLE_ID"]): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name="sab-ticket",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(title="📩 New Trade Ticket", color=0xff9900)
        embed.add_field(name="Creator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Other Trader", value=other_user.mention, inline=False)
        embed.add_field(name="Giving", value=self.giving.value, inline=True)
        embed.add_field(name="Receiving", value=self.receiving.value, inline=True)
        embed.set_footer(text="⏳ Waiting for middleman...")

        await channel.send(
            f"{interaction.user.mention} {other_user.mention} <@&{config['STAFF_ROLE_ID']}>",
            embed=embed,
            view=ClaimView()
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


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


# ================= COMMANDS =================

# PANEL
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 Middleman Ticket Panel",
        description="Click below to open a ticket",
        color=0xff6600
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1457964741745180785/1491392888469454879/file_00000000f0607208b08ba98abf46985f.png")

    await ctx.send(embed=embed, view=PanelView())


# SET CATEGORY
@bot.command()
async def category(ctx, category_id: int):
    config["CATEGORY_ID"] = category_id
    await ctx.send("✅ Category set")


# SET ROLES
@bot.command()
async def supportedrole(ctx, role_id: int):
    config["ALLOWED_ROLE_ID"] = role_id
    await ctx.send("✅ Supported role set")


@bot.command()
async def staffrole(ctx, role_id: int):
    config["STAFF_ROLE_ID"] = role_id
    await ctx.send("✅ Staff role set")


# SET LOG
@bot.command()
async def log(ctx, channel_id: int):
    config["LOG_CHANNEL_ID"] = channel_id
    await ctx.send("✅ Log channel set")


# HELP COMMAND
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 Bot Commands", color=0x3498db)

    embed.add_field(name="!panel", value="Send ticket panel", inline=False)
    embed.add_field(name="!category <id>", value="Set ticket category", inline=False)
    embed.add_field(name="!supportedrole <id>", value="Set allowed role", inline=False)
    embed.add_field(name="!staffrole <id>", value="Set staff role", inline=False)
    embed.add_field(name="!log <id>", value="Set log channel", inline=False)
    embed.add_field(name="/closeticket", value="Close ticket (staff only)", inline=False)

    await ctx.send(embed=embed)


# CLOSE
@bot.tree.command(name="closeticket")
async def closeticket(interaction: discord.Interaction):

    staff_role = interaction.guild.get_role(config["STAFF_ROLE_ID"])

    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Only staff", ephemeral=True)
        return

    await interaction.response.send_message("🔒 Closing...", ephemeral=True)

    messages = []
    async for msg in interaction.channel.history(limit=200):
        messages.append(f"{msg.author}: {msg.content}")

    transcript = "\n".join(messages)

    log_channel = interaction.guild.get_channel(config["LOG_CHANNEL_ID"])

    if log_channel:
        file = discord.File(
            fp=bytes(transcript, "utf-8"),
            filename=f"{interaction.channel.name}.txt"
        )
        await log_channel.send(f"📁 Ticket closed: {interaction.channel.name}", file=file)

    await asyncio.sleep(2)
    await interaction.channel.delete()


# READY
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# START
keep_alive()
bot.run(os.getenv("TOKEN"))