# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
"""
Main entry point for the Discord Attendance Bot.
Handles bot initialization, command registration, and event listeners.
"""
import os
import discord
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
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

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # "Hadir" is Indonesian for "Present" (used for marking attendance).
    @app_commands.command(name="hadir", description="Mark your daily attendance")
    async def hadir(self, interaction: discord.Interaction) -> None:
        """
        Command for users to mark their daily attendance.
        Checks time window, prevents duplicate attendance, and submits the user's name to the configured Google Form.
        """
        # Defer early to prevent timeout
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        try:
            user = interaction.user
            guild = interaction.guild
            if guild is None:
                return await interaction.followup.send(
                    "❌ This command must be used in a server.", ephemeral=True
                )

            guild_id = guild.id
            form_url, entry_id_name = await db.get_guild_form_url_and_entry_id_name(guild_id)
            tz = await db.get_timezone(guild_id)
            if not form_url:
                return await interaction.followup.send(
                    "❌ No attendance configured.", ephemeral=True
                )

            # Check time window
            record = await db.get_attendance_window(guild_id)
            if record is not None and record.get("day") is not None:
                if tz is not None and "time_delta" in tz:
                    jkt_tz = timezone(timedelta(hours=tz["time_delta"]))
                else:
                    jkt_tz = timezone.utc
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
                    return await interaction.followup.send(
                        f"{user.mention} ❌ Attendance denied (Attendance period has ended).", ephemeral=True
                    )

            # Check if already marked
            check_marked = await db.check_attendance(guild_id, user.id, form_url)
            if not check_marked:
                return await interaction.followup.send(
                    f"{user.mention} You've already marked attendance today.", ephemeral=True
                )

            # Submit to form
            submission_data = {entry_id_name: user.display_name}
            submit_success = await form_handler.submit_response(form_url, submission_data)

            if submit_success:
                return await interaction.followup.send(
                    f"{user.mention} Attendance recorded! ✅", ephemeral=False
                )
            else:
                logger.error("⚠️ Form submission failed")
                return await interaction.followup.send(
                    "⚠️ Failed to submit attendance.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Attendance error: {e}")
            return await interaction.followup.send(
                "⚠️ An error occurred while recording attendance.", ephemeral=True
            )


@bot.event
async def on_ready() -> None:
    """
    Event handler called when the bot has connected to Discord and is ready.
    Syncs slash commands to Discord.
    """
    logger.info("Bot is ready.")
    await bot.tree.sync()
    logger.info("Slash commands synced.")

async def main() -> None:
    """
    Main asynchronous entry point for starting the bot.
    Loads the Attendance Cog and GoogleFormManager, then starts the bot event loop.
    """
    async with bot:
        await bot.add_cog(Attendance(bot))
        await bot.add_cog(GoogleFormManager(bot))
        if DISCORD_TOKEN is None:
            raise RuntimeError("DISCORD_TOKEN is not set")
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    # this code is for Limit the thread pool to 2 workers for a 2vCPU server
    # Normally this is not needed because mark attendance is a lightweight task
    # executor = ThreadPoolExecutor(max_workers=2)
    # loop = asyncio.get_event_loop()
    # loop.set_default_executor(executor)
    asyncio.run(main())