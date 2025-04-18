import os
import discord
import logging
from dotenv import load_dotenv
from discord.ext import commands
from utils.GoogleForm import GoogleFormHandler
from utils.database import DatabaseHandler
import asyncio

# Load environment variables
load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    raise error

db = DatabaseHandler()
form_handler = GoogleFormHandler()

class GoogleFormManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="add_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), commands.has_permissions(manage_guild=True))
    async def add_gform_url(self, ctx: commands.Context, url: str):
        """Add/update Google Form URL for the guild"""
        if not url.startswith(("https://docs.google.com/forms/", "https://forms.gle/")):
            await ctx.send("❌ That doesn't look like a Google Form link.")
            return

        success = db.upsert_guild_form_url(ctx.guild.id, url)
        await ctx.send("✅ Google Form URL saved!" if success else "⚠️ Database error")

    @commands.command(name="delete_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), commands.has_permissions(manage_guild=True))
    async def delete_gform_url(self, ctx: commands.Context):
        """Remove Google Form URL for the guild"""
        success = db.delete_guild_form_url(ctx.guild.id)
        await ctx.send("🗑️ URL deleted" if success else "ℹ️ No URL set" if db.get_guild_form_url(ctx.guild.id) is None else "⚠️ Error")

    @commands.command(name="list_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), commands.has_permissions(manage_guild=True))
    async def list_gform_url(self, ctx: commands.Context):
        """List current Google Form URL"""
        form_url = db.get_guild_form_url(ctx.guild.id)
        await ctx.send(f"Current URL: {form_url}" if form_url else "No URL configured")
        
    @commands.command(name="help")
    @commands.check_any(commands.has_permissions(administrator=True), commands.has_permissions(manage_guild=True))
    async def help(self, ctx: commands.Context):
        """List command"""
        help_text = (
            "**📜 Available Commands:**\n"
            "1. `!add_gform_url <link>` — Add a new Google Form URL\n"
            "2. `!delete_gform_url` — Delete the existing Google Form URL\n"
            "3. `!list_gform_url` — Show the current Google Form URL\n"
            "4. `!hadir` — Mark your attendance\n"
        )
        await ctx.send(help_text)


@bot.command()
async def hadir(ctx):
    """Mark daily attendance"""
    user = ctx.author
    guild_id = ctx.guild.id
    
    # Get stored form URL
    form_url = db.get_guild_form_url(guild_id)
    if not form_url:
        await ctx.send("❌ No Google Form configured")
        return

    # Process attendance
    try:
        if db.check_hadir(guild_id, user.id):
            # Extract form URLs
            view_url, post_url = form_handler.extract_urls(form_url)
            if not view_url or not post_url:
                raise ValueError("Invalid form URL structure")

            # Get form fields
            form_data = form_handler.fetch_form_data(view_url)
            if not form_data:
                raise ValueError("Failed to fetch form data")

            # Prepare submission
            entry_ids = list(GoogleFormHandler.get_entry_ids(form_data))
            if not entry_ids:
                raise ValueError("No form fields found")

            submission_data = {"entry." + str(entry_ids[0]): user.display_name}
            if form_handler.submit_response(post_url, submission_data):
                await ctx.send(f"{user.mention} Hadir recorded! ✅")
            else:
                logger.error("⚠️ Form submission failed")

    except Exception as e:
        logger.error(f"Attendance error: {e}")


@bot.event
async def on_ready():
    logger.info("Bot is ready.")

async def main():
    async with bot:
        await bot.add_cog(GoogleFormManager(bot))
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())