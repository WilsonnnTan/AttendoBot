import os
import discord
import logging
import asyncio
from dotenv import load_dotenv
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

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
form_handler = GoogleForm_Url_Handler()
db = DatabaseHandler()

@bot.command()
async def hadir(ctx):
    """Mark daily attendance"""
    user = ctx.author
    guild_id = ctx.guild.id
    
    # Get stored form URL
    form_url = db.get_guild_form_url(guild_id)
    tz = db.get_timezone(guild_id)
    if not form_url:
        return await ctx.send("❌ No Attendance configured")
        
    # Time-window check (GMT+7)
    record = db.get_attendance_window(guild_id)
    if record and record.get("day") is not None:
        jkt_tz = timezone(timedelta(hours=tz["time_delta"]))
        now = datetime.now(timezone.utc).astimezone(jkt_tz)
        today = now.isoweekday()            # 1=Mon … 7=Sun
        current_time = now.time()           # datetime.time

        # unpack window
        day        = record["day"]
        start_time = current_time.replace(hour=record["start_hour"], minute=record["start_minute"], second=0, microsecond=0)
        end_time   = current_time.replace(hour=record["end_hour"],   minute=record["end_minute"],   second=0, microsecond=0)

        # deny if wrong day or outside window
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
        # check_hadir returns True if we should post, False if already marked today
        if db.check_hadir(guild_id, user.id, form_url):
            # extract view & post URLs
            view_url, post_url = form_handler.extract_urls(form_url)
            if not view_url or not post_url:
                raise ValueError("Invalid form URL structure")

            # fetch form data & IDs
            form_data = form_handler.fetch_form_data(view_url)
            if not form_data:
                raise ValueError("Failed to fetch form data")
            entry_ids = list(form_handler.get_entry_ids(form_data))
            if not entry_ids:
                raise ValueError("No form fields found")

            # submit with the first field = display_name
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