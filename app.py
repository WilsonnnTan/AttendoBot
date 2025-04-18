# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
"""
Main entry point for the Discord Attendance Bot.
Handles bot initialization, command registration, and event listeners.
"""

import os
import discord
import logging
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from utils.GoogleForm import GoogleForm_Url_Handler, GoogleFormManager
from utils.database import DatabaseHandler
from datetime import datetime, timezone, timedelta

# Load environment variables from .env file
load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configure logging for the application
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Discord bot and supporting handlers
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
form_handler = GoogleForm_Url_Handler()
db = DatabaseHandler()

@bot.command()
async def hadir(ctx):
    """
    Command for users to mark their daily attendance.
    Checks time window, prevents duplicate attendance, and submits the user's name to the configured Google Form.
    """
    user = ctx.author
    guild_id = ctx.guild.id
    
    # Retrieve the configured Google Form URL and timezone for this guild
    form_url = db.get_guild_form_url(guild_id)
    tz = db.get_timezone(guild_id)
    if not form_url:
        return await ctx.send("❌ No Attendance configured")
        
    # Check if attendance is within the allowed time window (if configured)
    record = db.get_attendance_window(guild_id)
    if record and record.get("day") is not None:
        jkt_tz = timezone(timedelta(hours=tz["time_delta"]))
        now = datetime.now(timezone.utc).astimezone(jkt_tz)
        today = now.isoweekday()            # 1=Mon … 7=Sun
        current_time = now.time()           # datetime.time

        # Attendance window unpacking
        day        = record["day"]
        start_time = current_time.replace(hour=record["start_hour"], minute=record["start_minute"], second=0, microsecond=0)
        end_time   = current_time.replace(hour=record["end_hour"],   minute=record["end_minute"],   second=0, microsecond=0)

        # Deny attendance if not the correct day or outside of allowed hours
        if today != day or not (start_time <= current_time <= end_time):
            weekdays = {
                1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
                4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'
            }
            display_day = weekdays.get(day, f"Day {day}")
            return await ctx.send(
                f"{user.mention} ❌ Attendance denied."
            )

    # Process attendance (only if within window or no window set)
    try:
        # db.check_hadir returns True if attendance should be marked, False if already marked today
        if db.check_hadir(guild_id, user.id, form_url):
            # Extract Google Form URLs
            view_url, post_url = form_handler.extract_urls(form_url)
            if not view_url or not post_url:
                raise ValueError("Invalid form URL structure")

            # Fetch Google Form data and field IDs
            form_data = form_handler.fetch_form_data(view_url)
            if not form_data:
                raise ValueError("Failed to fetch form data")
            entry_ids = list(form_handler.get_entry_ids(form_data))
            if not entry_ids:
                raise ValueError("No form fields found")

            # Submit attendance with user's display name
            submission_data = {f"entry.{entry_ids[0]}": user.display_name}
            if form_handler.submit_response(post_url, submission_data):
                return await ctx.send(f"{user.mention} Hadir recorded! ✅")
            else:
                logger.error("⚠️ Form submission failed")

        else:
            await ctx.send(f"{user.mention} You've already marked attendance today.")
    except Exception as e:
        logger.error(f"Attendance error: {e}")
        await ctx.send("⚠️ An error occurred while recording attendance.")
        
        
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """
    Global error handler for command errors.
    Notifies users if they lack permissions, otherwise re-raises the error.
    """
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    raise error

@bot.event
async def on_ready():
    """
    Event handler called when the bot has connected to Discord and is ready.
    """
    logger.info("Bot is ready.")

async def main():
    """
    Main asynchronous entry point for starting the bot.
    Loads the GoogleFormManager cog and starts the bot event loop.
    """
    async with bot:
        await bot.add_cog(GoogleFormManager(bot))
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    # Run the bot only if this script is executed directly
    asyncio.run(main())