"""
Main entry point for the Discord Attendance Bot.
Handles bot initialization, command registration, and event listeners.
"""
import os
import discord
import logging
import asyncio
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from utils.GoogleForm import GoogleForm_Url_Handler, GoogleFormManager
from utils.database import DatabaseHandler
from datetime import datetime, timezone, timedelta

# Load environment variables
load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot with intents and command tree
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = DatabaseHandler()
form_handler = GoogleForm_Url_Handler()

class Attendance(commands.Cog):
    """Cog for handling slash-based attendance commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hadir", description="Mark your daily attendance")
    async def hadir(self, interaction: discord.Interaction):
        """
        Command for users to mark their daily attendance.
        Checks time window, prevents duplicate attendance, and submits the user's name to the configured Google Form.
        """
        user = interaction.user
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "❌ This command must be used in a server.", ephemeral=True
            )

        guild_id = guild.id
        form_url = db.get_guild_form_url(guild_id)
        tz = db.get_timezone(guild_id)
        if not form_url:
            return await interaction.response.send_message(
                "❌ No attendance configured.", ephemeral=False
            )

        # Check time window if set
        record = db.get_attendance_window(guild_id)
        if record and record.get("day") is not None:
            jkt_tz = timezone(timedelta(hours=tz.get("time_delta", 0)))
            now = datetime.now(timezone.utc).astimezone(jkt_tz)
            today = now.isoweekday()
            current_time = now.time()

            start = current_time.replace(
                hour=record["start_hour"], minute=record["start_minute"], second=0, microsecond=0
            )
            end = current_time.replace(
                hour=record["end_hour"], minute=record["end_minute"], second=0, microsecond=0
            )

            if today != record["day"] or not (start <= current_time <= end):
                return await interaction.response.send_message(
                    f"{user.mention} ❌ Attendance denied.", ephemeral=False
                )

        # Process attendance
        try:
            if db.check_hadir(guild_id, user.id, form_url):
                view_url, post_url = form_handler.extract_urls(form_url)
                form_data = form_handler.fetch_form_data(view_url)
                entry_ids = list(form_handler.get_entry_ids(form_data))
                submission_data = {f"entry.{entry_ids[0]}": user.display_name}

                if form_handler.submit_response(post_url, submission_data):
                    return await interaction.response.send_message(
                        f"{user.mention} Hadir recorded! ✅",
                        ephemeral=False
                    )
                else:
                    logger.error("⚠️ Form submission failed")
                    return await interaction.response.send_message(
                        "⚠️ Failed to submit attendance.", ephemeral=True
                    )
            else:
                return await interaction.response.send_message(
                    f"{user.mention} You've already marked attendance today.", ephemeral=True
                )
        except Exception as e:
            logger.error(f"Attendance error: {e}")
            return await interaction.response.send_message(
                "⚠️ An error occurred while recording attendance.", ephemeral=True
            )

@bot.event
async def on_ready():
    """
    Event handler called when the bot has connected to Discord and is ready.
    Syncs slash commands to Discord.
    """
    logger.info("Bot is ready.")
    await bot.tree.sync()
    logger.info("Slash commands synced.")

async def main():
    """
    Main asynchronous entry point for starting the bot.
    Loads the Attendance Cog and GoogleFormManager, then starts the bot event loop.
    """
    async with bot:
        await bot.add_cog(Attendance(bot))
        await bot.add_cog(GoogleFormManager(bot))
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())