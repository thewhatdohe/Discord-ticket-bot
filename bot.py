import discord
from discord.ext import commands
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== CONFIG =====
config = {
    "CATEGORY_ID": None,
    "STAFF_ROLE_ID": None,
    "ALLOWED_ROLE_ID": None,
    "LOG_CHANNEL_ID": None
}


# ================= CLAIM BUTTON =================
class ClaimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.green)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        staff_role = interaction.guild.get_role(config["STAFF_ROLE_ID"])

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only staff!", ephemeral=True)
            return

        await interaction.channel.edit(name=f"claimed-by-{interaction.user.name}")

        button.label = f"Claimed by {interaction.user.name}"
        button.disabled = True

        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ Ticket claimed!", ephemeral=True)


# ================= MODAL =================
class TicketModal(discord.ui.Modal, title="SAB Ticket Form"):

    user_id = discord.ui.TextInput(label="Other Trader (mention or ID)")
    trade = discord.ui.TextInput(label="What are you giving?", style=discord.TextStyle.paragraph)
    tip = discord.ui.TextInput(label="Tip")

    def __init__(self, category_name):
        super().__init__()
        self.category_name = category_name

    async def on_submit(self, interaction: discord.Interaction):

        if None in config.values():
            await interaction.response.send_message("❌ Setup not done. Use /setpanel", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(config["CATEGORY_ID"])

        # ===== USER PARSE =====
        val = self.user_id.value.replace("<@", "").replace(">", "").replace("!", "")
        other_user = guild.get_member(int(val)) if val.isdigit() else None

        if not other_user:
            await interaction.response.send_message("❌ Invalid user ID/mention", ephemeral=True)
            return

        # ===== CREATE CHANNEL =====
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            other_user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(config["STAFF_ROLE_ID"]): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name="sab-ticket",
            category=category,
            overwrites=overwrites
        )

        # ===== EMBED =====
        embed = discord.Embed(title="📩 SAB TICKET", color=0x2ecc71)
        embed.add_field(name="Creator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Other Trader", value=other_user.mention, inline=False)
        embed.add_field(name="Giving", value=self.trade.value, inline=True)
        embed.add_field(name="Tip", value=self.tip.value, inline=True)
        embed.set_footer(text="⏳ Waiting for middleman...")

        await channel.send(
            f"{interaction.user.mention} {other_user.mention} <@&{config['STAFF_ROLE_ID']}>",
            embed=embed,
            view=ClaimView()
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        # ===== AUTO CLOSE AFTER 100 MIN =====
        await asyncio.sleep(6000)

        if channel:
            log_channel = guild.get_channel(config["LOG_CHANNEL_ID"])

            messages = []
            async for msg in channel.history(limit=100):
                messages.append(f"{msg.author}: {msg.content}")

            transcript = "\n".join(messages)

            if log_channel:
                file = discord.File(
                    fp=bytes(transcript, "utf-8"),
                    filename=f"{channel.name}.txt"
                )
                await log_channel.send(f"📁 Ticket Closed: {channel.name}", file=file)

            await channel.delete()


# ================= DROPDOWN =================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Blox Fruits"),
            discord.SelectOption(label="Steal a Brainrot"),
            discord.SelectOption(label="Escape Tsunami"),
            discord.SelectOption(label="Other"),
        ]
        super().__init__(placeholder="Select ticket type...", options=options)

    async def callback(self, interaction: discord.Interaction):

        role = interaction.guild.get_role(config["ALLOWED_ROLE_ID"])

        if role not in interaction.user.roles:
            await interaction.response.send_message("❌ Not allowed", ephemeral=True)
            return

        await interaction.response.send_modal(TicketModal(self.values[0]))


# ================= VIEW =================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# ================= SLASH SETUP =================
@bot.tree.command(name="setpanel", description="Setup ticket system")
async def setpanel(interaction: discord.Interaction,
                   category: discord.CategoryChannel,
                   staff_role: discord.Role,
                   allowed_role: discord.Role,
                   log_channel: discord.TextChannel):

    config["CATEGORY_ID"] = category.id
    config["STAFF_ROLE_ID"] = staff_role.id
    config["ALLOWED_ROLE_ID"] = allowed_role.id
    config["LOG_CHANNEL_ID"] = log_channel.id

    await interaction.response.send_message("✅ Setup complete!", ephemeral=True)


# ================= PANEL =================
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 SAB Ticket Panel",
        description="Select below to open ticket",
        color=0x2b2d31
    )
    await ctx.send(embed=embed, view=TicketView())


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


bot.run(os.getenv("TOKEN"))
