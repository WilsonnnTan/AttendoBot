import os
import discord
import logging
from dotenv import load_dotenv
from discord.ext import commands
from utils.GoogleForm import GoogleForm_Url_Handler, GoogleFormManager
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
db = DatabaseHandler()

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
        if db.check_hadir(guild_id, user.id, form_url):
            # Extract form URLs
            view_url, post_url = GoogleForm_Url_Handler.extract_urls(form_url)
            if not view_url or not post_url:
                raise ValueError("Invalid form URL structure")

            # Get form fields
            form_data = GoogleForm_Url_Handler.fetch_form_data(view_url)
            if not form_data:
                raise ValueError("Failed to fetch form data")

            # Prepare submission
            entry_ids = list(GoogleForm_Url_Handler.get_entry_ids(form_data))
            if not entry_ids:
                raise ValueError("No form fields found")

            submission_data = {"entry." + str(entry_ids[0]): user.display_name}
            if GoogleForm_Url_Handler.submit_response(post_url, submission_data):
                await ctx.send(f"{user.mention} Hadir recorded! ✅")
            else:
                logger.error("⚠️ Form submission failed")

    except Exception as e:
        logger.error(f"Attendance error: {e}")
        
        
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    raise error

@bot.event
async def on_ready():
    logger.info("Bot is ready.")

async def main():
    async with bot:
        await bot.add_cog(GoogleFormManager(bot))
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())