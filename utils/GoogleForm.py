import re
from datetime import time
import json
import requests
import logging
from discord.ext import commands
from utils.database import DatabaseHandler


db = DatabaseHandler()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GoogleForm_Url_Handler:
    """Handles Google Form interactions including URL extraction, data fetching, and submissions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_urls(self, url: str) -> tuple[str | None, str | None]:
        """
        Extracts both 'viewform' and 'formResponse' URLs from a Google Form link.
        
        Args:
            url (str): Shortened or full Google Form URL
            
        Returns:
            tuple: (view_url, post_url) or (None, None) on failure
        """
        try:
            # Expand shortened URLs
            if "forms.gle" in url:
                response = requests.get(url, allow_redirects=True)
                url = response.url

            # Extract form ID
            match = re.search(r'/d/e/([a-zA-Z0-9_-]+)/viewform', url)
            if match:
                form_id = match.group(1)
                return (
                    f"https://docs.google.com/forms/d/e/{form_id}/viewform",
                    f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
                )
            self.logger.warning("Couldn't find Google Form ID in URL")
            return None, None
            
        except Exception as e:
            self.logger.error(f"URL extraction failed: {e}")
            return None, None

    def submit_response(self, post_url: str, data: dict) -> bool:
        """
        Submits data to Google Form.
        
        Args:
            post_url (str): Form's submission endpoint
            data (dict): Form data {field_id: value}
            
        Returns:
            bool: True if successful
        """
        try:
            response = requests.post(post_url, data=data, timeout=10)
            return response.ok
        except requests.RequestException as e:
            self.logger.error(f"Submission failed: {e}")
            return False

    def fetch_form_data(self, view_url: str) -> list | dict | None:
        """
        Fetches hidden configuration data from Google Form.
        
        Args:
            view_url (str): Form's viewform URL
            
        Returns:
            Parsed JSON data or None
        """
        try:
            response = requests.get(view_url, timeout=15)
            response.raise_for_status()
            match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', response.text, flags=re.S)
            return json.loads(match.group(1))
        except Exception as e:
            self.logger.error(f"Data fetch failed: {e}")
            return None

    @staticmethod
    def get_entry_ids(data: dict | list) -> iter:
        """
        Recursively finds all field IDs in form data.
        
        Args:
            data: Parsed FB_PUBLIC_LOAD_DATA_ structure
            
        Yields:
            int: Field entry IDs
        """
        if isinstance(data, dict):
            for v in data.values():
                yield from GoogleForm_Url_Handler.get_entry_ids(v)
        elif isinstance(data, list):
            if len(data) == 3 and data[1] is None:
                yield data[0]
            else:
                for item in data:
                    yield from GoogleForm_Url_Handler.get_entry_ids(item)


class GoogleFormManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="add_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), 
                        commands.has_permissions(manage_guild=True))
    async def add_gform_url(self, ctx: commands.Context, url: str):
        """Add/update Google Form URL for the guild"""
        if not url.startswith(("https://docs.google.com/forms/", "https://forms.gle/")):
            await ctx.send("❌ That doesn't look like a Google Form link.")
            return

        success = db.upsert_guild_form_url(ctx.guild.id, url)
        await ctx.send("✅ Google Form URL saved!" if success else "⚠️ Database error")


    @commands.command(name="delete_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), 
                        commands.has_permissions(manage_guild=True))
    async def delete_gform_url(self, ctx: commands.Context):
        """Remove Google Form URL for the guild"""
        success = db.delete_guild_form_url(ctx.guild.id)
        await ctx.send("🗑️ URL deleted" if success else "ℹ️ No URL set" if db.get_guild_form_url(ctx.guild.id) is None else "⚠️ Error")


    @commands.command(name="list_gform_url")
    @commands.check_any(commands.has_permissions(administrator=True), 
                        commands.has_permissions(manage_guild=True))
    async def list_gform_url(self, ctx: commands.Context):
        """List current Google Form URL"""
        form_url = db.get_guild_form_url(ctx.guild.id)
        await ctx.send(f"Current URL: {form_url}" if form_url else "No URL configured")
        
        
    # @commands.command(name="attendance_time")
    # @commands.check_any(commands.has_permissions(administrator=True),
    #                     commands.has_permissions(manage_guild=True))
    # async def attendance_time(self, ctx: commands.Context, schedule: str):
    #     """
    #     Set the weekly attendance window.
    #     Format: <day>/<HH:MM>-<HH:MM>
    #       • day: 1-7 (Monday=1 … Sunday=7) or full weekday name (e.g. Monday)
    #       • HH:MM: 24-hour time
    #     Example:
    #       • !attendance_time 1/08:00-09:00
    #       • !attendance_time Friday/18:45-20:00
    #     """
    #     # 1) Parse with regex
    #     pattern = (
    #         r'^(?P<day>\d{1}|[A-Za-z]+)'   # day part
    #         r'\/'
    #         r'(?P<h1>\d{1,2}):(?P<m1>\d{2})'  # start time
    #         r'-'
    #         r'(?P<h2>\d{1,2}):(?P<m2>\d{2})$' # end time
    #     )
    #     m = re.match(pattern, schedule)
    #     if not m:
    #         return await ctx.send(
    #             "❌ Invalid format! Use `day/HH:MM-HH:MM`, e.g. `3/14:30-15:30`."
    #         )

    #     # 2) Extract and validate
    #     day_raw = m.group('day')
    #     h1, m1 = int(m.group('h1')), int(m.group('m1'))
    #     h2, m2 = int(m.group('h2')), int(m.group('m2'))

    #     if not (0 <= h1 < 24 and 0 <= m1 < 60 and 0 <= h2 < 24 and 0 <= m2 < 60):
    #         return await ctx.send("❌ Hours must be 0-23 and minutes 0-59.")

    #     # Ensure start < end
    #     start = time(hour=h1, minute=m1)
    #     end   = time(hour=h2, minute=m2)
    #     if start >= end:
    #         return await ctx.send("❌ End time must be after start time.")

    #     # 3) Normalize day
    #     weekdays = {
    #         'monday': 1, 'tuesday': 2, 'wednesday': 3,
    #         'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 7
    #     }
    #     try:
    #         day = int(day_raw) if day_raw.isdigit() else weekdays[day_raw.lower()]
    #     except (ValueError, KeyError):
    #         return await ctx.send("❌ Day must be 1-7 or a weekday name (e.g. Monday).")
    #     if not (1 <= day <= 7):
    #         return await ctx.send("❌ Day number must be between 1 and 7.")

    #     # 4) Store into your DB (implement upsert_attendance_window yourself)
    #     success = db.upsert_attendance_window(
    #         guild_id=ctx.guild.id,
    #         day=day,
    #         start_hour=h1, start_minute=m1,
    #         end_hour=h2,   end_minute=m2
    #     )
    #     if not success:
    #         return await ctx.send("⚠️ Failed to save attendance window. Please try again.")

    #     # 5) Confirm back to user
    #     # capitalize weekday name if given, else map number back
    #     display_day = (
    #         list(weekdays.keys())[list(weekdays.values()).index(day)].capitalize()
    #         if day in weekdays.values() else f"Day {day}"
    #     )
    #     await ctx.send(
    #         f"✅ Attendance window set for **{display_day}** from **{h1:02d}:{m1:02d}** "
    #         f"to **{h2:02d}:{m2:02d}**."
    #     )

        
    @commands.command(name="help")
    @commands.check_any(commands.has_permissions(administrator=True), 
                        commands.has_permissions(manage_guild=True))
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
        
