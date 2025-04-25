# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
import re
import asyncio
from typing import Optional, Any, List, Generator
import json
import httpx
import logging
import discord
from discord.ext import commands
from discord import app_commands
from utils.database import DatabaseHandler
from datetime import time
import os

db = DatabaseHandler()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleForm_Url_Handler:
    """Handles Google Form interactions including URL extraction, data fetching, and submissions."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client = httpx.AsyncClient()
        max_conc = int(os.getenv("GOOGLEFORM_MAX_CONCURRENCY", 10))
        self._semaphore = asyncio.Semaphore(max_conc)

    async def extract_url(self, form_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts both 'viewform' and 'formResponse' URLs from a Google Form link.
        """
        try:
            # Expand shortened URLs
            if "forms.gle" in form_url:
                async with self._semaphore:
                    response = await self._client.get(form_url, follow_redirects=True)
                err_msg = self._check_gform_response(response)
                if err_msg:
                    return None, err_msg
                form_url = str(response.url)

            # Extract form ID
            match = re.search(r'/d/e/([a-zA-Z0-9_-]+)(?:/|$)', form_url)
            if match:
                form_id = match.group(1)
                return f"https://docs.google.com/forms/d/e/{form_id}", None
            self.logger.warning("Couldn't find Google Form ID in URL")
            return None, "❌ Could not find a valid Google Form ID in the URL."
        except Exception as e:
            self.logger.error(f"URL extraction failed: {e}")
            return None, "❌ An unexpected error occurred while processing the form URL."

    def _check_gform_response(self, response: httpx.Response) -> Optional[str]:
        """
        Checks Google Form HTTP response for common errors (404, non-200) and returns a user-friendly message if needed.
        Returns None if the response is OK.
        """
        if response.status_code == 404:
            return "❌ The Google Form URL doesn't exist. Please check the link."
        if response.status_code != 200:
            logger.warning(f"Status code: {response.status_code}")
            return "⚠️ Couldn't access the Google Form. 🔒 This Google Form is private."
        return None

    async def submit_response(self, form_url: str, data: dict) -> bool:
        """
        Submits data to Google Form.
        """
        try:
            form_url += "/formResponse"
            async with self._semaphore:
                response = await self._client.post(form_url, data=data, timeout=10)
            return response.status_code == 200 or response.status_code == 302
        except httpx.RequestError as e:
            self.logger.error(f"Submission failed: {e}")
            return False

    async def fetch_form_data(self, form_url: str) -> tuple[dict | list | None, str | None]:
        """
        Fetches hidden configuration data from Google Form.
        """
        try:
            form_url += "/viewform"
            async with self._semaphore:
                response = await self._client.get(form_url, timeout=15)
            err_msg = self._check_gform_response(response)
            if err_msg:
                return None, err_msg
            match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', response.text, flags=re.S)
            if not match:
                # No form data found, likely private or restricted
                return None, "🔒 This Google Form is private, restricted, or not a valid attendance form."
            return json.loads(match.group(1)), None
        except Exception as e:
            self.logger.error(f"Data fetch failed: {e}")
            return None, "❌ An unexpected error occurred while fetching the form data."

    @staticmethod
    def get_entry_ids(data: dict[str, Any] | List[Any]) -> Generator[int, None, None]:
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
    async def cog_app_command_error(
        self, interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        # Permission error handler for all app commands in this Cog
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("⚠️ No Administrator permission", ephemeral=True)
            return
        # Optionally handle other errors or re-raise
        raise error

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.form_url_handler = GoogleForm_Url_Handler()

    @app_commands.command(name="add_gform_url", description="Add or update Google Form URL for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_gform_url(self, interaction: discord.Interaction, url: str) -> None:
        """
        Add/update Google Form URL for the guild.

        Example:
        /add_gform_url https://forms.gle/abc123def456
        """
        if not url.startswith(("https://docs.google.com/forms/", "https://forms.gle/")):
            await interaction.response.send_message("❌ That doesn't look like a Google Form link.", ephemeral=True)
            return
        else:
            extracted_url, error_reason = await self.form_url_handler.extract_url(url)
            if not extracted_url:
                await interaction.response.send_message(error_reason, ephemeral=True)
                return

            form_data, error_reason = await self.form_url_handler.fetch_form_data(extracted_url)
            if not form_data:
                await interaction.response.send_message(error_reason, ephemeral=True)
                return

            entry_ids = list(self.form_url_handler.get_entry_ids(form_data))
            entry_id_name = f"entry.{entry_ids[0]}"

        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        success = await db.upsert_guild_form_url(interaction.guild.id, extracted_url, entry_id_name)
        tz = await db.upsert_timezone(interaction.guild.id)
        await interaction.response.send_message(
            "✅ Google Form URL saved!" if success and tz else "⚠️ Failed to save Google Form URL!",
            ephemeral=True
        )

    @app_commands.command(name="delete_gform_url", description="Remove Google Form URL from the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_gform_url(self, interaction: discord.Interaction) -> None:
        """
        Remove Google Form URL from the guild.

        Example:
        /delete_gform_url
        """
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        form_url, entry_id_name = await db.get_guild_form_url_and_entry_id_name(interaction.guild.id)
        if not form_url:
            await interaction.response.send_message("⚠️ No URL set.", ephemeral=True)
            return

        success = await db.delete_guild_form_url_and_entry_id_name(interaction.guild.id)
        if success:
            message = "🗑️ URL deleted"
        else:
            message = "⚠️ Error"

        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="list_gform_url", description="List current Google Form URL for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_gform_url(self, interaction: discord.Interaction) -> None:
        """
        List current Google Form URL for the guild.

        Example:
        /list_gform_url
        """
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        form_url, entry_id_name = await db.get_guild_form_url_and_entry_id_name(interaction.guild.id)
        await interaction.response.send_message(
            f"Current URL: {form_url}/formResponse" if form_url else "No URL configured", ephemeral=True
        )

    @app_commands.command(
        name="set_attendance_time",
        description="Set the weekly attendance window. Format: <day>/<HH:MM>-<HH:MM>"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_attendance_time(self, interaction: discord.Interaction, schedule: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
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
            await interaction.response.send_message(
                "❌ Invalid format! Use `day/HH:MM-HH:MM`, e.g. `3/14:30-15:30`.", ephemeral=True
            )
            return

        # Extract and validate
        day_raw = m.group('day')
        h1, m1 = int(m.group('h1')), int(m.group('m1'))
        h2, m2 = int(m.group('h2')), int(m.group('m2'))

        if not (0 <= h1 < 24 and 0 <= m1 < 60 and 0 <= h2 < 24 and 0 <= m2 < 60):
            await interaction.response.send_message("❌ Hours must be 0-23 and minutes 0-59.", ephemeral=True)
            return

        # Ensure start < end
        start = time(hour=h1, minute=m1)
        end = time(hour=h2, minute=m2)
        if start >= end:
            await interaction.response.send_message("❌ End time must be after start time.", ephemeral=True)
            return

        # Normalize day
        weekdays = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 7
        }
        try:
            day = int(day_raw) if day_raw.isdigit() else weekdays[day_raw.lower()]
        except (ValueError, KeyError):
            await interaction.response.send_message(
                "❌ Day must be 1-7 or a weekday name (e.g. Monday).",
                ephemeral=True
            )
            return

        if not (1 <= day <= 7):
            await interaction.response.send_message("❌ Day number must be between 1 and 7.", ephemeral=True)
            return

        # Save to DB
        success = await db.upsert_attendance_window(
            guild_id=interaction.guild.id,
            day=day,
            start_hour=h1, start_minute=m1,
            end_hour=h2,   end_minute=m2
        )
        if not success:
            await interaction.response.send_message(
                "⚠️ Failed to save attendance Time. Please try again.",
                ephemeral=True
            )
            return

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
    async def show_attendance_time(self, interaction: discord.Interaction) -> None:
        """
        Show the current attendance window for the server.

        Example:
        /show_attendance_time
        """
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        record = await db.get_attendance_window(interaction.guild.id)
        if not record or record.get("day") is None:
            await interaction.response.send_message("❌ Attendance time has not been set yet.", ephemeral=True)
            return

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
    async def delete_attendance_time(self, interaction: discord.Interaction) -> None:
        """
        Delete the attendance time configuration.

        Example:
        /delete_attendance_time
        """
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        record = await db.get_attendance_window(interaction.guild.id)
        if not record:
            await interaction.response.send_message("⚠️ No attendance Time found.", ephemeral=True)
            return
        success = await db.delete_attendance_window(interaction.guild.id)
        if not success:
            await interaction.response.send_message("⚠️ Failed to delete attendance Time.", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Attendance Time has been deleted.", ephemeral=True)

    @app_commands.command(name="set_timezone", description="Set the timezone offset for the guild. Range: -12 to +14")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_timezone(self, interaction: discord.Interaction, offset: str) -> None:
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
            await interaction.response.send_message(
                "❌ Invalid timezone offset. Please enter a number between -12 and +14.",
                ephemeral=True
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        success = await db.upsert_timezone(interaction.guild.id, offset_int)
        await interaction.response.send_message(
            f"✅ Timezone offset saved as UTC{offset_int:+}" if success else "⚠️ Failed to save timezone.",
            ephemeral=True
        )

    @app_commands.command(name="show_timezone", description="Show the timezone offset for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_timezone(self, interaction: discord.Interaction) -> None:
        """
        Show the timezone offset for the guild.

        Example:
        /show_timezone
        """
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return
        data = await db.get_timezone(interaction.guild.id)
        if data and data.get("time_delta") is not None:
            time_delta = data["time_delta"]
            await interaction.response.send_message(f"✅ Timezone offset saved as UTC{time_delta:+d}", ephemeral=True)
        else:
            await interaction.response.send_message(
                "⚠️ No timezone offset has been set for this server.",
                ephemeral=True
            )

    @app_commands.command(name="help", description="Show all available bot commands and setup instructions.")
    async def help(self, interaction: discord.Interaction) -> None:
        """
        Sends Google Form setup instructions and
        a formatted list of all available bot commands and their usage examples.
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
