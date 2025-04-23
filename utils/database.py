# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
"""
Database handler for the Discord Attendance Bot.
Provides methods for interacting with the Supabase backend, including CRUD operations for guilds, attendance, and timezone settings.
Implements singleton pattern to ensure a single database client instance.
"""
import os
import logging
from uuid import uuid4
from datetime import datetime, timezone
from dotenv import load_dotenv
import httpx
from typing import Optional, Tuple
import asyncio

# Load environment variables from .env file
load_dotenv()

# Configure logging for database operations
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

class DatabaseHandler:
    """
    Singleton class for database operations using Supabase.
    Handles guild configuration, attendance records, and timezone management.
    """
    _instance = None
    _client: Optional[httpx.AsyncClient] = None
    _supabase_url: Optional[str] = None
    _supabase_key: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseHandler, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls._supabase_url = os.getenv("SUPABASE_URL")
        cls._supabase_key = os.getenv("SUPABASE_KEY")
        cls._client = httpx.AsyncClient()
        max_concurrency = int(os.getenv("SUPABASE_MAX_CONCURRENCY", 10))
        cls._semaphore = asyncio.Semaphore(max_concurrency)

    async def _request(self, method: str, path: str, **kwargs):
        if not self._supabase_url or not self._supabase_key:
            logger.error("Supabase credentials not set.")
            raise RuntimeError("Supabase credentials not set.")
        url = f"{self._supabase_url}/rest/v1/{path}"
        headers = kwargs.pop("headers", {})
        headers.update({
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        async with self._semaphore:
            try:
                resp = await self._client.request(method, url, headers=headers, **kwargs)
                resp.raise_for_status()
                # *Always* try to parse JSON; on empty or non-JSON body, return {}
                try:
                    return resp.json()
                except ValueError:
                    return {}
            except Exception as e:
                logger.error(f"Supabase async request error: {e}")
                return None
                
    # Guild form URL operations
    async def upsert_guild_form_url(self, guild_id: int, url: str) -> bool:
        """
        Upsert a guild's form URL in the database.
        """
        data = [{"guild_id": guild_id, "form_url": url}]
        headers = {"Prefer": "resolution=merge-duplicates"}
        params = {"on_conflict": "guild_id"}
        resp = await self._request("POST", "guilds", json=data, headers=headers, params=params)
        return resp is not None

    async def get_guild_form_url(self, guild_id: int) -> Optional[str]:
        resp = await self._request("GET", "guilds", params={"guild_id": f"eq.{guild_id}", "select": "form_url"})
        if resp and len(resp) > 0:
            return resp[0].get("form_url")
        return None
    
    async def delete_guild_form_url(self, guild_id: int) -> bool:
        data = {"form_url": None}
        resp = await self._request("PATCH", "guilds", json=data, params={"guild_id": f"eq.{guild_id}"})
        await self.delete_attendance_window(guild_id)
        return resp is not None

    # Attendance operations
    async def get_attendance(self, guild_id: int, user_id: int, form_url: str):
        resp = await self._request("GET", "attendances", params={
            "guild_id": f"eq.{guild_id}", "user_id": f"eq.{user_id}", "form_url": f"eq.{form_url}"})
        return resp[0] if resp else None

    async def insert_attendance(self, guild_id: int, user_id: int, form_url: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        data = [{
            "guild_id": guild_id,
            "user_id": user_id,
            "timestamp": now,
            "form_url": form_url
        }]
        headers = {"Prefer": "resolution=merge-duplicates"}
        params = {"on_conflict": "guild_id,user_id"}
        resp = await self._request("POST", "attendances", json=data, headers=headers, params=params)
        return resp is not None

    async def update_attendance(self, guild_id: int, user_id: int, form_url: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        headers = {"Prefer": "resolution=merge-duplicates"}
        params = {"on_conflict": "guild_id,user_id"}
        data = {"timestamp": now, "form_url": form_url}
        resp = await self._request("PATCH", "attendances", json=data, headers=headers, params=params)
        return resp is not None

    async def check_attendance(self, guild_id: int, user_id: int, form_url: str) -> bool:
        existing = await self.get_attendance(guild_id, user_id, form_url)
        today = datetime.now(timezone.utc).date()
        if existing:
            attendance_date = datetime.fromisoformat(existing["timestamp"]).date()
            if attendance_date != today:
                return await self.update_attendance(guild_id, user_id, form_url)
            return False  # Already marked attendance today
        return await self.insert_attendance(guild_id, user_id, form_url)
        
    
    async def upsert_attendance_window(self, guild_id: int, day: int, start_hour: int, start_minute: int, end_hour: int, end_minute: int) -> bool:
        data = [{
            "guild_id": guild_id,
            "day": day,
            "start_hour": start_hour,
            "start_minute": start_minute,
            "end_hour": end_hour,
            "end_minute": end_minute
        }]
        headers = {"Prefer": "resolution=merge-duplicates"}
        params = {"on_conflict": "guild_id"}
        resp = await self._request("POST", "guilds", json=data, headers=headers, params=params)
        return resp is not None
        
    async def get_attendance_window(self, guild_id: int):
        resp = await self._request("GET", "guilds", params={
            "guild_id": f"eq.{guild_id}",
            "select": "day,start_hour,start_minute,end_hour,end_minute"
        })
        return resp[0] if resp else None
        
    async def delete_attendance_window(self, guild_id: int):
        payload = {
            "day": None,
            "start_hour": None,
            "start_minute": None,
            "end_hour": None,
            "end_minute": None
        }
        resp = await self._request("PATCH", "guilds", json=payload, params={"guild_id": f"eq.{guild_id}"})
        return resp is not None
    
    async def upsert_timezone(self, guild_id: int, time_delta: int = 7) -> bool:
        data = [{"guild_id": guild_id, "time_delta": time_delta}]
        headers = {"Prefer": "resolution=merge-duplicates"}
        params = {"on_conflict": "guild_id"}
        resp = await self._request("POST", "Timezone", json=data, headers=headers, params=params)
        return resp is not None

    async def get_timezone(self, guild_id: int):
        resp = await self._request("GET", "Timezone", params={"guild_id": f"eq.{guild_id}", "select": "time_delta"})
        return resp[0] if resp else None