import os
import logging
from uuid import uuid4
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional, Tuple

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)


class DatabaseHandler:
    _instance = None
    _supabase: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseHandler, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        try:
            cls._supabase = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
            logger.info("Supabase client initialized.")
        except Exception as e:
            logger.error(f"Supabase initialization failed: {e}")
            cls._supabase = None

    # Guild form URL operations
    def upsert_guild_form_url(self, guild_id: int, url: str) -> bool:
        try:
            result = self._supabase.table("guilds").select("*").eq("guild_id", guild_id).execute()
            exists = result.data and len(result.data) > 0

            upsert_data = {
                "guild_id": guild_id,
                "form_url": url
            }
            self._supabase.table("guilds").upsert(upsert_data).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase upsert error: {e}")
            return False

    def get_guild_form_url(self, guild_id: int) -> Optional[str]:
        try:
            result = self._supabase.table("guilds").select("form_url").eq("guild_id", guild_id).execute()
            if result.data:
                return result.data[0].get("form_url")
            return None
        except Exception as e:
            logger.error(f"Error getting guild form URL: {e}")
            return None
    
    def delete_guild_form_url(self, guild_id: int) -> bool:
        try:
            self._supabase.table("guilds").update({"form_url": None}).eq("guild_id", guild_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete guild form URL: {e}")
            return False

    # Attendance operations
    def get_attendance(self, guild_id: int, user_id: int, form_url: str):
        try:
            result = self._supabase.table("attendances").select("*")\
                .eq("guild_id", guild_id).eq("user_id", user_id).eq("form_url", form_url).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            return None

    def insert_attendance(self, guild_id: int, user_id: int, form_url: str) -> bool:
        try:
            now = datetime.now(timezone.utc).isoformat()
            data = {
                "guild_id": guild_id,
                "user_id": user_id,
                "timestamp": now,
                "form_url": form_url
            }
            self._supabase.table("attendances").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Insert attendance failed: {e}")
            return False

    def update_attendance(self, guild_id: int, user_id: int, form_url: str) -> bool:
        try:
            now = datetime.now(timezone.utc).isoformat()
            self._supabase.table("attendances")\
                .update({"timestamp": now, "form_url": form_url})\
                .eq("guild_id", guild_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Update attendance failed: {e}")
            return False

    def check_hadir(self, guild_id: int, user_id: int, form_url: str) -> bool:
        try:
            existing = self.get_attendance(guild_id, user_id, form_url)
            today = datetime.now(timezone.utc).date()

            if existing:
                attendance_date = datetime.fromisoformat(existing["timestamp"]).date()
                if attendance_date != today:
                    return self.update_attendance(guild_id, user_id, form_url)
                return False  # Already marked hadir today
            return self.insert_attendance(guild_id, user_id, form_url)
        except Exception as e:
            logger.error(f"Check hadir error: {e}")
            return False

