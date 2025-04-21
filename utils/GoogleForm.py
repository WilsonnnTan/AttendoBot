# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
import re
import pytz
import json
import requests
import logging
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import DatabaseHandler
from datetime import time


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
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # Permission error handler for all app commands in this Cog
        if isinstance(error, app_commands.errors.MissingPermissions):
            return await interaction.response.send_message("⚠️ No Administrator permission", ephemeral=True)
        # Optionally handle other errors or re-raise
        raise error

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add_gform_url", description="Add or update Google Form URL for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_gform_url(self, interaction: discord.Interaction, url: str):
        """
        Add/update Google Form URL for the guild.

        Example:
        /add_gform_url https://forms.gle/abc123def456
        """
        if not url.startswith(("https://docs.google.com/forms/", "https://forms.gle/")):
            await interaction.response.send_message("❌ That doesn't look like a Google Form link.", ephemeral=True)
            return

        success = db.upsert_guild_form_url(interaction.guild.id, url)
        tz = db.upsert_timezone(interaction.guild.id)
        await interaction.response.send_message("✅ Google Form URL saved!" if success and tz else "⚠️ Database error", ephemeral=True)


    @app_commands.command(name="delete_gform_url", description="Remove Google Form URL from the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_gform_url(self, interaction: discord.Interaction):
        """
        Remove Google Form URL from the guild.

        Example:
        /delete_gform_url
        """
        success = db.delete_guild_form_url(interaction.guild.id)
        await interaction.response.send_message("🗑️ URL deleted" if success else "No URL set" if db.get_guild_form_url(interaction.guild.id) is None else "⚠️ Error", ephemeral=True)


    @app_commands.command(name="list_gform_url", description="List current Google Form URL for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_gform_url(self, interaction: discord.Interaction):
        """
        List current Google Form URL for the guild.

        Example:
        /list_gform_url
        """
        form_url = db.get_guild_form_url(interaction.guild.id)
        await interaction.response.send_message(f"Current URL: {form_url}" if form_url else "No URL configured", ephemeral=True)
        
        
    @app_commands.command(name="set_attendance_time", description="Set the weekly attendance window. Format: <day>/<HH:MM>-<HH:MM>")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_attendance_time(self, interaction: discord.Interaction, schedule: str):
        """
        Set the weekly attendance window.
        Format: <day>/<HH:MM>-<HH:MM>

        Example:
        /set_attendance_time Friday/08:00-09:00
        /set_attendance_time 5/14:00-15:00
        """
        pattern = (
            r'^(?P<day>\d{1}|[A-Za-z]+)'   
            r'\/'
            r'(?P<h1>\d{1,2}):(?P<m1>\d{2})'
            r'-'
            r'(?P<h2>\d{1,2}):(?P<m2>\d{2})$'
        )
        m = re.match(pattern, schedule)
        if not m:
            return await interaction.response.send_message(
                "❌ Invalid format! Use `day/HH:MM-HH:MM`, e.g. `3/14:30-15:30`.", ephemeral=True
            )

        # Extract and validate
        day_raw = m.group('day')
        h1, m1 = int(m.group('h1')), int(m.group('m1'))
        h2, m2 = int(m.group('h2')), int(m.group('m2'))

        if not (0 <= h1 < 24 and 0 <= m1 < 60 and 0 <= h2 < 24 and 0 <= m2 < 60):
            return await interaction.response.send_message("❌ Hours must be 0-23 and minutes 0-59.", ephemeral=True)

        # Ensure start < end
        start = time(hour=h1, minute=m1)
        end   = time(hour=h2, minute=m2)
        if start >= end:
            return await interaction.response.send_message("❌ End time must be after start time.", ephemeral=True)

        # Normalize day
        weekdays = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 7
        }
        try:
            day = int(day_raw) if day_raw.isdigit() else weekdays[day_raw.lower()]
        except (ValueError, KeyError):
            return await interaction.response.send_message("❌ Day must be 1-7 or a weekday name (e.g. Monday).", ephemeral=True)
        
        if not (1 <= day <= 7):
            return await interaction.response.send_message("❌ Day number must be between 1 and 7.", ephemeral=True)

        # Save to DB
        success = db.upsert_attendance_window(
            guild_id=interaction.guild.id,
            day=day,
            start_hour=h1, start_minute=m1,
            end_hour=h2,   end_minute=m2
        )
        if not success:
            return await interaction.response.send_message("⚠️ Failed to save attendance Time. Please try again.", ephemeral=True)

        # Confirm back to user
        # capitalize weekday name if given, else map number back
        display_day = (
            list(weekdays.keys())[list(weekdays.values()).index(day)].capitalize()
            if day in weekdays.values() else f"Day {day}"
        )
        await interaction.response.send_message(
            f"✅ Attendance Time set for **{display_day}** from **{h1:02d}:{m1:02d}** "
            f"to **{h2:02d}:{m2:02d}**.",
            ephemeral=True
        )


    @app_commands.command(name="show_attendance_time", description="Show the current attendance window for the server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_attendance_time(self, interaction: discord.Interaction):
        """
        Show the current attendance window for the server.

        Example:
        /show_attendance_time
        """
        record = db.get_attendance_window(interaction.guild.id)
        if not record or record.get("day") is None:
            return await interaction.response.send_message("❌ Attendance time has not been set yet.", ephemeral=True)

        weekdays = {
            1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
            4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'
        }

        day = record["day"]
        start_h = record["start_hour"]
        start_m = record["start_minute"]
        end_h = record["end_hour"]
        end_m = record["end_minute"]

        display_day = weekdays.get(day, f"Day {day}")
        await interaction.response.send_message(
            f"📅 Attendance Time **{display_day}**: "
            f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}",
            ephemeral=True
        )

    @app_commands.command(name="delete_attendance_time", description="Delete the attendance time configuration.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_attendance_time(self, interaction: discord.Interaction):
        """
        Delete the attendance time configuration.

        Example:
        /delete_attendance_time
        """
        success = db.delete_attendance_window(interaction.guild.id)
        if not success:
            return await interaction.response.send_message("⚠️ No attendance Time found.", ephemeral=True)
        await interaction.response.send_message(f"🗑️ Attendance Time has been deleted.", ephemeral=True)
        
    
    @app_commands.command(name="set_timezone", description="Set the timezone offset for the guild. Range: -12 to +14")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_timezone(self, interaction: discord.Interaction, offset: str):
        """
        Set the timezone offset for the guild.
        Range: -12 to +14

        Example:
        /set_timezone +7
        /set_timezone -5
        /set_timezone 0
        """
        try:
            offset_int = int(offset.replace("+", ""))
            if not -12 <= offset_int <= 14:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Invalid timezone offset. Please enter a number between -12 and +14.", ephemeral=True)

        success = db.upsert_timezone(interaction.guild.id, offset_int)
        await interaction.response.send_message(f"✅ Timezone offset saved as UTC{offset_int:+}" if success else "⚠️ Failed to save timezone.", ephemeral=True)
    

    @app_commands.command(name="show_timezone", description="Show the timezone offset for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_timezone(self, interaction: discord.Interaction):
        """
        Show the timezone offset for the guild.
        
        Example:
        /show_timezone
        """
        data = db.get_timezone(interaction.guild.id)
        if data and data.get("time_delta") is not None:
            time_delta = data["time_delta"]
            await interaction.response.send_message(f"✅ Timezone offset saved as UTC{time_delta:+d}", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No timezone offset has been set for this server.", ephemeral=True)
            
            
    @app_commands.command(name="help", description="Show all available bot commands and setup instructions.")
    async def help(self, interaction: discord.Interaction):
        """
        Sends Google Form setup instructions and a formatted list of all available bot commands and their usage examples.
        This command is restricted to users with administrator or manage_guild permissions.

        Args:
            ctx (commands.Context): The context in which the command was invoked.
        """
        # Google Form setup instructions
        setup_instructions = (
            "```\n"
            "📜 How to Set Up Google Form for Attendance:\n"
            "1. Create a Google Form with one text field for the name.\n"
            "2. Get the form URL (either the full URL or the shortened forms.gle link).\n"
            "3. Use the `/add_gform_url` command with your form URL.\n"
            "4. The bot will automatically handle form submissions for attendance.\n"
            "```"
        )
        # Multi-line string containing all commands and usage examples for the bot.
        help_text = (
            "```\n"
            "📜 Available Commands:\n"
            "1. /add_gform_url <link>\n"
            "   Example: /add_gform_url https://forms.gle/abc123def456\n\n"
            "2. /delete_gform_url\n"
            "   Example: /delete_gform_url\n\n"
            "3. /list_gform_url\n"
            "   Example: /list_gform_url\n\n"
            "4. /hadir\n"
            "   Example: /hadir\n\n"
            "5. /set_attendance_time <day>/<HH:MM>-<HH:MM>\n"
            "   Example: /set_attendance_time Friday/08:00-09:00\n"
            "   Example: /set_attendance_time 5/14:00-15:00\n"
            "   If not set, attendance can be marked anytime.\n\n"
            "6. /show_attendance_time\n"
            "   Example: /show_attendance_time\n\n"
            "7. /delete_attendance_time\n"
            "   Example: /delete_attendance_time\n\n"
            "8. /set_timezone <delta>\n"
            "   Set the time difference from UTC. If not set, UTC+7 (Jakarta) is used.\n"
            "   Example: /set_timezone -5\n"
            "   Example: /set_timezone 0\n\n"
            "9. /show_timezone\n"
            "   Example: /show_timezone\n"
            "```"
        )
        # Send setup instructions first, then the help message
        await interaction.response.send_message(setup_instructions, ephemeral=True)
        await interaction.followup.send(help_text, ephemeral=True)
